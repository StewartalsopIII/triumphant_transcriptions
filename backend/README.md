# Triumphant Transcripts Backend

FastAPI backend deployed on Vercel for audio transcription.

## Local Development

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the development server:
```bash
uvicorn api.index:app --reload --port ${PORT:-8000}
```

## Deployment

- Configure environment variables in Vercel or through a `.env` file (see `.env.example`).
- Deploy with the Vercel CLI or dashboard; the entry point is `api/index.py`.
