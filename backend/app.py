from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "audio_analysis/audio_input"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/align", methods=["POST"])
def align():
    if "vocals" not in request.files or "reference" not in request.files:
        return jsonify({"error": "Both vocals and reference must be uploaded"}), 400

    vocals = request.files["vocals"]
    reference = request.files["reference"]

    vocals_path = os.path.join(UPLOAD_FOLDER, vocals.filename)
    reference_path = os.path.join(UPLOAD_FOLDER, reference.filename)

    vocals.save(vocals_path)
    reference.save(reference_path)

    # Dummy response for now
    result = {
        "status": "success",
        "message": "Files uploaded and alignment processed",
        "vocals_file": vocals.filename,
        "reference_file": reference.filename,
        "alignment": "Dummy alignment result"
    }

    return jsonify(result), 200

if __name__ == "__main__":
    app.run(debug=True)
