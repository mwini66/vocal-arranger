import argparse
import os
import json
import librosa
import numpy as np

def extract_features(audio_path, output_path):
    """
    Extracts tempo, key, energy, pitch, and segment features from audio
    """
    y, sr = librosa.load(audio_path)

    # Tempo
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

    # Chroma (key)
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    key_strengths = chroma.mean(axis=1).tolist()

    # Energy (RMS)
    rms = librosa.feature.rms(y=y)[0]
    avg_energy = float(np.mean(rms))
    energy_profile = rms.tolist()

    # Pitch extraction (using librosa's piptrack)
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
    pitch_values = pitches[magnitudes > np.median(magnitudes)]
    avg_pitch = float(np.mean(pitch_values)) if len(pitch_values) > 0 else 0.0

    # Structural segmentation (onset detection)
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)
    segments = onset_times.tolist()

    result = {
        "audio": audio_path,
        "tempo_bpm": float(tempo),
        "chroma": key_strengths[:12],  # Simplified key representation
        "avg_energy": avg_energy,
        "energy_profile": energy_profile,
        "avg_pitch": avg_pitch,
        "segments_sec": segments
    }

    with open(output_path, "w") as f:
        json.dump(result, f, indent=4)

    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract audio features.")
    parser.add_argument("--audio", type=str, help="Path to input audio file.")
    parser.add_argument("--output", type=str, help="Path to output JSON file.")
    parser.add_argument("--test", action="store_true", help="Run test extraction on sample audio.")
    args = parser.parse_args()

    if args.test:
        # Use a sample file from audio_input
        sample_path = os.path.join(os.path.dirname(__file__), "audio_input", "reference.wav")
        output_path = os.path.join(os.path.dirname(__file__), "feature_output", "features.json")
        print(f"Extracting features from {sample_path}...")
        result = extract_features(sample_path, output_path)
        print(json.dumps(result, indent=2))
    elif args.audio and args.output:
        result = extract_features(args.audio, args.output)
        print(f"Features saved to {args.output}")
    else:
        parser.print_help()
