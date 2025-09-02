import json
from pathlib import Path
from typing import List, Dict, Any

# ---------- Config ----------
ALIGNMENT_JSON_PATH = Path("uploads/alignment.json")
LYRICS_PATH = Path("uploads/script.txt")

# Threshold (in seconds) for words to be considered part of the same local group
LOCAL_GAP_THRESHOLD = 0.3

def load_alignment(alignment_path: Path) -> List[Dict[str, Any]]:
    """Load Gentle alignment JSON."""
    with open(alignment_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Filter only successfully aligned words
    return [w for w in data.get("words", []) if w.get("case") == "success"]

def load_lyrics(lyrics_path: Path) -> List[str]:
    """Load lyrics.txt and split into lines (stripped)."""
    with open(lyrics_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    return lines

def map_words_to_lines(aligned_words: List[Dict[str, Any]], lyrics_lines: List[str]) -> List[Dict[str, Any]]:
    """
    Assign each aligned word to a lyric line based on order.
    Assumes the words in alignment JSON appear in the same sequence as lyrics.
    """
    mapped = []
    word_index = 0

    for line_idx, line in enumerate(lyrics_lines):
        line_words = line.split()
        for lw in line_words:
            if word_index >= len(aligned_words):
                break
            mapped.append({
                "word": aligned_words[word_index]["word"],
                "start": aligned_words[word_index]["start"],
                "end": aligned_words[word_index]["end"],
                "line_idx": line_idx
            })
            word_index += 1
    return mapped

def group_local_words(mapped_words: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    Group words into local clusters based on line_idx and small gaps.
    """
    local_groups = []
    current_group = []

    for i, w in enumerate(mapped_words):
        if not current_group:
            current_group.append(w)
            continue

        prev = current_group[-1]
        gap = w["start"] - prev["end"]

        if w["line_idx"] == prev["line_idx"] and gap <= LOCAL_GAP_THRESHOLD:
            current_group.append(w)
        else:
            local_groups.append(current_group)
            current_group = [w]

    if current_group:
        local_groups.append(current_group)

    return local_groups

def identify_global_groups(lyrics_lines: List[str]) -> List[Dict[str, Any]]:
    """
    Identify repeated lines as global movable sections.
    Returns a dict: {line_idx, text, occurrences}
    """
    seen = {}
    global_groups = []

    for idx, line in enumerate(lyrics_lines):
        if line in seen:
            seen[line]["occurrences"].append(idx)
        else:
            seen[line] = {"line_idx": idx, "text": line, "occurrences": [idx]}

    for v in seen.values():
        if len(v["occurrences"]) > 1:  # repeated line = global section
            global_groups.append(v)

    return global_groups

def generate_grouping_json(alignment_path: Path, lyrics_path: Path) -> Dict[str, Any]:
    aligned_words = load_alignment(alignment_path)
    lyrics_lines = load_lyrics(lyrics_path)
    mapped_words = map_words_to_lines(aligned_words, lyrics_lines)
    local_groups = group_local_words(mapped_words)
    global_groups = identify_global_groups(lyrics_lines)

    # Convert local_groups to simple JSON
    local_groups_json = [
        {
            "words": [w["word"] for w in group],
            "start": group[0]["start"],
            "end": group[-1]["end"],
            "line_idx": group[0]["line_idx"]
        }
        for group in local_groups
    ]

    return {
        "local_groups": local_groups_json,
        "global_groups": global_groups
    }

if __name__ == "__main__":
    grouping_json = generate_grouping_json(ALIGNMENT_JSON_PATH, LYRICS_PATH)
    out_path = Path("uploads/grouping.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(grouping_json, f, indent=2)
    print(f"Grouping JSON saved to {out_path}")
