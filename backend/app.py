import json
import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from audio_analysis.arrangement import AIVocalArranger
from audio_analysis.extract_features import extract_segment_features
from audio_analysis.whisperx_utils import transcribe_with_whisperx
from audio_analysis.reference_alignment import ReferenceAligner

load_dotenv()
app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads/audio"
ALIGNED_FOLDER = "uploads/aligned"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ALIGNED_FOLDER, exist_ok=True)

FEEDBACK_FILE = os.path.join("data", "arrangement_feedback.json")
os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)
if not os.path.exists(FEEDBACK_FILE):
    with open(FEEDBACK_FILE, "w") as f:
        json.dump([], f)

# Initialize AI vocal arranger and reference aligner
ai_arranger = AIVocalArranger()
reference_aligner = ReferenceAligner()


@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/aligned/<filename>')
def serve_aligned_audio(filename):
    return send_from_directory(ALIGNED_FOLDER, filename)


@app.route("/segment", methods=["POST"])
def segment():
    """
    Segment vocals using WhisperX and extract enhanced features for each segment.
    Accepts a vocals file upload (multipart/form-data).
    Returns: { "segments": [ {enhanced segment features}, ... ] }
    """
    if "vocals" not in request.files:
        return jsonify({"error": "Vocals file is required."}), 400

    vocals = request.files["vocals"]
    vocals_path = os.path.join(UPLOAD_FOLDER, vocals.filename)
    vocals.save(vocals_path)

    try:
        # Transcribe with WhisperX
        segments = transcribe_with_whisperx(vocals_path)

        # Extract enhanced features for AI analysis
        segment_features = extract_segment_features(vocals_path, segments)

        return jsonify({"segments": segment_features}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/arrange", methods=["POST"])
def arrange():
    """
    Arrange segments using AI/LLM analysis based on content, energy, and flow.
    This creates an intelligent ordering of segments without reference timing.
    """
    data = request.get_json()
    if not data or "segments" not in data:
        return jsonify({"error": "Missing segments in request"}), 400

    segments = data["segments"]
    target_structure = data.get("structure", "auto")
    genre_hint = data.get("genre")

    try:
        arrangement, confidence, analysis = ai_arranger.arrange_segments(
            segments, target_structure, genre_hint
        )

        return jsonify({
            "arrangement": arrangement,
            "confidence": confidence,
            "method": "ai_arrangement",
            "analysis": analysis,
            "structure": analysis.get('sections', {})
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/arrange/llm_only", methods=["POST"])
def arrange_llm_only():
    """
    Arrange segments using AI/LLM analysis (same as /arrange now).
    Expects JSON payload: { "segments": [...], "genre": "..." (optional) }
    """
    data = request.get_json()
    if not data or "segments" not in data:
        return jsonify({"error": "Missing segments in request"}), 400

    segments = data["segments"]
    genre_hint = data.get("genre")

    try:
        arrangement, confidence, analysis = ai_arranger._get_llm_arrangement(segments, genre_hint)

        return jsonify({
            "arrangement": arrangement,
            "confidence": confidence,
            "method": "ai_llm",
            "analysis": analysis,
            "genre": genre_hint
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/arrangement/compare", methods=["POST"])
def compare_arrangements():
    """
    Compare different arrangement approaches (now just AI with different parameters).
    Expects JSON payload: {
        "segments": [...],
        "methods": ["ai", "ai_pop", "ai_hiphop"] (optional),
        "genre": "..." (optional)
    }
    """
    data = request.get_json()
    if not data or "segments" not in data:
        return jsonify({"error": "Missing segments in request"}), 400

    segments = data["segments"]
    methods = data.get("methods", ["ai"])
    genre_hint = data.get("genre")

    try:
        results = {}

        # Test AI with different genre hints
        if "ai" in methods or "hybrid" in methods:  # Keep "hybrid" for backward compatibility
            try:
                arr, conf, analysis = ai_arranger.arrange_segments(segments, "auto", genre_hint)
                results["ai"] = {
                    "arrangement": arr,
                    "confidence": conf,
                    "analysis": analysis
                }
            except Exception as e:
                results["ai"] = {"error": str(e)}

        if "ai_pop" in methods:
            try:
                arr, conf, analysis = ai_arranger.arrange_segments(segments, "standard_pop", "pop")
                results["ai_pop"] = {
                    "arrangement": arr,
                    "confidence": conf,
                    "analysis": analysis
                }
            except Exception as e:
                results["ai_pop"] = {"error": str(e)}

        if "ai_hiphop" in methods:
            try:
                arr, conf, analysis = ai_arranger.arrange_segments(segments, "hip_hop", "hip-hop")
                results["ai_hiphop"] = {
                    "arrangement": arr,
                    "confidence": conf,
                    "analysis": analysis
                }
            except Exception as e:
                results["ai_hiphop"] = {"error": str(e)}

        # Legacy support for "llm_only"
        if "llm_only" in methods:
            try:
                arr, conf, analysis = ai_arranger._get_llm_arrangement(segments, genre_hint)
                results["llm_only"] = {
                    "arrangement": arr,
                    "confidence": conf,
                    "analysis": analysis
                }
            except Exception as e:
                results["llm_only"] = {"error": str(e)}

        # Calculate similarity between methods
        similarities = {}
        arrangements = {k: v.get("arrangement", []) for k, v in results.items() if "arrangement" in v}

        for method1 in arrangements:
            for method2 in arrangements:
                if method1 != method2:
                    key = f"{method1}_vs_{method2}"
                    if key not in similarities:
                        sim = _calculate_arrangement_similarity(
                            arrangements[method1], arrangements[method2]
                        )
                        similarities[key] = sim

        return jsonify({
            "results": results,
            "similarities": similarities,
            "methods_tested": methods
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _calculate_arrangement_similarity(arr1, arr2):
    """Calculate similarity between two arrangements."""
    if len(arr1) != len(arr2):
        return 0.0
    similarity = sum(1 for i, j in zip(arr1, arr2) if i == j) / len(arr1)
    return similarity


@app.route("/arrangement/feedback", methods=["POST"])
def arrangement_feedback():
    """
    Accepts user feedback for an arrangement.
    Expects JSON payload:
    {
        "audio_id": str,
        "arrangement_type": "hybrid" | "llm_only",
        "ordered_indices": [...],
        "score": float,
        "user_rating": int (1-5),
        "segments": [...] (optional),
        "timestamp": str (optional)
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing feedback data"}), 400

    data["timestamp"] = data.get("timestamp") or datetime.utcnow().isoformat()

    try:
        with open(FEEDBACK_FILE, "r+") as f:
            feedback_list = json.load(f)
            feedback_list.append(data)
            f.seek(0)
            json.dump(feedback_list, f, indent=2)
            f.truncate()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/model_status", methods=["GET"])
def model_status():
    """
    Get status of available AI services for vocal arrangement and reference alignment.
    Returns: { "models": {...}, "services": {...}, "arrangement_methods": [...] }
    """
    try:
        status = {
            "models": {
                "ai_llm": False,
                "openrouter": False
            },
            "services": {
                "openrouter": False,
                "whisper": True,
                "feature_extraction": True,
                "reference_alignment": True
            },
            "arrangement_methods": ["ai", "ai_pop", "ai_hiphop", "reference_alignment"],
            "structure_templates": list(ai_arranger.structure_templates.keys()),
            "alignment_features": {
                "reference_processing": True,
                "text_similarity_matching": True,
                "audio_time_stretching": True,
                "segment_alignment": True
            }
        }

        # Check OpenRouter AI availability
        try:
            ai_available = ai_arranger.llm_client.is_available()
            status["models"]["ai_llm"] = ai_available
            status["models"]["openrouter"] = ai_available
            status["services"]["openrouter"] = ai_available
        except Exception:
            pass

        return jsonify(status), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/align/reference", methods=["POST"])
def align_reference():
    """
    Align vocals to a reference track.
    Expects JSON payload: {
        "segments": [...],
        "reference_track": "path/to/reference.mp3",
        "alignment_method": "dynamic" | "static" (optional)
    }
    Returns: {
        "alignment": [...],
        "method": "reference_alignment",
        "parameters": {...}
    }
    """
    data = request.get_json()
    if not data or "segments" not in data or "reference_track" not in data:
        return jsonify({"error": "Missing segments or reference track in request"}), 400

    segments = data["segments"]
    reference_track = data["reference_track"]
    alignment_method = data.get("alignment_method", "dynamic")

    try:
        # Perform alignment
        alignment = reference_aligner.align_segments_to_reference(
            segments, reference_track, method=alignment_method
        )

        return jsonify({
            "alignment": alignment,
            "method": "reference_alignment",
            "parameters": {
                "alignment_method": alignment_method
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/align/status", methods=["GET"])
def alignment_status():
    """
    Get status of the alignment process for a specific job.
    Expects query parameter: job_id
    Returns: { "job_id": str, "status": "pending" | "processing" | "completed" | "error", ... }
    """
    job_id = request.args.get("job_id")
    if not job_id:
        return jsonify({"error": "Missing job_id parameter"}), 400

    try:
        status = reference_aligner.get_alignment_status(job_id)
        return jsonify(status), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/reference/process", methods=["POST"])
def process_reference():
    """
    Process reference track to extract segments and features.
    Accepts a reference track file upload (multipart/form-data).
    Returns: { "reference_segments": [ {enhanced segment features}, ... ] }
    """
    if "reference" not in request.files:
        return jsonify({"error": "Reference track file is required."}), 400

    reference = request.files["reference"]
    reference_path = os.path.join(UPLOAD_FOLDER, f"ref_{reference.filename}")
    reference.save(reference_path)

    try:
        # Process reference track
        reference_segments = reference_aligner.process_reference_track(reference_path)

        return jsonify({
            "reference_segments": reference_segments,
            "reference_path": reference_path,
            "total_segments": len(reference_segments)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/align/to_reference", methods=["POST"])
def align_to_reference():
    """
    Align user vocal segments to match a reference track's timing and sequence.
    This preserves audio quality by placing segments without time-stretching.
    """
    if "vocals" not in request.files or "reference" not in request.files:
        return jsonify({"error": "Both vocals and reference files are required"}), 400

    vocals = request.files["vocals"]
    reference = request.files["reference"]

    vocals_path = os.path.join(UPLOAD_FOLDER, f"user_vocals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
    reference_path = os.path.join(UPLOAD_FOLDER, f"reference_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")

    vocals.save(vocals_path)
    reference.save(reference_path)

    try:
        # Process reference track to get timing segments
        reference_segments = reference_aligner.process_reference_track(reference_path)

        # Process user vocals to get segments with features
        user_segments = transcribe_with_whisperx(vocals_path)
        user_features = extract_segment_features(vocals_path, user_segments)

        # Align user segments to reference timing
        aligned_segments, alignment_info = reference_aligner.align_to_reference(
            user_features, reference_segments
        )

        # Create aligned audio file
        output_filename = f"aligned_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        output_path = os.path.join(ALIGNED_FOLDER, output_filename)

        aligned_audio_path = reference_aligner.create_aligned_audio(
            vocals_path, aligned_segments, output_path
        )

        return jsonify({
            "aligned_segments": aligned_segments,
            "alignment_info": alignment_info,
            "aligned_audio_url": f"/aligned/{output_filename}",
            "method": "reference_alignment"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/arrange_and_align", methods=["POST"])
def arrange_and_align():
    """
    Complete workflow: AI arrange segments, then align to reference track timing.
    This combines intelligent arrangement with reference-based timing.
    """
    if "vocals" not in request.files or "reference" not in request.files:
        return jsonify({"error": "Both vocals and reference files are required"}), 400

    vocals = request.files["vocals"]
    reference = request.files["reference"]
    genre_hint = request.form.get("genre")

    vocals_path = os.path.join(UPLOAD_FOLDER, f"user_vocals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
    reference_path = os.path.join(UPLOAD_FOLDER, f"reference_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")

    vocals.save(vocals_path)
    reference.save(reference_path)

    try:
        # Step 1: Segment and analyze user vocals
        user_segments = transcribe_with_whisperx(vocals_path)
        user_features = extract_segment_features(vocals_path, user_segments)

        # Step 2: AI arrange segments based on content/energy
        arrangement, confidence, analysis = ai_arranger.arrange_segments(
            user_features, "auto", genre_hint
        )

        # Reorder user segments according to AI arrangement
        arranged_segments = [user_features[i] for i in arrangement]

        # Step 3: Process reference track
        reference_segments = reference_aligner.process_reference_track(reference_path)

        # Step 4: Align arranged segments to reference timing
        aligned_segments, alignment_info = reference_aligner.align_to_reference(
            arranged_segments, reference_segments
        )

        # Step 5: Create final aligned audio
        output_filename = f"arranged_aligned_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        output_path = os.path.join(ALIGNED_FOLDER, output_filename)

        # Create temporary audio with arranged segments for alignment
        temp_arranged_path = os.path.join(UPLOAD_FOLDER, f"temp_arranged_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")

        # For now, use original vocals path - in production you'd create arranged audio first
        aligned_audio_path = reference_aligner.create_aligned_audio(
            vocals_path, aligned_segments, output_path
        )

        return jsonify({
            "original_segments": user_features,
            "ai_arrangement": {
                "arrangement": arrangement,
                "confidence": confidence,
                "analysis": analysis
            },
            "aligned_segments": aligned_segments,
            "alignment_info": alignment_info,
            "aligned_audio_url": f"/aligned/{output_filename}",
            "method": "ai_arrangement_then_reference_alignment"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/process_with_reference", methods=["POST"])
def process_with_reference():
    """
    Complete workflow: Segment vocals, AI arrange, then align to reference track.
    This is the main endpoint called by the frontend's "Process & Align to Reference" button.
    """
    if "vocals" not in request.files or "reference" not in request.files:
        return jsonify({"error": "Both vocals and reference files are required"}), 400

    vocals = request.files["vocals"]
    reference = request.files["reference"]
    genre_hint = request.form.get("genre")

    vocals_path = os.path.join(UPLOAD_FOLDER, f"user_vocals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
    reference_path = os.path.join(UPLOAD_FOLDER, f"reference_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")

    vocals.save(vocals_path)
    reference.save(reference_path)

    try:
        # Step 1: Segment and analyze user vocals
        user_segments = transcribe_with_whisperx(vocals_path)
        user_features = extract_segment_features(vocals_path, user_segments)

        # Step 2: Process reference track
        reference_segments = reference_aligner.process_reference_track(reference_path)

        # Step 3: AI arrange user segments based on content/energy
        arrangement, confidence, analysis = ai_arranger.arrange_segments(
            user_features, "auto", genre_hint
        )

        # Reorder user segments according to AI arrangement
        arranged_segments = [user_features[i] for i in arrangement]

        # Step 4: Align arranged segments to reference timing
        aligned_segments, alignment_info = reference_aligner.align_to_reference(
            arranged_segments, reference_segments
        )

        # Step 5: Create final aligned audio
        output_filename = f"processed_aligned_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        output_path = os.path.join(ALIGNED_FOLDER, output_filename)

        aligned_audio_path = reference_aligner.create_aligned_audio(
            vocals_path, aligned_segments, output_path
        )

        return jsonify({
            "user_segments": user_features,
            "reference_segments": reference_segments,
            "ai_arrangement": {
                "arrangement": arrangement,
                "confidence": confidence,
                "analysis": analysis
            },
            "aligned_segments": aligned_segments,
            "alignment_info": alignment_info,
            "aligned_audio_path": f"/aligned/{output_filename}",
            "method": "complete_workflow"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
