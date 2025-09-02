import json

def align_vocals(reference_path, vocals_path, output_path):
    """
    Dummy alignment function.
    Replace with Gentle or spectral alignment later.
    """
    result = {
        "reference": reference_path,
        "vocals": vocals_path,
        "alignment": [
            {"timestamp": 0.0, "note": "C4", "status": "aligned"},
            {"timestamp": 1.2, "note": "E4", "status": "aligned"},
            {"timestamp": 2.5, "note": "G4", "status": "shifted"},
        ]
    }

    with open(output_path, "w") as f:
        json.dump(result, f, indent=4)

    return result
