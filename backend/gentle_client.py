import requests
import os

GENTLE_URL = "http://localhost:8765/transcriptions?async=false"

def align_audio_with_text(audio_path, transcript_path, output_json_path):
    """
    Sends audio and transcript to Gentle, saves JSON output.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio not found: {audio_path}")
    if not os.path.exists(transcript_path):
        raise FileNotFoundError(f"Transcript not found: {transcript_path}")

    with open(audio_path, 'rb') as audio_file, open(transcript_path, 'r') as text_file:
        files = {
            'audio': audio_file,
            'transcript': text_file
        }
        response = requests.post(GENTLE_URL, files=files)
        
    if response.status_code != 200:
        raise Exception(f"Gentle request failed: {response.status_code}")

    json_data = response.json()

    with open(output_json_path, 'w', encoding='utf-8') as f:
        import json
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    return json_data
