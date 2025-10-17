import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import google.generativeai as genai

from api.config import ENV, GEMINI_API_KEY, GEMINI_MODEL_NAME
from api.services.archive import AudioPayload, get_archive_manager

logger = logging.getLogger(__name__)

# Configure Gemini client once at import time
genai.configure(api_key=GEMINI_API_KEY)

PROMPT = """
Transcribe this audio and return JSON in this EXACT format (no other text):
{
  "originalStrict": "word-for-word transcription in the original language spoken",
  "englishStrict": "word-for-word English translation"
}

VARIANT SPECIFICATIONS:

originalStrict - Verbatim capture:
• Include every word, pause, filler (um, uh, like, you know, basically, actually)
• Keep false starts, repetitions, incomplete thoughts
• Original language only

englishStrict - Verbatim English:
• Direct word-for-word translation including all fillers
• Maintain spoken structure even if awkward

Only return valid JSON, nothing else.
"""


async def apply_light_edit(text: str, max_move_ratio: float = 0.3) -> str:
    """
    Apply light editing with sentence reordering:
    - Remove filler words (um, uh, like, etc.)
    - Fix grammar and punctuation
    - Reorder up to 30% of sentences for better flow
    - Preserve exact vocabulary
    """
    prompt = (
        "You will receive a passage of text.\n"
        f"You may reorder up to {int(max_move_ratio * 100)}% of the sentences to improve clarity "
        "and you may correct punctuation or obvious grammar mistakes.\n"
        "You must NOT rephrase the wording of any sentence beyond those fixes.\n"
        "Also remove filler words (um, uh, like, you know, basically, actually), "
        "fix grammar to create complete sentences, and remove repetitions.\n"
        "PRESERVE the exact vocabulary - do not paraphrase or use synonyms.\n"
        "Return ONLY the updated passage as plain text. Do not add explanations or formatting.\n\n"
        "Text:\n" + text
    )

    try:
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        response = model.generate_content(prompt)
        result_text = (response.text or "").strip()

        if result_text.startswith("```"):
            segments = result_text.split("```")
            if len(segments) >= 2:
                result_text = segments[1]
                if result_text.startswith("json") or result_text.startswith("text"):
                    result_text = result_text[4:]
            result_text = result_text.strip()

        return result_text
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("light_edit_failed: %s", exc, exc_info=True)
        # Return original text if editing fails
        return text


async def transcribe_audio(
    audio_content: bytes,
    filename: Optional[str],
    content_type: Optional[str],
) -> Dict[str, Any]:
    """Send audio bytes to Gemini and return transcription variants."""
    try:
        safe_name = Path(filename).name if filename else "recording.m4a"
        mime_type = content_type or "audio/m4a"
        file_size = len(audio_content) if audio_content is not None else 0

        session_id = uuid.uuid4().hex
        request_received_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            "gemini_request_started: session_id=%s filename=%s mime_type=%s size=%s",
            session_id,
            safe_name,
            mime_type,
            file_size,
        )

        # Step 1: Get strict variants from Gemini
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

        raw_response_text = (response.text or "")
        result_text = raw_response_text.strip()

        # Strip code blocks if present
        if result_text.startswith("```"):
            segments = result_text.split("```")
            if len(segments) >= 2:
                result_text = segments[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            result_text = result_text.strip()

        strict_variants = json.loads(result_text)
        logger.info("strict_transcription_successful: session_id=%s", session_id)

        # Step 2: Apply light editing to create light variants
        logger.info("applying_light_edits: session_id=%s", session_id)
        original_light = await apply_light_edit(strict_variants["originalStrict"])
        english_light = await apply_light_edit(strict_variants["englishStrict"])

        light_variants = {
            "originalLight": original_light,
            "englishLight": english_light,
        }

        audio_payload = AudioPayload(
            filename=safe_name,
            content_type=mime_type,
            size_bytes=file_size,
            data=audio_content,
        )

        archive_metadata = {
            "model": GEMINI_MODEL_NAME,
            "environment": ENV,
            "receivedAt": request_received_at,
            "filename": safe_name,
            "contentType": mime_type,
            "sizeBytes": file_size,
        }

        archive_manager = get_archive_manager()
        archive_info = await archive_manager.persist_session(
            session_id=session_id,
            prompt=PROMPT.strip(),
            raw_response_text=raw_response_text.strip(),
            strict_variants=strict_variants,
            light_variants=light_variants,
            audio=audio_payload,
            metadata=archive_metadata,
        )
        logger.info(
            "archive_persisted: session_id=%s backend=%s enabled=%s",
            session_id,
            archive_info.get("backend"),
            archive_info.get("enabled"),
        )

        # Step 3: Return all 4 variants
        result = {
            "sessionId": session_id,
            "archive": archive_info,
            "originalStrict": strict_variants["originalStrict"],
            "originalLight": original_light,
            "englishStrict": strict_variants["englishStrict"],
            "englishLight": english_light,
        }

        logger.info("transcription_successful: session_id=%s", session_id)
        return result

    except json.JSONDecodeError as exc:
        logger.error("json_parse_failed: %s", exc, exc_info=True)
        raise ValueError(f"Failed to parse Gemini response as JSON: {exc}") from exc
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("transcription_failed: %s", exc, exc_info=True)
        raise
