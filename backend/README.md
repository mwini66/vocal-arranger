# AI-Driven Vocal Arranger Backend

## Overview
Flask-based backend that powers reference-based AI vocal arrangement. Uses OpenRouter's GPT models to intelligently arrange freestyle vocals by matching them to reference track structures, energy patterns, and timing characteristics.

## Tech Stack
- **Python 3.11+**
- **Flask** (RESTful API)
- **OpenRouter API** (GPT models for intelligent arrangement)
- **WhisperX** (High-accuracy speech transcription and segmentation)
- **librosa** (Advanced audio feature extraction)
- **scikit-learn** (Text similarity matching)
- **soundfile** (Audio file processing)
- **CORS** (Cross-origin resource sharing)

## Key Features

### 🎯 3-Step Processing Pipeline
1. **Input Vocals Processing**: WhisperX segmentation → Feature extraction → Structural analysis
2. **Reference Track Processing**: Reference analysis → Energy mapping → Timing extraction
3. **AI-Powered Arrangement**: LLM analysis → Intelligent matching → Audio generation

### 🤖 Advanced AI Integration
- **OpenRouter GPT Models**: Sophisticated arrangement intelligence
- **Reference-Based Analysis**: Matches input vocals to reference structure
- **Energy Progression Modeling**: Maintains musical flow and dynamics
- **Confidence Scoring**: AI provides arrangement quality metrics

### 🎵 Enhanced Audio Analysis
- **Multi-Feature Extraction**: Energy, pitch, tempo, spectral analysis
- **Mood Detection**: Emotional categorization of vocal segments
- **Structural Hints**: Automatic intro/verse/chorus/outro detection
- **Text Analysis**: Keyword extraction, repetition detection, semantic analysis

## Project Architecture
```
backend/
├── app.py                          # Main Flask application with 15+ API endpoints
├── audio_analysis/
│   ├── arrangement.py              # AIVocalArranger with reference-based logic
│   ├── llm_utils.py               # OpenRouterClient for GPT integration
│   ├── extract_features.py        # Enhanced audio feature extraction
│   ├── whisperx_utils.py          # WhisperX transcription utilities
│   └── reference_alignment.py     # Reference processing & audio generation
├── data/
│   └── arrangement_feedback.json  # User feedback collection
├── uploads/
│   ├── audio/                     # Input vocals and reference tracks
│   └── aligned/                   # Generated arranged audio files
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

## Setup & Installation

### Prerequisites
- Python 3.11 or higher
- OpenRouter API key
- FFmpeg (for audio processing)

### 1. Environment Setup
```bash
# Navigate to backend directory
cd vocal-arranger/backend

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install System Dependencies
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows
# Download FFmpeg from https://ffmpeg.org/download.html
```

### 3. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Variables
Create `.env` file with your API credentials:
```env
# OpenRouter API Key (get from https://openrouter.ai)
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

### 5. Run the Server
```bash
python app.py
```

Server runs at `http://localhost:5000` with CORS enabled for frontend integration.

## API Endpoints

### 🎯 Core 3-Step Workflow

#### `POST /process_vocals`
**Step 1: Input Vocals Processing**
- **Input**: Multipart form with `vocals` audio file
- **Process**: WhisperX transcription → Enhanced feature extraction → Structural analysis
- **Output**: Segmented vocals with comprehensive feature data
```json
{
  "segments": [...],
  "vocals_path": "path/to/processed/vocals.wav",
  "total_segments": 12,
  "method": "whisperx_analysis"
}
```

#### `POST /process_reference`
**Step 2: Reference Track Processing**
- **Input**: Multipart form with `reference` audio file
- **Process**: WhisperX analysis → Structure extraction → Energy mapping
- **Output**: Reference track segments with timing and energy data
```json
{
  "reference_segments": [...],
  "reference_path": "path/to/reference.wav",
  "total_segments": 8,
  "method": "reference_analysis"
}
```

#### `POST /arrange_to_reference`
**Step 3: AI-Powered Arrangement**
- **Input**: JSON with `input_segments`, `reference_segments`, optional `genre`
- **Process**: GPT analysis → Intelligent matching → Audio generation
- **Output**: Arranged vocals with statistics and downloadable audio
```json
{
  "arranged_segments": [...],
  "ai_analysis": {
    "confidence": 0.85,
    "reasoning": "Matched high-energy segments to chorus sections...",
    "method": "llm_reference_arrangement"
  },
  "arranged_audio_url": "/aligned/arranged_vocals.wav"
}
```

### 🔧 Utility Endpoints

#### `GET /model_status`
Check AI service availability
```json
{
  "models": {
    "ai_llm": true,
    "openrouter": true
  },
  "services": {
    "whisper": true,
    "feature_extraction": true,
    "reference_alignment": true
  }
}
```

#### `POST /arrangement/feedback`
Submit user feedback for AI improvement
```json
{
  "audio_id": "session_123",
  "arrangement_type": "ai_reference",
  "user_rating": 4,
  "score": 0.85
}
```

### 📁 File Serving

#### `GET /audio/<filename>`
Serve uploaded audio files

#### `GET /aligned/<filename>`
Serve generated arranged audio files

## Core Components

### AIVocalArranger (`arrangement.py`)
**Main AI arrangement engine with reference-based logic**
- `arrange_segments_to_reference()`: Core LLM-based arrangement
- `_prepare_reference_descriptions()`: Reference structure analysis
- `_create_reference_arrangement_prompt()`: Specialized LLM prompts
- `_parse_reference_arrangement_response()`: AI response processing

### OpenRouterClient (`llm_utils.py`)
**GPT model integration for intelligent arrangement**
- Connection management and error handling
- Token optimization and response parsing
- Model availability checking

### Enhanced Feature Extraction (`extract_features.py`)
**Comprehensive audio analysis pipeline**
- Energy categorization (5 levels: very low to very high)
- Pitch analysis with categorical classification
- Mood detection (party, intense, emotional, uplifting, neutral)
- Structural hint detection (intro, hook, outro patterns)
- Text analysis (repetition, keywords, word count metrics)

### Reference Alignment (`reference_alignment.py`)
**Reference processing and audio generation**
- `process_reference_track()`: Extract reference structure
- `align_to_reference()`: Match segments to reference timing
- `create_arranged_audio()`: Generate final audio files

## AI Arrangement Process

### 1. Input Analysis
```python
# WhisperX segments vocals
segments = transcribe_with_whisperx(vocals_path)

# Extract comprehensive features
features = extract_segment_features(vocals_path, segments)
# → Energy, pitch, mood, structural hints, text analysis
```

### 2. Reference Processing
```python
# Analyze reference track structure
reference_segments = process_reference_track(reference_path)
# → Timing patterns, energy progression, structural mapping
```

### 3. LLM-Based Arrangement
```python
# GPT analyzes both input and reference
arrangement = arrange_segments_to_reference(
    input_segments, reference_segments, genre_hint
)
# → Intelligent matching based on energy, content, structure
```

### 4. Audio Generation
```python
# Create arranged audio file
audio_path = create_arranged_audio(
    vocals_path, arranged_segments, output_path
)
# → High-quality audio preserving original vocal characteristics
```

## Enhanced Features

### 🎵 Audio Analysis Features
- **Energy Categorization**: 5-level energy classification with thresholds
- **Pitch Analysis**: Frequency-based pitch categorization 
- **Mood Detection**: Keyword-based emotional analysis
- **Structural Hints**: Pattern recognition for song sections
- **Text Characteristics**: Repetition analysis, keyword extraction

### 🤖 AI Intelligence
- **Reference-Aware Prompts**: Specialized LLM instructions for reference matching
- **Energy Progression**: Maintains musical flow and dynamics
- **Confidence Scoring**: AI self-assessment of arrangement quality
- **Error Recovery**: Graceful fallback to simpler arrangements

### 📊 Analytics & Feedback
- **Usage Metrics**: Track processing times and success rates
- **User Feedback**: 5-star rating system for arrangement quality
- **Arrangement Statistics**: Match rates, confidence scores, usage data
- **Continuous Learning**: Feedback collection for AI improvement

## Performance Metrics

### Technical Performance
- **Processing Speed**: Varies by audio length; typically 10-30s for vocal segmentation, 5-15s for reference analysis
- **AI Response Time**: 15-45s for arrangement generation (depends on OpenRouter API availability)
- **Audio Quality**: Preserves original vocal characteristics during arrangement
- **Memory Usage**: Handles typical vocal files (<10MB) efficiently

### Quality Metrics
- **Segmentation Accuracy**: Generally good phrase identification with WhisperX
- **Arrangement Confidence**: AI provides confidence scores (varies by content complexity)
- **User Feedback**: Collects user ratings for continuous improvement
- **API Reliability**: Dependent on external services (OpenRouter, WhisperX)

## Development Tools

### Code Quality
```bash
# Format code
black backend/

# Lint code  
flake8 backend/

# Type checking
mypy backend/
```

### Testing
```bash
# Run tests
pytest backend/tests/

# Test with coverage
pytest --cov=backend backend/tests/
```

### Debugging
```bash
# Run with debug mode
FLASK_ENV=development python app.py

# Enable verbose logging
export LOG_LEVEL=DEBUG
```

## Error Handling

- **API Failures**: Graceful fallback when OpenRouter is unavailable
- **Audio Processing Errors**: Detailed error messages with recovery suggestions
- **File Upload Issues**: Comprehensive validation and error reporting
- **Memory Management**: Automatic cleanup of temporary files

## Security Features

- **Input Validation**: Strict validation of all file uploads and API inputs
- **Rate Limiting**: Prevents API abuse and ensures fair usage
- **Error Sanitization**: Safe error messages without exposing system details
- **CORS Configuration**: Proper cross-origin resource sharing setup

---

*The backend provides a robust, scalable foundation for AI-driven vocal arrangement with professional-grade audio processing and intelligent arrangement capabilities.*
