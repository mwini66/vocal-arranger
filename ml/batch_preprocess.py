import argparse
import json
import logging
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from backend.audio_analysis.extract_features import extract_segment_features
from backend.audio_analysis.whisperx_utils import transcribe_with_whisperx

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BatchProcessor:
    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = Path(input_dir).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(exist_ok=True, parents=True)

    def process_all_files(self) -> None:
        """Process all audio files in the input directory."""
        audio_extensions = ['.wav', '.mp3', '.flac', '.m4a', '.ogg']
        audio_files = [f for f in self.input_dir.iterdir()
                       if f.suffix.lower() in audio_extensions]

        if not audio_files:
            logger.warning(f"No audio files found in {self.input_dir}")
            return

        logger.info(f"Found {len(audio_files)} audio files to process")

        for audio_file in audio_files:
            try:
                self.process_single_file(audio_file)
            except Exception as e:
                logger.error(f"Failed to process {audio_file}: {e}")
                continue

    def process_single_file(self, audio_file: Path) -> None:
        """Process a single audio file and save results."""
        logger.info(f"Processing: {audio_file.name}")

        output_file = self.output_dir / f"{audio_file.stem}_features.json"

        if output_file.exists():
            logger.info(f"Skipping {audio_file.name} - already processed")
            return

        try:
            # Segment and transcribe with Whisper
            logger.info(f"Segmenting and transcribing: {audio_file.name}")
            segments = transcribe_with_whisperx(str(audio_file))

            if not segments:
                logger.warning(f"No segments found for {audio_file.name}")
                return

            logger.info(f"Found {len(segments)} segments")

            # Extract features for each segment
            logger.info(f"Extracting features for: {audio_file.name}")
            segment_features = extract_segment_features(str(audio_file), segments)

            # Create structured data
            processed_data = {
                "song_id": audio_file.stem,
                "original_file": str(audio_file),
                "processing_date": str(Path().cwd()),
                "segments": segment_features,
                "true_order": list(range(len(segment_features))),  # Original order as default
                "metadata": {
                    "total_segments": len(segment_features),
                    "total_duration": sum(seg.get('duration', 0) for seg in segment_features)
                }
            }

            with open(output_file, 'w') as f:
                json.dump(processed_data, f, indent=2)

            logger.info(f"Saved features to: {output_file}")

        except Exception as e:
            logger.error(f"Error processing {audio_file.name}: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description="Batch process royalty-free vocal samples")
    parser.add_argument(
        "--input_dir",
        type=str,
        default=str(Path(__file__).parent / "data" / "audio"),
        help="Directory containing audio files to process"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=str(Path(__file__).parent / "data" / "features"),
        help="Directory to save processed features"
    )
    parser.add_argument(
        "--single_file",
        type=str,
        help="Process a single file instead of batch processing"
    )

    args = parser.parse_args()

    os.makedirs(args.input_dir, exist_ok=True)
    os.makedirs(args.output_dir, exist_ok=True)

    processor = BatchProcessor(args.input_dir, args.output_dir)

    if args.single_file:
        audio_file = Path(args.single_file).resolve()
        if audio_file.exists():
            processor.process_single_file(audio_file)
        else:
            logger.error(f"File not found: {args.single_file}")
    else:
        processor.process_all_files()


if __name__ == "__main__":
    main()
