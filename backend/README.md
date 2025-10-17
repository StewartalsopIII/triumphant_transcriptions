# Triumphant Transcripts Backend

FastAPI backend deployed on Vercel for audio transcription powered by Google Gemini.

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
3. Set environment variables (see below). When working locally you can copy `.env.example` to `.env` and source it:
   ```bash
   cp .env.example .env
   source .env
   ```
4. Run the development server:
   ```bash
   uvicorn api.index:app --reload --port ${PORT:-8000}
   ```

## Environment Variables

| Name | Description |
| ---- | ----------- |
| `ENV` | Runtime environment label (default: `development`). |
| `PORT` | Local development port (default: `8000`). |
| `CORS_ORIGINS` | Comma-separated list of allowed origins (default: `*`). |
| `GEMINI_API_KEY` | **Required.** Google Gemini API key. |
| `GEMINI_MODEL_NAME` | Gemini model to use (default: `gemini-2.0-flash-exp`). |
| `ARCHIVE_STORAGE` | Optional. `none` (default), `local`, or `vercel_blob` to control artifact archiving. |
| `ARCHIVE_LOCAL_DIR` | Optional when using `local` storage. Directory for session artifacts (default: `./archive`). |
| `ARCHIVE_BLOB_PREFIX` | Optional key prefix when using Vercel Blob (default: `sessions`). |
| `VERCEL_BLOB_READ_WRITE_TOKEN` | Required when `ARCHIVE_STORAGE=vercel_blob`. Token for Vercel Blob access. |

## Gemini Setup (Production)

1. Obtain an API key from [Google AI Studio](https://aistudio.google.com/apikey).
2. Enable the **Gemini 2.0 Flash Experimental** model in AI Studio.
3. Configure the Vercel project secrets:
   ```bash
   vercel env add GEMINI_API_KEY
   vercel env add GEMINI_MODEL_NAME  # use: gemini-2.0-flash-exp
   ```
4. Redeploy the backend:
   ```bash
   vercel --prod
   ```

## Deployment

- Ensure the environment variables above are configured in Vercel (or provided via a `.env` file for local testing).
- Deploy with the Vercel CLI or dashboard; the entry point remains `api/index.py`.

## Session Archiving

- Each transcription request now returns a `sessionId` and an `archive` payload describing where the audio, prompts, and Gemini responses are stored.
- By default archiving is disabled (`ARCHIVE_STORAGE=none`). Configure one of the storage modes before deploying so investigations have full context.
- **Local mode** (`ARCHIVE_STORAGE=local`): artifacts are written to `ARCHIVE_LOCAL_DIR`. Only use this for local debugging because serverless file systems are ephemeral.
- **Vercel Blob mode** (`ARCHIVE_STORAGE=vercel_blob`):
  1. Create a Blob store in the Vercel dashboard.
  2. Generate a read/write token and set `VERCEL_BLOB_READ_WRITE_TOKEN`.
  3. Optionally set `ARCHIVE_BLOB_PREFIX` to group session folders.
- Saved artifacts include: original audio, strict/light transcripts, the raw Gemini response text, the prompt, and request metadata.
- Results appear in the mobile app under Session Details and can be copied for support tickets.
