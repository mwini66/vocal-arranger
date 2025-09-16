import logging
from typing import List, Dict, Tuple

import numpy as np

from audio_analysis.arrangement_ml import arrange_ml
from audio_analysis.arrangement_rule import arrange_rule
from audio_analysis.llm_utils import arrange_with_llm
from ml.train_arrangement_ml import ArrangementMLTrainer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EnsembleArranger:
    def __init__(self):
        self.ml_trainer = ArrangementMLTrainer()

    def arrange_ensemble(self, segments: List[Dict], methods: List[str] = None) -> Tuple[List[int], float, Dict]:
        """
        Arrange segments using ensemble of multiple methods.

        Args:
            segments: List of segment dictionaries with features
            methods: List of methods to use ['rule', 'ml', 'llm', 'trained_ml']

        Returns:
            best_arrangement: List of segment indices in best order
            confidence: Confidence score for the arrangement
            all_results: Dictionary containing all method results
        """
        if methods is None:
            methods = ['rule', 'ml', 'llm', 'trained_ml']

        all_results = {}
        arrangements = {}
        scores = {}

        # Run each method
        for method in methods:
            try:
                if method == 'rule':
                    arrangement, score = arrange_rule(segments)
                    all_results['rule'] = {
                        'arrangement': arrangement,
                        'score': score,
                        'method': 'rule-based',
                        'available': True
                    }

                elif method == 'ml':
                    arrangement, score = arrange_ml(segments)
                    all_results['ml'] = {
                        'arrangement': arrangement,
                        'score': score,
                        'method': 'ml-weighted',
                        'available': True
                    }

                elif method == 'llm':
                    arrangement, score = arrange_with_llm(segments)
                    all_results['llm'] = {
                        'arrangement': arrangement,
                        'score': score,
                        'method': 'llm-local',
                        'available': True
                    }

                elif method == 'trained_ml':
                    arrangement, score = self.ml_trainer.arrange_segments_ml(segments)
                    all_results['trained_ml'] = {
                        'arrangement': arrangement,
                        'score': score,
                        'method': 'trained-ml',
                        'available': True
                    }

                arrangements[method] = arrangement
                scores[method] = score

            except Exception as e:
                logger.error(f"Method {method} failed: {e}")
                all_results[method] = {
                    'arrangement': list(range(len(segments))),
                    'score': 0.0,
                    'method': method,
                    'available': False,
                    'error': str(e)
                }

        # Select best arrangement using voting and scoring
        best_arrangement, ensemble_confidence = self._select_best_arrangement(
            arrangements, scores, segments
        )

        # Add ensemble results
        all_results['ensemble'] = {
            'arrangement': best_arrangement,
            'score': ensemble_confidence,
            'method': 'ensemble',
            'available': True
        }

        return best_arrangement, ensemble_confidence, all_results

    def _select_best_arrangement(self, arrangements: Dict[str, List[int]],
                                 scores: Dict[str, float],
                                 segments: List[Dict]) -> Tuple[List[int], float]:
        """Select the best arrangement from multiple methods."""
        if not arrangements:
            return list(range(len(segments))), 0.0

        # Weight methods by their typical reliability
        method_weights = {
            'rule': 0.25,
            'ml': 0.20,
            'llm': 0.30,
            'trained_ml': 0.35  # Highest weight for trained model
        }

        # Calculate weighted scores
        weighted_scores = {}
        for method, arrangement in arrangements.items():
            base_score = scores.get(method, 0.0)
            weight = method_weights.get(method, 0.1)

            # Add bonus for musical structure coherence
            structure_bonus = self._calculate_structure_bonus(arrangement, segments)

            final_score = (base_score * weight) + structure_bonus
            weighted_scores[method] = final_score

        # Select method with highest weighted score
        best_method = max(weighted_scores.keys(), key=lambda k: weighted_scores[k])
        best_arrangement = arrangements[best_method]
        best_score = weighted_scores[best_method]

        # If scores are close, use voting
        if len(weighted_scores) > 1:
            score_values = list(weighted_scores.values())
            if max(score_values) - min(score_values) < 0.15:  # Close scores
                best_arrangement = self._vote_arrangement(arrangements, segments)
                best_score = np.mean(list(weighted_scores.values()))

        return best_arrangement, min(1.0, best_score)

    def _vote_arrangement(self, arrangements: Dict[str, List[int]],
                          segments: List[Dict]) -> List[int]:
        """Use voting to select arrangement when scores are close."""
        if not arrangements:
            return list(range(len(segments)))

        n_segments = len(segments)
        position_votes = np.zeros((n_segments, n_segments))  # [segment][position]

        # Count votes for each segment at each position
        for arrangement in arrangements.values():
            for pos, seg_idx in enumerate(arrangement):
                if 0 <= seg_idx < n_segments and 0 <= pos < n_segments:
                    position_votes[seg_idx][pos] += 1

        # Select arrangement based on highest votes
        final_arrangement = []
        used_segments = set()

        for pos in range(n_segments):
            # Find segment with most votes for this position
            available_segments = [i for i in range(n_segments) if i not in used_segments]
            if not available_segments:
                break

            best_segment = max(available_segments,
                               key=lambda s: position_votes[s][pos])
            final_arrangement.append(best_segment)
            used_segments.add(best_segment)

        # Fill any missing segments
        for i in range(n_segments):
            if i not in used_segments:
                final_arrangement.append(i)

        return final_arrangement[:n_segments]

    def _calculate_structure_bonus(self, arrangement: List[int],
                                   segments: List[Dict]) -> float:
        """Calculate bonus score for good musical structure."""
        if len(arrangement) < 2:
            return 0.0

        bonus = 0.0

        # Energy progression bonus
        energies = [segments[i].get('energy', 0) for i in arrangement]
        if len(energies) >= 3:
            # Reward if energy builds toward middle/end
            first_third = np.mean(energies[:len(energies) // 3])
            last_third = np.mean(energies[-len(energies) // 3:])
            if last_third > first_third:
                bonus += 0.1

        # Duration variety bonus
        durations = [segments[i].get('duration', 0) for i in arrangement]
        if np.std(durations) > 0.5:  # Good variety in segment lengths
            bonus += 0.05

        # Text coherence bonus (simple keyword overlap)
        texts = [segments[i].get('text', '') for i in arrangement]
        if len(texts) >= 2:
            total_overlap = 0
            comparisons = 0
            for i in range(len(texts) - 1):
                words1 = set(texts[i].lower().split())
                words2 = set(texts[i + 1].lower().split())
                if words1 and words2:
                    overlap = len(words1 & words2) / len(words1 | words2)
                    total_overlap += overlap
                    comparisons += 1

            if comparisons > 0:
                avg_overlap = total_overlap / comparisons
                if 0.1 < avg_overlap < 0.7:  # Some overlap but not too much
                    bonus += 0.05

        return min(0.3, bonus)  # Cap bonus at 0.3


# Global ensemble instance
_ensemble_arranger = None


def get_ensemble_arranger() -> EnsembleArranger:
    """Get or create ensemble arranger instance."""
    global _ensemble_arranger
    if _ensemble_arranger is None:
        _ensemble_arranger = EnsembleArranger()
    return _ensemble_arranger


def arrange_ensemble(segments: List[Dict], methods: List[str] = None) -> Tuple[List[int], float, Dict]:
    """Convenience function for ensemble arrangement."""
    arranger = get_ensemble_arranger()
    return arranger.arrange_ensemble(segments, methods)
