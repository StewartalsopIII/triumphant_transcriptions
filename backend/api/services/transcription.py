import json
import logging
from pathlib import Path
from typing import Dict, Optional

import google.generativeai as genai

from api.config import GEMINI_API_KEY, GEMINI_MODEL_NAME

logger = logging.getLogger(__name__)

# Configure Gemini client once at import time
genai.configure(api_key=GEMINI_API_KEY)

PROMPT = """
Transcribe this audio and return JSON in this EXACT format (no other text):
{
  "originalStrict": "word-for-word transcription in the original language spoken",
  "originalLight": "same language as original, remove um/uh/like filler words, fix grammar, keep exact vocabulary",
  "englishStrict": "word-for-word English translation",
  "englishLight": "natural English translation, remove filler words, clean grammar"
}

Only return valid JSON, nothing else.
"""


async def transcribe_audio(
    audio_content: bytes,
    filename: Optional[str],
    content_type: Optional[str],
) -> Dict[str, str]:
    """Send audio bytes to Gemini and return transcription variants."""
    try:
        safe_name = Path(filename).name if filename else "recording.m4a"
        mime_type = content_type or "audio/m4a"
        file_size = len(audio_content) if audio_content is not None else 0

        logger.info(
            "gemini_request_started: filename=%s mime_type=%s size=%s",
            safe_name,
            mime_type,
            file_size,
        )

        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        response = model.generate_content(
            [
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": audio_content,
                    }
                },
                {"text": PROMPT},
            ]
        )

        result_text = (response.text or "").strip()

        if result_text.startswith("```"):
            segments = result_text.split("```")
            if len(segments) >= 2:
                result_text = segments[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            result_text = result_text.strip()

        result = json.loads(result_text)
        logger.info("transcription_successful")
        return result
    except json.JSONDecodeError as exc:
        logger.error("json_parse_failed: %s", exc, exc_info=True)
        raise ValueError(f"Failed to parse Gemini response as JSON: {exc}") from exc
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("transcription_failed: %s", exc, exc_info=True)
        raise
