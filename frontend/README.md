# AI-Driven Vocal Arranger Frontend

## Overview
This is the frontend for the AI-Driven Vocal Arranger project. It provides a modern web UI for uploading freestyle vocals, visualizing AI-enhanced segment analysis, and experiencing intelligent vocal arrangement powered by OpenRouter's gpt-oss model.

## Tech Stack
- Next.js 14+ (React)
- TypeScript
- TailwindCSS
- Jest (testing)
- Prettier (formatting)
- ESLint (linting)
- Node.js 24.4.1
- npm

## Key Features
- **Intuitive Upload Interface**: Upload audio files or record directly in browser
- **AI Segment Visualization**: Rich display of vocal segments with energy, pitch, mood, and structural analysis
- **Multiple AI Arrangement Methods**: Compare different AI approaches (genre-specific, structure-based)
- **Real-time Confidence Scoring**: See how confident the AI is in its arrangement decisions
- **User Feedback System**: Rate arrangements to help improve AI performance
- **Responsive Design**: Works seamlessly on desktop and mobile devices

## Folder Structure
```
frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx              # Main upload and arrangement interface
│   │   ├── layout.tsx            # App layout and global styles
│   │   └── globals.css           # Global CSS with TailwindCSS
│   ├── components/ui/
│   │   ├── AIVocalArranger.tsx   # Main AI arrangement interface
│   │   ├── AudioPlayer.tsx       # Audio playback component
│   │   ├── card.tsx              # Reusable card component
│   │   └── button.tsx            # Reusable button component
│   └── lib/
│       └── utils.ts              # Utility functions
├── public/                       # Static assets
└── package.json                  # Dependencies and scripts
```

## Setup

### 1. Clone the repository
```bash
git clone <repo-url>
cd vocal-arranger/frontend
```

### 2. Install Node.js 24.4.1
Use [nvm](https://github.com/nvm-sh/nvm) to install the correct Node.js version:
```bash
nvm install 24.4.1
nvm use 24.4.1
```

### 3. Install dependencies
```bash
npm install
```

### 4. Environment Variables
Create `.env.local` with your backend API URL:
```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:5000
```

## Running the App
```bash
npm run dev
```

The app will be available at `http://localhost:3000`

## User Workflow

### 1. Upload or Record Vocals
- **Upload**: Select any audio file with freestyle vocals
- **Record**: Use built-in browser recording for live vocals
- **Preview**: Listen to uploaded audio before processing

### 2. AI Analysis & Segmentation
- **Automatic Processing**: WhisperX transcribes and segments vocals
- **Enhanced Features**: AI analyzes each segment for:
  - Energy levels (very low to very high)
  - Pitch categories (low to high)
  - Mood detection (party, intense, sad, positive, neutral)
  - Structural hints (intro-like, hook-like, outro-like)
  - Repetition analysis and text characteristics

### 3. AI-Powered Arrangement
- **Genre Selection**: Choose from pop, hip-hop, R&B, or auto-detect
- **Structure Options**: Standard pop, hip-hop, R&B, or simple arrangements
- **Multiple Methods**: Compare different AI arrangement approaches
- **Confidence Scoring**: See how confident the AI is (0-100%)

### 4. Review & Feedback
- **Detailed Analysis**: View AI reasoning for arrangement decisions
- **Segment Visualization**: Rich cards showing all segment characteristics
- **User Rating**: Rate arrangements (1-5 stars) to improve AI
- **Method Comparison**: See similarities between different AI approaches

## Components Overview

### AIVocalArranger
Main component that handles the AI arrangement interface:
- **Controls Panel**: Genre/structure selection, arrangement methods
- **Segment Display**: Rich visualization of vocal segments with characteristics
- **Method Comparison**: Side-by-side comparison of different AI approaches
- **Feedback System**: User rating and feedback collection

### AudioPlayer
Reusable audio playback component:
- **Waveform Display**: Visual representation of audio
- **Playback Controls**: Play, pause, seek functionality
- **Browser Compatibility**: Works across different browsers

## Development

### Run Development Server
```bash
npm run dev
```

### Build for Production
```bash
npm run build
```

### Run Tests
```bash
npm run test
```

### Linting
```bash
npm run lint
```

### Code Formatting
```bash
npx prettier --write .
```

## AI Integration

The frontend communicates with the backend AI system through these key flows:

1. **Segment Analysis**: `/segment` endpoint processes audio and returns enhanced features
2. **AI Arrangement**: `/arrange` endpoint uses gpt-oss for intelligent arrangement
3. **Method Comparison**: `/arrangement/compare` tests multiple AI approaches
4. **Feedback Loop**: `/arrangement/feedback` improves AI with user ratings

## Success Metrics
- **User Experience**: Intuitive upload and arrangement workflow
- **Performance**: <3s segment processing, <5s AI arrangement
- **AI Transparency**: Clear confidence scores and reasoning display
- **Feedback Collection**: High user engagement with rating system
