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


@app.route("/arrange", methods=["POST"])
def arrange():
    """
    Arrange segments using AI/LLM analysis based on content, energy, and flow.
    This creates an intelligent ordering of segments without reference timing.
    Used by legacy AIVocalArranger component.
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
            "arrangement_methods": ["ai", "reference_alignment"],
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


@app.route("/process_vocals", methods=["POST"])
def process_vocals():
    """
    Step 1: Process input vocals - segment and extract features for arrangement.
    This is the main vocals processing endpoint used by the current UI.
    """
    if "vocals" not in request.files:
        return jsonify({"error": "Vocals file is required."}), 400

    vocals = request.files["vocals"]
    vocals_path = os.path.join(UPLOAD_FOLDER, f"input_vocals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
    vocals.save(vocals_path)

    try:
        # Transcribe with WhisperX
        segments = transcribe_with_whisperx(vocals_path)

        # Extract enhanced features for AI analysis
        segment_features = extract_segment_features(vocals_path, segments)

        return jsonify({
            "segments": segment_features,
            "vocals_path": vocals_path,
            "total_segments": len(segment_features),
            "method": "whisperx_analysis"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/process_reference", methods=["POST"])
def process_reference_vocals():
    """
    Step 2: Process reference vocals - segment and extract features for timing/energy reference.
    This analyzes the reference track structure used by the current UI.
    """
    if "reference" not in request.files:
        return jsonify({"error": "Reference file is required."}), 400

    reference = request.files["reference"]
    reference_path = os.path.join(UPLOAD_FOLDER, f"reference_vocals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
    reference.save(reference_path)

    try:
        # Transcribe reference with WhisperX
        segments = transcribe_with_whisperx(reference_path)

        # Extract enhanced features for reference structure
        segment_features = extract_segment_features(reference_path, segments)

        return jsonify({
            "reference_segments": segment_features,
            "reference_path": reference_path,
            "total_segments": len(segment_features),
            "method": "reference_analysis"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/arrange_to_reference", methods=["POST"])
def arrange_to_reference():
    """
    Step 3: Use LLM to arrange input vocals segments to match reference track structure.
    Takes processed input segments and reference segments, uses AI to create optimal arrangement.
    This is the main arrangement endpoint used by the current UI.
    """
    data = request.get_json()
    if not data or "input_segments" not in data or "reference_segments" not in data:
        return jsonify({"error": "Both input_segments and reference_segments are required"}), 400

    input_segments = data["input_segments"]
    reference_segments = data["reference_segments"]
    input_vocals_path = data.get("input_vocals_path")
    genre_hint = data.get("genre")

    try:
        # Step 1: Get AI arrangement based on reference structure
        arrangement, confidence, analysis = ai_arranger.arrange_segments_to_reference(
            input_segments, reference_segments, genre_hint
        )

        # Step 2: Reorder input segments according to AI arrangement
        arranged_segments = [input_segments[i] for i in arrangement]

        # Step 3: Create aligned audio if input vocals path provided
        aligned_audio_path = None
        if input_vocals_path:
            output_filename = f"arranged_to_reference_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
            output_path = os.path.join(ALIGNED_FOLDER, output_filename)

            # Create arranged audio based on new segment order
            aligned_audio_path = reference_aligner.create_arranged_audio(
                input_vocals_path, arranged_segments, output_path
            )

        return jsonify({
            "arranged_segments": arranged_segments,
            "original_arrangement": arrangement,
            "ai_analysis": {
                "confidence": confidence,
                "reasoning": analysis.get("reasoning", ""),
                "method": "llm_reference_arrangement"
            },
            "reference_structure": {
                "total_reference_segments": len(reference_segments),
                "matched_segments": len([s for s in arranged_segments if s]),
                "energy_progression": [s.get("energy", 0) for s in reference_segments],
                "timing_structure": [s.get("duration", 0) for s in reference_segments]
            },
            "arranged_audio_url": f"/aligned/{output_filename}" if aligned_audio_path else None,
            "method": "ai_reference_arrangement"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
