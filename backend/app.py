from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from audio_analysis.extract_features import extract_features
from audio_analysis.whisperx_utils import transcribe_with_whisperx
from pydub import AudioSegment

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "audio_analysis/audio_input"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

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

    # Feature extraction for both files
    vocals_features_path = vocals_path + "_features.json"
    reference_features_path = reference_path + "_features.json"
    vocals_features = extract_features(vocals_path, vocals_features_path)
    reference_features = extract_features(reference_path, reference_features_path)

    # WhisperX transcription for both files
    vocals_segments = transcribe_with_whisperx(vocals_path)
    reference_segments = transcribe_with_whisperx(reference_path)

    # Alignment logic: match words and rearrange live recording
    live_audio = AudioSegment.from_file(vocals_path)
    arranged = AudioSegment.empty()
    timeline = []
    match_count = 0
    for ref_word in reference_segments:
        match = next(
            (
                w for w in vocals_segments
                if (w.get("word") or w.get("text", "")).strip().lower()
                == (ref_word.get("word") or ref_word.get("text", "")).strip().lower()
            ),
            None
        )
        if match:
            match_count += 1
            start_ms = int(match["start"] * 1000)
            end_ms = int(match["end"] * 1000)
            segment = live_audio[start_ms:end_ms]
            arranged += segment
            timeline.append({"word": ref_word.get("word") or ref_word.get("text", ""), "start": ref_word["start"], "end": ref_word["end"]})
    if match_count == 0:
        print(f"[ERROR] No matching segments found between vocals and reference.")
        return jsonify({"error": "No matching segments found between vocals and reference. Please check your input files."}), 400
    arranged_path = vocals_path.replace(".wav", "_arranged.wav")
    print(f"[DEBUG] Attempting to export arranged audio to: {arranged_path}")
    try:
        arranged.export(arranged_path, format="wav")
        print(f"[DEBUG] Exported arranged audio to: {arranged_path}")
        if not os.path.exists(arranged_path) or os.path.getsize(arranged_path) == 0:
            print(f"[ERROR] Arranged audio file not created or is empty: {arranged_path}")
            return jsonify({"error": "Failed to create arranged audio file."}), 500
        print(f"[INFO] Arranged audio file created: {arranged_path} ({os.path.getsize(arranged_path)} bytes)")
    except Exception as e:
        print(f"[ERROR] Exception during arranged audio export: {e}")
        return jsonify({"error": f"Exception during audio export: {str(e)}"}), 500
    arranged_filename = os.path.basename(arranged_path)
    arranged_url = request.host_url.rstrip('/') + '/audio/' + arranged_filename
    result = {
        "status": "success",
        "message": "Files uploaded, features extracted, and vocals arranged",
        "vocals_file": vocals.filename,
        "reference_file": reference.filename,
        "vocals_features": vocals_features,
        "reference_features": reference_features,
        "vocals_segments": vocals_segments,
        "reference_segments": reference_segments,
        "timeline": timeline,
        "arranged_audio_url": arranged_url
    }

    return jsonify(result), 200

def rearrange_audio(vocals_path, vocals_segments, reference_order, output_path):
    """
    Rearranges the vocals audio according to the reference order using alignment segments.
    vocals_path: path to vocals audio file
    vocals_segments: list of dicts with 'word', 'start', 'end' (seconds)
    reference_order: list of words (in desired order)
    output_path: path to save rearranged audio
    """
    live_audio = AudioSegment.from_file(vocals_path)
    arranged = AudioSegment.empty()
    timeline = []
    for ref_word in reference_order:
        match = next(
            (
                w for w in vocals_segments
                if (w.get("word") or w.get("text", "")).strip().lower() == ref_word.strip().lower()
            ),
            None
        )
        if match:
            start_ms = int(match["start"] * 1000)
            end_ms = int(match["end"] * 1000)
            segment = live_audio[start_ms:end_ms]
            arranged += segment
            timeline.append({"word": ref_word, "start": match["start"], "end": match["end"]})
    arranged.export(output_path, format="wav")
    return output_path, timeline

@app.route("/rearrange", methods=["POST"])
def rearrange():
    # Accept vocals file (or path) and reference order (list of words)
    vocals_file = request.files.get("vocals")
    vocals_path = request.form.get("vocals_path")
    reference_order = request.form.get("reference_order")
    vocals_segments = request.form.get("vocals_segments")

    # Parse reference_order and vocals_segments if provided as JSON strings
    import json
    if reference_order:
        reference_order = json.loads(reference_order)
    else:
        return jsonify({"error": "reference_order is required"}), 400
    if vocals_segments:
        vocals_segments = json.loads(vocals_segments)
    else:
        # If not provided, require vocals file and run transcription
        if not vocals_file and not vocals_path:
            return jsonify({"error": "vocals file or path required"}), 400
        if vocals_file:
            vocals_path = os.path.join(UPLOAD_FOLDER, vocals_file.filename)
            vocals_file.save(vocals_path)
        vocals_segments = transcribe_with_whisperx(vocals_path)

    # Rearrange audio
    output_path = vocals_path.replace(".wav", "_rearranged.wav")
    arranged_path, timeline = rearrange_audio(vocals_path, vocals_segments, reference_order, output_path)

    return jsonify({
        "status": "success",
        "arranged_audio_url": arranged_path,
        "timeline": timeline
    }), 200

if __name__ == "__main__":
    app.run(debug=True)
