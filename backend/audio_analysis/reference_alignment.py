import difflib
import logging
from typing import List, Dict, Tuple, Optional
import re

import librosa
import numpy as np
import soundfile as sf
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .extract_features import extract_segment_features, convert_numpy_types
from .whisperx_utils import transcribe_with_whisperx

logger = logging.getLogger(__name__)


class TemporalAligner:
    """
    Temporal alignment system that matches input vocals to reference track timing.

    Fixed implementation that properly:
    - Reorders input segments to match reference sequence
    - Uses accurate similarity calculations
    - Handles word-level and phrase-level alignment
    - Creates properly time-aligned output audio
    """

    def __init__(self, similarity_threshold: float = 0.3):
        self.vectorizer = TfidfVectorizer(stop_words='english', lowercase=True)
        self.similarity_threshold = similarity_threshold

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

    def align_to_reference_timing(
            self,
            input_segments: List[Dict],
            reference_segments: List[Dict],
            input_audio_path: str,
            output_path: str
    ) -> Tuple[List[Dict], Dict, str]:
        """
        Main temporal alignment function with proper sequence alignment.

        Args:
            input_segments: User's vocal segments with features
            reference_segments: Reference track segments with features
            input_audio_path: Path to input audio file
            output_path: Path for output aligned audio

        Returns:
            Tuple of (aligned_segments, alignment_info, output_audio_path)
        """
        try:
            logger.info(f"Aligning {len(input_segments)} input segments to {len(reference_segments)} reference segments")

            # Step 1: Find optimal sequence alignment
            alignment_result = self._find_optimal_sequence_alignment(input_segments, reference_segments)

            # Step 2: Create time-aligned segments
            aligned_segments = self._create_time_aligned_segments(
                alignment_result, input_segments, reference_segments
            )

            # Step 3: Generate time-aligned audio
            aligned_audio_path = self._create_temporal_audio(
                input_audio_path, aligned_segments, output_path
            )

            # Step 4: Generate alignment statistics
            alignment_info = self._generate_alignment_info(
                input_segments, reference_segments, alignment_result, aligned_segments
            )

            logger.info(f"Alignment complete: {alignment_info.get('match_rate', 0):.1%} match rate")

            return convert_numpy_types(aligned_segments), convert_numpy_types(alignment_info), aligned_audio_path

        except Exception as e:
            logger.error(f"Temporal alignment failed: {e}")
            raise

    def _find_optimal_sequence_alignment(
            self,
            input_segments: List[Dict],
            reference_segments: List[Dict]
    ) -> Dict:
        """
        Find the optimal sequence alignment using dynamic programming approach.
        This properly reorders input segments to match reference sequence.
        """
        # Extract and clean text for comparison
        input_texts = [self._clean_text(seg.get('text', '')) for seg in input_segments]
        ref_texts = [self._clean_text(seg.get('text', '')) for seg in reference_segments]

        logger.info(f"Input texts: {input_texts}")
        logger.info(f"Reference texts: {ref_texts}")

        # Create similarity matrix
        similarity_matrix = self._calculate_text_similarity_matrix(input_texts, ref_texts)

        # Find best alignment using sequence matching
        alignment = self._find_best_sequence_alignment(
            similarity_matrix, input_texts, ref_texts, input_segments, reference_segments
        )

        return alignment

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for comparison."""
        if not text:
            return ""
        # Convert to lowercase, remove punctuation, normalize whitespace
        text = re.sub(r'[^\w\s]', '', text.lower())
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _calculate_text_similarity_matrix(self, input_texts: List[str], ref_texts: List[str]) -> np.ndarray:
        """
        Calculate accurate text similarity matrix using multiple methods.
        """
        n_ref = len(ref_texts)
        n_input = len(input_texts)
        similarity_matrix = np.zeros((n_ref, n_input))

        for i, ref_text in enumerate(ref_texts):
            for j, input_text in enumerate(input_texts):
                if not ref_text or not input_text:
                    similarity_matrix[i, j] = 0.0
                    continue

                similarities = []

                # 1. Exact match bonus
                if ref_text == input_text:
                    similarities.append(1.0)

                # 2. Word overlap similarity (Jaccard index)
                ref_words = set(ref_text.split())
                input_words = set(input_text.split())
                if ref_words or input_words:
                    overlap = len(ref_words.intersection(input_words))
                    union = len(ref_words.union(input_words))
                    jaccard = overlap / union if union > 0 else 0.0
                    similarities.append(jaccard)

                # 3. Sequence similarity (difflib)
                seq_sim = difflib.SequenceMatcher(None, ref_text, input_text).ratio()
                similarities.append(seq_sim)

                # 4. Levenshtein-based similarity
                import editdistance
                if ref_text and input_text:
                    max_len = max(len(ref_text), len(input_text))
                    if max_len > 0:
                        edit_dist = editdistance.eval(ref_text, input_text)
                        lev_sim = 1.0 - (edit_dist / max_len)
                        similarities.append(lev_sim)

                # Take the maximum similarity
                final_similarity = max(similarities) if similarities else 0.0
                similarity_matrix[i, j] = final_similarity

        logger.info(f"Similarity matrix:\n{similarity_matrix}")
        return similarity_matrix

    def _find_best_sequence_alignment(
            self,
            similarity_matrix: np.ndarray,
            input_texts: List[str],
            ref_texts: List[str],
            input_segments: List[Dict],
            reference_segments: List[Dict]
    ) -> Dict:
        """
        Find the best sequence alignment that maximizes overall similarity
        while maintaining sequence order as much as possible.
        """
        n_ref, n_input = similarity_matrix.shape

        # Try different alignment strategies and pick the best one
        strategies = [
            self._greedy_alignment,
            self._dynamic_programming_alignment,
            self._sequence_aware_alignment
        ]

        best_alignment = None
        best_score = -1

        for strategy in strategies:
            try:
                alignment = strategy(
                    similarity_matrix, input_texts, ref_texts,
                    input_segments, reference_segments
                )
                score = self._score_alignment(alignment, similarity_matrix)

                logger.info(f"Strategy {strategy.__name__}: score = {score:.3f}")

                if score > best_score:
                    best_score = score
                    best_alignment = alignment
            except Exception as e:
                logger.warning(f"Strategy {strategy.__name__} failed: {e}")
                continue

        if best_alignment is None:
            # Fallback: create empty alignment
            best_alignment = {
                'matches': [],
                'input_order': list(range(n_input)),
                'reference_coverage': [False] * n_ref,
                'total_similarity': 0.0
            }

        logger.info(f"Best alignment score: {best_score:.3f}")
        return best_alignment

    def _greedy_alignment(
            self,
            similarity_matrix: np.ndarray,
            input_texts: List[str],
            ref_texts: List[str],
            input_segments: List[Dict],
            reference_segments: List[Dict]
    ) -> Dict:
        """
        Greedy alignment: for each reference segment, find best unused input segment.
        """
        n_ref, n_input = similarity_matrix.shape
        matches = []
        used_input = set()

        for ref_idx in range(n_ref):
            best_input_idx = None
            best_similarity = 0.0

            for input_idx in range(n_input):
                if input_idx not in used_input and similarity_matrix[ref_idx, input_idx] > self.similarity_threshold:
                    if similarity_matrix[ref_idx, input_idx] > best_similarity:
                        best_similarity = similarity_matrix[ref_idx, input_idx]
                        best_input_idx = input_idx

            matches.append({
                'reference_idx': ref_idx,
                'input_idx': best_input_idx,
                'similarity': best_similarity,
                'is_matched': best_input_idx is not None
            })

            if best_input_idx is not None:
                used_input.add(best_input_idx)

        return {
            'matches': matches,
            'input_order': [m['input_idx'] for m in matches],
            'reference_coverage': [m['is_matched'] for m in matches],
            'total_similarity': sum(m['similarity'] for m in matches if m['is_matched'])
        }

    def _dynamic_programming_alignment(
            self,
            similarity_matrix: np.ndarray,
            input_texts: List[str],
            ref_texts: List[str],
            input_segments: List[Dict],
            reference_segments: List[Dict]
    ) -> Dict:
        """
        Dynamic programming alignment for optimal global alignment.
        """
        n_ref, n_input = similarity_matrix.shape

        # DP table: dp[i][j] = best score aligning first i reference segments with first j input segments
        dp = np.zeros((n_ref + 1, n_input + 1))
        traceback = {}

        # Fill DP table
        for i in range(1, n_ref + 1):
            for j in range(1, n_input + 1):
                # Option 1: Match ref[i-1] with input[j-1]
                match_score = dp[i-1][j-1] + similarity_matrix[i-1][j-1]

                # Option 2: Skip reference segment (insert silence)
                skip_ref_score = dp[i-1][j]

                # Option 3: Skip input segment
                skip_input_score = dp[i][j-1]

                if match_score >= skip_ref_score and match_score >= skip_input_score:
                    dp[i][j] = match_score
                    traceback[(i, j)] = 'match'
                elif skip_ref_score >= skip_input_score:
                    dp[i][j] = skip_ref_score
                    traceback[(i, j)] = 'skip_ref'
                else:
                    dp[i][j] = skip_input_score
                    traceback[(i, j)] = 'skip_input'

        # Traceback to find optimal alignment
        matches = []
        i, j = n_ref, n_input

        while i > 0 or j > 0:
            if (i, j) in traceback:
                action = traceback[(i, j)]
                if action == 'match':
                    similarity = similarity_matrix[i-1][j-1]
                    matches.append({
                        'reference_idx': i-1,
                        'input_idx': j-1,
                        'similarity': similarity,
                        'is_matched': similarity > self.similarity_threshold
                    })
                    i -= 1
                    j -= 1
                elif action == 'skip_ref':
                    matches.append({
                        'reference_idx': i-1,
                        'input_idx': None,
                        'similarity': 0.0,
                        'is_matched': False
                    })
                    i -= 1
                else:  # skip_input
                    j -= 1
            else:
                break

        matches.reverse()  # Reverse to get correct order

        return {
            'matches': matches,
            'input_order': [m['input_idx'] for m in matches],
            'reference_coverage': [m['is_matched'] for m in matches],
            'total_similarity': sum(m['similarity'] for m in matches if m['is_matched'])
        }

    def _sequence_aware_alignment(
            self,
            similarity_matrix: np.ndarray,
            input_texts: List[str],
            ref_texts: List[str],
            input_segments: List[Dict],
            reference_segments: List[Dict]
    ) -> Dict:
        """
        Sequence-aware alignment that tries to maintain order while maximizing similarity.
        """
        # Use difflib.SequenceMatcher for sequence alignment
        matcher = difflib.SequenceMatcher(None, input_texts, ref_texts)
        matching_blocks = matcher.get_matching_blocks()

        matches = []
        ref_covered = set()
        input_covered = set()

        # Process matching blocks first
        for block in matching_blocks:
            input_start, ref_start, size = block.a, block.b, block.size

            for i in range(size):
                input_idx = input_start + i
                ref_idx = ref_start + i

                if input_idx < len(input_texts) and ref_idx < len(ref_texts):
                    similarity = similarity_matrix[ref_idx][input_idx]

                    matches.append({
                        'reference_idx': ref_idx,
                        'input_idx': input_idx,
                        'similarity': similarity,
                        'is_matched': similarity > self.similarity_threshold
                    })

                    ref_covered.add(ref_idx)
                    input_covered.add(input_idx)

        # Fill in unmatched reference segments
        for ref_idx in range(len(ref_texts)):
            if ref_idx not in ref_covered:
                matches.append({
                    'reference_idx': ref_idx,
                    'input_idx': None,
                    'similarity': 0.0,
                    'is_matched': False
                })

        # Sort matches by reference index
        matches.sort(key=lambda x: x['reference_idx'])

        return {
            'matches': matches,
            'input_order': [m['input_idx'] for m in matches],
            'reference_coverage': [m['is_matched'] for m in matches],
            'total_similarity': sum(m['similarity'] for m in matches if m['is_matched'])
        }

    def _score_alignment(self, alignment: Dict, similarity_matrix: np.ndarray) -> float:
        """
        Score an alignment based on similarity and sequence coherence.
        """
        if not alignment['matches']:
            return 0.0

        # Base score: average similarity of matched segments
        matched_similarities = [m['similarity'] for m in alignment['matches'] if m['is_matched']]
        avg_similarity = sum(matched_similarities) / max(1, len(matched_similarities))

        # Coverage score: how many reference segments are matched
        coverage = sum(alignment['reference_coverage']) / len(alignment['reference_coverage'])

        # Sequence coherence: bonus for maintaining input order
        sequence_bonus = 0.0
        input_indices = [m['input_idx'] for m in alignment['matches'] if m['input_idx'] is not None]
        if len(input_indices) > 1:
            ordered_count = 0
            for i in range(len(input_indices) - 1):
                if input_indices[i] < input_indices[i + 1]:
                    ordered_count += 1
            sequence_bonus = ordered_count / (len(input_indices) - 1) * 0.2

        # Combined score
        return 0.5 * avg_similarity + 0.3 * coverage + 0.2 * sequence_bonus

    def _create_time_aligned_segments(
            self,
            alignment_result: Dict,
            input_segments: List[Dict],
            reference_segments: List[Dict]
    ) -> List[Dict]:
        """
        Create time-aligned segments based on alignment result.
        """
        aligned_segments = []

        for match in alignment_result['matches']:
            ref_idx = match['reference_idx']
            input_idx = match['input_idx']
            ref_seg = reference_segments[ref_idx]

            # Use reference timing
            start_time = ref_seg['start']
            end_time = ref_seg['end']

            if match['is_matched'] and input_idx is not None:
                # Use matched input segment
                input_seg = input_segments[input_idx]
                aligned_segment = {
                    'start': start_time,
                    'end': end_time,
                    'text': input_seg['text'],
                    'segment_index': len(aligned_segments),

                    # Copy input segment features
                    'energy': input_seg.get('energy', 0.5),
                    'pitch': input_seg.get('pitch', 0.5),
                    'duration': end_time - start_time,
                    'pause': input_seg.get('pause', 0),

                    'energy_category': input_seg.get('energy_category', 'medium'),
                    'pitch_category': input_seg.get('pitch_category', 'medium'),
                    'duration_category': input_seg.get('duration_category', 'medium'),
                    'text_density': input_seg.get('text_density', 'medium'),

                    'is_repetitive': input_seg.get('is_repetitive', False),
                    'has_vocal_runs': input_seg.get('has_vocal_runs', False),
                    'is_sustained': input_seg.get('is_sustained', False),

                    'likely_intro': input_seg.get('likely_intro', False),
                    'likely_outro': input_seg.get('likely_outro', False),
                    'likely_hook': input_seg.get('likely_hook', False),

                    'keywords': input_seg.get('keywords', []),
                    'word_count': input_seg.get('word_count', 0),
                    'unique_word_ratio': input_seg.get('unique_word_ratio', 0),

                    # Alignment metadata
                    'original_start': input_seg['start'],
                    'original_end': input_seg['end'],
                    'reference_text': ref_seg['text'],
                    'matched_input_text': input_seg['text'],
                    'alignment_similarity': match['similarity']
                }
            else:
                # Create silence segment
                aligned_segment = {
                    'start': start_time,
                    'end': end_time,
                    'text': '[SILENCE]',
                    'segment_index': len(aligned_segments),

                    # Default features for silence
                    'energy': 0.0,
                    'pitch': 0.0,
                    'duration': end_time - start_time,
                    'pause': 0.0,

                    'energy_category': 'low',
                    'pitch_category': 'low',
                    'duration_category': 'short',
                    'text_density': 'low',

                    'is_repetitive': False,
                    'has_vocal_runs': False,
                    'is_sustained': False,

                    'likely_intro': False,
                    'likely_outro': False,
                    'likely_hook': False,

                    'keywords': [],
                    'word_count': 0,
                    'unique_word_ratio': 0.0,

                    # Alignment metadata
                    'reference_text': ref_seg['text'],
                    'alignment_similarity': 0.0
                }

            aligned_segments.append(aligned_segment)

        return aligned_segments

    def _create_temporal_audio(
            self,
            input_audio_path: str,
            aligned_segments: List[Dict],
            output_path: str
    ) -> str:
        """
        Create time-aligned audio file from aligned segments.
        """
        try:
            # Load input audio
            audio, sr = librosa.load(input_audio_path, sr=None)

            # Calculate total duration from reference timing
            if not aligned_segments:
                return output_path

            total_duration = max([seg['end'] for seg in aligned_segments])
            output_length = int(total_duration * sr)
            output_audio = np.zeros(output_length)

            # Process each aligned segment
            for segment in aligned_segments:
                if segment.get('text') == '[SILENCE]':
                    continue  # Skip silence segments (leave as zeros)

                # Target timing (from reference)
                target_start = segment['start']
                target_end = segment['end']
                target_start_sample = int(target_start * sr)
                target_end_sample = int(target_end * sr)
                target_length = target_end_sample - target_start_sample

                # Original timing (from input)
                if 'original_start' in segment and 'original_end' in segment:
                    orig_start = segment['original_start']
                    orig_end = segment['original_end']
                    orig_start_sample = int(orig_start * sr)
                    orig_end_sample = int(orig_end * sr)

                    # Extract original audio segment
                    if orig_end_sample <= len(audio) and orig_start_sample >= 0:
                        segment_audio = audio[orig_start_sample:orig_end_sample]

                        # Time-stretch to fit target duration
                        if len(segment_audio) > 0 and target_length > 0:
                            if len(segment_audio) != target_length:
                                # Use librosa for time stretching
                                stretch_ratio = len(segment_audio) / target_length
                                segment_audio = librosa.effects.time_stretch(segment_audio, rate=stretch_ratio)

                            # Ensure exact target length
                            if len(segment_audio) > target_length:
                                segment_audio = segment_audio[:target_length]
                            elif len(segment_audio) < target_length:
                                segment_audio = np.pad(segment_audio, (0, target_length - len(segment_audio)))

                            # Place in output audio
                            if target_end_sample <= len(output_audio):
                                output_audio[target_start_sample:target_end_sample] = segment_audio

            # Save output
            sf.write(output_path, output_audio, sr)
            logger.info(f"Created time-aligned audio: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to create temporal audio: {e}")
            raise

    def _generate_alignment_info(
            self,
            input_segments: List[Dict],
            reference_segments: List[Dict],
            alignment_result: Dict,
            aligned_segments: List[Dict]
    ) -> Dict:
        """
        Generate alignment statistics and information.
        """
        matches = alignment_result['matches']
        matched_count = sum(1 for m in matches if m['is_matched'])
        total_similarity = sum(m['similarity'] for m in matches if m['is_matched'])
        avg_similarity = total_similarity / max(1, matched_count)

        match_rate = matched_count / len(reference_segments) if reference_segments else 0
        usage_rate = matched_count / len(input_segments) if input_segments else 0

        silence_segments = len([s for s in aligned_segments if s.get('text') == '[SILENCE]'])
        silence_percentage = (silence_segments / len(aligned_segments)) * 100 if aligned_segments else 0

        return {
            'total_reference_segments': len(reference_segments),
            'total_input_segments': len(input_segments),
            'matched_segments': matched_count,
            'match_rate': match_rate,
            'average_similarity': avg_similarity,
            'usage_rate': usage_rate,
            'silence_percentage': silence_percentage,
            'total_duration': aligned_segments[-1]['end'] if aligned_segments else 0,
            'alignment_method': 'sequence_alignment'
        }


# Backward compatibility alias
ReferenceAligner = TemporalAligner
