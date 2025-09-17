import os
import json
import logging
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import numpy as np
import librosa
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import difflib

from .whisperx_utils import transcribe_with_whisperx
from .extract_features import extract_segment_features, convert_numpy_types

logger = logging.getLogger(__name__)


class ReferenceAligner:
    """
    Aligns user vocal segments to match a reference track's timing and sequence.
    """

    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english', lowercase=True)

    def process_reference_track(self, reference_path: str) -> List[Dict]:
        """
        Process reference track to extract segments with features.

        Args:
            reference_path: Path to reference vocal audio file

        Returns:
            List of reference segments with features
        """
        try:
            # Transcribe reference track with WhisperX
            reference_segments = transcribe_with_whisperx(reference_path)

            # Extract enhanced features for reference segments
            reference_features = extract_segment_features(reference_path, reference_segments)

            logger.info(f"Processed reference track: {len(reference_features)} segments")
            return reference_features

        except Exception as e:
            logger.error(f"Failed to process reference track: {e}")
            raise

    def align_to_reference(self, user_segments: List[Dict], reference_segments: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        Align user segments to match reference track timing and sequence.

        Args:
            user_segments: User's vocal segments with features
            reference_segments: Reference track segments with features

        Returns:
            Tuple of (aligned_segments, alignment_info)
        """
        try:
            # Find best matches between user and reference segments
            alignment_map = self._find_segment_matches(user_segments, reference_segments)

            # Create aligned segments with reference timing
            aligned_segments = self._create_aligned_segments(
                user_segments, reference_segments, alignment_map
            )

            # Generate alignment statistics
            alignment_info = self._generate_alignment_info(
                user_segments, reference_segments, alignment_map
            )

            return convert_numpy_types(aligned_segments), convert_numpy_types(alignment_info)

        except Exception as e:
            logger.error(f"Alignment failed: {e}")
            raise

    def _find_segment_matches(self, user_segments: List[Dict], reference_segments: List[Dict]) -> List[Dict]:
        """
        Find the best matching user segments for each reference segment.
        """
        matches = []

        # Extract text from segments
        user_texts = [seg.get('text', '').strip() for seg in user_segments]
        ref_texts = [seg.get('text', '').strip() for seg in reference_segments]

        # Remove empty texts
        valid_user_indices = [i for i, text in enumerate(user_texts) if text]
        valid_ref_indices = [i for i, text in enumerate(ref_texts) if text]

        if not valid_user_indices or not valid_ref_indices:
            logger.warning("No valid text segments found for alignment")
            return []

        # Create text similarity matrix using TF-IDF and cosine similarity
        all_texts = [user_texts[i] for i in valid_user_indices] + [ref_texts[i] for i in valid_ref_indices]

        if len(all_texts) > 1:
            try:
                tfidf_matrix = self.vectorizer.fit_transform(all_texts)
                user_tfidf = tfidf_matrix[:len(valid_user_indices)]
                ref_tfidf = tfidf_matrix[len(valid_user_indices):]
                similarity_matrix = cosine_similarity(ref_tfidf, user_tfidf)
            except Exception as e:
                logger.warning(f"TF-IDF similarity failed, using string matching: {e}")
                similarity_matrix = self._string_similarity_matrix(
                    [ref_texts[i] for i in valid_ref_indices],
                    [user_texts[i] for i in valid_user_indices]
                )
        else:
            similarity_matrix = np.array([[1.0]])

        # Find best matches
        used_user_segments = set()

        for ref_idx, ref_seg_idx in enumerate(valid_ref_indices):
            similarities = similarity_matrix[ref_idx]

            # Sort user segments by similarity
            sorted_user_indices = sorted(
                range(len(valid_user_indices)),
                key=lambda i: similarities[i],
                reverse=True
            )

            # Find the best unused match
            best_match = None
            best_similarity = 0.0

            for user_idx in sorted_user_indices:
                user_seg_idx = valid_user_indices[user_idx]
                if user_seg_idx not in used_user_segments:
                    best_match = user_seg_idx
                    best_similarity = similarities[user_idx]
                    used_user_segments.add(user_seg_idx)
                    break

            matches.append({
                'reference_index': ref_seg_idx,
                'user_index': best_match,
                'similarity': best_similarity,
                'reference_text': ref_texts[ref_seg_idx],
                'user_text': user_texts[best_match] if best_match is not None else None
            })

        return matches

    def _string_similarity_matrix(self, ref_texts: List[str], user_texts: List[str]) -> np.ndarray:
        """
        Create similarity matrix using string matching as fallback.
        """
        matrix = np.zeros((len(ref_texts), len(user_texts)))

        for i, ref_text in enumerate(ref_texts):
            for j, user_text in enumerate(user_texts):
                # Use sequence matcher for similarity
                similarity = difflib.SequenceMatcher(None, ref_text.lower(), user_text.lower()).ratio()
                matrix[i][j] = similarity

        return matrix

    def _create_aligned_segments(self, user_segments: List[Dict], reference_segments: List[Dict], alignment_map: List[Dict]) -> List[Dict]:
        """
        Create new segments with user audio data but reference timing.
        """
        aligned_segments = []

        for match in alignment_map:
            ref_idx = match['reference_index']
            user_idx = match['user_index']

            if user_idx is None:
                # No matching user segment found, create silence or skip
                ref_seg = reference_segments[ref_idx]
                aligned_segments.append({
                    **ref_seg,
                    'text': f"[MISSING: {ref_seg.get('text', '')}]",
                    'user_segment_index': None,
                    'alignment_type': 'missing',
                    'similarity': 0.0
                })
            else:
                # Merge user segment data with reference timing
                user_seg = user_segments[user_idx]
                ref_seg = reference_segments[ref_idx]

                aligned_segment = {
                    # Use reference timing
                    'start': ref_seg['start'],
                    'end': ref_seg['end'],
                    'duration': ref_seg['end'] - ref_seg['start'],

                    # Use user audio characteristics
                    'text': user_seg['text'],
                    'energy': user_seg.get('energy', 0.0),
                    'pitch': user_seg.get('pitch', 0.0),
                    'loudness': user_seg.get('loudness', 0.0),
                    'spectral_centroid': user_seg.get('spectral_centroid', 0.0),
                    'zero_crossing_rate': user_seg.get('zero_crossing_rate', 0.0),
                    'mfcc': user_seg.get('mfcc', []),
                    'chroma': user_seg.get('chroma', []),
                    'tempo': user_seg.get('tempo', 0.0),

                    # Alignment metadata
                    'user_segment_index': user_idx,
                    'reference_segment_index': ref_idx,
                    'alignment_type': 'matched',
                    'similarity': match['similarity'],
                    'original_start': user_seg['start'],
                    'original_end': user_seg['end'],
                    'time_adjustment': ref_seg['start'] - user_seg['start']
                }

                aligned_segments.append(aligned_segment)

        return aligned_segments

    def _generate_alignment_info(self, user_segments: List[Dict], reference_segments: List[Dict],
                               alignment_map: List[Dict]) -> Dict:
        """
        Generate statistics and information about the alignment process.
        """
        total_refs = len(reference_segments)
        matched_refs = len([m for m in alignment_map if m['user_index'] is not None])
        unmatched_refs = total_refs - matched_refs

        similarities = [m['similarity'] for m in alignment_map if m['user_index'] is not None]
        avg_similarity = np.mean(similarities) if similarities else 0.0

        total_user_segments = len(user_segments)
        used_user_segments = len(set(m['user_index'] for m in alignment_map if m['user_index'] is not None))
        unused_user_segments = total_user_segments - used_user_segments

        return {
            'total_reference_segments': total_refs,
            'matched_segments': matched_refs,
            'unmatched_segments': unmatched_refs,
            'match_rate': matched_refs / total_refs if total_refs > 0 else 0.0,
            'average_similarity': avg_similarity,
            'total_user_segments': total_user_segments,
            'used_user_segments': used_user_segments,
            'unused_user_segments': unused_user_segments,
            'usage_rate': used_user_segments / total_user_segments if total_user_segments > 0 else 0.0,
            'alignment_map': alignment_map
        }

    def create_aligned_audio(self, user_audio_path: str, aligned_segments: List[Dict],
                           output_path: str) -> str:
        """
        Create new audio file with user vocals arranged according to reference timing.
        Uses segment placement instead of time stretching to preserve audio quality.

        Args:
            user_audio_path: Path to user's audio file
            aligned_segments: Segments with alignment information
            output_path: Path for output audio file

        Returns:
            Path to created aligned audio file
        """
        try:
            # Load user audio
            y_user, sr = librosa.load(user_audio_path, sr=None)

            # Calculate total duration needed
            if not aligned_segments:
                raise ValueError("No aligned segments provided")

            total_duration = max(seg['end'] for seg in aligned_segments)
            total_samples = int(total_duration * sr)

            # Create output audio array
            y_output = np.zeros(total_samples)

            for segment in aligned_segments:
                if segment.get('alignment_type') == 'missing':
                    # Skip missing segments (they become silence)
                    continue

                # Calculate sample indices for user audio (original timing)
                user_start_sample = int(segment['original_start'] * sr)
                user_end_sample = int(segment['original_end'] * sr)

                # Calculate sample indices for output audio (reference timing)
                output_start_sample = int(segment['start'] * sr)

                # Extract user audio segment at original length (no stretching)
                user_segment = y_user[user_start_sample:user_end_sample]

                if len(user_segment) == 0:
                    continue

                # Calculate how much space we have in the reference timing
                reference_duration = segment['end'] - segment['start']
                reference_samples = int(reference_duration * sr)
                user_samples = len(user_segment)

                if user_samples <= reference_samples:
                    # User segment fits in reference slot - place it at the start
                    end_idx = min(output_start_sample + user_samples, total_samples)
                    y_output[output_start_sample:end_idx] = user_segment[:end_idx - output_start_sample]
                else:
                    # User segment is longer than reference slot - trim it
                    # Option 1: Take the first part
                    trimmed_segment = user_segment[:reference_samples]
                    end_idx = min(output_start_sample + len(trimmed_segment), total_samples)
                    y_output[output_start_sample:end_idx] = trimmed_segment[:end_idx - output_start_sample]

                    # Option 2: Take the middle part (preserves more vocal content)
                    # start_trim = (user_samples - reference_samples) // 2
                    # trimmed_segment = user_segment[start_trim:start_trim + reference_samples]
                    # end_idx = min(output_start_sample + len(trimmed_segment), total_samples)
                    # y_output[output_start_sample:end_idx] = trimmed_segment[:end_idx - output_start_sample]

            # Apply gentle fade in/out to reduce clicks
            fade_samples = min(int(0.01 * sr), len(y_output) // 20)  # 10ms fade or 5% of audio
            if fade_samples > 0:
                # Fade in
                fade_in = np.linspace(0, 1, fade_samples)
                y_output[:fade_samples] *= fade_in

                # Fade out
                fade_out = np.linspace(1, 0, fade_samples)
                y_output[-fade_samples:] *= fade_out

            # Save aligned audio
            import soundfile as sf
            sf.write(output_path, y_output, sr)

            logger.info(f"Created aligned audio without time stretching: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to create aligned audio: {e}")
            raise
