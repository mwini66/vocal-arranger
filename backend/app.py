import json
import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from audio_analysis.arrangement import AIVocalArranger
from audio_analysis.extract_features import extract_segment_features
from audio_analysis.whisperx_utils import transcribe_with_whisperx

load_dotenv()
app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads/audio"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

FEEDBACK_FILE = os.path.join("data", "arrangement_feedback.json")
os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)
if not os.path.exists(FEEDBACK_FILE):
    with open(FEEDBACK_FILE, "w") as f:
        json.dump([], f)

# Initialize AI vocal arranger
ai_arranger = AIVocalArranger()


@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


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
    Arrange segments using AI/LLM analysis.
    Expects JSON payload: {
        "segments": [...],
        "structure": "auto" | "standard_pop" | "hip_hop" | "rnb" | "simple" (optional),
        "genre": "hip-hop" | "rnb" | "pop" | etc (optional)
    }
    Returns: {
        "arrangement": [...],
        "confidence": float,
        "method": "ai_llm",
        "analysis": {...}
    }
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
            "method": analysis.get("method", "ai_llm"),
            "analysis": analysis,
            "structure": target_structure,
            "genre": genre_hint
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
    Get status of available AI services for vocal arrangement.
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
                "feature_extraction": True
            },
            "arrangement_methods": ["ai", "ai_pop", "ai_hiphop"],
            "structure_templates": list(ai_arranger.structure_templates.keys())
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


if __name__ == "__main__":
    app.run(debug=True)
