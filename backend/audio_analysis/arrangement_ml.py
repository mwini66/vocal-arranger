"""
ML-based arrangement logic for vocal segments.
"""
from typing import List, Dict, Tuple
import numpy as np

def arrange_ml(segments: List[Dict]) -> Tuple[List[int], float]:
    """
    Arrange segments using a simple ML-inspired scoring function.
    For now, use a weighted sum of features (energy, pitch, duration, pause).
    Args:
        segments: List of segment dicts with features (energy, pitch, text, duration, pause, keywords)
    Returns:
        ordered_indices: List of indices representing arrangement order
        score: Float score for arrangement quality
    """
    if not segments:
        return [], 0.0
    # Feature weights (can be tuned or learned)
    weights = {
        "energy": 0.4,
        "pitch": 0.2,
        "duration": 0.2,
        "pause": 0.2
    }
    # Compute score for each segment
    def segment_score(seg):
        return (
            weights["energy"] * seg.get("energy", 0) +
            weights["pitch"] * seg.get("pitch", 0) +
            weights["duration"] * seg.get("duration", 0) +
            weights["pause"] * seg.get("pause", 0)
        )
    scores = [segment_score(seg) for seg in segments]
    # Sort segments by score (descending)
    ordered_indices = list(map(int, np.argsort(scores)[::-1].tolist()))
    # Arrangement score: normalized sum of segment scores
    arrangement_score = float(np.mean(scores)) / (float(max(scores)) if max(scores) else 1.0)
    return ordered_indices, arrangement_score
