import logging
import re
from typing import Any, Dict, List

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel
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


class TransformRequest(BaseModel):
    text: str
    type: str  # "tweet" | "professional" | "custom"
    customPrompt: str | None = None


SOFT_CONSTRAINT_PROMPT = """You are rewriting a transcript excerpt. Follow these rules strictly:
- Obey the user's instruction exactly.
- Output a single paragraph (no blank lines or bullet lists).
- Keep the response under 120 words.
- Do not add commentary, headings, or explanations.

Return only the rewritten text."""


def build_custom_prompt(user_instruction: str, transcript: str) -> str:
    sanitized_instruction = user_instruction.strip()
    return (
        f"{SOFT_CONSTRAINT_PROMPT}\n\n"
        f"User instruction:\n{sanitized_instruction}\n\n"
        f"Transcript:\n{transcript.strip()}\n"
    )


def analyze_custom_output(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    word_count = len(re.findall(r"\b\w+\b", cleaned))
    has_paragraph_breaks = "\n\n" in cleaned or cleaned.count("\n") > 0
    has_list_markers = bool(
        re.search(r"^\s*(?:[-*•]|\d+\.)\s+", cleaned, flags=re.MULTILINE)
    )

    violations: List[str] = []
    if word_count > 120:
        violations.append("word_limit_exceeded")
    if has_paragraph_breaks:
        violations.append("multiple_paragraphs_detected")
    if has_list_markers:
        violations.append("list_formatting_detected")

    return {
        "wordCount": word_count,
        "violations": violations,
    }


@app.post("/api/transcribe")
async def transcribe_audio_endpoint(audio: UploadFile = File(...)) -> Dict[str, Any]:
    """Accept audio uploads and return Gemini transcription variants."""
    try:
        logger.info("transcribe_started: filename=%s", audio.filename)

        contents = await audio.read()
        file_size = len(contents)
        logger.info("audio_received: size=%s bytes", file_size)

        result = await transcribe_audio(contents, audio.filename, audio.content_type)

        logger.info("transcribe_finished: session_id=%s", result.get("sessionId"))
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

@app.post("/api/transform")
async def transform_text(request: TransformRequest):
    try:
        logger.info("transform_started: type=%s", request.type)

        import google.generativeai as genai
        from api.config import GEMINI_MODEL_NAME

        if request.type == "tweet":
            prompt = f"""Condense this to ~280 characters, make it punchy and engaging for Twitter/X. Keep the core insight but make it shareable:

{request.text}

Only return the tweet text, nothing else."""
        elif request.type == "professional":
            prompt = f"""Rewrite this in a formal, professional tone suitable for business communication. Remove casual language and structure it clearly:

{request.text}

Only return the professional version, nothing else."""
        elif request.type == "custom":
            if not request.customPrompt:
                raise HTTPException(status_code=400, detail="customPrompt required for custom type")
            prompt = build_custom_prompt(request.customPrompt, request.text)
        else:
            raise HTTPException(status_code=400, detail="Invalid type. Use: tweet, professional, or custom")

        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        response = model.generate_content(prompt)
        result_text = (response.text or "").strip()

        response_payload: Dict[str, Any] = {"text": result_text}
        if request.type == "custom":
            diagnostics = analyze_custom_output(result_text)
            response_payload.update(
                {
                    "violations": diagnostics["violations"],
                    "metadata": {"wordCount": diagnostics["wordCount"]},
                }
            )

        logger.info("transform_finished")
        return response_payload
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("transform_failed: %s", exc, exc_info=True)
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
