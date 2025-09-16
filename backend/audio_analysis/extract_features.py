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
    For each segment, extract energy, pitch, duration, pause, keywords and enhanced features for LLM analysis.
    Args:
        audio_path: path to audio file
        segments: list of dicts with 'start', 'end', 'text'
    Returns:
        List of dicts with features per segment optimized for AI arrangement
    """
    y, sr = librosa.load(audio_path)
    segment_features = []
    prev_end = 0.0

    # Global audio characteristics for normalization
    global_rms = librosa.feature.rms(y=y)[0]
    global_energy_mean = np.mean(global_rms)
    global_energy_std = np.std(global_rms)

    # Global pitch characteristics
    global_pitches, global_magnitudes = librosa.piptrack(y=y, sr=sr)
    valid_pitches = global_pitches[global_magnitudes > np.median(global_magnitudes)]
    global_pitch_mean = np.mean(valid_pitches) if valid_pitches.size > 0 else 200.0
    global_pitch_std = np.std(valid_pitches) if valid_pitches.size > 0 else 50.0

    for i, seg in enumerate(segments):
        start = seg.get('start', 0)
        end = seg.get('end', 0)
        text = seg.get('text', seg.get('word', ''))

        # Audio slice
        start_sample = int(start * sr)
        end_sample = int(end * sr)
        y_seg = y[start_sample:end_sample] if end_sample > start_sample else np.array([])

        # Raw energy
        if y_seg.size > 0:
            seg_rms = librosa.feature.rms(y=y_seg)[0]
            raw_energy = float(np.mean(seg_rms))
            energy_variance = float(np.var(seg_rms))
        else:
            raw_energy = 0.0
            energy_variance = 0.0

        # Normalized energy (0-1 scale relative to global audio)
        energy = max(0.0, min(1.0, (raw_energy - global_energy_mean) / (global_energy_std * 2) + 0.5)) if global_energy_std > 0 else 0.5

        # Raw pitch
        if y_seg.size > 0:
            pitches, magnitudes = librosa.piptrack(y=y_seg, sr=sr)
            pitch_values = pitches[magnitudes > np.median(magnitudes)] if magnitudes.size > 0 else np.array([])
            raw_pitch = float(np.mean(pitch_values)) if pitch_values.size > 0 else global_pitch_mean
            pitch_variance = float(np.var(pitch_values)) if pitch_values.size > 1 else 0.0
        else:
            raw_pitch = global_pitch_mean
            pitch_variance = 0.0

        # Normalized pitch (0-1 scale)
        pitch = max(0.0, min(1.0, (raw_pitch - global_pitch_mean) / (global_pitch_std * 2) + 0.5)) if global_pitch_std > 0 else 0.5

        # Duration and timing
        duration = end - start
        pause = start - prev_end if start > prev_end else 0.0
        prev_end = end

        # Text analysis
        words = text.lower().split() if text else []
        keywords = nltk.word_tokenize(text.lower()) if text else []
        word_count = len(words)
        unique_word_ratio = len(set(words)) / len(words) if words else 0.0

        # Enhanced features for LLM analysis
        features = {
            # Basic segment info
            "start": start,
            "end": end,
            "text": text,
            "segment_index": i,

            # Normalized audio features (0-1 scale for LLM)
            "energy": energy,
            "pitch": pitch,
            "duration": duration,
            "pause": pause,

            # Raw values for reference
            "raw_energy": raw_energy,
            "raw_pitch": raw_pitch,

            # Variance indicators (stability vs dynamics)
            "energy_variance": energy_variance,
            "pitch_variance": pitch_variance,

            # Text characteristics
            "keywords": keywords,
            "word_count": word_count,
            "unique_word_ratio": unique_word_ratio,

            # Categorical features for LLM understanding
            "energy_category": _categorize_energy(energy),
            "pitch_category": _categorize_pitch(pitch),
            "duration_category": _categorize_duration(duration),
            "text_density": _categorize_text_density(word_count, duration),

            # Musical characteristics
            "is_repetitive": _is_repetitive_text(text),
            "has_vocal_runs": pitch_variance > 1000.0,  # High pitch variance indicates runs/melisma
            "is_sustained": energy_variance < 0.01 and duration > 3.0,  # Steady energy, long duration

            # Structural hints
            "likely_intro": _likely_intro(text, i, len(segments)),
            "likely_outro": _likely_outro(text, i, len(segments)),
            "likely_hook": _likely_hook(text, energy, pitch_variance),
        }

        segment_features.append(features)

    return segment_features


def _categorize_energy(energy):
    """Categorize normalized energy for LLM understanding."""
    if energy > 0.75:
        return "very_high"
    elif energy > 0.6:
        return "high"
    elif energy > 0.4:
        return "moderate"
    elif energy > 0.25:
        return "low"
    else:
        return "very_low"


def _categorize_pitch(pitch):
    """Categorize normalized pitch for LLM understanding."""
    if pitch > 0.75:
        return "very_high"
    elif pitch > 0.6:
        return "high"
    elif pitch > 0.4:
        return "mid_range"
    elif pitch > 0.25:
        return "low"
    else:
        return "very_low"


def _categorize_duration(duration):
    """Categorize segment duration."""
    if duration > 8.0:
        return "very_long"
    elif duration > 5.0:
        return "long"
    elif duration > 3.0:
        return "moderate"
    elif duration > 1.5:
        return "short"
    else:
        return "very_short"


def _categorize_text_density(word_count, duration):
    """Categorize how dense the lyrics are (words per second)."""
    if duration == 0:
        return "no_text"

    words_per_second = word_count / duration
    if words_per_second > 4.0:
        return "very_dense"  # Rap-like
    elif words_per_second > 2.5:
        return "dense"
    elif words_per_second > 1.5:
        return "moderate"
    elif words_per_second > 0.5:
        return "sparse"
    else:
        return "very_sparse"  # Mostly vocalizations


def _is_repetitive_text(text):
    """Check if text contains repetitive elements (good for hooks/choruses)."""
    if not text:
        return False

    words = text.lower().split()
    if len(words) < 3:
        return False

    # Check for repeated words
    word_counts = {}
    for word in words:
        word_counts[word] = word_counts.get(word, 0) + 1

    max_repeats = max(word_counts.values())
    return max_repeats >= 3 or max_repeats / len(words) > 0.4


def _likely_intro(text, index, total_segments):
    """Heuristics for identifying intro segments."""
    if index > 2:  # Not in first few segments
        return False

    if not text:
        return index == 0  # First segment with no text often intro

    text_lower = text.lower()
    intro_phrases = [
        "let's go", "here we go", "come on", "yo", "uh", "yeah", "oh",
        "intro", "start", "begin", "ready"
    ]

    return any(phrase in text_lower for phrase in intro_phrases)


def _likely_outro(text, index, total_segments):
    """Heuristics for identifying outro segments."""
    if index < total_segments - 3:  # Not in last few segments
        return False

    if not text:
        return index == total_segments - 1  # Last segment with no text often outro

    text_lower = text.lower()
    outro_phrases = [
        "goodbye", "see you", "end", "outro", "fade", "bye",
        "that's all", "finish", "done", "over"
    ]

    return any(phrase in text_lower for phrase in outro_phrases)


def _likely_hook(text, energy, pitch_variance):
    """Heuristics for identifying hook/chorus segments."""
    if not text:
        return False

    # High energy often indicates chorus/hook
    energy_score = 1 if energy > 0.6 else 0

    # Repetitive text often indicates hook
    repetitive_score = 1 if _is_repetitive_text(text) else 0

    # Simple/catchy phrases
    words = text.lower().split()
    simple_score = 1 if len(words) <= 8 and len(set(words)) <= 6 else 0

    # Vocal runs/melisma often in hooks
    runs_score = 1 if pitch_variance > 1000.0 else 0

    total_score = energy_score + repetitive_score + simple_score + runs_score
    return total_score >= 2


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
