import logging
from typing import Dict

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from api.config import CORS_ORIGINS, ENV
from api.services.transcription import transcribe_audio

# Setup logging for Vercel
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Triumphant Transcripts API",
    description="Audio transcription API with Gemini",
    version="1.0.0"
)

# CORS - Critical for Expo Go to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root() -> Dict[str, str]:
    """Root endpoint - confirms API is running"""
    logger.info("root_endpoint_accessed")
    return {
        "message": "Triumphant Transcripts API is live!",
        "environment": ENV,
        "version": "1.0.0"
    }

@app.get("/api/health")
def health_check() -> Dict[str, str]:
    """Health check endpoint for monitoring"""
    logger.info("health_check_accessed")
    return {"status": "ok"}

@app.get("/api/test")
def test_endpoint() -> Dict[str, str]:
    """Test endpoint to verify API is reachable from mobile"""
    logger.info("test_endpoint_accessed")
    return {
        "message": "If you can see this from your phone, CORS is working!",
        "timestamp": "2025-01-01T00:00:00Z"
    }

@app.post("/api/transcribe")
async def transcribe_audio_endpoint(audio: UploadFile = File(...)) -> Dict[str, str]:
    """Accept audio uploads and return Gemini transcription variants."""
    try:
        logger.info("transcribe_started: filename=%s", audio.filename)

        contents = await audio.read()
        file_size = len(contents)
        logger.info("audio_received: size=%s bytes", file_size)

        result = await transcribe_audio(contents, audio.filename, audio.content_type)

        logger.info("transcribe_finished")
        return result
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("transcribe_failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(exc),
                "suggestion": "Check Vercel logs with: vercel logs",
            },
        ) from exc


# Error handler for debugging
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"unhandled_exception: {str(exc)}", exc_info=True)
    return {
        "error": "Internal server error",
        "detail": str(exc),
        "suggestion": "Check Vercel logs with: vercel logs"
    }
