# Vocal Arranger Backend

## Overview
This backend provides API endpoints and scripts for speech segmentation of vocal tracks using Whisper. It detects and splits vocal phrases, enabling users to re-arrange segments for creative composition.

## Tech Stack
- Python 3.11+
- Flask (API)
- whisper (speech segmentation)
- pytest, flake8, black, python-dotenv

## Folder Structure
- `backend/` — Flask app and segmentation modules
- `backend/audio_analysis/` — Whisper-based segmentation scripts
- `backend/segmenter.py` — Main entry for speech segmentation
- `backend/data/` — Processed audio and segment logs
- `backend/uploads/` — User uploaded audio files

## Setup with Conda-Forge

### 1. Install Conda/Miniconda
If you don't have conda installed:
```bash
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh
bash Miniconda3-latest-MacOSX-x86_64.sh
```

### 2. Clone and Navigate to Backend
```bash
git clone <repo-url>
cd vocal-arranger/backend
```

### 3. Create Conda Environment
```bash
conda create -n vocalarranger python=3.11 -c conda-forge
conda activate vocalarranger
conda install flask
pip install openai-whisper black flake8 pytest python-dotenv
```

### 4. Environment Variables
Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
```

## Running the App
```bash
conda activate vocalarranger
python app.py
```

## Main Features
- Segment vocals into phrases using Whisper
- Export segment timings and text
- API for uploading audio and retrieving segments
- Tools for re-arranging segmented phrases

## Out of Scope
- No beat/instrumental alignment
- No genre-specific arrangement
- No full AI arrangement engine

## Requirements

### ffmpeg (Required for audio processing)
- **macOS:**
  ```bash
  brew install ffmpeg
  ```
- **Ubuntu/Debian:**
  ```bash
  sudo apt-get update
  sudo apt-get install ffmpeg
  ```
- **Windows:**
  Download from https://ffmpeg.org/download.html and add the `bin` directory to your system PATH.

### NLTK punkt tokenizer (Required for keyword extraction)
- The backend will automatically download the punkt tokenizer if missing. If you see errors, ensure your server has internet access or manually run:
  ```python
  import nltk
  nltk.download('punkt')
  ```

## Troubleshooting
- Ensure conda environment is activated before running any commands
- If you add new dependencies, update your environment
- For environment variable issues, check your `.env` file
- If you see `[Errno 2] No such file or directory: 'ffmpeg'`, install ffmpeg as above and restart your backend.
- If you see NLTK errors about missing 'punkt', ensure the punkt tokenizer is downloaded as above.

---
For more details, see the main project README.
