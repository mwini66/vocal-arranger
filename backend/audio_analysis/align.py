# backend/aligner.py

from audio_analysis.feature_extraction import extract_features

def align_vocals(reference_path, vocal_path):
    """
    Placeholder function for aligning vocals to a reference track.
    For now, it just extracts features and returns them as a dict.
    """
    reference_features = extract_features(reference_path)
    vocal_features = extract_features(vocal_path)

    return {
        "reference": reference_features,
        "vocals": vocal_features,
        "status": "alignment logic placeholder"
    }
