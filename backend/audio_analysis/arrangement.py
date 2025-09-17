import json
import logging
from typing import List, Dict, Optional, Tuple

from .llm_utils import OpenRouterClient

logger = logging.getLogger(__name__)


class AIVocalArranger:
    """
    AI-driven vocal arrangement system that uses LLM analysis to organize
    vocal segments into coherent song structures based on lyrics, energy, and mood.
    """

    def __init__(self):
        self.llm_client = OpenRouterClient()

        # Song structure templates for reference
        self.structure_templates = {
            "standard_pop": ["intro", "verse", "chorus", "verse", "chorus", "bridge", "chorus", "outro"],
            "hip_hop": ["intro", "verse", "hook", "verse", "hook", "bridge", "hook", "outro"],
            "rnb": ["intro", "verse", "pre_chorus", "chorus", "verse", "pre_chorus", "chorus", "bridge", "chorus",
                    "outro"],
            "simple": ["intro", "verse", "chorus", "verse", "chorus", "outro"]
        }

    def arrange_segments(self, segments: List[Dict], target_structure: str = "auto",
                         genre_hint: Optional[str] = None) -> Tuple[List[int], float, Dict]:
        """
        Main arrangement method using AI/LLM analysis.

        Args:
            segments: List of segment dictionaries with text, energy, pitch, etc.
            target_structure: Target song structure or "auto"
            genre_hint: Genre hint for arrangement style

        Returns:
            Tuple of (arrangement_indices, confidence, analysis)
        """
        try:
            # Get LLM arrangement
            arrangement, confidence, analysis = self._get_llm_arrangement(segments, genre_hint)
            return arrangement, confidence, analysis

        except Exception as e:
            logger.error(f"AI arrangement failed: {e}")
            # Fallback to original order
            fallback = list(range(len(segments)))
            return fallback, 0.3, {"error": str(e), "method": "fallback"}

    def _get_llm_arrangement(self, segments: List[Dict], genre_hint: Optional[str] = None) -> Tuple[
        List[int], float, Dict]:
        """
        Get arrangement using LLM analysis of lyrics, energy, and mood.
        """
        if not self.llm_client.is_available():
            raise Exception("AI model not available - check OPENROUTER_API_KEY")

        # Prepare structured input for LLM
        segment_descriptions = self._prepare_segment_descriptions(segments)

        # Create LLM prompt
        prompt = self._create_arrangement_prompt(segment_descriptions, genre_hint)

        # Get LLM response
        response = self.llm_client.generate_completion(prompt, max_tokens=500)

        if not response:
            raise Exception("No response from AI model")

        # Parse LLM response
        arrangement, confidence, analysis = self._parse_llm_response(response, len(segments))

        return arrangement, confidence, analysis

    def _prepare_segment_descriptions(self, segments: List[Dict]) -> List[str]:
        """
        Convert segments into structured descriptions for LLM analysis.
        """
        descriptions = []

        for i, segment in enumerate(segments):
            text = segment.get('text', '').strip()
            energy = segment.get('energy', 0.5)
            pitch = segment.get('pitch', 0.5)
            duration = segment.get('duration', segment.get('end', 0) - segment.get('start', 0))

            # Use enhanced features if available (from new extract_features)
            energy_category = segment.get('energy_category', self._categorize_energy(energy))
            pitch_category = segment.get('pitch_category', self._categorize_pitch(pitch))

            # Detect structural hints
            likely_intro = segment.get('likely_intro', self._detect_intro(text, i, len(segments)))
            likely_outro = segment.get('likely_outro', self._detect_outro(text, i, len(segments)))
            likely_hook = segment.get('likely_hook', self._detect_hook(text, energy))
            is_repetitive = segment.get('is_repetitive', self._is_repetitive_text(text))

            # Analyze lyrics for mood/content
            mood = self._analyze_segment_mood(text)

            desc = f"Segment {i + 1}: \"{text}\" – {energy_category}, {pitch_category}, {mood}"

            # Add duration info
            if duration > 10:
                desc += ", long phrase"
            elif duration < 3:
                desc += ", short phrase"

            # Add structural hints
            hints = []
            if likely_intro: hints.append("intro-like")
            if likely_outro: hints.append("outro-like")
            if likely_hook: hints.append("hook-like")
            if is_repetitive: hints.append("repetitive")

            if hints:
                desc += f" ({', '.join(hints)})"

            descriptions.append(desc)

        return descriptions

    def _categorize_energy(self, energy: float) -> str:
        """Categorize energy level."""
        if energy > 0.75:
            return "very high energy"
        elif energy > 0.6:
            return "high energy"
        elif energy > 0.4:
            return "moderate energy"
        elif energy > 0.25:
            return "low energy"
        else:
            return "very low energy"

    def _categorize_pitch(self, pitch: float) -> str:
        """Categorize pitch level."""
        if pitch > 0.75:
            return "very high pitch"
        elif pitch > 0.6:
            return "high pitch"
        elif pitch > 0.4:
            return "mid-range pitch"
        elif pitch > 0.25:
            return "low pitch"
        else:
            return "very low pitch"

    def _detect_intro(self, text: str, index: int, total: int) -> bool:
        """Detect if segment is likely an intro."""
        if index > 2: return False
        intro_words = ["let's go", "come on", "here we go", "yo", "uh", "yeah", "intro", "start"]
        return any(word in text.lower() for word in intro_words)

    def _detect_outro(self, text: str, index: int, total: int) -> bool:
        """Detect if segment is likely an outro."""
        if index < total - 3: return False
        outro_words = ["goodbye", "end", "outro", "fade", "bye", "finish", "done"]
        return any(word in text.lower() for word in outro_words)

    def _detect_hook(self, text: str, energy: float) -> bool:
        """Detect if segment is likely a hook/chorus."""
        return (energy > 0.6 and self._is_repetitive_text(text)) or len(text.split()) <= 8

    def _is_repetitive_text(self, text: str) -> bool:
        """Check if text is repetitive (good for hooks)."""
        if not text: return False
        words = text.lower().split()
        if len(words) < 3: return False
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
        max_repeats = max(word_counts.values())
        return max_repeats >= 3 or max_repeats / len(words) > 0.4

    def _analyze_segment_mood(self, text: str) -> str:
        """Simple mood/content analysis of lyrics."""
        if not text: return "neutral"

        text_lower = text.lower()

        # Emotional keywords
        positive_words = ["love", "happy", "joy", "fly", "high", "amazing", "good", "great"]
        intense_words = ["fight", "power", "strong", "fire", "wild", "crazy", "loud"]
        sad_words = ["cry", "sad", "lonely", "hurt", "pain", "lost", "down"]
        party_words = ["party", "dance", "club", "night", "music", "beat"]

        if any(word in text_lower for word in party_words):
            return "party/energetic"
        elif any(word in text_lower for word in intense_words):
            return "intense/powerful"
        elif any(word in text_lower for word in positive_words):
            return "uplifting/positive"
        elif any(word in text_lower for word in sad_words):
            return "emotional/sad"
        else:
            return "neutral"

    def _create_arrangement_prompt(self, descriptions: List[str], genre_hint: Optional[str] = None) -> str:
        """Create the LLM prompt for vocal arrangement."""
        genre_context = f"for a {genre_hint} song" if genre_hint else ""

        prompt = f"""You are a professional music arranger. Arrange these vocal segments into a coherent song structure {genre_context}.

Vocal segments:
{chr(10).join(descriptions)}

Your task:
1. Assign each segment to a song section (intro, verse, chorus, bridge, outro)  
2. Order segments logically (some may repeat for choruses)
3. Consider lyrical flow, energy progression, and musical coherence

Arrangement principles:
- Start with intro-like or low energy segments
- Build energy toward choruses/hooks
- Use repetitive segments for choruses
- Create contrast with bridges
- End with outro-like or calming segments
- Ensure smooth lyrical transitions

Respond in this exact JSON format:
{{
    "arrangement": [
        {{"segment_index": 0, "section": "intro", "position": 1}},
        {{"segment_index": 1, "section": "verse", "position": 2}},
        {{"segment_index": 2, "section": "chorus", "position": 3}}
    ],
    "reasoning": "Brief explanation of arrangement choices",
    "confidence": 0.8
}}

Focus on creating natural flow and energy progression."""

        return prompt

    def _parse_llm_response(self, response: str, num_segments: int) -> Tuple[List[int], float, Dict]:
        """Parse LLM response and extract arrangement information."""
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                parsed = json.loads(json_str)

                # Extract arrangement order
                arrangement_data = parsed.get('arrangement', [])
                arrangement = []

                # Sort by position and extract segment indices
                sorted_arrangement = sorted(arrangement_data, key=lambda x: x.get('position', 0))
                for item in sorted_arrangement:
                    seg_idx = item.get('segment_index')
                    if seg_idx is not None and 0 <= seg_idx < num_segments:
                        arrangement.append(seg_idx)

                # Ensure all segments are used at least once
                used_segments = set(arrangement)
                missing_segments = [i for i in range(num_segments) if i not in used_segments]
                arrangement.extend(missing_segments)

                confidence = parsed.get('confidence', 0.6)
                reasoning = parsed.get('reasoning', 'No reasoning provided')

                analysis = {
                    'sections': {item.get('segment_index'): item.get('section') for item in arrangement_data},
                    'reasoning': reasoning,
                    'method': 'ai_llm',
                    'response': response
                }

                return arrangement, confidence, analysis

        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")

        # Fallback arrangement
        fallback_arrangement = list(range(num_segments))
        return fallback_arrangement, 0.4, {
            'error': 'Failed to parse AI response',
            'method': 'fallback',
            'raw_response': response
        }

    def arrange_segments_to_reference(self, input_segments: List[Dict], reference_segments: List[Dict],
                                      genre_hint: Optional[str] = None) -> Tuple[List[int], float, Dict]:
        """
        Arrange input vocal segments to match the structure and energy flow of reference segments.
        Uses LLM to analyze both sets and create optimal arrangement.
        """
        try:
            # Get LLM arrangement based on reference structure
            arrangement, confidence, analysis = self._get_llm_reference_arrangement(
                input_segments, reference_segments, genre_hint
            )
            return arrangement, confidence, analysis

        except Exception as e:
            logger.error(f"Reference-based arrangement failed: {e}")
            # Fallback to original order
            fallback = list(range(len(input_segments)))
            return fallback, 0.3, {"error": str(e), "method": "fallback"}

    def _get_llm_reference_arrangement(self, input_segments: List[Dict], reference_segments: List[Dict],
                                       genre_hint: Optional[str] = None) -> Tuple[List[int], float, Dict]:
        """
        Use LLM to arrange input segments to match reference track structure.
        """
        if not self.llm_client.is_available():
            raise Exception("AI model not available - check OPENROUTER_API_KEY")

        # Prepare input and reference segment descriptions
        input_descriptions = self._prepare_segment_descriptions(input_segments)
        reference_descriptions = self._prepare_reference_descriptions(reference_segments)

        # Create LLM prompt for reference-based arrangement
        prompt = self._create_reference_arrangement_prompt(
            input_descriptions, reference_descriptions, genre_hint
        )

        # Get LLM response
        response = self.llm_client.generate_completion(prompt, max_tokens=600)

        if not response:
            raise Exception("No response from AI model")

        # Parse LLM response
        arrangement, confidence, analysis = self._parse_reference_arrangement_response(
            response, len(input_segments)
        )

        return arrangement, confidence, analysis

    def _prepare_reference_descriptions(self, reference_segments: List[Dict]) -> List[str]:
        """
        Convert reference segments into structured descriptions for LLM analysis.
        """
        descriptions = []

        for i, segment in enumerate(reference_segments):
            text = segment.get('text', '').strip()
            energy = segment.get('energy', 0.5)
            pitch = segment.get('pitch', 0.5)
            duration = segment.get('duration', segment.get('end', 0) - segment.get('start', 0))

            energy_category = segment.get('energy_category', self._categorize_energy(energy))
            pitch_category = segment.get('pitch_category', self._categorize_pitch(pitch))

            timing = f"{segment.get('start', 0):.1f}s-{segment.get('end', 0):.1f}s"

            desc = f"Reference {i + 1} ({timing}): \"{text}\" – {energy_category}, {pitch_category}"

            if duration > 10:
                desc += ", long section"
            elif duration < 3:
                desc += ", short section"

            descriptions.append(desc)

        return descriptions

    def _create_reference_arrangement_prompt(self, input_descriptions: List[str],
                                             reference_descriptions: List[str],
                                             genre_hint: Optional[str] = None) -> str:
        """
        Create LLM prompt for arranging input segments to match reference structure.
        """
        genre_context = f"for a {genre_hint} song" if genre_hint else ""

        prompt = f"""You are a professional music arranger. You need to arrange the INPUT VOCAL SEGMENTS to match the structure, energy flow, and timing of the REFERENCE TRACK {genre_context}.

REFERENCE TRACK STRUCTURE:
{chr(10).join(reference_descriptions)}

INPUT VOCAL SEGMENTS TO ARRANGE:
{chr(10).join(input_descriptions)}

Your task:
1. Analyze the reference track's energy progression, timing, and structural flow
2. Match input segments to reference segments based on:
   - Similar energy levels (high energy input → high energy reference positions)
   - Compatible lyrical content and mood
   - Appropriate segment duration and timing
   - Musical flow and contrast
3. Some input segments may be used multiple times, some may not be used
4. The goal is to create a vocal arrangement that follows the reference track's energy and structural pattern

Arrangement principles:
- Match energy progression: high energy input segments go to high energy reference positions
- Respect timing: longer input segments for longer reference sections
- Create smooth transitions between segments
- Use repetition strategically (choruses, hooks)
- Maintain the reference track's overall arc and flow

Respond in this exact JSON format:
{{
    "arrangement": [
        {{"input_segment_index": 0, "reference_position": 1, "reasoning": "Low energy intro matches reference"}},
        {{"input_segment_index": 2, "reference_position": 2, "reasoning": "High energy content for chorus section"}},
        {{"input_segment_index": 1, "reference_position": 3, "reasoning": "Melodic content for verse"}}
    ],
    "energy_matching": "Brief explanation of how energy levels were matched",
    "structural_analysis": "Analysis of how arrangement follows reference structure",
    "confidence": 0.8
}}

Focus on creating an arrangement that captures the reference track's energy and structural essence."""

        return prompt

    def _parse_reference_arrangement_response(self, response: str, num_input_segments: int) -> Tuple[
        List[int], float, Dict]:
        """
        Parse LLM response for reference-based arrangement.
        """
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                parsed = json.loads(json_str)

                # Extract arrangement order
                arrangement_data = parsed.get('arrangement', [])
                arrangement = []

                # Sort by reference position and extract input segment indices
                sorted_arrangement = sorted(arrangement_data, key=lambda x: x.get('reference_position', 0))
                for item in sorted_arrangement:
                    seg_idx = item.get('input_segment_index')
                    if seg_idx is not None and 0 <= seg_idx < num_input_segments:
                        arrangement.append(seg_idx)

                # Fill any missing positions with unused segments
                used_segments = set(arrangement)
                unused_segments = [i for i in range(num_input_segments) if i not in used_segments]
                arrangement.extend(unused_segments)

                confidence = parsed.get('confidence', 0.7)

                analysis = {
                    'energy_matching': parsed.get('energy_matching', 'No energy analysis provided'),
                    'structural_analysis': parsed.get('structural_analysis', 'No structural analysis provided'),
                    'method': 'llm_reference_arrangement',
                    'arrangement_details': arrangement_data,
                    'response': response
                }

                return arrangement, confidence, analysis

        except Exception as e:
            logger.error(f"Failed to parse reference arrangement response: {e}")

        # Fallback arrangement
        fallback_arrangement = list(range(num_input_segments))
        return fallback_arrangement, 0.4, {
            'error': 'Failed to parse AI response',
            'method': 'fallback',
            'raw_response': response
        }
