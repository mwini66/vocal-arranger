# AI-Driven Vocal Arranger Frontend

## Overview
Modern React-based frontend for the AI-Driven Vocal Arranger system. Features a streamlined 3-step workflow for reference-based vocal arrangement using OpenRouter's GPT models and WhisperX segmentation.

## Tech Stack
- **Next.js 14+** (App Router)
- **TypeScript** 
- **TailwindCSS** (Styling)
- **React Hooks** (State management)
- **Node.js 24.4.1**
- **npm** (Package management)

## Key Features

### 🎯 3-Step Reference Workflow
1. **Process Input Vocals**: Upload/record → WhisperX segmentation → Feature extraction
2. **Process Reference Track**: Upload reference → Structure analysis → Energy mapping
3. **AI Arrangement**: Genre selection → LLM analysis → Intelligent arrangement → Audio output

### 🎵 Advanced Audio Interface
- **Live Recording**: Browser-based vocal recording with MediaRecorder API
- **Audio Preview**: Built-in audio player for uploads and outputs
- **File Management**: Upload, preview, and remove audio files
- **Download Support**: New-tab downloads for arranged vocals

### 🤖 AI Integration
- **Real-time Status**: Shows OpenRouter API availability
- **Genre Selection**: Pop, Hip-Hop, R&B, Rock, Folk, Electronic
- **Confidence Display**: AI arrangement confidence scores
- **Error Handling**: Detailed error messages and recovery

### 📊 Results Visualization
- **Arrangement Statistics**: Match rates, confidence scores, usage metrics
- **Segment Analysis**: Energy, pitch, mood, structural hints
- **Progress Indicators**: Independent loading states for each step

## Project Structure
```
frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx              # Main 3-step workflow interface
│   │   ├── layout.tsx            # App layout and metadata
│   │   └── globals.css           # TailwindCSS configuration
│   ├── components/ui/
│   │   ├── AudioPlayer.tsx       # Audio playback component
│   │   ├── AIVocalArranger.tsx   # Legacy arrangement interface
│   │   ├── card.tsx              # UI card component
│   │   └── button.tsx            # UI button component
│   └── lib/
│       └── utils.ts              # Utility functions
├── public/                       # Static assets
├── package.json                  # Dependencies and scripts
├── tsconfig.json                 # TypeScript configuration
├── tailwind.config.ts            # TailwindCSS configuration
└── next.config.ts                # Next.js configuration
```

## Setup & Installation

### Prerequisites
- Node.js 24.4.1 or higher
- npm package manager
- Running backend server

### 1. Environment Setup
```bash
# Navigate to frontend directory
cd vocal-arranger/frontend

# Install Node.js 24.4.1 (using nvm)
nvm install 24.4.1
nvm use 24.4.1
```

### 2. Install Dependencies
```bash
npm install
```

### 3. Environment Variables
Create `.env.local` file:
```env
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:5000
```

### 4. Run Development Server
```bash
npm run dev
```

Access the application at `http://localhost:3000`

## User Workflow

### Step 1: Input Vocals Processing
- **Upload or Record**: Select audio file or use live recording
- **Audio Preview**: Listen to uploaded vocals before processing
- **Process Button**: Triggers WhisperX segmentation and feature extraction
- **Results**: Displays detected segments with analysis

### Step 2: Reference Track Processing  
- **Upload Reference**: Select reference vocal track
- **Audio Preview**: Listen to reference track
- **Process Button**: Analyzes reference structure and energy patterns
- **Results**: Shows reference segments and processing confirmation

### Step 3: AI Arrangement
- **Genre Selection**: Choose from 7 genre options or auto-detect
- **AI Model Status**: Real-time display of OpenRouter API availability
- **Arrangement Button**: Triggers LLM-based intelligent arrangement
- **Results**: Downloadable arranged audio with statistics

### Final Output
- **Audio Player**: Play arranged vocals directly in browser
- **Download Button**: Save arranged vocals (opens in new tab)
- **Statistics Dashboard**: Match rates, confidence scores, usage metrics
- **Performance Metrics**: Reference segments, matched segments, usage rates

## Component Architecture

### Main Page (`page.tsx`)
- **State Management**: 15+ React state variables for workflow control
- **API Integration**: Handles all backend communication
- **Error Handling**: Comprehensive error display and recovery
- **Loading States**: Independent loading indicators for each step

### AudioPlayer Component
- **Universal Audio**: Supports multiple audio formats
- **Browser Compatibility**: Works across modern browsers
- **Responsive Design**: Adapts to different screen sizes

### Legacy AIVocalArranger Component
- **Backward Compatibility**: Supports older arrangement methods
- **Segment Visualization**: Rich display of vocal characteristics
- **Method Comparison**: Side-by-side arrangement comparison

## API Integration

### Core Endpoints
- `POST /process_vocals` - Step 1: Input vocals processing
- `POST /process_reference` - Step 2: Reference track processing
- `POST /arrange_to_reference` - Step 3: AI arrangement
- `GET /model_status` - AI model availability check

### Data Flow
1. **File Upload** → FormData → Backend processing
2. **Processing Status** → Real-time loading indicators
3. **Results Display** → Rich visualization of analysis
4. **Audio Output** → Downloadable arranged vocals

## Development Scripts

```bash
# Development server with hot reload
npm run dev

# Production build
npm run build

# Production server
npm start

# Type checking
npm run type-check

# Linting
npm run lint

# Fix linting issues
npm run lint --fix
```

## Key Features Implementation

### 🎵 Audio Processing
- **File Handling**: Drag & drop, file selection, live recording
- **Format Support**: MP3, WAV, M4A, and other browser-supported formats
- **Preview System**: Built-in audio player for all uploaded files

### 🤖 AI Integration
- **Model Status**: Real-time OpenRouter API availability checking
- **Genre Intelligence**: 7 different genre options with auto-detection
- **Confidence Scoring**: AI provides arrangement confidence ratings
- **Error Recovery**: Graceful handling of API failures

### 📊 Data Visualization
- **Segment Cards**: Rich display of vocal segment characteristics
- **Statistics Dashboard**: Comprehensive arrangement metrics
- **Progress Tracking**: Visual indicators for each processing step

### 💾 Session Management
- **Path Storage**: Uses sessionStorage for audio file paths
- **State Persistence**: Maintains workflow state across interactions
- **Error Recovery**: Preserves user data during error states

## Performance Optimization

- **Lazy Loading**: Components load only when needed
- **Optimized Re-renders**: Minimal re-rendering with proper state management
- **Asset Optimization**: Next.js automatic image and asset optimization
- **Code Splitting**: Automatic route-based code splitting

## Browser Support
- **Modern Browsers**: Chrome 90+, Firefox 90+, Safari 14+, Edge 90+
- **Audio API**: MediaRecorder for live recording
- **File API**: Drag & drop and file selection support

---

*The frontend provides an intuitive interface for the AI-driven vocal arrangement system, making professional vocal arrangement accessible through a modern web application.*
