import logging
import time
from typing import List, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "phi:latest"):
        self.base_url = base_url
        self.model = model
        self.session = requests.Session()

    def is_available(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            response = self.session.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = [m["name"] for m in response.json().get("models", [])]
                return self.model in models
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            return False

    def generate_completion(self, prompt: str, max_tokens: int = 150) -> Optional[str]:
        """Generate text completion using Ollama."""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_ctx": 2048,
                    "temperature": 0.1,
                    "top_p": 0.9
                }
            }

            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                logger.error(f"Ollama request failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error generating completion: {e}")
            return None

    def tag_segment_structure(self, text: str, energy: float = 0.0, duration: float = 0.0) -> str:
        """Tag a segment as intro, verse, chorus, bridge, or outro."""
        prompt = f"""Analyze this vocal segment and classify it as one of: intro, verse, chorus, bridge, outro.

Segment text: "{text}"
Energy level: {energy:.2f}
Duration: {duration:.2f} seconds

Consider:
- Intro: Often introductory, lower energy, setting the scene
- Verse: Storytelling, narrative content, moderate energy  
- Chorus: Catchy, repetitive, higher energy, main hook
- Bridge: Transitional, different from verse/chorus
- Outro: Concluding, farewell, wrapping up

Respond with only one word: intro, verse, chorus, bridge, or outro"""

        result = self.generate_completion(prompt, max_tokens=10)
        if result:
            # Extract just the tag word
            tag = result.lower().strip().split()[0]
            if tag in ["intro", "verse", "chorus", "bridge", "outro"]:
                return tag

        # Fallback based on energy and duration
        if energy < 0.3:
            return "intro"
        elif energy > 0.7:
            return "chorus"
        else:
            return "verse"

    def suggest_arrangement(self, segments: List[Dict]) -> List[int]:
        """Suggest an arrangement order for segments."""
        if not segments:
            return []

        # Create a summary of segments for the prompt
        segment_summary = []
        for i, seg in enumerate(segments):
            summary = f"Segment {i}: '{seg.get('text', '')[:50]}...' (energy: {seg.get('energy', 0):.2f}, duration: {seg.get('duration', 0):.1f}s)"
            segment_summary.append(summary)

        prompt = f"""Arrange these vocal segments into a coherent song structure. Consider:
- Start with an engaging intro
- Build energy toward a climax  
- Create logical lyrical flow
- End with a satisfying conclusion

Segments:
{chr(10).join(segment_summary)}

Respond with only the segment numbers in order, separated by commas (e.g., "0,2,1,3")."""

        result = self.generate_completion(prompt, max_tokens=50)
        if result:
            try:
                # Parse the arrangement order
                order_str = result.strip().split('\n')[0]  # Take first line only
                indices = [int(x.strip()) for x in order_str.split(',') if x.strip().isdigit()]

                # Validate indices
                valid_indices = [i for i in indices if 0 <= i < len(segments)]
                if len(valid_indices) == len(segments) and set(valid_indices) == set(range(len(segments))):
                    return valid_indices

            except Exception as e:
                logger.error(f"Failed to parse arrangement: {e}")

        # Fallback: arrange by energy progression
        return sorted(range(len(segments)), key=lambda i: segments[i].get('energy', 0))

    def get_text_embedding(self, text: str) -> Optional[List[float]]:
        """Get text embedding from Ollama (if supported by model)."""
        try:
            payload = {
                "model": self.model,
                "prompt": f"Generate embedding for: {text}",
                "stream": False
            }

            response = self.session.post(
                f"{self.base_url}/api/embeddings",
                json=payload,
                timeout=15
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("embedding")

        except Exception as e:
            logger.debug(f"Embedding not supported: {e}")

        return None

    def batch_tag_segments(self, segments: List[Dict]) -> List[str]:
        """Tag multiple segments efficiently."""
        tags = []
        for segment in segments:
            text = segment.get('text', '')
            energy = segment.get('energy', 0.0)
            duration = segment.get('duration', 0.0)

            tag = self.tag_segment_structure(text, energy, duration)
            tags.append(tag)

            # Small delay to avoid overwhelming Ollama
            time.sleep(0.1)

        return tags


# Global client instance
_ollama_client = None


def get_ollama_client(model: str = "phi:latest") -> OllamaClient:
    """Get or create Ollama client instance."""
    global _ollama_client
    if _ollama_client is None or _ollama_client.model != model:
        _ollama_client = OllamaClient(model=model)
    return _ollama_client


def arrange_with_llm(segments: List[Dict]) -> tuple[List[int], float]:
    """Arrange segments using LLM and return order with confidence score."""
    client = get_ollama_client()

    if not client.is_available():
        logger.warning("Ollama not available, falling back to energy-based arrangement")
        # Fallback: arrange by energy
        order = sorted(range(len(segments)), key=lambda i: segments[i].get('energy', 0))
        return order, 0.5

    try:
        # Get structure tags
        tags = client.batch_tag_segments(segments)

        # Get arrangement suggestion
        suggested_order = client.suggest_arrangement(segments)

        # Calculate confidence based on structure coherence
        tag_order = [tags[i] for i in suggested_order]
        structure_score = calculate_structure_score(tag_order)

        return suggested_order, structure_score

    except Exception as e:
        logger.error(f"LLM arrangement failed: {e}")
        # Fallback arrangement
        order = list(range(len(segments)))
        return order, 0.3


def calculate_structure_score(tag_order: List[str]) -> float:
    """Calculate how well the tag order follows typical song structure."""
    ideal_patterns = [
        ["intro", "verse", "chorus", "verse", "chorus", "outro"],
        ["verse", "chorus", "verse", "chorus", "bridge", "chorus", "outro"],
        ["intro", "verse", "chorus", "verse", "chorus", "bridge", "chorus", "outro"]
    ]

    best_score = 0.0
    for pattern in ideal_patterns:
        score = 0.0
        for i, tag in enumerate(tag_order):
            if i < len(pattern) and tag == pattern[i]:
                score += 1.0
        score /= max(len(tag_order), len(pattern))
        best_score = max(best_score, score)

    return best_score
