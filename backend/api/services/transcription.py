import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, NoReturn

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

Formatting guidelines for both variants:
• Insert a single newline when the speaker clearly pauses or shifts to a new thought
• Do not insert double newlines or formal paragraph breaks
• If unsure, err on the side of fewer line breaks to preserve the spoken flow

Only return valid JSON, nothing else.
"""

CONTINUE_PROMPT_TEMPLATE = """
The previous response stopped mid-thought. You must continue the transcript until the audio ends.

Partial transcript that you already returned:
{partial_json}

Return ONLY the missing continuation in this exact JSON shape (no other text):
{
  "originalStrict": "continuation text only, do not repeat prior content",
  "englishStrict": "continuation text only, do not repeat prior content"
}

Do not restate any sentences that appear in the partial transcript. Continue seamlessly from where it stops and include the complete remainder of the audio.
"""

MAX_CONTINUATION_ATTEMPTS = 1
MIN_TRUNCATION_LENGTH = 200


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
        "Structure the text into coherent paragraphs separated by double line breaks, grouping "
        "sentences by topic so it reads like polished prose.\n"
        "Do not introduce headings, bullet lists, or other formats unless they are already present.\n"
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
        strict_variants, raw_response_text = await _request_strict_variants(
            audio_content,
            mime_type,
            PROMPT,
            session_id=session_id,
        )
        logger.info("strict_transcription_successful: session_id=%s", session_id)

        continuation_raw_responses: List[str] = []
        retry_count = 0
        needs_continuation = any(
            _is_truncated(strict_variants.get(field, ""))
            for field in ("originalStrict", "englishStrict")
        )

        truncation_detected = needs_continuation

        while needs_continuation and retry_count < MAX_CONTINUATION_ATTEMPTS:
            retry_count += 1
            logger.warning(
                "strict_transcription_truncated_detected: session_id=%s attempt=%s",
                session_id,
                retry_count,
            )

            partial_json = json.dumps(
                {
                    "originalStrict": strict_variants.get("originalStrict", ""),
                    "englishStrict": strict_variants.get("englishStrict", ""),
                },
                ensure_ascii=True,
                indent=2,
            )
            continue_prompt = CONTINUE_PROMPT_TEMPLATE.format(partial_json=partial_json)
            try:
                continuation_variants_raw, continuation_raw = await _request_strict_variants(
                    audio_content,
                    mime_type,
                    continue_prompt,
                    session_id=session_id,
                )
            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning(
                    "strict_transcription_continuation_parse_failed: session_id=%s attempt=%s error=%s",
                    session_id,
                    retry_count,
                    exc,
                )
                break

            continuation_raw_responses.append(continuation_raw.strip())

            if not isinstance(continuation_variants_raw, dict):
                logger.warning(
                    "strict_transcription_continuation_non_dict: session_id=%s attempt=%s type=%s",
                    session_id,
                    retry_count,
                    type(continuation_variants_raw).__name__,
                )
                break

            continuation_variants = continuation_variants_raw

            for field in ("originalStrict", "englishStrict"):
                addition_raw = continuation_variants.get(field)
                addition = (addition_raw or "").strip()
                if not addition:
                    continue
                base = strict_variants.get(field, "")
                separator = "" if not base or base.endswith((" ", "\n")) else " "
                strict_variants[field] = f"{base}{separator}{addition}"

            needs_continuation = any(
                _is_truncated(strict_variants.get(field, ""))
                for field in ("originalStrict", "englishStrict")
            )

        if needs_continuation:
            logger.warning("strict_transcription_still_truncated: session_id=%s", session_id)
        else:
            logger.info(
                "strict_transcription_continuation_complete: session_id=%s attempts=%s",
                session_id,
                retry_count,
            )

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
            "continuationAttempts": retry_count,
            "truncationDetected": truncation_detected,
            "truncatedAfterRetries": needs_continuation,
        }

        archive_manager = get_archive_manager()
        raw_payload = raw_response_text.strip()
        if continuation_raw_responses:
            continuation_text = "\n\n--- CONTINUATION ---\n\n".join(continuation_raw_responses)
            raw_payload = f"{raw_payload}\n\n--- CONTINUATION ---\n\n{continuation_text}".strip()
        archive_info = await archive_manager.persist_session(
            session_id=session_id,
            prompt=PROMPT.strip(),
            raw_response_text=raw_payload,
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
def _strip_code_fence(text: str) -> str:
    """Remove leading Markdown code fences the model sometimes returns."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        segments = cleaned.split("```")
        if len(segments) >= 2:
            cleaned = segments[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            elif cleaned.startswith("text"):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    return cleaned


def _is_truncated(text: str) -> bool:
    """Heuristic to flag transcripts that probably stopped early."""
    stripped = text.strip()
    if not stripped:
        return False

    if len(stripped) < MIN_TRUNCATION_LENGTH:
        return False

    terminal_chars = {'.', '!', '?', '"', "'", ')', '…', '”', '’'}
    if stripped[-1] in terminal_chars:
        return False

    return True


async def _request_strict_variants(
    audio_content: bytes,
    mime_type: str,
    prompt: str,
    *,
    session_id: Optional[str] = None,
) -> Tuple[Dict[str, Any], str]:
    model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    response = model.generate_content(
        [
            {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": audio_content,
                }
            },
            {"text": prompt},
        ]
    )

    raw_response_text = response.text or ""
    parsed_text = _strip_code_fence(raw_response_text)
    try:
        strict_variants = json.loads(parsed_text)
    except json.JSONDecodeError as exc:
        # Gemini occasionally returns invalid JSON containing literal control
        # characters (e.g. raw newlines). Retry with loose parsing first.
        if "Invalid control character" in str(exc):
            try:
                strict_variants = json.loads(parsed_text, strict=False)
                logger.warning(
                    "strict_transcription_parse_recovered: session_id=%s mode=loose",
                    session_id,
                )
            except json.JSONDecodeError:
                strict_variants = _log_and_raise_parse_error(parsed_text, session_id, exc)
        else:
            strict_variants = _log_and_raise_parse_error(parsed_text, session_id, exc)
    return strict_variants, raw_response_text


def _log_and_raise_parse_error(
    parsed_text: str, session_id: Optional[str], exc: Exception
) -> NoReturn:
    snippet = parsed_text[:800]
    safe_snippet = (
        snippet.encode("unicode_escape", "backslashreplace")
        .decode("ascii", "replace")
    )
    logger.error(
        "strict_transcription_parse_failed: session_id=%s error=%s snippet=%s",
        session_id,
        exc,
        safe_snippet,
    )
    raise exc
