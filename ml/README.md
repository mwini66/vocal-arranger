# Vocal Arranger AI Setup Guide

This guide will help you set up the complete AI-driven vocal arrangement system with local LLMs and classical ML models.

## Prerequisites

1. **System Requirements:**
   - macOS, Linux, or Windows
   - Python 3.11+
   - Node.js 24.4.1
   - ffmpeg (for audio processing)
   - At least 8GB RAM (16GB recommended for LLM)

2. **Install ffmpeg:**
   ```bash
   # macOS
   brew install ffmpeg
   
   # Ubuntu/Debian
   sudo apt-get install ffmpeg
   
   # Windows: Download from https://ffmpeg.org/download.html
   ```

3. **Install Ollama (for local LLM):**
   ```bash
   # macOS/Linux
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Start Ollama service
   ollama serve
   
   # Pull a lightweight model (in another terminal)
   ollama pull phi
   ```

## Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd vocal-arranger/backend
   ```

2. **Create Python environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create data directories:**
   ```bash
   mkdir -p audio_analysis/audio_input/royalty_free
   mkdir -p data/features
   mkdir -p data/models
   ```

5. **Create environment file:**
   ```bash
   touch .env
   # Add any custom configurations if needed
   ```

## Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd ../frontend
   ```

2. **Install Node.js dependencies:**
   ```bash
   npm install
   ```

3. **Create environment file:**
   ```bash
   cp .env.example .env.local
   # Edit .env.local to set NEXT_PUBLIC_API_URL=http://localhost:5000
   ```

## Getting Started

### Step 1: Collect Royalty-Free Data

1. **Download vocal samples:**
   - Use the sources listed in `backend/data/royalty_free_sources.md`
   - Save audio files to `backend/audio_analysis/audio_input/royalty_free/`
   - Aim for at least 5-10 different vocal tracks

2. **Update the tracking table:**
   - Document each sample's source and license in `royalty_free_sources.md`

### Step 2: Process Training Data

1. **Start the backend:**
   ```bash
   cd backend
   python app.py
   ```

2. **Batch process your audio files:**
   ```bash
   # Using the API
   curl -X POST http://localhost:5000/batch_segment
   
   # Or using the script directly
   python audio_analysis/batch_preprocess.py
   ```

### Step 3: Train ML Models

1. **Train classical ML models:**
   ```bash
   # Via API
   curl -X POST http://localhost:5000/train_ml
   
   # Or directly
   python audio_analysis/train_arrangement_ml.py
   ```

### Step 4: Test the System

1. **Check model status:**
   ```bash
   curl http://localhost:5000/model_status
   ```

2. **Start the frontend:**
   ```bash
   cd ../frontend
   npm run dev
   ```

3. **Visit http://localhost:3000** and test the full workflow:
   - Upload a vocal track
   - View AI-generated arrangements
   - Rate and provide feedback

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/segment` | POST | Segment vocals and extract features |
| `/arrange` | POST | Basic rule/ML arrangement |
| `/arrange_ml` | POST | Trained ML model arrangement |
| `/arrange_llm` | POST | Local LLM arrangement |
| `/arrange_ensemble` | POST | Best of all methods |
| `/batch_segment` | POST | Process all files in royalty_free folder |
| `/train_ml` | POST | Train ML models on feature data |
| `/model_status` | GET | Check availability of all models/services |
| `/arrangement/feedback` | POST | Submit user feedback |

## Configuration Options

### Ollama LLM Configuration
- Model: `phi` (default, lightweight)
- Alternative models: `llama2`, `mistral`
- Change model in `audio_analysis/llm_utils.py`

### ML Model Configuration
- Default: RandomForest + LightGBM
- Text embeddings: SentenceTransformers (local)
- Features: energy, pitch, duration, pause, text, keywords

### Cost Optimization
- All processing is local (no cloud APIs)
- Lightweight models prioritized
- Caching for repeated LLM queries
- Fast training with scikit-learn

## Troubleshooting

### Common Issues

1. **"No such file or directory: 'ffmpeg'"**
   - Install ffmpeg using the instructions above

2. **NLTK punkt errors**
   - The system auto-downloads required data
   - If issues persist: `python -c "import nltk; nltk.download('punkt')"`

3. **Ollama not available**
   - Ensure `ollama serve` is running
   - Check model is pulled: `ollama list`

4. **Insufficient training data**
   - Add more vocal samples to the royalty_free folder
   - Need at least 3 processed files for training

5. **Memory issues**
   - Use smaller models: `ollama pull phi:mini`
   - Reduce batch sizes in processing

### Performance Tips

1. **Speed up processing:**
   - Use SSD storage
   - Increase RAM allocation
   - Process files in smaller batches

2. **Improve arrangement quality:**
   - Add more diverse training data
   - Provide user feedback regularly
   - Experiment with different LLM models

## Development Workflow

1. **Add new vocal samples** → `royalty_free/` folder
2. **Process samples** → `/batch_segment` API
3. **Train models** → `/train_ml` API
4. **Test arrangements** → Frontend UI
5. **Collect feedback** → Automatic via UI
6. **Retrain** → Periodic model updates

## Next Steps

- Collect 20-50 high-quality vocal samples
- Build a substantial feedback dataset
- Experiment with different LLM prompts
- Add genre-specific arrangement patterns
- Implement advanced ML architectures

Your AI vocal arrangement system is now ready for production use with cost-effective, local processing!
