import logging
import os
from typing import List, Dict, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


class OpenRouterClient:
    def __init__(self, api_key: str = None, model: str = "gpt-oss"):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"
        self.session = requests.Session()

        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            })

    def is_available(self) -> bool:
        """Check if OpenRouter API is available."""
        if not self.api_key:
            logger.error("OpenRouter API key not provided")
            return False

        try:
            # Test with a simple request
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 1
                },
                timeout=10
            )
            return response.status_code in [200, 429]  # 429 is rate limit, but API is available
        except Exception as e:
            logger.error(f"Failed to connect to OpenRouter: {e}")
            return False

    def generate_completion(self, prompt: str, max_tokens: int = 300) -> Optional[str]:
        """Generate text completion using OpenRouter API."""
        if not self.api_key:
            logger.error("OpenRouter API key not provided")
            return None

        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a professional music arranger who specializes in vocal arrangement and song structure."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.1,
                "top_p": 0.9
            }

            response = self.session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=45
            )

            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"].strip()
                else:
                    logger.error("No choices in OpenRouter response")
                    return None
            else:
                logger.error(f"OpenRouter request failed: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error generating completion: {e}")
            return None

    def analyze_segment_sequence(self, segments: List[Dict]) -> Tuple[List[str], List[int]]:
        """
        Analyze the full sequence of segments for optimal arrangement.
        Returns structure analysis and suggested arrangement order.
        """
        if not segments:
            return [], []

        # Create comprehensive segment description
        segment_descriptions = []
        for i, seg in enumerate(segments):
            text = seg.get('text', '').strip()[:100]  # Truncate very long text
            energy = seg.get('energy', 0)
            duration = seg.get('duration', 0)
            pause = seg.get('pause', 0)

            desc = f"[{i}] \"{text}\" (E:{energy:.3f}, D:{duration:.1f}s, P:{pause:.1f}s)"
            segment_descriptions.append(desc)

        max_id = len(segment_descriptions) - 1
        prompt = f"""Rearrange these vocal segments into a coherent song.

        Rules:
        - Use only segment numbers 0-{max_id}.
        - Output only the arrangement as comma-separated numbers.
        - Intro = low energy
        - Verse = medium energy
        - Chorus = high energy, repeated
        - Bridge = contrast
        - Outro = calm

        Segments:
        {chr(10).join(segment_descriptions)}

        Output only:
        ARRANGEMENT:"""

        result = self.generate_completion(prompt, max_tokens=100)

        if result:
            try:
                return self._parse_arrangement_response(result, len(segments))
            except Exception as e:
                logger.error(f"Failed to parse arrangement response: {e}")

        # Fallback: return original order
        return ["original"], list(range(len(segments)))

    def _parse_arrangement_response(self, response: str, num_segments: int) -> Tuple[List[str], List[int]]:
        """Parse the LLM response for arrangement order."""
        try:
            # Look for the arrangement line
            lines = response.strip().split('\n')
            arrangement_line = None

            for line in lines:
                if 'ARRANGEMENT:' in line.upper() or any(char.isdigit() for char in line):
                    arrangement_line = line
                    break

            if not arrangement_line:
                arrangement_line = lines[-1] if lines else ""

            # Extract numbers
            import re
            numbers = re.findall(r'\d+', arrangement_line)
            arrangement = [int(n) for n in numbers if 0 <= int(n) < num_segments]

            # Ensure all segments are included
            if len(set(arrangement)) != num_segments:
                logger.warning("LLM arrangement incomplete, using original order")
                arrangement = list(range(num_segments))

            return ["llm_analysis"], arrangement

        except Exception as e:
            logger.error(f"Error parsing arrangement response: {e}")
            return ["error"], list(range(num_segments))
