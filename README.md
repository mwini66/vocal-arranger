# AI-Driven Vocal Arranger

An intelligent vocal arrangement system that automatically segments freestyle vocals and uses AI to arrange them to match reference track structures. The system combines WhisperX transcription, advanced audio analysis, and LLM-powered arrangement to create professionally structured vocal compositions.

## 🎯 Project Overview

The **AI-Driven Vocal Arranger** transforms unstructured freestyle vocal recordings into professionally arranged compositions by:

1. **Processing Input Vocals**: Segments and analyzes freestyle vocals using WhisperX and audio feature extraction
2. **Processing Reference Tracks**: Analyzes reference vocals to extract structure, energy patterns, and timing
3. **AI-Powered Arrangement**: Uses OpenRouter's GPT models to intelligently arrange input segments to match reference track characteristics

### Key Innovation
- **Reference-Based AI Arrangement**: LLM analyzes both input and reference vocals to create arrangements that match the reference track's energy flow, structure, and timing patterns
- **Enhanced Audio Analysis**: Extracts comprehensive features including energy levels, pitch categories, mood detection, and structural hints
- **Intelligent Matching**: AI considers lyrical content, energy progression, and musical structure for optimal vocal placement

## 🏗️ Architecture

### Backend (Python/Flask)
- **Framework**: Flask with modular audio analysis pipeline
- **AI/LLM**: OpenRouter API integration for intelligent arrangement
- **Audio Processing**: WhisperX for transcription, librosa for feature extraction
- **Core Features**: Reference-based arrangement, segment analysis, confidence scoring

### Frontend (Next.js/TypeScript)
- **Framework**: Next.js with TypeScript and TailwindCSS
- **UI Components**: Custom audio production interface with segment visualization
- **Workflow**: 3-step process (Process Input → Process Reference → AI Arrange)
- **Features**: Audio preview, download functionality, arrangement statistics

## 📁 Project Structure

```
vocal-arranger/
├── backend/
│   ├── app.py                    # Flask main application with 6 core API endpoints
│   ├── audio_analysis/
│   │   ├── arrangement.py        # AIVocalArranger with reference-based logic
│   │   ├── llm_utils.py         # OpenRouter client for GPT integration
│   │   ├── extract_features.py  # Enhanced audio feature extraction
│   │   ├── whisperx_utils.py    # WhisperX transcription utilities
│   │   └── reference_alignment.py # Reference track processing and alignment
│   ├── data/                    # User feedback and processing logs
│   ├── uploads/                 # Input vocals and reference tracks
│   └── uploads/aligned/         # Generated arranged audio files
└── frontend/
    ├── src/
    │   ├── app/
    │   │   └── page.tsx         # Main UI with 3-step workflow
    │   ├── components/ui/
    │   │   └── AudioPlayer.tsx   # Audio playback component
    │   └── lib/                 # Utilities and helpers
    └── public/                  # Static assets
```

## 🚀 Current Features

### ✅ Complete Implementation
- **3-Step Workflow**: Process Input Vocals → Process Reference → AI Arrange
- **WhisperX Integration**: Accurate vocal segmentation and transcription
- **Enhanced Feature Extraction**: Energy, pitch, mood, structural hints analysis
- **AI-Powered Arrangement**: OpenRouter GPT models for intelligent vocal placement
- **Reference-Based Matching**: AI analyzes both input and reference to create optimal arrangements
- **Audio Output Generation**: Creates downloadable arranged vocal files
- **User Feedback System**: Rating collection for continuous AI improvement
- **Real-time Status**: Shows processing status and AI model availability

### 🎵 Audio Analysis Features
- **Energy Categorization**: Very low to very high energy levels
- **Pitch Analysis**: Low to high pitch classification
- **Mood Detection**: Party, intense, emotional, uplifting, neutral moods
- **Structural Hints**: Intro-like, hook-like, outro-like segment identification
- **Text Analysis**: Repetition detection, keyword extraction, word count metrics

## 🛠️ Technical Implementation

### Core Workflow:
1. **Input Processing**: WhisperX segments vocals → Extract audio features → Store segment data
2. **Reference Processing**: WhisperX analyzes reference → Extract structural patterns → Map energy flow
3. **AI Arrangement**: LLM receives both datasets → Analyzes compatibility → Creates arrangement plan
4. **Audio Generation**: Applies arrangement to input vocals → Creates aligned output file

### Key Technologies:
- **OpenRouter API**: GPT models for arrangement intelligence
- **WhisperX**: High-accuracy speech transcription and segmentation
- **librosa**: Audio feature extraction and analysis
- **Flask**: RESTful API backend with CORS support
- **Next.js**: Modern React frontend with TypeScript

## 🔧 Setup Instructions

### Backend Setup
```bash
cd backend
pip install -r requirements.txt

# Create .env file
echo "OPENROUTER_API_KEY=your_key_here" > .env

# Run server
python app.py
```

### Frontend Setup
```bash
cd frontend
npm install

# Create .env.local file
echo "NEXT_PUBLIC_API_URL=http://localhost:5000" > .env.local

# Run development server
npm run dev
```

## 📊 API Endpoints

### Core Processing
- `POST /process_vocals` - Process input vocals (Step 1)
- `POST /process_reference` - Process reference track (Step 2)  
- `POST /arrange_to_reference` - AI arrangement (Step 3)

### Status & Feedback
- `GET /model_status` - Check AI model availability
- `POST /arrangement/feedback` - Submit user ratings

## 🎯 User Workflow

### Main Workflow (3-Step Process):
1. **Upload Input Vocals**: Freestyle or unordered vocal recordings
2. **Upload Reference Track**: Vocal track with desired structure/energy
3. **AI Processing**: 
   - Input analysis (segments, energy, mood, lyrics)
   - Reference analysis (structure, timing, energy progression)
   - Intelligent arrangement matching input to reference patterns
4. **Download Result**: Professionally arranged vocals with statistics

### Output Features:
- **High-Quality Audio**: Preserves original vocal quality during arrangement
- **Arrangement Statistics**: Match rates, confidence scores, usage metrics
- **AI Transparency**: Shows reasoning behind arrangement decisions
- **User Feedback**: Rate arrangements to improve future AI performance

## 🧪 Performance Metrics

### Technical Performance:
- **Processing Speed**: Varies by audio length; typically 10-30s for input vocals, 5-15s for reference tracks
- **AI Response Time**: 15-45s for arrangement generation (depends on OpenRouter API availability)
- **Audio Quality**: Preserves original vocal characteristics during arrangement
- **Confidence Scoring**: AI provides confidence scores (varies by content complexity)

### Success Metrics:
- **Arrangement Quality**: AI confidence varies by content and reference match quality
- **User Satisfaction**: Collecting user ratings for continuous improvement
- **Processing Reliability**: Generally reliable with proper error handling for API failures
- **Feature Accuracy**: Audio feature extraction works well for energy/mood categorization

## 🔄 Recent Updates

### v2.0 - Reference-Based AI Arrangement
- **New 3-Step Workflow**: Separate processing for input and reference
- **Enhanced LLM Prompts**: Reference-aware arrangement intelligence
- **Improved UI**: Streamlined interface with clear progress indicators
- **Audio Generation**: Creates downloadable arranged vocal files
- **Statistics Dashboard**: Detailed arrangement analysis and metrics

### Technical Improvements
- **Separate Loading States**: Independent processing indicators
- **Model Status Display**: Real-time AI availability checking  
- **Enhanced Error Handling**: Detailed error messages and recovery
- **Audio Download**: New tab downloads with proper file naming

## 🌟 Future Roadmap

- **Multi-Reference Support**: Blend characteristics from multiple reference tracks
- **Genre-Specific Models**: Specialized AI for different musical genres
- **Real-time Processing**: Live vocal arrangement during recording
- **Advanced Audio Effects**: Pitch correction and timing refinement
- **DAW Integration**: Plugin versions for major music production software

---

*The AI-Driven Vocal Arranger represents the cutting edge of AI-assisted music production, making professional vocal arrangement accessible to artists of all skill levels.*
