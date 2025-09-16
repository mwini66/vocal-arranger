# Vocal Arranger Frontend

## Overview
This is the frontend for the Vocal Arranger project. It provides a modern web UI for uploading vocal tracks, visualizing Whisper-based speech segments, and re-arranging segments into new compositions.

## Tech Stack
- Next.js (React)
- TypeScript
- TailwindCSS
- Zustand (state management)
- Jest (testing)
- Prettier (formatting)
- ESLint (linting)
- Node.js 24.4.1
- npm

## Folder Structure
- `src/components/ui/` — Segment visualization and arrangement controls
- `src/app/` — Upload and arrangement pages
- `src/lib/` — Zustand store for segment state
- `public/` — Static assets

## Setup

### 1. Clone the repository
```
git clone <repo-url>
cd vocal-arranger/frontend
```

### 2. Install Node.js 24.4.1
Use [nvm](https://github.com/nvm-sh/nvm) or [fnm](https://github.com/Schniz/fnm) to install the correct Node.js version:
```
nvm install 24.4.1
nvm use 24.4.1
```

### 3. Install dependencies
```
npm install
```

### 4. Environment Variables
Copy `.env.example` to `.env.local` and fill in your configuration:
```
cp .env.example .env.local
```

## Running the App
```
npm run dev
```

## Main Features
- Upload vocal tracks
- Display segmented phrases (timings + text)
- Drag-and-drop re-arrangement of segments
- Export arranged composition

## Out of Scope
- No instrumental/beat alignment
- No genre-specific arrangement
- No full AI arrangement engine

## Troubleshooting
- Ensure you are using Node.js 24.4.1.
- If you add new dependencies, run `npm install` again.
- For issues with environment variables, check your `.env.local` file.

---
For more details, see the main project README.
