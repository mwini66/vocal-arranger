import json
import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from audio_analysis.arrangement import AIVocalArranger
from audio_analysis.extract_features import extract_segment_features
from audio_analysis.reference_alignment import ReferenceAligner, TemporalAligner
from audio_analysis.whisperx_utils import transcribe_with_whisperx

load_dotenv()
app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads/audio"
ALIGNED_FOLDER = "uploads/aligned"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ALIGNED_FOLDER, exist_ok=True)

FEEDBACK_FILE = os.path.join("data", "arrangement_feedback.json")
os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)
if not os.path.exists(FEEDBACK_FILE):
    with open(FEEDBACK_FILE, "w") as f:
        json.dump([], f)

# Initialize AI vocal arranger and reference aligner
ai_arranger = AIVocalArranger()
reference_aligner = ReferenceAligner()

# Initialize temporal aligner (replacing LLM-based approach)
temporal_aligner = TemporalAligner(similarity_threshold=0.3)


@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/aligned/<filename>')
def serve_aligned_audio(filename):
    return send_from_directory(ALIGNED_FOLDER, filename)


@app.route("/arrange", methods=["POST"])
def arrange():
    """
    Arrange segments using AI/LLM analysis based on content, energy, and flow.
    This creates an intelligent ordering of segments without reference timing.
    Used by legacy AIVocalArranger component.
    """
    data = request.get_json()
    if not data or "segments" not in data:
        return jsonify({"error": "Missing segments in request"}), 400

    segments = data["segments"]
    target_structure = data.get("structure", "auto")
    genre_hint = data.get("genre")

    try:
        arrangement, confidence, analysis = ai_arranger.arrange_segments(
            segments, target_structure, genre_hint
        )

        return jsonify({
            "arrangement": arrangement,
            "confidence": confidence,
            "method": "ai_arrangement",
            "analysis": analysis,
            "structure": analysis.get('sections', {})
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/arrangement/feedback", methods=["POST"])
def arrangement_feedback():
    """
    Enhanced feedback system for AI arrangement quality assessment.
    Collects comprehensive data for training future end-to-end AI models.

    Expected JSON payload:
    {
        "session_id": str,
        "user_rating": int (1-5),
        "audio_quality": int (1-5),
        "arrangement_coherence": int (1-5),
        "energy_flow": int (1-5),
        "lyrical_flow": int (1-5),
        "overall_satisfaction": int (1-5),
        "feedback_text": str (optional),
        "would_use_again": bool,
        "arrangement_data": {
            "original_segments": [...],
            "arranged_segments": [...],
            "ai_analysis": {...},
            "reference_segments": [...] (optional),
            "genre": str (optional)
        }
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing feedback data"}), 400

    # Validate required fields
    required_fields = ["session_id", "user_rating", "arrangement_data"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Create comprehensive feedback record
    feedback_record = {
        "feedback_id": f"fb_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{data['session_id'][-8:]}",
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": data["session_id"],

        # User ratings (1-5 scale)
        "ratings": {
            "overall": data["user_rating"],
            "audio_quality": data.get("audio_quality", data["user_rating"]),
            "arrangement_coherence": data.get("arrangement_coherence", data["user_rating"]),
            "energy_flow": data.get("energy_flow", data["user_rating"]),
            "lyrical_flow": data.get("lyrical_flow", data["user_rating"]),
            "overall_satisfaction": data.get("overall_satisfaction", data["user_rating"])
        },

        # Qualitative feedback
        "feedback": {
            "text": data.get("feedback_text", ""),
            "would_use_again": data.get("would_use_again", True)
        },

        # AI arrangement data for model training
        "arrangement_analysis": {
            "original_arrangement": data["arrangement_data"].get("original_arrangement", []),
            "ai_confidence": data["arrangement_data"].get("ai_analysis", {}).get("confidence", 0),
            "ai_reasoning": data["arrangement_data"].get("ai_analysis", {}).get("reasoning", ""),
            "arrangement_method": data["arrangement_data"].get("ai_analysis", {}).get("method", "unknown"),
            "genre_hint": data["arrangement_data"].get("genre", "auto-detect")
        },

        # Segment-level training data
        "training_data": {
            "input_segments": _extract_segment_features_for_training(
                data["arrangement_data"].get("original_segments", [])
            ),
            "arranged_segments": _extract_segment_features_for_training(
                data["arrangement_data"].get("arranged_segments", [])
            ),
            "reference_segments": _extract_segment_features_for_training(
                data["arrangement_data"].get("reference_segments", [])
            ) if data["arrangement_data"].get("reference_segments") else None,

            # Arrangement pattern analysis
            "arrangement_pattern": _analyze_arrangement_pattern(
                data["arrangement_data"].get("original_segments", []),
                data["arrangement_data"].get("arranged_segments", [])
            ),

            # Feature correlations for training
            "feature_analysis": _analyze_segment_relationships(
                data["arrangement_data"].get("arranged_segments", [])
            )
        },

        # Model performance metrics
        "model_performance": {
            "processing_successful": True,
            "segments_used": len(data["arrangement_data"].get("arranged_segments", [])),
            "segments_available": len(data["arrangement_data"].get("original_segments", [])),
            "usage_efficiency": len(data["arrangement_data"].get("arranged_segments", [])) / max(1, len(
                data["arrangement_data"].get("original_segments", []))),
            "reference_match_quality": data["arrangement_data"].get("reference_structure", {}).get("matched_segments",
                                                                                                   0) / max(1, len(
                data["arrangement_data"].get("reference_segments", []))) if data["arrangement_data"].get(
                "reference_segments") else None
        }
    }

    try:
        # Save to feedback file
        with open(FEEDBACK_FILE, "r+") as f:
            feedback_list = json.load(f)
            feedback_list.append(feedback_record)
            f.seek(0)
            json.dump(feedback_list, f, indent=2)
            f.truncate()

        # Also save detailed training data separately for ML pipeline
        _save_training_data(feedback_record)

        return jsonify({
            "status": "success",
            "feedback_id": feedback_record["feedback_id"],
            "message": "Comprehensive feedback recorded for model training"
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to save feedback: {str(e)}"}), 500


def _extract_segment_features_for_training(segments):
    """Extract key features from segments for ML training"""
    if not segments:
        return []

    training_features = []
    for i, segment in enumerate(segments):
        feature_vector = {
            "position": i,
            "start_time": segment.get("start", 0),
            "end_time": segment.get("end", 0),
            "duration": segment.get("end", 0) - segment.get("start", 0),

            # Audio features (normalized 0-1)
            "energy": segment.get("energy", 0),
            "pitch": segment.get("pitch", 0),
            "pause_before": segment.get("pause", 0),

            # Categorical features (encoded)
            "energy_category": segment.get("energy_category", "medium"),
            "pitch_category": segment.get("pitch_category", "medium"),
            "duration_category": segment.get("duration_category", "medium"),
            "text_density": segment.get("text_density", "medium"),

            # Text features
            "text": segment.get("text", ""),
            "word_count": segment.get("word_count", 0),
            "unique_word_ratio": segment.get("unique_word_ratio", 0),
            "keywords": segment.get("keywords", []),

            # Musical characteristics (boolean)
            "is_repetitive": segment.get("is_repetitive", False),
            "has_vocal_runs": segment.get("has_vocal_runs", False),
            "is_sustained": segment.get("is_sustained", False),

            # Structural hints (boolean)
            "likely_intro": segment.get("likely_intro", False),
            "likely_outro": segment.get("likely_outro", False),
            "likely_hook": segment.get("likely_hook", False)
        }
        training_features.append(feature_vector)

    return training_features


def _analyze_arrangement_pattern(original_segments, arranged_segments):
    """Analyze how segments were rearranged for pattern learning"""
    if not original_segments or not arranged_segments:
        return {}

    # Create mapping from arranged back to original
    arrangement_mapping = []
    for arranged_idx, arranged_segment in enumerate(arranged_segments):
        # Find this segment in the original list
        for orig_idx, orig_segment in enumerate(original_segments):
            if (arranged_segment.get("text", "") == orig_segment.get("text", "") and
                    abs(arranged_segment.get("start", 0) - orig_segment.get("start", 0)) < 0.1):
                arrangement_mapping.append({
                    "arranged_position": arranged_idx,
                    "original_position": orig_idx,
                    "movement_distance": arranged_idx - orig_idx
                })
                break

    return {
        "mapping": arrangement_mapping,
        "total_segments": len(arranged_segments),
        "segments_reordered": len([m for m in arrangement_mapping if m["movement_distance"] != 0]),
        "average_movement": sum([abs(m["movement_distance"]) for m in arrangement_mapping]) / max(1,
                                                                                                  len(arrangement_mapping)),
        "pattern_type": _classify_arrangement_pattern(arrangement_mapping)
    }


def _classify_arrangement_pattern(mapping):
    """Classify the type of arrangement pattern for training data"""
    if not mapping:
        return "unknown"

    movements = [m["movement_distance"] for m in mapping]
    reordered_count = len([m for m in movements if m != 0])

    if reordered_count == 0:
        return "no_change"
    elif reordered_count <= 2:
        return "minimal_reorder"
    elif all(m >= 0 for m in movements):
        return "forward_progression"
    elif all(m <= 0 for m in movements):
        return "reverse_order"
    else:
        return "complex_reorder"


def _analyze_segment_relationships(segments):
    """Analyze relationships between adjacent segments for training"""
    if len(segments) < 2:
        return {}

    relationships = []
    for i in range(len(segments) - 1):
        current = segments[i]
        next_seg = segments[i + 1]

        relationship = {
            "position": i,
            "energy_transition": next_seg.get("energy", 0) - current.get("energy", 0),
            "pitch_transition": next_seg.get("pitch", 0) - current.get("pitch", 0),
            "duration_ratio": next_seg.get("end", 0) - next_seg.get("start", 0) / max(0.1, current.get("end",
                                                                                                       0) - current.get(
                "start", 0)),
            "text_similarity": _calculate_text_similarity(current.get("text", ""), next_seg.get("text", "")),
            "structural_compatibility": _check_structural_compatibility(current, next_seg)
        }
        relationships.append(relationship)

    return {
        "segment_transitions": relationships,
        "energy_flow_pattern": [r["energy_transition"] for r in relationships],
        "pitch_flow_pattern": [r["pitch_transition"] for r in relationships],
        "overall_coherence_score": sum([r["text_similarity"] for r in relationships]) / max(1, len(relationships))
    }


def _calculate_text_similarity(text1, text2):
    """Simple text similarity for training data"""
    if not text1 or not text2:
        return 0

    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())

    if not words1 or not words2:
        return 0

    intersection = words1.intersection(words2)
    union = words1.union(words2)

    return len(intersection) / len(union) if union else 0


def _check_structural_compatibility(seg1, seg2):
    """Check if two segments work well together structurally"""
    compatibility_score = 0

    # Energy compatibility
    energy_diff = abs(seg1.get("energy", 0) - seg2.get("energy", 0))
    if energy_diff < 0.3:  # Similar energy levels
        compatibility_score += 0.3
    elif energy_diff > 0.5:  # Good contrast
        compatibility_score += 0.2

    # Structural role compatibility
    if seg1.get("likely_intro", False) and not seg2.get("likely_outro", False):
        compatibility_score += 0.3
    if seg2.get("likely_outro", False) and not seg1.get("likely_intro", False):
        compatibility_score += 0.3
    if seg1.get("likely_hook", False) or seg2.get("likely_hook", False):
        compatibility_score += 0.4

    return min(1.0, compatibility_score)


def _save_training_data(feedback_record):
    """Save structured training data for ML pipeline"""
    training_dir = os.path.join("data", "training")
    os.makedirs(training_dir, exist_ok=True)

    training_file = os.path.join(training_dir, f"training_data_{datetime.now().strftime('%Y%m')}.jsonl")

    # Create training example in JSONL format
    training_example = {
        "feedback_id": feedback_record["feedback_id"],
        "timestamp": feedback_record["timestamp"],
        "rating": feedback_record["ratings"]["overall"],
        "features": feedback_record["training_data"],
        "target_quality": feedback_record["ratings"],
        "arrangement_success": feedback_record["ratings"]["overall"] >= 4
    }

    # Append to monthly training file
    with open(training_file, "a") as f:
        f.write(json.dumps(training_example) + "\n")


@app.route("/model_status", methods=["GET"])
def model_status():
    """
    Get status of available AI services for vocal arrangement and reference alignment.
    Returns: { "models": {...}, "services": {...}, "arrangement_methods": [...] }
    """
    try:
        status = {
            "models": {
                "ai_llm": False,
                "openrouter": False
            },
            "services": {
                "openrouter": False,
                "whisper": True,
                "feature_extraction": True,
                "reference_alignment": True
            },
            "arrangement_methods": ["ai", "reference_alignment"],
            "structure_templates": list(ai_arranger.structure_templates.keys()),
            "alignment_features": {
                "reference_processing": True,
                "text_similarity_matching": True,
                "audio_time_stretching": True,
                "segment_alignment": True
            }
        }

        # Check OpenRouter AI availability
        try:
            ai_available = ai_arranger.llm_client.is_available()
            status["models"]["ai_llm"] = ai_available
            status["models"]["openrouter"] = ai_available
            status["services"]["openrouter"] = ai_available
        except Exception:
            pass

        return jsonify(status), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/process_vocals", methods=["POST"])
def process_vocals():
    """
    Step 1: Process input vocals - segment and extract features for arrangement.
    This is the main vocals processing endpoint used by the current UI.
    """
    if "vocals" not in request.files:
        return jsonify({"error": "Vocals file is required."}), 400

    vocals = request.files["vocals"]
    vocals_path = os.path.join(UPLOAD_FOLDER, f"input_vocals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
    vocals.save(vocals_path)

    try:
        # Transcribe with WhisperX
        segments = transcribe_with_whisperx(vocals_path)

        # Extract enhanced features for AI analysis
        segment_features = extract_segment_features(vocals_path, segments)

        return jsonify({
            "segments": segment_features,
            "vocals_path": vocals_path,
            "total_segments": len(segment_features),
            "method": "whisperx_analysis"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/process_reference", methods=["POST"])
def process_reference_vocals():
    """
    Step 2: Process reference vocals - segment and extract features for timing/energy reference.
    This analyzes the reference track structure used by the current UI.
    """
    if "reference" not in request.files:
        return jsonify({"error": "Reference file is required."}), 400

    reference = request.files["reference"]
    reference_path = os.path.join(UPLOAD_FOLDER, f"reference_vocals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
    reference.save(reference_path)

    try:
        # Transcribe reference with WhisperX
        segments = transcribe_with_whisperx(reference_path)

        # Extract enhanced features for reference structure
        segment_features = extract_segment_features(reference_path, segments)

        return jsonify({
            "reference_segments": segment_features,
            "reference_path": reference_path,
            "total_segments": len(segment_features),
            "method": "reference_analysis"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/arrange_to_reference", methods=["POST"])
def arrange_to_reference():
    """
    Step 3: Temporal alignment - match input vocals to reference track timing.

    This creates a time-aligned version where:
    - Input segments are matched to reference segments based on text/audio similarity
    - Output matches reference track duration exactly
    - Unmatched reference segments become silence
    - Input segments are placed at reference timestamps
    - Handles partial matches (e.g., input starting midway through reference)

    This is the main temporal alignment endpoint used by the current UI.
    """
    data = request.get_json()
    if not data or "input_segments" not in data or "reference_segments" not in data:
        return jsonify({"error": "Both input_segments and reference_segments are required"}), 400

    input_segments = data["input_segments"]
    reference_segments = data["reference_segments"]
    input_vocals_path = data.get("input_vocals_path")
    genre_hint = data.get("genre")  # Not used in temporal alignment but kept for compatibility

    if not input_vocals_path:
        return jsonify({"error": "input_vocals_path is required for temporal alignment"}), 400

    try:
        # Create output filename
        output_filename = f"temporal_aligned_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        output_path = os.path.join(ALIGNED_FOLDER, output_filename)

        # Perform temporal alignment
        aligned_segments, alignment_info, aligned_audio_path = temporal_aligner.align_to_reference_timing(
            input_segments,
            reference_segments,
            input_vocals_path,
            output_path
        )

        # Create compatibility response format
        return jsonify({
            "arranged_segments": aligned_segments,
            "original_arrangement": list(range(len(aligned_segments))),  # Sequential for temporal alignment
            "ai_analysis": {
                "confidence": alignment_info.get("average_similarity", 0),
                "reasoning": f"Temporal alignment with {alignment_info.get('match_rate', 0):.1%} match rate. "
                           f"{alignment_info.get('silence_percentage', 0):.1f}% silence padding.",
                "method": "temporal_alignment"
            },
            "reference_structure": {
                "total_reference_segments": alignment_info.get("total_reference_segments", 0),
                "matched_segments": alignment_info.get("matched_segments", 0),
                "energy_progression": [s.get("energy", 0) for s in reference_segments],
                "timing_structure": [s.get("end", 0) - s.get("start", 0) for s in reference_segments],
                "match_rate": alignment_info.get("match_rate", 0),
                "silence_percentage": alignment_info.get("silence_percentage", 0),
                "total_duration": alignment_info.get("total_duration", 0),
                "similarity_threshold": temporal_aligner.similarity_threshold
            },
            "temporal_alignment_info": alignment_info,
            "arranged_audio_url": f"/aligned/{output_filename}" if aligned_audio_path else None,
            "method": "temporal_alignment"
        }), 200

    except Exception as e:
        return jsonify({"error": f"Temporal alignment failed: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)
