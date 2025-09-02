import json
import librosa

def extract_features(audio_path, output_path):
    """
    Extracts tempo and key features from audio
    """
    y, sr = librosa.load(audio_path)

    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    key_strengths = chroma.mean(axis=1).tolist()

    result = {
        "audio": audio_path,
        "tempo_bpm": float(tempo),
        "chroma": key_strengths[:12]  # Simplified key representation
    }

    with open(output_path, "w") as f:
        json.dump(result, f, indent=4)

    return result
