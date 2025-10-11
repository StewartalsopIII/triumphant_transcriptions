import logging
from typing import Dict, Union

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from api.config import CORS_ORIGINS, ENV

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

@app.post("/api/upload")
async def upload_audio(audio: UploadFile = File(...)) -> Dict[str, Union[str, int, None]]:
    """Accepts audio file uploads and reports metadata."""
    try:
        logger.info(
            f"upload_started: filename={audio.filename}, content_type={audio.content_type}"
        )

        contents = await audio.read()
        file_size = len(contents)

        logger.info(f"upload_finished: size={file_size} bytes")

        return {
            "status": "received",
            "filename": audio.filename,
            "size": file_size,
            "content_type": audio.content_type,
        }
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("upload_failed: %s", str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


# Error handler for debugging
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"unhandled_exception: {str(exc)}", exc_info=True)
    return {
        "error": "Internal server error",
        "detail": str(exc),
        "suggestion": "Check Vercel logs with: vercel logs"
    }
