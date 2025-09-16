"""
Test script for arrangement logic and API.
"""
import requests
import os
from audio_analysis.whisperx_utils import transcribe_with_whisperx
from audio_analysis.extract_features import extract_segment_features

AUDIO_PATH = os.path.join(os.path.dirname(__file__), "audio_input", "reference.wav")
API_URL = "http://127.0.0.1:5000/arrange"

if __name__ == "__main__":
    print("Transcribing audio with WhisperX...")
    segments = transcribe_with_whisperx(AUDIO_PATH)
    print(f"Got {len(segments)} segments.")
    print("Extracting segment features...")
    segment_features = extract_segment_features(AUDIO_PATH, segments)
    print(f"Extracted features for {len(segment_features)} segments.")
    for mode in ["rule", "ml"]:
        print(f"\nTesting arrangement mode: {mode}")
        response = requests.post(API_URL, json={"segments": segment_features, "mode": mode})
        if response.status_code == 200:
            result = response.json()
            print(f"Arrangement order: {result['arrangement']}")
            print(f"Arrangement score: {result['score']}")
        else:
            print(f"Error: {response.text}")

