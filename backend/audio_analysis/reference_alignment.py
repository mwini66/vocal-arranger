import difflib
import logging
from typing import List, Dict, Tuple

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

    Key features:
    - Finds matching segments between input and reference
    - Arranges input segments in reference order
    - Time-aligns output to match reference timestamps
    - Pads with silence when segments don't match
    - Handles partial matches (e.g., starting midway through reference)
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
        Main temporal alignment function.

        Args:
            input_segments: User's vocal segments with features
            reference_segments: Reference track segments with features
            input_audio_path: Path to input audio file
            output_path: Path for output aligned audio

        Returns:
            Tuple of (aligned_segments, alignment_info, output_audio_path)
        """
        try:
            # Step 1: Find segment matches between input and reference
            segment_matches = self._find_segment_matches(input_segments, reference_segments)

            # Step 2: Create temporal alignment plan
            alignment_plan = self._create_alignment_plan(segment_matches, reference_segments)

            # Step 3: Generate time-aligned audio
            aligned_audio_path = self._create_temporal_audio(
                input_audio_path, input_segments, alignment_plan, output_path
            )

            # Step 4: Create aligned segment metadata
            aligned_segments = self._create_aligned_segments(alignment_plan, input_segments)

            # Step 5: Generate alignment statistics
            alignment_info = self._generate_alignment_info(
                input_segments, reference_segments, segment_matches, alignment_plan
            )

            return convert_numpy_types(aligned_segments), convert_numpy_types(alignment_info), aligned_audio_path

        except Exception as e:
            logger.error(f"Temporal alignment failed: {e}")
            raise

    def _find_segment_matches(self, input_segments: List[Dict], reference_segments: List[Dict]) -> List[Dict]:
        """
        Find matching segments between input and reference using windowed text and audio similarity.
        Uses different window sizes to find the best sequential matching patterns.
        """
        # Extract text from segments
        input_texts = [seg.get('text', '').strip() for seg in input_segments]
        ref_texts = [seg.get('text', '').strip() for seg in reference_segments]

        # Filter out empty texts
        valid_input_indices = [i for i, text in enumerate(input_texts) if text]
        valid_ref_indices = [i for i, text in enumerate(ref_texts) if text]

        if not valid_input_indices or not valid_ref_indices:
            logger.warning("No valid text segments found for matching")
            return []

        # Try different windowing approaches and pick the best one
        window_results = []

        # Try window sizes from 1 to min(8, available segments)
        max_window_size = min(8, len(valid_input_indices), len(valid_ref_indices))

        for window_size in range(1, max_window_size + 1):
            logger.info(f"Trying window size {window_size}")
            matches = self._find_matches_with_window(
                input_segments, reference_segments,
                valid_input_indices, valid_ref_indices,
                window_size
            )

            # Calculate overall matching quality
            quality_score = self._calculate_matching_quality(matches)

            window_results.append({
                'window_size': window_size,
                'matches': matches,
                'quality_score': quality_score,
                'total_matches': len([m for m in matches if m['is_matched']]),
                'avg_similarity': sum([m['similarity'] for m in matches if m['is_matched']]) / max(1, len([m for m in
                                                                                                           matches if m[
                                                                                                               'is_matched']]))
            })

            logger.info(
                f"Window size {window_size}: {quality_score:.3f} quality, {len([m for m in matches if m['is_matched']])} matches")

        # Select best windowing result
        best_result = max(window_results, key=lambda x: x['quality_score'])
        logger.info(
            f"Selected window size {best_result['window_size']} with quality score {best_result['quality_score']:.3f}")

        return best_result['matches']

    def _find_matches_with_window(
            self,
            input_segments: List[Dict],
            reference_segments: List[Dict],
            valid_input_indices: List[int],
            valid_ref_indices: List[int],
            window_size: int
    ) -> List[Dict]:
        """
        Find matches using a specific window size for sequential matching.
        """
        matches = []
        used_input_segments = set()

        # Create similarity matrices for different window configurations
        if window_size == 1:
            # Single segment matching (original approach)
            similarity_matrix = self._calculate_similarity_matrix(
                input_segments, reference_segments,
                valid_input_indices, valid_ref_indices
            )

            for ref_idx, ref_seg_idx in enumerate(valid_ref_indices):
                similarities = similarity_matrix[ref_idx]

                # Find best unused match above threshold
                best_match = None
                best_similarity = 0.0

                for input_idx in range(len(valid_input_indices)):
                    input_seg_idx = valid_input_indices[input_idx]
                    similarity = similarities[input_idx]

                    if (input_seg_idx not in used_input_segments and
                            similarity > self.similarity_threshold and
                            similarity > best_similarity):
                        best_match = input_seg_idx
                        best_similarity = similarity

                if best_match is not None:
                    used_input_segments.add(best_match)

                matches.append({
                    'reference_index': ref_seg_idx,
                    'input_index': best_match,
                    'similarity': best_similarity,
                    'reference_text': reference_segments[ref_seg_idx].get('text', ''),
                    'input_text': input_segments[best_match].get('text', '') if best_match is not None else None,
                    'reference_start': reference_segments[ref_seg_idx].get('start', 0),
                    'reference_end': reference_segments[ref_seg_idx].get('end', 0),
                    'is_matched': best_match is not None,
                    'window_size': window_size
                })

        else:
            # Multi-segment windowed matching
            matches = self._windowed_sequence_matching(
                input_segments, reference_segments,
                valid_input_indices, valid_ref_indices,
                window_size
            )

        return matches

    def _windowed_sequence_matching(
            self,
            input_segments: List[Dict],
            reference_segments: List[Dict],
            valid_input_indices: List[int],
            valid_ref_indices: List[int],
            window_size: int
    ) -> List[Dict]:
        """
        Perform windowed sequence matching to find the best sequential alignments.
        """
        matches = []
        used_input_segments = set()

        # Create all possible windows for reference and input
        ref_windows = []
        for i in range(len(valid_ref_indices) - window_size + 1):
            window_indices = valid_ref_indices[i:i + window_size]
            ref_windows.append({
                'start_idx': i,
                'indices': window_indices,
                'texts': [reference_segments[idx].get('text', '') for idx in window_indices],
                'combined_text': ' '.join([reference_segments[idx].get('text', '') for idx in window_indices])
            })

        input_windows = []
        for i in range(len(valid_input_indices) - window_size + 1):
            window_indices = valid_input_indices[i:i + window_size]
            input_windows.append({
                'start_idx': i,
                'indices': window_indices,
                'texts': [input_segments[idx].get('text', '') for idx in window_indices],
                'combined_text': ' '.join([input_segments[idx].get('text', '') for idx in window_indices])
            })

        # Calculate window-to-window similarities
        window_matches = []
        for ref_window in ref_windows:
            best_input_window = None
            best_similarity = 0.0

            for input_window in input_windows:
                # Check if any segments in this input window are already used
                if any(idx in used_input_segments for idx in input_window['indices']):
                    continue

                # Calculate combined similarity for the window
                window_similarity = self._calculate_window_similarity(
                    ref_window, input_window, input_segments, reference_segments
                )

                if window_similarity > best_similarity and window_similarity > self.similarity_threshold:
                    best_similarity = window_similarity
                    best_input_window = input_window

            window_matches.append({
                'ref_window': ref_window,
                'input_window': best_input_window,
                'similarity': best_similarity,
                'is_matched': best_input_window is not None
            })

            # Mark input segments as used
            if best_input_window is not None:
                for idx in best_input_window['indices']:
                    used_input_segments.add(idx)

        # Convert window matches back to individual segment matches
        for ref_idx, ref_seg_idx in enumerate(valid_ref_indices):
            # Find which window this reference segment belongs to
            segment_match = None

            for window_match in window_matches:
                if ref_seg_idx in window_match['ref_window']['indices'] and window_match['is_matched']:
                    # Find corresponding input segment in the matched window
                    ref_position = window_match['ref_window']['indices'].index(ref_seg_idx)
                    input_seg_idx = window_match['input_window']['indices'][ref_position]

                    segment_match = {
                        'reference_index': ref_seg_idx,
                        'input_index': input_seg_idx,
                        'similarity': window_match['similarity'],
                        'reference_text': reference_segments[ref_seg_idx].get('text', ''),
                        'input_text': input_segments[input_seg_idx].get('text', ''),
                        'reference_start': reference_segments[ref_seg_idx].get('start', 0),
                        'reference_end': reference_segments[ref_seg_idx].get('end', 0),
                        'is_matched': True,
                        'window_size': window_size,
                        'window_similarity': window_match['similarity']
                    }
                    break

            # If no window match found, create unmatched entry
            if segment_match is None:
                segment_match = {
                    'reference_index': ref_seg_idx,
                    'input_index': None,
                    'similarity': 0.0,
                    'reference_text': reference_segments[ref_seg_idx].get('text', ''),
                    'input_text': None,
                    'reference_start': reference_segments[ref_seg_idx].get('start', 0),
                    'reference_end': reference_segments[ref_seg_idx].get('end', 0),
                    'is_matched': False,
                    'window_size': window_size,
                    'window_similarity': 0.0
                }

            matches.append(segment_match)

        return matches

    def _calculate_window_similarity(
            self,
            ref_window: Dict,
            input_window: Dict,
            input_segments: List[Dict],
            reference_segments: List[Dict]
    ) -> float:
        """
        Calculate similarity between two windows of segments.
        Combines text similarity and sequential audio feature similarity.
        """
        # Text similarity for combined window text
        ref_text = ref_window['combined_text'].lower()
        input_text = input_window['combined_text'].lower()

        # Use multiple text similarity methods
        text_similarities = []

        # 1. TF-IDF similarity
        try:
            texts = [ref_text, input_text]
            if len(texts) > 1 and ref_text and input_text:
                tfidf_matrix = self.vectorizer.fit_transform(texts)
                tfidf_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
                text_similarities.append(tfidf_sim)
        except:
            pass

        # 2. String similarity (Levenshtein-based)
        if ref_text and input_text:
            string_sim = difflib.SequenceMatcher(None, ref_text, input_text).ratio()
            text_similarities.append(string_sim)

        # 3. Word overlap similarity
        if ref_text and input_text:
            ref_words = set(ref_text.split())
            input_words = set(input_text.split())
            if ref_words or input_words:
                overlap_sim = len(ref_words.intersection(input_words)) / len(ref_words.union(input_words))
                text_similarities.append(overlap_sim)

        # Take best text similarity
        text_similarity = max(text_similarities) if text_similarities else 0.0

        # Audio feature similarity across the window
        audio_similarities = []
        for i in range(len(ref_window['indices'])):
            ref_idx = ref_window['indices'][i]
            input_idx = input_window['indices'][i]

            ref_seg = reference_segments[ref_idx]
            input_seg = input_segments[input_idx]

            # Individual segment audio similarity
            audio_sim = self._calculate_audio_similarity(ref_seg, input_seg)
            audio_similarities.append(audio_sim)

        # Average audio similarity across window
        audio_similarity = sum(audio_similarities) / len(audio_similarities) if audio_similarities else 0.0

        # Sequential bonus - reward consecutive matching patterns
        sequential_bonus = 0.1 if len(ref_window['indices']) > 1 else 0.0

        # Combined similarity with weights
        combined_similarity = (0.6 * text_similarity + 0.3 * audio_similarity + sequential_bonus)

        return min(1.0, combined_similarity)

    def _calculate_audio_similarity(self, ref_seg: Dict, input_seg: Dict) -> float:
        """
        Calculate audio feature similarity between two segments.
        """
        # Compare energy, pitch, duration
        energy_sim = 1 - abs(ref_seg.get('energy', 0.5) - input_seg.get('energy', 0.5))
        pitch_sim = 1 - abs(ref_seg.get('pitch', 0.5) - input_seg.get('pitch', 0.5))

        # Duration similarity (normalized)
        ref_duration = ref_seg.get('end', 0) - ref_seg.get('start', 0)
        input_duration = input_seg.get('end', 0) - input_seg.get('start', 0)
        duration_ratio = min(ref_duration, input_duration) / max(ref_duration, input_duration, 0.1)

        # Combine audio features
        return (energy_sim + pitch_sim + duration_ratio) / 3

    def _calculate_matching_quality(self, matches: List[Dict]) -> float:
        """
        Calculate overall quality score for a set of matches.
        Considers match rate, average similarity, and sequential coherence.
        """
        if not matches:
            return 0.0

        matched_segments = [m for m in matches if m['is_matched']]

        # Base metrics
        match_rate = len(matched_segments) / len(matches)
        avg_similarity = sum([m['similarity'] for m in matched_segments]) / max(1, len(matched_segments))

        # Sequential coherence bonus
        sequential_bonus = 0.0
        if len(matched_segments) > 1:
            consecutive_matches = 0
            for i in range(len(matches) - 1):
                if matches[i]['is_matched'] and matches[i + 1]['is_matched']:
                    # Check if input segments are also consecutive
                    if matches[i]['input_index'] is not None and matches[i + 1]['input_index'] is not None:
                        if abs(matches[i]['input_index'] - matches[i + 1]['input_index']) <= 2:
                            consecutive_matches += 1

            sequential_bonus = consecutive_matches / max(1, len(matches) - 1) * 0.2

        # Quality score combines match rate, similarity, and sequential coherence
        quality_score = (0.4 * match_rate + 0.4 * avg_similarity + 0.2 * sequential_bonus)

        return quality_score

    def create_arranged_audio(self, input_path: str, arranged_segments: List[Dict], output_path: str) -> str:
        """
        Create audio file from arranged segments (for backward compatibility).
        """
        try:
            # Load input audio
            audio, sr = librosa.load(input_path, sr=None)

            # Calculate total duration
            if not arranged_segments:
                return output_path

            total_duration = max([seg['end'] for seg in arranged_segments])
            output_length = int(total_duration * sr)
            output_audio = np.zeros(output_length)

            # Combine segments
            for segment in arranged_segments:
                if segment.get('text') == '[SILENCE]':
                    continue  # Skip silence segments

                start_sample = int(segment['start'] * sr)
                end_sample = int(segment['end'] * sr)

                # Get original segment timing if available
                original_start = segment.get('original_start', segment['start'])
                original_end = segment.get('original_end', segment['end'])

                orig_start_sample = int(original_start * sr)
                orig_end_sample = int(original_end * sr)

                # Extract and place audio
                if orig_end_sample <= len(audio):
                    segment_audio = audio[orig_start_sample:orig_end_sample]
                    target_length = end_sample - start_sample

                    if len(segment_audio) != target_length and target_length > 0:
                        # Time-stretch to fit
                        stretch_ratio = len(segment_audio) / target_length
                        segment_audio = librosa.effects.time_stretch(segment_audio, rate=stretch_ratio)

                        # Ensure exact length
                        if len(segment_audio) > target_length:
                            segment_audio = segment_audio[:target_length]
                        elif len(segment_audio) < target_length:
                            segment_audio = np.pad(segment_audio, (0, target_length - len(segment_audio)))

                    output_audio[start_sample:end_sample] = segment_audio

            # Save output
            sf.write(output_path, output_audio, sr)
            return output_path

        except Exception as e:
            logger.error(f"Failed to create arranged audio: {e}")
            raise

    def _calculate_similarity_matrix(
            self,
            input_segments: List[Dict],
            reference_segments: List[Dict],
            valid_input_indices: List[int],
            valid_ref_indices: List[int]
    ) -> np.ndarray:
        """
        Calculate similarity matrix combining text and audio features.
        """
        # Text similarity using TF-IDF
        input_texts = [input_segments[i].get('text', '') for i in valid_input_indices]
        ref_texts = [reference_segments[i].get('text', '') for i in valid_ref_indices]

        all_texts = ref_texts + input_texts

        if len(all_texts) > 1:
            try:
                tfidf_matrix = self.vectorizer.fit_transform(all_texts)
                ref_tfidf = tfidf_matrix[:len(ref_texts)]
                input_tfidf = tfidf_matrix[len(ref_texts):]
                text_similarity = cosine_similarity(ref_tfidf, input_tfidf)
            except Exception as e:
                logger.warning(f"TF-IDF failed, using string similarity: {e}")
                text_similarity = self._string_similarity_matrix(ref_texts, input_texts)
        else:
            text_similarity = np.array([[1.0]])

        # Audio feature similarity
        audio_similarity = self._audio_similarity_matrix(
            input_segments, reference_segments,
            valid_input_indices, valid_ref_indices
        )

        # Combine similarities (weighted: 60% text, 40% audio)
        combined_similarity = 0.6 * text_similarity + 0.4 * audio_similarity

        return combined_similarity

    def _string_similarity_matrix(self, ref_texts: List[str], input_texts: List[str]) -> np.ndarray:
        """Calculate string similarity using difflib."""
        similarity_matrix = np.zeros((len(ref_texts), len(input_texts)))

        for i, ref_text in enumerate(ref_texts):
            for j, input_text in enumerate(input_texts):
                similarity = difflib.SequenceMatcher(None, ref_text.lower(), input_text.lower()).ratio()
                similarity_matrix[i, j] = similarity

        return similarity_matrix

    def _audio_similarity_matrix(
            self,
            input_segments: List[Dict],
            reference_segments: List[Dict],
            valid_input_indices: List[int],
            valid_ref_indices: List[int]
    ) -> np.ndarray:
        """Calculate audio feature similarity."""
        similarity_matrix = np.zeros((len(valid_ref_indices), len(valid_input_indices)))

        for i, ref_idx in enumerate(valid_ref_indices):
            ref_seg = reference_segments[ref_idx]

            for j, input_idx in enumerate(valid_input_indices):
                input_seg = input_segments[input_idx]

                # Compare energy, pitch, duration
                energy_sim = 1 - abs(ref_seg.get('energy', 0.5) - input_seg.get('energy', 0.5))
                pitch_sim = 1 - abs(ref_seg.get('pitch', 0.5) - input_seg.get('pitch', 0.5))

                # Duration similarity (normalized)
                ref_duration = ref_seg.get('end', 0) - ref_seg.get('start', 0)
                input_duration = input_seg.get('end', 0) - input_seg.get('start', 0)
                duration_ratio = min(ref_duration, input_duration) / max(ref_duration, input_duration, 0.1)

                # Combine audio features
                audio_sim = (energy_sim + pitch_sim + duration_ratio) / 3
                similarity_matrix[i, j] = audio_sim

        return similarity_matrix

    def _create_alignment_plan(self, matches: List[Dict], reference_segments: List[Dict]) -> List[Dict]:
        """
        Create temporal alignment plan based on matches.
        """
        alignment_plan = []

        for match in matches:
            ref_start = match['reference_start']
            ref_end = match['reference_end']

            plan_item = {
                'start_time': ref_start,
                'end_time': ref_end,
                'duration': ref_end - ref_start,
                'input_segment_index': match['input_index'],
                'reference_segment_index': match['reference_index'],
                'is_silence': not match['is_matched'],
                'similarity': match['similarity'],
                'reference_text': match['reference_text']  # Add reference text to plan
            }

            alignment_plan.append(plan_item)

        return alignment_plan

    def _create_temporal_audio(
            self,
            input_audio_path: str,
            input_segments: List[Dict],
            alignment_plan: List[Dict],
            output_path: str
    ) -> str:
        """
        Create time-aligned audio based on alignment plan with enhanced audio quality.
        Implements crossfading, better time-stretching, and audio smoothing techniques.
        """
        try:
            # Load input audio with higher quality settings
            input_audio, sr = librosa.load(input_audio_path, sr=None, mono=True)

            # Calculate total duration from reference
            total_duration = max([item['end_time'] for item in alignment_plan])
            output_length = int(total_duration * sr)

            # Initialize output audio with silence
            output_audio = np.zeros(output_length, dtype=np.float32)

            # Enhanced audio processing parameters
            fade_duration = min(0.02, 0.1)  # 20ms crossfade, max 100ms
            fade_samples = int(fade_duration * sr)

            # Fill in matched segments with enhanced processing
            for plan_item in alignment_plan:
                start_sample = int(plan_item['start_time'] * sr)
                end_sample = int(plan_item['end_time'] * sr)

                if not plan_item['is_silence'] and plan_item['input_segment_index'] is not None:
                    # Get input segment audio with padding for smooth transitions
                    input_seg = input_segments[plan_item['input_segment_index']]
                    seg_start_sample = int(input_seg['start'] * sr)
                    seg_end_sample = int(input_seg['end'] * sr)

                    # Add small padding around segment for better quality
                    padding_samples = int(0.01 * sr)  # 10ms padding
                    padded_start = max(0, seg_start_sample - padding_samples)
                    padded_end = min(len(input_audio), seg_end_sample + padding_samples)

                    segment_audio = input_audio[padded_start:padded_end].copy()

                    # Enhanced time-stretching if needed
                    target_length = end_sample - start_sample
                    if len(segment_audio) != target_length and target_length > 0:
                        segment_audio = self._high_quality_time_stretch(
                            segment_audio, target_length, sr
                        )

                    # Apply fade-in and fade-out to prevent clicks
                    segment_audio = self._apply_crossfades(segment_audio, fade_samples)

                    # Ensure exact length after processing
                    if len(segment_audio) > target_length:
                        segment_audio = segment_audio[:target_length]
                    elif len(segment_audio) < target_length:
                        segment_audio = np.pad(segment_audio, (0, target_length - len(segment_audio)))

                    # Advanced placement with overlap handling
                    self._place_segment_with_crossfade(
                        output_audio, segment_audio, start_sample, end_sample, fade_samples
                    )

            # Post-process the entire output for smoothness
            output_audio = self._post_process_audio(output_audio, sr)

            # Save output audio with high quality settings
            sf.write(output_path, output_audio, sr, subtype='PCM_16')
            logger.info(f"Created high-quality temporal audio: {output_path}")

            return output_path

        except Exception as e:
            logger.error(f"Failed to create temporal audio: {e}")
            raise

    def _high_quality_time_stretch(self, audio: np.ndarray, target_length: int, sr: int) -> np.ndarray:
        """
        High-quality time stretching using phase vocoder with overlap-add.
        """
        try:
            if len(audio) == target_length:
                return audio

            # Calculate stretch ratio
            stretch_ratio = len(audio) / target_length

            # Use librosa's phase vocoder for high-quality time stretching
            # This maintains phase coherence and reduces artifacts
            stretched_audio = librosa.effects.time_stretch(
                audio,
                rate=stretch_ratio,
                hop_length=512,  # Smaller hop for better quality
                n_fft=2048  # Larger FFT for better frequency resolution
            )

            # Apply gentle low-pass filter to reduce high-frequency artifacts
            # Only if significant stretching occurred
            if abs(stretch_ratio - 1.0) > 0.2:  # If stretch > 20%
                from scipy import signal
                # Design anti-aliasing filter
                nyquist = sr / 2
                cutoff = min(8000, nyquist * 0.8)  # Gentle cutoff at 8kHz or 80% Nyquist
                b, a = signal.butter(4, cutoff / nyquist, btype='low')
                stretched_audio = signal.filtfilt(b, a, stretched_audio)

            return stretched_audio.astype(np.float32)

        except Exception as e:
            logger.warning(f"Advanced time stretch failed, using basic method: {e}")
            # Fallback to simple resampling if phase vocoder fails
            from scipy import signal
            return signal.resample(audio, target_length).astype(np.float32)

    def _apply_crossfades(self, audio: np.ndarray, fade_samples: int) -> np.ndarray:
        """
        Apply smooth fade-in and fade-out to audio segment.
        """
        if len(audio) <= fade_samples * 2:
            # For very short segments, apply gentle envelope
            envelope_length = len(audio) // 4
            if envelope_length > 0:
                fade_in = np.linspace(0, 1, envelope_length)
                fade_out = np.linspace(1, 0, envelope_length)
                audio[:envelope_length] *= fade_in
                audio[-envelope_length:] *= fade_out
        else:
            # Apply cosine-shaped fades for smooth transitions
            fade_in = 0.5 * (1 - np.cos(np.linspace(0, np.pi, fade_samples)))
            fade_out = 0.5 * (1 - np.cos(np.linspace(np.pi, 2 * np.pi, fade_samples)))

            audio[:fade_samples] *= fade_in
            audio[-fade_samples:] *= fade_out

        return audio

    def _place_segment_with_crossfade(
            self,
            output_audio: np.ndarray,
            segment_audio: np.ndarray,
            start_sample: int,
            end_sample: int,
            fade_samples: int
    ):
        """
        Place segment in output with intelligent crossfading to avoid clicks.
        """
        segment_length = len(segment_audio)
        target_length = end_sample - start_sample

        # Ensure we don't exceed output bounds
        actual_end = min(start_sample + segment_length, len(output_audio), end_sample)
        actual_length = actual_end - start_sample

        if actual_length <= 0:
            return

        # Trim segment if necessary
        if segment_length > actual_length:
            segment_audio = segment_audio[:actual_length]

        # Check for overlap with existing audio
        existing_audio = output_audio[start_sample:actual_end]
        has_existing_content = np.any(np.abs(existing_audio) > 1e-6)

        if has_existing_content and fade_samples > 0:
            # Intelligent mixing of overlapping content
            overlap_start = max(0, fade_samples)
            overlap_end = min(len(segment_audio), len(existing_audio))

            if overlap_end > overlap_start:
                # Create smooth transition between existing and new audio
                mix_length = overlap_end - overlap_start
                mix_fade = np.linspace(1, 0, mix_length)  # Fade out existing
                new_fade = np.linspace(0, 1, mix_length)  # Fade in new

                mixed_section = (existing_audio[overlap_start:overlap_end] * mix_fade +
                                 segment_audio[overlap_start:overlap_end] * new_fade)

                # Place the mixed section
                output_audio[start_sample + overlap_start:start_sample + overlap_end] = mixed_section

                # Place non-overlapping parts
                if overlap_start > 0:
                    output_audio[start_sample:start_sample + overlap_start] = segment_audio[:overlap_start]
                if overlap_end < len(segment_audio):
                    output_audio[start_sample + overlap_end:actual_end] = segment_audio[overlap_end:actual_length]
            else:
                output_audio[start_sample:actual_end] = segment_audio[:actual_length]
        else:
            # No overlap, direct placement
            output_audio[start_sample:actual_end] = segment_audio[:actual_length]

    def _post_process_audio(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """
        Apply final post-processing to improve overall audio quality.
        """
        try:
            # 1. Gentle normalization to prevent clipping
            max_amplitude = np.max(np.abs(audio))
            if max_amplitude > 0.95:  # If close to clipping
                audio = audio * (0.9 / max_amplitude)  # Normalize to -0.9dB peak

            # 2. Apply gentle high-pass filter to remove DC offset and low-end rumble
            from scipy import signal
            # High-pass at 80Hz to remove DC and very low frequencies
            nyquist = sr / 2
            high_cutoff = 80.0 / nyquist
            if high_cutoff < 0.5:  # Ensure valid frequency
                b, a = signal.butter(2, high_cutoff, btype='high')
                audio = signal.filtfilt(b, a, audio)

            # 3. Apply very gentle compression to even out levels
            audio = self._gentle_compression(audio)

            # 4. Final gentle limiter to prevent any remaining artifacts
            audio = np.clip(audio, -0.98, 0.98)

            return audio.astype(np.float32)

        except Exception as e:
            logger.warning(f"Post-processing failed, returning original: {e}")
            return audio

    def _gentle_compression(self, audio: np.ndarray, threshold: float = 0.7, ratio: float = 2.0) -> np.ndarray:
        """
        Apply gentle compression to smooth out level differences.
        """
        try:
            # Simple soft-knee compression
            abs_audio = np.abs(audio)
            gain = np.ones_like(abs_audio)

            # Find samples above threshold
            above_threshold = abs_audio > threshold
            if np.any(above_threshold):
                # Calculate compression gain
                excess = abs_audio[above_threshold] - threshold
                compressed_excess = excess / ratio
                gain[above_threshold] = (threshold + compressed_excess) / abs_audio[above_threshold]

            # Apply gain smoothing to avoid artifacts
            from scipy import ndimage
            gain_smooth = ndimage.gaussian_filter1d(gain, sigma=1.0)

            return audio * gain_smooth

        except Exception as e:
            logger.warning(f"Compression failed: {e}")
            return audio
