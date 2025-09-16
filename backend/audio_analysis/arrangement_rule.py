"""
Rule-based arrangement logic for vocal segments.
"""
from typing import List, Dict, Tuple
from collections import defaultdict

def tag_structure(segments):
    """
    Tag segments as intro, verse, chorus, outro based on energy, duration, and position.
    Returns a list of structure tags.
    """
    n = len(segments)
    energies = [seg.get("energy", 0) for seg in segments]
    durations = [seg.get("duration", 0) for seg in segments]
    tags = ["verse"] * n
    if n > 0:
        min_energy_idx = energies.index(min(energies))
        max_energy_idx = energies.index(max(energies))
        max_duration_idx = durations.index(max(durations))
        tags[min_energy_idx] = "intro"
        tags[max_energy_idx] = "chorus"
        tags[max_duration_idx] = "verse"
        tags[-1] = "outro"
    return tags

def arrange_rule(segments: List[Dict]) -> Tuple[List[int], float]:
    """
    Enhanced rule-based arrangement:
    - Tag musical structure (intro, verse, chorus, outro)
    - Alternate high/low energy for contrast
    - Use pauses/duration for pacing
    - Group by keywords and semantic flow
    - Score by structure, contrast, pacing, and grouping
    """
    if not segments:
        return [], 0.0
    n = len(segments)
    structure_tags = tag_structure(segments)
    # Alternate high/low energy for contrast
    sorted_by_energy = sorted(range(n), key=lambda i: segments[i]["energy"])
    high_energy = sorted_by_energy[n//2:]
    low_energy = sorted_by_energy[:n//2]
    alternated = []
    for hi, lo in zip(high_energy, low_energy):
        alternated.append(lo)
        alternated.append(hi)
    # Fill in remaining if uneven
    remaining = set(range(n)) - set(alternated)
    alternated.extend(list(remaining))
    # Group by keywords (semantic flow)
    keyword_groups = defaultdict(list)
    for i in alternated:
        kws = tuple(segments[i].get("keywords", []))
        keyword_groups[kws].append(i)
    ordered_indices = []
    for group in keyword_groups.values():
        group_sorted = sorted(group, key=lambda i: segments[i].get("energy", 0))
        ordered_indices.extend(group_sorted)
    # Pacing: penalize consecutive segments with short pauses
    pacing_score = sum(
        1 for i in range(1, len(ordered_indices))
        if segments[ordered_indices[i]].get("pause", 0) > 0.2
    ) / max(1, len(ordered_indices)-1)
    # Structure score: reward correct tag order (intro, verse, chorus, outro)
    tag_order = [structure_tags[i] for i in ordered_indices]
    structure_score = 0.0
    if tag_order:
        expected = ["intro", "verse", "chorus", "outro"]
        structure_score = sum(1 for t in expected if t in tag_order) / len(expected)
    # Contrast score: reward alternation of energy
    contrast_score = sum(
        1 for i in range(1, len(ordered_indices))
        if (segments[ordered_indices[i]].get("energy", 0) > segments[ordered_indices[i-1]].get("energy", 0)) != (i % 2 == 0)
    ) / max(1, len(ordered_indices)-1)
    # Grouping score: reward grouping by keywords
    keyword_score = len(keyword_groups) / max(1, n)
    # Final score: weighted sum
    score = float(0.3 * structure_score + 0.2 * contrast_score + 0.2 * pacing_score + 0.3 * keyword_score)
    ordered_indices = [int(i) for i in ordered_indices]
    return ordered_indices, score
