import json
import logging
import pickle
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder

sys.path.append(str(Path(__file__).parent.parent))

try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import lightgbm as lgb

    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ArrangementMLTrainer:
    def __init__(self, features_dir: str = str(Path(__file__).parent / "data" / "features"),
                 models_dir: str = str(Path(__file__).parent / "data" / "models")):
        self.features_dir = Path(features_dir)
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True, parents=True)

        # Initialize text embedding model (local)
        self.text_model = None
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.text_model = SentenceTransformer('all-MiniLM-L6-v2')  # Fast, lightweight
                logger.info("Loaded SentenceTransformer model")
            except Exception as e:
                logger.warning(f"Failed to load SentenceTransformer: {e}")

        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()

    def load_training_data(self) -> Tuple[List[Dict], List[List[int]]]:
        """Load processed feature files and extract training data."""
        feature_files = list(self.features_dir.glob("*_features.json"))

        if not feature_files:
            raise ValueError(f"No feature files found in {self.features_dir}")

        all_songs = []
        all_arrangements = []

        logger.info(f"Loading {len(feature_files)} feature files")

        for file_path in feature_files:
            try:
                with open(file_path, 'r') as f:
                    song_data = json.load(f)

                segments = song_data.get('segments', [])
                true_order = song_data.get('true_order', list(range(len(segments))))

                if segments and len(segments) >= 2:  # Need at least 2 segments
                    all_songs.append(segments)
                    all_arrangements.append(true_order)

            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")
                continue

        logger.info(f"Loaded {len(all_songs)} songs for training")
        return all_songs, all_arrangements

    def extract_features(self, segments: List[Dict]) -> np.ndarray:
        """Extract features from segments for ML training."""
        features = []

        for segment in segments:
            seg_features = [
                segment.get('energy', 0.0),
                segment.get('pitch', 0.0),
                segment.get('duration', 0.0),
                segment.get('pause', 0.0),
                len(segment.get('keywords', [])),  # Number of keywords
                len(segment.get('text', '')),  # Text length
            ]

            # Add text embedding if available
            if self.text_model and segment.get('text'):
                try:
                    text_embedding = self.text_model.encode(segment['text'])
                    seg_features.extend(text_embedding.tolist())
                except Exception as e:
                    logger.debug(f"Text embedding failed: {e}")
                    # Fallback: simple text features
                    text = segment.get('text', '').lower()
                    seg_features.extend([
                        text.count('chorus') > 0,
                        text.count('verse') > 0,
                        text.count('intro') > 0,
                        text.count('outro') > 0,
                    ])
            else:
                # Simple text features without embeddings
                text = segment.get('text', '').lower()
                seg_features.extend([
                    text.count('chorus') > 0,
                    text.count('verse') > 0,
                    text.count('intro') > 0,
                    text.count('outro') > 0,
                ])

            features.append(seg_features)

        return np.array(features)

    def prepare_ranking_data(self, all_songs: List[List[Dict]], all_arrangements: List[List[int]]) -> Tuple[
        np.ndarray, np.ndarray]:
        """Prepare data for ranking model (predicts segment quality scores)."""
        X, y = [], []

        for segments, true_order in zip(all_songs, all_arrangements):
            if len(segments) != len(true_order):
                continue

            segment_features = self.extract_features(segments)

            # Create quality scores based on true arrangement order
            # Earlier segments in arrangement get higher scores
            quality_scores = np.zeros(len(segments))
            for pos, seg_idx in enumerate(true_order):
                # Higher score for segments that appear earlier in good arrangement
                quality_scores[seg_idx] = 1.0 - (pos / len(true_order))

            X.extend(segment_features)
            y.extend(quality_scores)

        return np.array(X), np.array(y)

    def train_ranking_model(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """Train a ranking model to score segments."""
        logger.info("Training ranking model...")

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Try different models
        models = {
            'random_forest': RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1),
        }

        if LIGHTGBM_AVAILABLE:
            models['lightgbm'] = lgb.LGBMRegressor(n_estimators=100, random_state=42, verbose=-1)

        best_model = None
        best_score = float('inf')
        best_name = None

        for name, model in models.items():
            try:
                logger.info(f"Training {name}...")
                model.fit(X_train_scaled, y_train)

                # Evaluate
                y_pred = model.predict(X_test_scaled)
                mse = mean_squared_error(y_test, y_pred)

                logger.info(f"{name} MSE: {mse:.4f}")

                if mse < best_score:
                    best_score = mse
                    best_model = model
                    best_name = name

            except Exception as e:
                logger.error(f"Failed to train {name}: {e}")
                continue

        if best_model is None:
            raise ValueError("No models trained successfully")

        logger.info(f"Best model: {best_name} (MSE: {best_score:.4f})")

        return {
            'model': best_model,
            'scaler': self.scaler,
            'model_name': best_name,
            'mse': best_score
        }

    def save_model(self, model_data: Dict, model_type: str = "ranking") -> str:
        """Save trained model and preprocessing components."""
        model_path = self.models_dir / f"{model_type}_model.pkl"

        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)

        logger.info(f"Saved model to {model_path}")
        return str(model_path)

    def load_model(self, model_type: str = "ranking") -> Optional[Dict]:
        """Load trained model."""
        model_path = self.models_dir / f"{model_type}_model.pkl"

        if not model_path.exists():
            return None

        try:
            with open(model_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return None

    def arrange_segments_ml(self, segments: List[Dict]) -> Tuple[List[int], float]:
        """Arrange segments using trained ML model."""
        model_data = self.load_model("ranking")

        if model_data is None:
            logger.warning("No trained model found, using fallback arrangement")
            # Fallback: arrange by energy
            order = sorted(range(len(segments)), key=lambda i: segments[i].get('energy', 0))
            return order, 0.3

        try:
            model = model_data['model']
            scaler = model_data['scaler']

            # Extract features
            X = self.extract_features(segments)
            X_scaled = scaler.transform(X)

            # Predict quality scores
            scores = model.predict(X_scaled)

            # Arrange by predicted scores (highest first)
            arrangement = sorted(range(len(segments)), key=lambda i: scores[i], reverse=True)

            # Calculate confidence based on score variance
            confidence = min(1.0, np.std(scores) * 2)  # Higher variance = higher confidence

            return arrangement, float(confidence)

        except Exception as e:
            logger.error(f"ML arrangement failed: {e}")
            # Fallback arrangement
            order = list(range(len(segments)))
            return order, 0.2


def train_arrangement_models(features_dir: str = "data/features") -> None:
    """Main training function."""
    trainer = ArrangementMLTrainer(features_dir)

    try:
        # Load training data
        all_songs, all_arrangements = trainer.load_training_data()

        if len(all_songs) < 5:
            logger.warning(f"Only {len(all_songs)} songs available for training. Need more data for robust models.")

        # Prepare ranking data
        X, y = trainer.prepare_ranking_data(all_songs, all_arrangements)

        logger.info(f"Training data shape: {X.shape}")
        logger.info(f"Target data shape: {y.shape}")

        # Train ranking model
        model_data = trainer.train_ranking_model(X, y)

        # Save model
        trainer.save_model(model_data, "ranking")

        logger.info("Training completed successfully!")

    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Train ML models for vocal arrangement")
    parser.add_argument(
        "--features_dir",
        type=str,
        default=str(Path(__file__).parent / "data" / "features"),
        help="Directory containing processed feature files"
    )
    parser.add_argument(
        "--test_arrangement",
        action="store_true",
        help="Test arrangement on a sample file"
    )

    args = parser.parse_args()

    if args.test_arrangement:
        trainer = ArrangementMLTrainer()

        # Load a sample file
        feature_files = list(Path(args.features_dir).glob("*_features.json"))
        if feature_files:
            with open(feature_files[0], 'r') as f:
                song_data = json.load(f)
                segments = song_data.get('segments', [])

            if segments:
                arrangement, confidence = trainer.arrange_segments_ml(segments)
                print(f"Sample arrangement: {arrangement}")
                print(f"Confidence: {confidence:.3f}")
        else:
            print("No feature files found for testing")
    else:
        train_arrangement_models(args.features_dir)


if __name__ == "__main__":
    main()
