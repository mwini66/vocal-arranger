# AI-Driven Vocal Arranger Backend

## Overview
This backend provides AI-powered vocal arrangement using OpenRouter's gpt-oss model. It segments freestyle vocals using WhisperX, extracts enhanced audio features, and uses LLM analysis to intelligently arrange segments into coherent song structures based on lyrics, energy, and musical characteristics.

## Tech Stack
- Python 3.11+
- Flask (REST API)
- OpenRouter API (gpt-oss model for AI arrangement)
- WhisperX (speech segmentation and transcription)
- librosa (audio feature extraction)
- python-dotenv, requests

## Key Features
- **AI-Driven Arrangement**: Uses gpt-oss LLM to analyze lyrics, energy, and mood for intelligent vocal arrangement
- **Enhanced Audio Analysis**: Extracts energy, pitch, duration, mood, and structural hints from each vocal segment
- **Multiple Genre Support**: Supports pop, hip-hop, R&B, and custom song structures
- **Confidence Scoring**: AI provides confidence ratings for arrangement decisions
- **User Feedback System**: Collects user ratings to improve AI performance over time

## Folder Structure
```
backend/
├── app.py                    # Main Flask application with API endpoints
├── audio_analysis/
│   ├── arrangement.py        # AIVocalArranger class for LLM-based arrangement
│   ├── llm_utils.py         # OpenRouterClient for gpt-oss API integration
│   ├── extract_features.py  # Enhanced audio feature extraction
│   └── whisperx_utils.py    # WhisperX transcription utilities
├── data/                    # Arrangement feedback and logs
├── uploads/audio/           # User uploaded audio files
└── requirements.txt         # Python dependencies
```

## Setup

### 1. Clone and Navigate to Backend
```bash
git clone <repo-url>
cd vocal-arranger/backend
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file with your OpenRouter API key:
```bash
# .env
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

Get your free API key from: https://openrouter.ai

### 4. Install System Dependencies
For audio processing:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg
```

## Running the App
```bash
python app.py
```

The API will be available at `http://localhost:5000`

## API Endpoints

### Core Endpoints

#### `POST /segment`
Upload and segment vocal audio file
- **Input**: Multipart form with `vocals` file
- **Output**: Enhanced segment features with AI analysis data
- **Process**: WhisperX transcription → Audio feature extraction → Structural hints

#### `POST /arrange`
AI-powered vocal arrangement
- **Input**: JSON with `segments`, optional `genre` and `structure`
- **Output**: Intelligent arrangement with confidence score and reasoning
- **Process**: gpt-oss LLM analyzes lyrics, energy, and musical structure

#### `POST /arrange/llm_only`
Pure LLM arrangement (same as `/arrange`)
- **Input**: JSON with `segments` and optional `genre`
- **Output**: AI arrangement with detailed analysis

#### `POST /arrangement/compare`
Compare different AI arrangement approaches
- **Input**: JSON with `segments` and `methods` array
- **Output**: Multiple arrangements with similarity analysis

#### `POST /arrangement/feedback`
Submit user feedback on arrangements
- **Input**: JSON with rating and arrangement data
- **Output**: Success confirmation

#### `GET /model_status`
Check AI service availability
- **Output**: Status of OpenRouter connection and available models

## AI Arrangement Process

1. **Audio Upload** → WhisperX segments vocals and transcribes lyrics
2. **Feature Extraction** → Analyzes energy, pitch, mood, repetition, structural hints
3. **LLM Analysis** → gpt-oss processes segment descriptions and musical knowledge
4. **Intelligent Arrangement** → AI orders segments considering:
   - Energy progression (build-ups, climaxes)
   - Lyrical flow and semantic meaning
   - Musical structure (intro/verse/chorus/outro)
   - Genre conventions and song templates
5. **Confidence Scoring** → AI rates its own arrangement decisions

## Example Workflow

```python
# 1. Upload vocal file
POST /segment
→ Returns segments with enhanced features

# 2. AI arrangement
POST /arrange
{
  "segments": [...],
  "genre": "pop",
  "structure": "standard_pop"
}
→ Returns intelligent arrangement with 85% confidence

# 3. User feedback
POST /arrangement/feedback
{
  "user_rating": 4,
  "arrangement_type": "ai_llm"
}
```

## Development

### Code Formatting
```bash
black backend/
```

### Linting
```bash
flake8 backend/
```

### Testing
```bash
pytest backend/tests/
```

## Success Metrics
- **Segmentation Accuracy**: >95% correct vocal phrase identification
- **Processing Speed**: <2x real-time for segmentation
- **AI Confidence**: Average >70% arrangement confidence
- **User Satisfaction**: Target >4/5 user rating
