# Vocal Arranger Backend

## Overview
This is the backend for the Vocal Arranger project. It provides audio alignment, feature extraction, and arrangement services via a Flask API and modular Python scripts.

## Tech Stack
- Python 3.11+
- Flask
- pytest (testing)
- flake8 (linting)
- black (formatting)
- python-dotenv (environment variables)

## Folder Structure
- `backend/` — Main backend code and modules
- `backend/audio_analysis/` — Audio feature extraction and alignment scripts
- `backend/data/` — Data files (audio, logs, features)
- `templates/` — HTML templates
- `uploads/` — User-uploaded and processed files

## Setup

### 1. Clone the repository
```
git clone <repo-url>
cd vocal-arranger/backend
```

### 2. Create and activate a virtual environment
```
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies
```
pip install -r requirements.txt
pip install black flake8 pytest python-dotenv
```

### 4. Environment Variables
Copy `.env.example` to `.env` and fill in your secrets and configuration:
```
cp .env.example .env
```

## Running the App
```
python app.py
```

## Development Commands
- **Run tests:**
  ```
  pytest
  ```
- **Lint code:**
  ```
  flake8 backend/
  ```
- **Format code:**
  ```
  black backend/
  ```

## Troubleshooting
- Ensure your virtual environment is activated before running commands.
- If you add new dependencies, update `requirements.txt`.
- For issues with environment variables, check your `.env` file and python-dotenv usage.

---
For more details, see the main project README.
