import difflib
import logging
import re
from typing import List, Dict, Tuple

import librosa
import numpy as np
import soundfile as sf
from sklearn.feature_extraction.text import TfidfVectorizer

from .extract_features import extract_segment_features, convert_numpy_types
from .whisperx_utils import transcribe_with_whisperx

logger = logging.getLogger(__name__)


class TemporalAligner:
    """
    Enhanced temporal alignment system that matches input vocals to reference track timing.

    Multi-level matching approach:
    1. Text similarity matching (word-level alignment)
    2. Audio feature matching (energy, pitch, duration)
    3. Windowed matching (1, 2, 3+ segment windows)
    4. Best window selection based on overall match quality

    Features:
    - Reorders input segments to match reference sequence
    - Uses accurate multi-level similarity calculations
    - Handles windowed sequence matching for better context
    - Creates properly time-aligned output audio
    """

    def __init__(self, similarity_threshold: float = 0.3, audio_weight: float = 0.4, text_weight: float = 0.6):
        self.vectorizer = TfidfVectorizer(stop_words='english', lowercase=True)
        self.similarity_threshold = similarity_threshold
        self.audio_weight = audio_weight  # Weight for audio feature matching
        self.text_weight = text_weight    # Weight for text matching
        self.max_window_size = 4          # Maximum window size to try

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
            logger.info(
                f"Aligning {len(input_segments)} input segments to {len(reference_segments)} reference segments")

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
        Find the optimal sequence alignment using multi-level windowed matching approach.

        Multi-level matching:
        1. Text similarity (word matching)
        2. Audio feature similarity (energy, pitch, duration)
        3. Windowed matching (1, 2, 3+ segment windows)
        4. Best window selection based on overall match quality
        """
        # Extract and clean text for comparison
        input_texts = [self._clean_text(seg.get('text', '')) for seg in input_segments]
        ref_texts = [self._clean_text(seg.get('text', '')) for seg in reference_segments]

        logger.info(f"Input texts: {input_texts}")
        logger.info(f"Reference texts: {ref_texts}")

        # Try different window sizes for multi-level matching
        best_alignment = None
        best_score = -1
        best_window_size = 1

        # Test window sizes from 1 to max_window_size
        max_window = min(self.max_window_size, len(input_segments), len(reference_segments))

        for window_size in range(1, max_window + 1):
            logger.info(f"Testing window size: {window_size}")

            try:
                # Create multi-level similarity matrix for this window size
                similarity_matrix = self._calculate_multilevel_similarity_matrix(
                    input_segments, reference_segments, input_texts, ref_texts, window_size
                )

                # Find best alignment using this window size
                alignment = self._find_windowed_alignment(
                    similarity_matrix, input_texts, ref_texts,
                    input_segments, reference_segments, window_size
                )

                # Score this alignment
                score = self._score_windowed_alignment(alignment, similarity_matrix, window_size)

                logger.info(f"Window size {window_size}: score = {score:.3f}, "
                          f"matches = {len([m for m in alignment['matches'] if m['is_matched']])}")

                if score > best_score:
                    best_score = score
                    best_alignment = alignment
                    best_window_size = window_size

            except Exception as e:
                logger.warning(f"Window size {window_size} failed: {e}")
                continue

        logger.info(f"Best alignment: window_size={best_window_size}, score={best_score:.3f}")

        if best_alignment is None:
            # Fallback to single segment matching
            similarity_matrix = self._calculate_multilevel_similarity_matrix(
                input_segments, reference_segments, input_texts, ref_texts, 1
            )
            best_alignment = self._find_windowed_alignment(
                similarity_matrix, input_texts, ref_texts,
                input_segments, reference_segments, 1
            )

        return best_alignment

    def _calculate_multilevel_similarity_matrix(
            self,
            input_segments: List[Dict],
            reference_segments: List[Dict],
            input_texts: List[str],
            ref_texts: List[str],
            window_size: int
    ) -> np.ndarray:
        """
        Calculate multi-level similarity matrix combining text and audio features
        for different window sizes.
        """
        n_ref = len(reference_segments) - window_size + 1
        n_input = len(input_segments) - window_size + 1

        if n_ref <= 0 or n_input <= 0:
            # Fallback for small segments
            return self._calculate_single_segment_similarity(
                input_segments, reference_segments, input_texts, ref_texts
            )

        similarity_matrix = np.zeros((n_ref, n_input))

        logger.info(f"Computing {window_size}-window similarity matrix: {n_ref}x{n_input}")

        for ref_idx in range(n_ref):
            for input_idx in range(n_input):
                # Get window segments
                ref_window = reference_segments[ref_idx:ref_idx + window_size]
                input_window = input_segments[input_idx:input_idx + window_size]

                # Calculate combined similarity for this window
                similarity = self._calculate_window_similarity(
                    input_window, ref_window, window_size
                )

                similarity_matrix[ref_idx, input_idx] = similarity

        logger.info(f"Window {window_size} similarity matrix:\n{similarity_matrix}")
        return similarity_matrix

    def _calculate_window_similarity(
            self,
            input_window: List[Dict],
            ref_window: List[Dict],
            window_size: int
    ) -> float:
        """
        Calculate similarity for a window of segments using multi-level matching:
        1. Text similarity (60% weight)
        2. Audio feature similarity (40% weight)
        """
        text_similarities = []
        audio_similarities = []

        # Calculate similarities for each segment pair in the window
        for i in range(window_size):
            input_seg = input_window[i]
            ref_seg = ref_window[i]

            # Text similarity
            text_sim = self._calculate_text_segment_similarity(
                input_seg.get('text', ''), ref_seg.get('text', '')
            )
            text_similarities.append(text_sim)

            # Audio feature similarity
            audio_sim = self._calculate_audio_feature_similarity(input_seg, ref_seg)
            audio_similarities.append(audio_sim)

        # Average similarities across the window
        avg_text_similarity = sum(text_similarities) / len(text_similarities)
        avg_audio_similarity = sum(audio_similarities) / len(audio_similarities)

        # Window coherence bonus - reward consecutive matching
        window_coherence = self._calculate_window_coherence(input_window, ref_window)

        # Combined similarity with weights
        combined_similarity = (
            self.text_weight * avg_text_similarity +
            self.audio_weight * avg_audio_similarity +
            0.1 * window_coherence  # Small bonus for window coherence
        )

        return min(1.0, combined_similarity)

    def _calculate_text_segment_similarity(self, input_text: str, ref_text: str) -> float:
        """
        Hybrid text similarity calculation combining lexical and phonetic methods.

        Components:
        1. Lexical similarity (character/word matching) - 60%
        2. Phonetic similarity (sound-based matching) - 40%

        This helps distinguish between words that look similar but sound different,
        like "I" vs "live" which would score low on phonetic similarity.
        """
        if not input_text or not ref_text:
            return 0.0

        # Clean texts
        input_clean = self._clean_text(input_text)
        ref_clean = self._clean_text(ref_text)

        if not input_clean or not ref_clean:
            return 0.0

        # 1. Exact match bonus
        if input_clean == ref_clean:
            return 1.0

        # 2. Calculate lexical similarities (existing methods)
        lexical_similarities = []

        # Word overlap similarity (Jaccard index)
        input_words = set(input_clean.split())
        ref_words = set(ref_clean.split())
        if input_words and ref_words:
            intersection = len(input_words.intersection(ref_words))
            union = len(input_words.union(ref_words))
            jaccard = intersection / union if union > 0 else 0.0
            lexical_similarities.append(jaccard)

        # Sequence similarity (difflib)
        seq_sim = difflib.SequenceMatcher(None, input_clean, ref_clean).ratio()
        lexical_similarities.append(seq_sim)

        # Levenshtein-based similarity
        try:
            import editdistance
            max_len = max(len(input_clean), len(ref_clean))
            if max_len > 0:
                edit_dist = editdistance.eval(input_clean, ref_clean)
                lev_sim = 1.0 - (edit_dist / max_len)
                lexical_similarities.append(lev_sim)
        except ImportError:
            pass

        # Substring matching bonus
        if input_clean in ref_clean or ref_clean in input_clean:
            lexical_similarities.append(0.8)

        # 3. Calculate phonetic similarities (NEW)
        phonetic_similarities = []

        # Phonetic similarity at word level
        input_word_list = input_clean.split()
        ref_word_list = ref_clean.split()

        if input_word_list and ref_word_list:
            # Calculate phonetic similarity for each word pair
            word_phonetic_scores = []

            for input_word in input_word_list:
                best_phonetic_score = 0.0
                for ref_word in ref_word_list:
                    phonetic_score = self._calculate_phonetic_word_similarity(input_word, ref_word)
                    best_phonetic_score = max(best_phonetic_score, phonetic_score)
                word_phonetic_scores.append(best_phonetic_score)

            # Average phonetic similarity across all input words
            avg_phonetic = sum(word_phonetic_scores) / len(word_phonetic_scores)
            phonetic_similarities.append(avg_phonetic)

        # Phrase-level phonetic similarity
        phrase_phonetic = self._calculate_phonetic_phrase_similarity(input_clean, ref_clean)
        phonetic_similarities.append(phrase_phonetic)

        # 4. Combine lexical and phonetic similarities
        lexical_score = max(lexical_similarities) if lexical_similarities else 0.0
        phonetic_score = max(phonetic_similarities) if phonetic_similarities else 0.0

        # Hybrid score: 60% lexical, 40% phonetic
        # This ensures that "I" and "live" get a low phonetic score despite character overlap
        hybrid_score = 0.6 * lexical_score + 0.4 * phonetic_score

        logger.debug(f"Text similarity '{input_clean}' vs '{ref_clean}': "
                    f"lexical={lexical_score:.3f}, phonetic={phonetic_score:.3f}, "
                    f"hybrid={hybrid_score:.3f}")

        return hybrid_score

    def _calculate_phonetic_word_similarity(self, word1: str, word2: str) -> float:
        """
        Calculate phonetic similarity between two words using available phonetic algorithms.

        Uses:
        1. Soundex (English phonetic algorithm)
        2. Metaphone (more accurate than Soundex)
        3. NYSIIS (Name similarity algorithm)
        4. Phoneme-level distance
        """
        if not word1 or not word2:
            return 0.0

        if word1 == word2:
            return 1.0

        similarities = []

        # 1. Soundex similarity
        try:
            import jellyfish
            soundex1 = jellyfish.soundex(word1)
            soundex2 = jellyfish.soundex(word2)
            soundex_sim = 1.0 if soundex1 == soundex2 else 0.0
            similarities.append(soundex_sim)
        except ImportError:
            # Fallback simple soundex implementation
            soundex_sim = 1.0 if self._simple_soundex(word1) == self._simple_soundex(word2) else 0.0
            similarities.append(soundex_sim)

        # 2. Metaphone similarity
        try:
            import jellyfish
            metaphone1 = jellyfish.metaphone(word1)
            metaphone2 = jellyfish.metaphone(word2)
            metaphone_sim = 1.0 if metaphone1 == metaphone2 else 0.0
            similarities.append(metaphone_sim)
        except (ImportError, AttributeError):
            pass

        # 3. NYSIIS similarity (alternative to Double Metaphone)
        try:
            import jellyfish
            nysiis1 = jellyfish.nysiis(word1)
            nysiis2 = jellyfish.nysiis(word2)
            nysiis_sim = 1.0 if nysiis1 == nysiis2 else 0.0
            similarities.append(nysiis_sim)
        except (ImportError, AttributeError):
            pass

        # 4. Phoneme-level edit distance
        phoneme_sim = self._calculate_phoneme_similarity(word1, word2)
        similarities.append(phoneme_sim)

        # Return the best phonetic similarity
        return max(similarities) if similarities else 0.0

    def _calculate_phonetic_phrase_similarity(self, phrase1: str, phrase2: str) -> float:
        """
        Calculate phonetic similarity for entire phrases.
        """
        if not phrase1 or not phrase2:
            return 0.0

        # Simple approach: average phonetic similarity of all word pairs
        words1 = phrase1.split()
        words2 = phrase2.split()

        if not words1 or not words2:
            return 0.0

        # For each word in phrase1, find best phonetic match in phrase2
        total_similarity = 0.0
        for word1 in words1:
            best_sim = max([self._calculate_phonetic_word_similarity(word1, word2) for word2 in words2])
            total_similarity += best_sim

        return total_similarity / len(words1)

    def _calculate_phoneme_similarity(self, word1: str, word2: str) -> float:
        """
        Calculate similarity based on estimated phoneme sequences.
        This is a simplified phoneme-level comparison.
        """
        if not word1 or not word2:
            return 0.0

        # Convert to simplified phoneme representations
        phonemes1 = self._word_to_phonemes(word1)
        phonemes2 = self._word_to_phonemes(word2)

        if not phonemes1 or not phonemes2:
            return 0.0

        # Calculate edit distance between phoneme sequences
        try:
            # Try jellyfish first (more likely to be available)
            import jellyfish
            phoneme_distance = jellyfish.levenshtein_distance(phonemes1, phonemes2)
            max_len = max(len(phonemes1), len(phonemes2))
            similarity = 1.0 - (phoneme_distance / max_len) if max_len > 0 else 0.0
            return similarity
        except ImportError:
            pass

        try:
            # Try python-Levenshtein as fallback
            import Levenshtein
            phoneme_distance = Levenshtein.distance(phonemes1, phonemes2)
            max_len = max(len(phonemes1), len(phonemes2))
            similarity = 1.0 - (phoneme_distance / max_len) if max_len > 0 else 0.0
            return similarity
        except ImportError:
            pass

        # Final fallback to sequence matching
        return difflib.SequenceMatcher(None, phonemes1, phonemes2).ratio()

    def _word_to_phonemes(self, word: str) -> str:
        """
        Convert word to simplified phoneme representation.
        This is a basic approximation - in production, you'd use a proper phoneme dictionary.
        """
        if not word:
            return ""

        word = word.lower()

        # Basic English phoneme mapping (simplified)
        phoneme_map = {
            # Vowels
            'a': 'A', 'e': 'E', 'i': 'I', 'o': 'O', 'u': 'U',
            'y': 'I',  # y often sounds like i

            # Common consonant clusters
            'ph': 'F', 'th': 'T', 'sh': 'S', 'ch': 'C',
            'ck': 'K', 'ng': 'N',

            # Silent letters (common cases)
            'ght': 'T',  # night -> nIT
            'kn': 'N',   # knife -> nIF
            'wr': 'R',   # write -> rIT
            'mb': 'M',   # lamb -> laM
        }

        # Apply phoneme mappings
        result = word
        for pattern, replacement in phoneme_map.items():
            result = result.replace(pattern, replacement)

        # Remove common silent ending letters
        if result.endswith('e') and len(result) > 2:
            result = result[:-1]

        # Remove duplicate consonants
        deduplicated = ""
        prev_char = ""
        for char in result:
            if char != prev_char or char in 'AEIOU':
                deduplicated += char
            prev_char = char

        return deduplicated.upper()

    def _simple_soundex(self, word: str) -> str:
        """
        Simple Soundex implementation as fallback.
        """
        if not word:
            return ""

        word = word.upper()

        # Keep first letter
        soundex = word[0]

        # Soundex mapping
        mapping = {
            'BFPV': '1', 'CGJKQSXZ': '2', 'DT': '3',
            'L': '4', 'MN': '5', 'R': '6'
        }

        for char in word[1:]:
            for key, value in mapping.items():
                if char in key:
                    if len(soundex) == 1 or soundex[-1] != value:
                        soundex += value
                    break

        # Pad or trim to 4 characters
        soundex = (soundex + '000')[:4]
        return soundex

    def _calculate_audio_feature_similarity(self, input_seg: Dict, ref_seg: Dict) -> float:
        """
        Calculate audio feature similarity between two segments.
        Matches energy, pitch, and duration as requested.
        """
        similarities = []

        # 1. Energy similarity (normalized 0-1)
        input_energy = input_seg.get('energy', 0.5)
        ref_energy = ref_seg.get('energy', 0.5)
        energy_sim = 1.0 - abs(input_energy - ref_energy)
        similarities.append(energy_sim)

        # 2. Pitch similarity (normalized 0-1)
        input_pitch = input_seg.get('pitch', 0.5)
        ref_pitch = ref_seg.get('pitch', 0.5)
        pitch_sim = 1.0 - abs(input_pitch - ref_pitch)
        similarities.append(pitch_sim)

        # 3. Duration similarity
        input_duration = input_seg.get('end', 0) - input_seg.get('start', 0)
        ref_duration = ref_seg.get('end', 0) - ref_seg.get('start', 0)

        if input_duration > 0 and ref_duration > 0:
            duration_ratio = min(input_duration, ref_duration) / max(input_duration, ref_duration)
            similarities.append(duration_ratio)
        else:
            similarities.append(0.5)  # Neutral score for missing duration

        # 4. Categorical feature matching (bonus points)
        categorical_bonus = 0.0

        # Energy category matching
        if (input_seg.get('energy_category', '') == ref_seg.get('energy_category', '') and
            input_seg.get('energy_category', '')):
            categorical_bonus += 0.1

        # Pitch category matching
        if (input_seg.get('pitch_category', '') == ref_seg.get('pitch_category', '') and
            input_seg.get('pitch_category', '')):
            categorical_bonus += 0.1

        # Musical characteristics matching
        musical_features = ['is_repetitive', 'has_vocal_runs', 'is_sustained']
        matching_features = sum(1 for feat in musical_features
                               if input_seg.get(feat, False) == ref_seg.get(feat, False))
        categorical_bonus += (matching_features / len(musical_features)) * 0.1

        # Average audio similarities + categorical bonus
        avg_audio_sim = sum(similarities) / len(similarities)
        return min(1.0, avg_audio_sim + categorical_bonus)

    def _calculate_window_coherence(self, input_window: List[Dict], ref_window: List[Dict]) -> float:
        """
        Calculate coherence bonus for windowed matching.
        Rewards windows where segments flow naturally together.
        """
        if len(input_window) <= 1:
            return 0.0

        coherence_score = 0.0

        # Check energy flow consistency
        input_energy_flow = [seg.get('energy', 0.5) for seg in input_window]
        ref_energy_flow = [seg.get('energy', 0.5) for seg in ref_window]

        # Calculate energy transition patterns
        input_transitions = [input_energy_flow[i+1] - input_energy_flow[i]
                           for i in range(len(input_energy_flow)-1)]
        ref_transitions = [ref_energy_flow[i+1] - ref_energy_flow[i]
                         for i in range(len(ref_energy_flow)-1)]

        # Reward similar energy transition patterns
        if input_transitions and ref_transitions:
            transition_similarity = 0.0
            for i_trans, r_trans in zip(input_transitions, ref_transitions):
                # Similar direction bonus
                if (i_trans > 0 and r_trans > 0) or (i_trans < 0 and r_trans < 0):
                    transition_similarity += 0.5
                # Similar magnitude bonus
                magnitude_sim = 1.0 - abs(abs(i_trans) - abs(r_trans))
                transition_similarity += magnitude_sim * 0.5

            coherence_score += transition_similarity / len(input_transitions) * 0.5

        # Check text flow consistency (consecutive word relationships)
        for i in range(len(input_window) - 1):
            input_words = set(self._clean_text(input_window[i].get('text', '')).split())
            next_input_words = set(self._clean_text(input_window[i+1].get('text', '')).split())
            ref_words = set(self._clean_text(ref_window[i].get('text', '')).split())
            next_ref_words = set(self._clean_text(ref_window[i+1].get('text', '')).split())

            # Reward if word relationships are similar
            input_overlap = len(input_words.intersection(next_input_words))
            ref_overlap = len(ref_words.intersection(next_ref_words))

            if input_overlap > 0 and ref_overlap > 0:
                coherence_score += 0.2

        return min(1.0, coherence_score)

    def _calculate_single_segment_similarity(
            self,
            input_segments: List[Dict],
            reference_segments: List[Dict],
            input_texts: List[str],
            ref_texts: List[str]
    ) -> np.ndarray:
        """
        Fallback single segment similarity matrix.
        """
        n_ref = len(reference_segments)
        n_input = len(input_segments)
        similarity_matrix = np.zeros((n_ref, n_input))

        for i in range(n_ref):
            for j in range(n_input):
                text_sim = self._calculate_text_segment_similarity(
                    input_texts[j], ref_texts[i]
                )
                audio_sim = self._calculate_audio_feature_similarity(
                    input_segments[j], reference_segments[i]
                )

                combined_sim = self.text_weight * text_sim + self.audio_weight * audio_sim
                similarity_matrix[i, j] = combined_sim

        return similarity_matrix

    def _find_windowed_alignment(
            self,
            similarity_matrix: np.ndarray,
            input_texts: List[str],
            ref_texts: List[str],
            input_segments: List[Dict],
            reference_segments: List[Dict],
            window_size: int
    ) -> Dict:
        """
        Find the best alignment using windowed segments and multi-level matching.
        Considers text similarity, audio feature similarity, and window coherence.
        """
        n_ref, n_input = similarity_matrix.shape

        # Initialize matches
        matches = [[{
            'reference_idx': None,
            'input_idx': None,
            'similarity': 0.0,
            'is_matched': False,
            'match_type': 'unmatched'
        } for _ in range(n_input)] for _ in range(n_ref)]

        # Track used input segments
        used_input = set()

        # Pass 1: High-confidence matches (above threshold)
        for ref_idx in range(n_ref):
            best_input_idx = None
            best_similarity = 0.0

            for input_idx in range(n_input):
                if input_idx not in used_input:
                    similarity = similarity_matrix[ref_idx, input_idx]
                    if similarity > self.similarity_threshold and similarity > best_similarity:
                        best_similarity = similarity
                        best_input_idx = input_idx

            if best_input_idx is not None:
                matches[ref_idx][best_input_idx] = {
                    'reference_idx': ref_idx,
                    'input_idx': best_input_idx,
                    'similarity': best_similarity,
                    'is_matched': True,
                    'match_type': 'high_confidence'
                }
                used_input.add(best_input_idx)

        # Pass 2: Windowed matching - try to find best input segment for each reference segment
        for ref_idx in range(n_ref):
            if matches[ref_idx][0]['is_matched']:
                continue  # Already matched in pass 1

            # Get the window of reference segments
            ref_window = [ref_idx + i for i in range(window_size) if ref_idx + i < n_ref]

            # Find the best input segment for this window
            best_input_idx = None
            best_window_score = -1

            for input_idx in range(n_input):
                if input_idx in used_input:
                    continue  # Skip already used input segments

                # Calculate the windowed similarity score
                window_score = 0.0
                for r_idx in ref_window:
                    window_score += matches[r_idx][input_idx]['similarity'] if matches[r_idx][input_idx]['is_matched'] else 0.0

                if window_score > best_window_score:
                    best_window_score = window_score
                    best_input_idx = input_idx

            if best_input_idx is not None:
                # Match this input segment to the entire window of reference segments
                for r_idx in ref_window:
                    matches[r_idx][best_input_idx] = {
                        'reference_idx': r_idx,
                        'input_idx': best_input_idx,
                        'similarity': similarity_matrix[r_idx][best_input_idx],
                        'is_matched': True,
                        'match_type': 'windowed_match'
                    }
                used_input.add(best_input_idx)

        # Compile final matches
        final_matches = []
        for ref_idx in range(n_ref):
            best_match = max(matches[ref_idx], key=lambda m: m['similarity'], default=None)
            if best_match and best_match['is_matched']:
                final_matches.append(best_match)
            else:
                # Unmatched reference segment, create a synthetic match
                final_matches.append({
                    'reference_idx': ref_idx,
                    'input_idx': None,
                    'similarity': 0.0,
                    'is_matched': False,
                    'match_type': 'unmatched'
                })

        return {
            'matches': final_matches,
            'input_order': [m['input_idx'] for m in final_matches],
            'reference_coverage': [m['is_matched'] for m in final_matches],
            'total_similarity': sum(m['similarity'] for m in final_matches if m['is_matched'])
        }

    def _score_windowed_alignment(self, alignment: Dict, similarity_matrix: np.ndarray, window_size: int) -> float:
        """
        Score an alignment based on windowed matching quality.
        Considers average similarity, coverage, and sequence coherence.
        """
        if not alignment['matches']:
            return 0.0

        # Base score: average similarity of matched segments
        matched_similarities = [m['similarity'] for m in alignment['matches'] if m['is_matched']]
        avg_similarity = sum(matched_similarities) / max(1, len(matched_similarities))

        # Coverage score: how many reference segments are matched
        coverage = sum(alignment['reference_coverage']) / len(alignment['reference_coverage'])

        # Input usage score: how many input segments are used
        input_usage = len([m for m in alignment['matches'] if m['input_idx'] is not None]) / max(1,
                                                                                                 similarity_matrix.shape[
                                                                                                     1])

        # Sequence coherence: bonus for maintaining input order
        sequence_bonus = 0.0
        input_indices = [m['input_idx'] for m in alignment['matches'] if m['input_idx'] is not None]
        if len(input_indices) > 1:
            ordered_count = 0
            for i in range(len(input_indices) - 1):
                if input_indices[i] < input_indices[i + 1]:
                    ordered_count += 1
            sequence_bonus = ordered_count / (len(input_indices) - 1) * 0.15

        # Window size penalty: discourage very large window sizes
        window_size_penalty = max(0, window_size - 1) * 0.05

        # Combined score prioritizing input usage to avoid silence gaps
        return 0.3 * avg_similarity + 0.2 * coverage + 0.4 * input_usage + 0.1 * sequence_bonus - window_size_penalty

    def _create_temporal_audio(
            self,
            input_audio_path: str,
            aligned_segments: List[Dict],
            output_path: str
    ) -> str:
        """
        Create time-aligned audio file from aligned segments.
        FIXED: Now handles synthetic timing and ensures all segments are included.
        """
        try:
            # Load input audio
            audio, sr = librosa.load(input_audio_path, sr=None)

            # Calculate total duration from aligned segments (including synthetic ones)
            if not aligned_segments:
                return output_path

            total_duration = max([seg['end'] for seg in aligned_segments])
            output_length = int(total_duration * sr)
            output_audio = np.zeros(output_length)

            logger.info(f"Creating audio: {len(aligned_segments)} segments, {total_duration:.2f}s total duration")

            # Process each aligned segment
            for segment in aligned_segments:
                if segment.get('text') == '[SILENCE]':
                    continue  # Skip silence segments (leave as zeros)

                # Target timing (from reference or synthetic)
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
                                try:
                                    segment_audio = librosa.effects.time_stretch(segment_audio, rate=stretch_ratio)
                                except Exception as e:
                                    logger.warning(
                                        f"Time stretching failed for segment {segment.get('segment_index', '?')}: {e}")
                                    # Fallback: simple resampling
                                    if target_length > 0:
                                        segment_audio = librosa.resample(segment_audio, orig_sr=len(segment_audio),
                                                                         target_sr=target_length)

                            # Ensure exact target length
                            if len(segment_audio) > target_length:
                                segment_audio = segment_audio[:target_length]
                            elif len(segment_audio) < target_length:
                                segment_audio = np.pad(segment_audio, (0, target_length - len(segment_audio)))

                            # Place in output audio
                            if target_end_sample <= len(output_audio) and target_start_sample >= 0:
                                output_audio[target_start_sample:target_end_sample] = segment_audio
                                logger.debug(
                                    f"Placed segment {segment.get('segment_index', '?')} at {target_start:.2f}-{target_end:.2f}s")
                            else:
                                logger.warning(
                                    f"Segment {segment.get('segment_index', '?')} timing out of bounds: {target_start:.2f}-{target_end:.2f}s")
                    else:
                        logger.warning(
                            f"Original audio segment out of bounds: {orig_start:.2f}-{orig_end:.2f}s (audio length: {len(audio) / sr:.2f}s)")

            # Save output
            sf.write(output_path, output_audio, sr)
            logger.info(f"Created time-aligned audio: {output_path} ({len(output_audio) / sr:.2f}s)")
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

    def _create_time_aligned_segments(
            self,
            alignment_result: Dict,
            input_segments: List[Dict],
            reference_segments: List[Dict]
    ) -> List[Dict]:
        """
        Create time-aligned segments based on alignment result.
        FIXED: Now handles synthetic timing for extended segments.
        """
        aligned_segments = []

        for match in alignment_result['matches']:
            ref_idx = match['reference_idx']
            input_idx = match['input_idx']

            # Determine timing - use synthetic timing if available
            if 'synthetic_timing' in match:
                start_time = match['synthetic_timing']['start']
                end_time = match['synthetic_timing']['end']
                ref_text = match['synthetic_timing']['text']
            elif ref_idx < len(reference_segments):
                ref_seg = reference_segments[ref_idx]
                start_time = ref_seg['start']
                end_time = ref_seg['end']
                ref_text = ref_seg['text']
            else:
                # Fallback timing
                start_time = 0.0
                end_time = 1.0
                ref_text = ""

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
                    'reference_text': ref_text,
                    'matched_input_text': input_seg['text'],
                    'alignment_similarity': match['similarity'],
                    'match_type': match.get('match_type', 'standard'),
                    'is_synthetic': 'synthetic_timing' in match
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
                    'reference_text': ref_text,
                    'alignment_similarity': 0.0,
                    'match_type': match.get('match_type', 'unmatched'),
                    'is_synthetic': 'synthetic_timing' in match
                }

            aligned_segments.append(aligned_segment)

        return aligned_segments

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
                'is_matched': best_input_idx is not None,
                'match_type': 'greedy'
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
                match_score = dp[i - 1][j - 1] + similarity_matrix[i - 1][j - 1]

                # Option 2: Skip reference segment (insert silence)
                skip_ref_score = dp[i - 1][j]

                # Option 3: Skip input segment
                skip_input_score = dp[i][j - 1]

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
                    similarity = similarity_matrix[i - 1][j - 1]
                    matches.append({
                        'reference_idx': i - 1,
                        'input_idx': j - 1,
                        'similarity': similarity,
                        'is_matched': similarity > self.similarity_threshold,
                        'match_type': 'dynamic_programming'
                    })
                    i -= 1
                    j -= 1
                elif action == 'skip_ref':
                    matches.append({
                        'reference_idx': i - 1,
                        'input_idx': None,
                        'similarity': 0.0,
                        'is_matched': False,
                        'match_type': 'dynamic_programming'
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
                        'is_matched': similarity > self.similarity_threshold,
                        'match_type': 'sequence_aware'
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
                    'is_matched': False,
                    'match_type': 'sequence_aware'
                })

        # Sort matches by reference index
        matches.sort(key=lambda x: x['reference_idx'])

        return {
            'matches': matches,
            'input_order': [m['input_idx'] for m in matches],
            'reference_coverage': [m['is_matched'] for m in matches],
            'total_similarity': sum(m['similarity'] for m in matches if m['is_matched'])
        }

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for comparison."""
        if not text:
            return ""
        # Convert to lowercase, remove punctuation, normalize whitespace
        text = re.sub(r'[^\w\s]', '', text.lower())
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity for helper functions."""
        if not text1 or not text2:
            return 0.0

        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0
