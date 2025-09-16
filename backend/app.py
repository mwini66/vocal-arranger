import json
import os
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from audio_analysis.arrangement_ml import arrange_ml
from audio_analysis.arrangement_rule import arrange_rule
from audio_analysis.ensemble_arrangement import arrange_ensemble
from audio_analysis.extract_features import extract_segment_features
from audio_analysis.llm_utils import arrange_with_llm
from audio_analysis.whisperx_utils import transcribe_with_whisperx
from ml.train_arrangement_ml import ArrangementMLTrainer

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads/audio"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

FEEDBACK_FILE = os.path.join("data", "arrangement_feedback.json")
os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)
if not os.path.exists(FEEDBACK_FILE):
    with open(FEEDBACK_FILE, "w") as f:
        json.dump([], f)

# Initialize ML trainer
ml_trainer = ArrangementMLTrainer()


@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/arrange", methods=["POST"])
def arrange():
    """
    Arrange segments using rule-based or ML-based logic.
    Expects JSON payload:
    {
        "segments": [ {"start":..., "end":..., "text":..., "energy":..., "pitch":..., "duration":..., "pause":..., "keywords":...}, ... ],
        "mode": "rule" or "ml"
    }
    Returns:
        {
            "arrangement": [ordered indices],
            "score": float,
            "mode": str
        }
    """
    data = request.get_json()
    if not data or "segments" not in data or "mode" not in data:
        return jsonify({"error": "Missing segments or mode in request"}), 400
    segments = data["segments"]
    mode = data["mode"]
    if mode == "rule":
        ordered_indices, score = arrange_rule(segments)
    elif mode == "ml":
        ordered_indices, score = arrange_ml(segments)
    else:
        return jsonify({"error": "Invalid mode. Use 'rule' or 'ml'"}), 400
    return jsonify({
        "arrangement": ordered_indices,
        "score": score,
        "mode": mode
    }), 200


@app.route("/arrangement/feedback", methods=["POST"])
def arrangement_feedback():
    """
    Accepts user feedback for an arrangement.
    Expects JSON payload:
    {
        "audio_id": str,
        "arrangement_type": "rule" or "ml",
        "ordered_indices": [...],
        "score": float,
        "user_rating": int (e.g. 1-5),
        "timestamp": str (optional)
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing feedback data"}), 400
    data["timestamp"] = data.get("timestamp") or datetime.utcnow().isoformat()
    # Append feedback to file
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


@app.route("/segment", methods=["POST"])
def segment():
    """
    Segment vocals using WhisperX and extract features for each segment.
    Accepts a vocals file upload (multipart/form-data).
    Returns: { "segments": [ {start, end, text, energy, pitch, duration, pause, keywords}, ... ] }
    """
    if "vocals" not in request.files:
        return jsonify({"error": "Vocals file is required."}), 400
    vocals = request.files["vocals"]
    vocals_path = os.path.join(UPLOAD_FOLDER, vocals.filename)
    vocals.save(vocals_path)
    try:
        segments = transcribe_with_whisperx(vocals_path)
        segment_features = extract_segment_features(vocals_path, segments)
        return jsonify({"segments": segment_features}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/arrange_ml", methods=["POST"])
def arrange_ml_endpoint():
    """
    Arrange segments using trained ML model.
    Expects JSON payload: { "segments": [...] }
    Returns: { "arrangement": [...], "score": float, "method": "trained_ml" }
    """
    data = request.get_json()
    if not data or "segments" not in data:
        return jsonify({"error": "Missing segments in request"}), 400

    segments = data["segments"]

    try:
        arrangement, score = ml_trainer.arrange_segments_ml(segments)
        return jsonify({
            "arrangement": arrangement,
            "score": score,
            "method": "trained_ml"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/arrange_llm", methods=["POST"])
def arrange_llm_endpoint():
    """
    Arrange segments using local LLM (Ollama).
    Expects JSON payload: { "segments": [...] }
    Returns: { "arrangement": [...], "score": float, "method": "llm" }
    """
    data = request.get_json()
    if not data or "segments" not in data:
        return jsonify({"error": "Missing segments in request"}), 400

    segments = data["segments"]

    try:
        arrangement, score = arrange_with_llm(segments)
        return jsonify({
            "arrangement": arrangement,
            "score": score,
            "method": "llm"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/arrange_ensemble", methods=["POST"])
def arrange_ensemble_endpoint():
    """
    Arrange segments using ensemble of all methods.
    Expects JSON payload: {
        "segments": [...],
        "methods": ["rule", "ml", "llm", "trained_ml"] (optional)
    }
    Returns: {
        "best_arrangement": [...],
        "confidence": float,
        "all_results": {...}
    }
    """
    data = request.get_json()
    if not data or "segments" not in data:
        return jsonify({"error": "Missing segments in request"}), 400

    segments = data["segments"]
    methods = data.get("methods", ["rule", "ml", "llm", "trained_ml"])

    try:
        best_arrangement, confidence, all_results = arrange_ensemble(segments, methods)
        return jsonify({
            "best_arrangement": best_arrangement,
            "confidence": confidence,
            "all_results": all_results,
            "method": "ensemble"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/model_status", methods=["GET"])
def model_status():
    """
    Get status of available models and services.
    Returns: { "models": {...}, "services": {...} }
    """
    try:
        from audio_analysis.llm_utils import get_ollama_client

        status = {
            "models": {
                "rule_based": True,
                "ml_weighted": True,
                "trained_ml": False,
                "llm": False
            },
            "services": {
                "ollama": False,
                "whisper": True,
                "feature_extraction": True
            }
        }

        # Check if trained ML model exists
        trained_model = ml_trainer.load_model("ranking")
        status["models"]["trained_ml"] = trained_model is not None

        # Check Ollama availability
        try:
            ollama_client = get_ollama_client()
            status["models"]["llm"] = ollama_client.is_available()
            status["services"]["ollama"] = ollama_client.is_available()
        except Exception:
            pass

        return jsonify(status), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
