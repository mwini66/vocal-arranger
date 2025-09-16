import argparse
import json
import os
import ssl

import librosa
import numpy as np

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

import nltk

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', quiet=True)


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


def extract_segment_features(audio_path, segments):
    """
    For each segment, extract energy, pitch, duration, pause, keywords.
    Args:
        audio_path: path to audio file
        segments: list of dicts with 'start', 'end', 'text'
    Returns:
        List of dicts with features per segment
    """
    y, sr = librosa.load(audio_path)
    segment_features = []
    prev_end = 0.0
    for seg in segments:
        start = seg.get('start', 0)
        end = seg.get('end', 0)
        text = seg.get('text', seg.get('word', ''))
        # Audio slice
        start_sample = int(start * sr)
        end_sample = int(end * sr)
        y_seg = y[start_sample:end_sample] if end_sample > start_sample else np.array([])
        # Energy
        energy = float(np.mean(librosa.feature.rms(y=y_seg))) if y_seg.size > 0 else 0.0
        # Pitch
        pitches, magnitudes = librosa.piptrack(y=y_seg, sr=sr) if y_seg.size > 0 else (np.array([]), np.array([]))
        pitch_values = pitches[magnitudes > np.median(magnitudes)] if magnitudes.size > 0 else np.array([])
        avg_pitch = float(np.mean(pitch_values)) if pitch_values.size > 0 else 0.0
        # Duration
        duration = end - start
        # Pause
        pause = start - prev_end if start > prev_end else 0.0
        prev_end = end
        # Keywords (simple split)
        keywords = nltk.word_tokenize(text.lower()) if text else []
        segment_features.append({
            "start": start,
            "end": end,
            "text": text,
            "energy": energy,
            "pitch": avg_pitch,
            "duration": duration,
            "pause": pause,
            "keywords": keywords
        })
    return segment_features


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
