# Vocal Arranger Backend

## Overview
This is the backend for the Vocal Arranger project. It provides audio alignment, feature extraction, and arrangement services via a Flask API and modular Python scripts.

## Tech Stack
- Python 3.11+
- Flask (web framework)
- librosa (audio analysis)
- madmom (beat tracking)
- essentia (advanced audio analysis)
- whisper (speech recognition)
- aubio (real-time audio labeling)
- tensorflow/scikit-learn (ML models)
- pydub/soundfile (audio manipulation)
- scipy/numpy (signal processing)

## Development Tools
- pytest (testing)
- flake8 (linting)
- black (formatting)
- python-dotenv (environment variables)

## Folder Structure
- `backend/` — Main backend code and core processing modules
- `backend/audio_analysis/` — AI/ML audio feature extraction and alignment algorithms
  - `align.py` — DTW and beat alignment algorithms
  - `extract_features.py` — Energy, pitch, and structural analysis
  - `utils.py` — Audio processing utilities
  - `view_log.py` — Analysis logging and metrics
- `backend/segmenter.py` — AI-driven vocal segmentation with ML models
- `backend/aligner.py` — Dynamic time warping and vocal-beat alignment
- `backend/grouping.py` — Take management and arrangement ranking system
- `backend/gentle_client.py` — Forced alignment integration
- `backend/data/` — Training data, processed audio, logs, and ML model outputs
- `backend/uploads/` — User uploaded and processed audio files

## Setup with Conda-Forge

### 1. Install Conda/Miniconda
If you don't have conda installed:
```bash
# Download and install Miniconda
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh
bash Miniconda3-latest-MacOSX-x86_64.sh
```

### 2. Clone and Navigate to Backend
```bash
git clone <repo-url>
cd vocal-arranger/backend
```

### 3. Create Conda Environment with Audio Libraries
```bash
# Create environment with Python 3.11 and core audio libraries
conda create -n autocomposer python=3.11 -c conda-forge

# Activate environment
conda activate autocomposer

# Install audio processing libraries from conda-forge (precompiled binaries)
conda install -c conda-forge librosa madmom aubio essentia-tensorflow

# Install additional audio and ML libraries
conda install -c conda-forge scipy numpy soundfile pydub tensorflow scikit-learn

# Install web framework and development tools
conda install -c conda-forge flask flask-cors

# Install development tools
pip install black flake8 pytest python-dotenv

# Install whisper for speech recognition
pip install openai-whisper
```

### 4. Alternative: Use Environment File
Create from environment.yml:
```bash
conda env create -f environment.yml
conda activate autocomposer
```

### 5. Environment Variables
Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
```

## Running the App
```bash
# Activate conda environment
conda activate autocomposer

# Run the Flask application
python app.py
```

## Development Commands

### Core Commands
```bash
# Activate environment (run this first)
conda activate autocomposer

# Run the application
python app.py

# Run tests
pytest

# Lint code
flake8 backend/

# Format code
black backend/

# Validate AI models
python audio_analysis/extract_features.py --test
```

### Conda Environment Management
```bash
# List environments
conda env list

# Export current environment
conda env export > environment.yml

# Update environment from file
conda env update -f environment.yml

# Remove environment
conda env remove -n autocomposer
```

## AI/ML Components

### Audio Processing Pipeline
1. **Vocal Segmentation** (`segmenter.py`) - ML models + energy thresholds
2. **Beat Detection** (`audio_analysis/extract_features.py`) - madmom/essentia
3. **Alignment** (`aligner.py`) - Dynamic Time Warping with AI enhancement
4. **Quality Assessment** - Custom metrics for timing and musical coherence

### Success Metrics
- Alignment precision: <25ms timing deviation
- Segmentation accuracy: >95% correct phrase identification
- Processing speed: <2x real-time for complete arrangement

## Troubleshooting

### Conda-Forge Specific Issues
- **Library conflicts**: Use `conda list` to check installed versions
- **Missing dependencies**: Try `conda install -c conda-forge <package>`
- **Environment activation**: Ensure `conda activate autocomposer` before running commands

### Audio Library Issues
- **librosa installation**: conda-forge version includes all dependencies
- **madmom compatibility**: Use conda-forge version for best compatibility
- **essentia-tensorflow**: Includes both essentia and tensorflow integration

### General Issues
- Ensure conda environment is activated before running any commands
- If you add new dependencies, update `environment.yml`
- For environment variable issues, check your `.env` file
- Use `conda clean --all` to free up disk space

## Development Workflow

### Phase 1a: Intelligent Audio Analysis (Current)
**Priority Files:**
- `audio_analysis/extract_features.py` - Energy detection and structural analysis
- `segmenter.py` - AI-driven vocal segmentation

**Tasks:**
- Instrumental energy detection and segmentation
- Vocal phrase segmentation using ML models
- AI training pipeline for genre-specific patterns

### Phase 1b: Intelligent Arrangement Engine (Next)
**Priority Files:**
- `aligner.py` - DTW alignment and vocal-beat matching
- `grouping.py` - Take management and ranking system

---
For more details, see the main project README.
