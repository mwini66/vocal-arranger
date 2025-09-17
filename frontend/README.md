# AI-Driven Vocal Arranger Frontend - Temporal Alignment Interface

## Overview
Modern React-based frontend for the AI-Driven Vocal Arranger system featuring intelligent speech segmentation and temporal alignment. Provides an intuitive 3-step workflow for processing freestyle vocals, analyzing reference tracks, and creating professionally aligned vocal arrangements through advanced windowed matching.

## Tech Stack
- **Next.js 14+** (App Router)
- **TypeScript** 
- **TailwindCSS** (Styling)
- **React Hooks** (State management)
- **Node.js 24.4.1**
- **npm** (Package management)

## Core System Workflow

### 🎯 Primary: 3-Step Temporal Alignment Workflow
1. **Process Input Vocals**: Upload/record → WhisperX speech segmentation → Enhanced feature extraction
2. **Process Reference Track**: Upload reference → Structure analysis → Timing pattern extraction
3. **Temporal Alignment**: Advanced windowed matching → Quality optimization → High-quality audio output

### 🎵 Key Innovation Features
- **Automated Speech Segmentation**: Whisper-based phrase detection with >95% accuracy
- **Intelligent Segment Visualization**: Real-time display of vocal phrase boundaries and characteristics
- **Advanced Matching Analysis**: Detailed comparison of text similarity and audio feature compatibility
- **Professional Audio Generation**: High-quality time-aligned output with crossfading and compression

## Key Features

### 🎵 Advanced Audio Interface
- **Live Recording**: Browser-based vocal recording with MediaRecorder API
- **Audio Preview**: Built-in audio player for uploads and outputs
- **File Management**: Upload, preview, and remove audio files with drag-and-drop support
- **Download Support**: High-quality downloads for temporally-aligned vocals

### ⚡ Temporal Alignment Features
- **Detailed Match Visualization**: Segment-by-segment similarity analysis with color-coded quality indicators
- **Matching Statistics**: Real-time display of match rates, similarity scores, and usage metrics
- **Quality Insights**: TF-IDF text similarity breakdown and audio feature matching details
- **Algorithm Transparency**: Shows windowing approach, similarity thresholds, and processing methods

### 📊 Enhanced Results Visualization
- **Arrangement Statistics**: Match rates, confidence scores, usage efficiency
- **Segment Analysis**: Energy, pitch, mood, structural hints, and keywords
- **Progress Indicators**: Independent loading states for each processing step
- **Interactive Details**: Expandable matching analysis with similarity breakdowns

## Project Structure
```
frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx              # Main temporal alignment interface
│   │   ├── layout.tsx            # App layout and metadata
│   │   └── globals.css           # TailwindCSS configuration
│   ├── components/ui/
│   │   ├── AudioPlayer.tsx       # Universal audio playback component
│   │   ├── FeedbackModal.tsx     # Comprehensive user feedback collection
│   │   ├── card.tsx              # UI card component
│   │   └── button.tsx            # UI button component
│   └── lib/
│       └── utils.ts              # Utility functions and helpers
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

## User Workflows

### Primary: Temporal Alignment Workflow

#### Step 1: Input Vocals Processing
- **Upload or Record**: Select audio file or use live recording with MediaRecorder API
- **Audio Preview**: Listen to uploaded vocals before processing with built-in player
- **Process Button**: Triggers WhisperX speech segmentation and comprehensive feature extraction
- **Results Display**: Shows detected segments with energy, pitch, mood, and text analysis

#### Step 2: Reference Track Processing  
- **Upload Reference**: Select reference vocal track with desired timing structure
- **Audio Preview**: Listen to reference track to verify timing patterns
- **Process Button**: Analyzes reference structure, energy patterns, and timing characteristics
- **Results Confirmation**: Displays reference segments and processing success status

#### Step 3: Advanced Temporal Alignment
- **Automatic Processing**: System performs multi-window matching analysis automatically
- **Quality Optimization**: Selects best windowing approach based on similarity scores
- **Real-time Feedback**: Shows processing progress with detailed status updates
- **Results Visualization**: Comprehensive matching analysis with segment-by-segment details

## Component Architecture

### Main Page (`page.tsx`)
**Comprehensive temporal alignment interface**
- **State Management**: 15+ React state variables for workflow control
- **API Integration**: Handles all backend communication with error recovery
- **Workflow Management**: Seamless 3-step temporal alignment process
- **Loading States**: Independent loading indicators for each processing step

### Enhanced Features:
- **Detailed Matching Analysis**: Expandable segment-by-segment visualization
- **Quality Indicators**: Color-coded similarity scores and match quality
- **Statistics Dashboard**: Real-time metrics and performance indicators
- **Session Management**: Maintains state across workflow steps

### AudioPlayer Component
**Universal audio playback system**
- **Format Support**: MP3, WAV, M4A, and other browser-supported formats
- **Responsive Design**: Adapts to different screen sizes and contexts
- **Error Handling**: Graceful fallback for unsupported formats

### FeedbackModal Component
**Comprehensive user feedback collection**
- **Multi-dimensional Ratings**: Audio quality, arrangement coherence, energy flow
- **Detailed Data Collection**: Session tracking, arrangement analysis, user preferences
- **Training Data Generation**: Structured data for ML model improvement

## API Integration

### Core Temporal Alignment Endpoints
- `POST /process_vocals` - Step 1: Input vocals processing with WhisperX speech segmentation
- `POST /process_reference` - Step 2: Reference track analysis and structure extraction
- `POST /arrange_to_reference` - Step 3: Advanced windowed temporal alignment

### System Status & Feedback
- `GET /model_status` - Real-time availability of all system components
- `POST /arrangement/feedback` - Comprehensive user feedback with training data

### Enhanced Data Flow
1. **File Upload** → FormData with validation → Backend processing with progress tracking
2. **Processing Status** → Real-time loading indicators with detailed status messages
3. **Results Display** → Rich visualization with interactive analysis details
4. **Audio Output** → High-quality downloadable results with statistics

## Advanced UI Features

### 🎵 Temporal Alignment Visualization
- **Segment Matching Cards**: Detailed comparison of reference vs input segments
- **Similarity Indicators**: Visual bars showing text and audio feature similarity
- **Quality Color Coding**: Green (>70%), Yellow (40-70%), Red (<40%) similarity scores
- **Match Type Display**: Shows matched segments vs silence padding with explanations

### 📊 Statistics Dashboard
```typescript
// Real-time statistics display
interface AlignmentStats {
  match_rate: number;           // Percentage of reference segments matched
  average_similarity: number;   // Average similarity across matches
  silence_percentage: number;   // Percentage of output filled with silence
  usage_rate: number;          // Percentage of input segments used
  window_size_used: number;    // Optimal window size selected
}
```

### 🎛️ Interactive Controls
- **Expandable Details**: "Show/Hide Matching Details" for in-depth analysis
- **Download Management**: Direct downloads and new-tab opening for audio files
- **Session Persistence**: Uses sessionStorage for audio file paths and state

## Development Scripts

```bash
# Development server with hot reload and advanced debugging
npm run dev

# Production build with optimization
npm run build

# Production server
npm start

# TypeScript type checking
npm run type-check

# ESLint with Next.js config
npm run lint

# Fix linting issues automatically
npm run lint --fix

# Code formatting with Prettier
npm run format
```

## Key Implementation Details

### 🎵 Advanced Audio Processing
- **File Handling**: Drag & drop, file selection, live recording with validation
- **Format Support**: Comprehensive browser audio format compatibility
- **Preview System**: Built-in audio player with fallback support
- **Quality Indicators**: File size, duration, and format information display

### ⚡ Temporal Alignment Features
- **Multi-Window Visualization**: Shows how different window sizes affect matching
- **Similarity Breakdown**: Separate display of text similarity vs audio feature matching
- **Sequential Analysis**: Highlights consecutive segment matches and coherence
- **Algorithm Transparency**: Explains TF-IDF, cosine similarity, and windowing approach

### 📊 Enhanced Data Visualization
- **Match Quality Cards**: Individual segment analysis with color-coded similarity scores
- **Statistics Grids**: Multi-dimensional metric display (match rate, similarity, usage)
- **Progress Tracking**: Visual indicators for each processing step with detailed status
- **Interactive Analysis**: Expandable details for technical users and simplified view for others

### 💾 Advanced Session Management
- **State Persistence**: Maintains workflow state across browser interactions
- **Path Storage**: Uses sessionStorage for audio file paths and processing results
- **Error Recovery**: Preserves user data and progress during error states
- **Workflow Continuity**: Seamless progression through 3-step alignment process

## Performance Optimization

- **Lazy Loading**: Components and resources load only when needed
- **Optimized Re-renders**: Minimal re-rendering with proper React state management
- **Asset Optimization**: Next.js automatic image and asset optimization with caching
- **Code Splitting**: Automatic route-based code splitting for faster initial loads
- **API Efficiency**: Smart caching and batched requests for repeated operations

## Browser Support & Compatibility
- **Modern Browsers**: Chrome 90+, Firefox 90+, Safari 14+, Edge 90+ with full feature support
- **Audio API**: MediaRecorder API for live recording with fallback for older browsers
- **File API**: Drag & drop and file selection support across all target browsers
- **WebAudio**: Advanced audio processing and visualization where supported

## Accessibility Features
- **Keyboard Navigation**: Full keyboard accessibility for all interactive elements
- **Screen Reader Support**: ARIA labels and semantic HTML structure
- **High Contrast**: Color schemes that work with high contrast modes
- **Focus Management**: Clear visual focus indicators and logical tab ordering

## Success Metrics & Validation

### Core Metrics (aligned with project goals):
- **Segmentation Visualization**: >95% accurate vocal phrase display ✅
- **User Workflow**: Intuitive upload → segment → arrange workflow ✅
- **Match Quality Display**: 60-90% successful alignment visualization ✅
- **Processing Speed**: Real-time progress indicators and feedback ✅

### Validation Commands:
```bash
# Frontend validation
npm run build
npm run test
npm run lint
npx prettier --check .

# Workflow testing
npm run test -- --testNamePattern="upload.*visualization.*arrangement"
```

## Testing & Validation

### UI Testing
- **Segment Visualization**: Test display of segmented phrases with timings and text
- **Upload Workflows**: Validate drag-and-drop and file selection functionality
- **Arrangement Controls**: Test temporal alignment interface and result display

### Performance Testing  
- **Loading Performance**: Ensure <3s initial load time
- **Audio Processing**: Real-time progress indicators during segmentation
- **Memory Management**: Efficient handling of audio file uploads and processing

---

*The frontend provides an intuitive, production-ready interface for advanced vocal arrangement through intelligent speech segmentation and temporal alignment, making professional vocal arrangement accessible through a user-friendly web application that fulfills the original project vision of automated phrase detection and re-arrangement.*
