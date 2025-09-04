# Vocal Arranger Frontend

## Overview
This is the frontend for the Vocal Arranger project. It provides a modern web UI for uploading, aligning, and arranging vocal and instrumental tracks.

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
- `src/components/ui/` — Reusable UI components
- `src/app/` — App entry, layout, and pages
- `src/lib/` — Utility functions and Zustand stores
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
Create a `.env.local` file in the `frontend/` directory for secrets and configuration. Example:
```
NEXT_PUBLIC_API_URL=http://localhost:5000
# Add other config as needed
```

## Running the App
```
npm run dev
```

## Development Commands
- **Build:**
  ```
  npm run build
  ```
- **Run tests (Jest):**
  ```
  npm run test
  ```
- **Lint code (ESLint):**
  ```
  npm run lint
  ```
- **Format code (Prettier):**
  ```
  npx prettier --write .
  ```

## State Management
- Use [Zustand](https://github.com/pmndrs/zustand) for global/shared state.
- Place stores in `src/lib/store.ts` or similar.

## Troubleshooting
- Ensure you are using Node.js 24.4.1.
- If you add new dependencies, run `npm install` again.
- For issues with environment variables, check your `.env.local` file.

---
For more details, see the main project README.
