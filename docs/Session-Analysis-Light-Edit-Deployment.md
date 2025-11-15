# Session Analysis – Light Edit Deployment

## Objectives
- Narrow Gemini transcription prompt to strict outputs only.
- Layer a bespoke light-edit pass that keeps vocabulary intact while improving readability.
- Redeploy the FastAPI backend on Vercel and wire the Expo client to the refreshed endpoint.

## Backend Changes
- Trimmed `PROMPT` in `backend/api/services/transcription.py` to request only `originalStrict` and `englishStrict` variants.
- Introduced `apply_light_edit` helper that:
  - Calls Gemini with explicit rules for sentence reordering (≤30%), filler removal, and grammar cleanup.
  - Strips accidental code fences (` ``` `) from responses before returning text.
  - Falls back to the original text and logs an error if Gemini fails.
- Rewrote `transcribe_audio` to:
  - Fetch strict variants, clean code fences, and JSON-decode the result.
  - Invoke `apply_light_edit` twice to generate `originalLight` and `englishLight`.
  - Return all four variants to preserve the existing API surface.
- Logging additions: `strict_transcription_successful` and `applying_light_edits` provide clear checkpoints when tailing Vercel logs.

## Deployment Actions
- Confirmed Vercel authentication (`vercel whoami`).
- Pushed a production build via `vercel --prod` (deployment ID: `triumphant-transcripts-backend-r03x37x63`).
- Verified health check at `https://triumphant-transcripts-backend.vercel.app/api/health`.
- Ensured the stable alias `https://triumphant-transcripts-backend.vercel.app` points to the new deployment (`vercel alias set`).

## Expo Integration Notes
- `.env` in `app-expo/audio-recorder` now resolves the production alias through `EXPO_PUBLIC_API_URL`.
- Production-mode testing command:
  ```bash
  EXPO_PUBLIC_API_URL="https://triumphant-transcripts-backend.vercel.app" npx expo start --no-dev --minify
  ```
- For an OTA release after validation, run:
  ```bash
  npx eas update --branch production --message "Light edit pipeline"
  ```

## Validation & Manual QA
- Deployed backend responds with `{"status":"ok"}` at `/api/health`.
- Manual Expo test plan:
  1. Launch Expo Go using the production command above.
  2. Record a clip and submit for transcription.
  3. Confirm `originalLight`/`englishLight` show reordered sentences (≤30%), filler removal, and preserved vocabulary.
  4. Watch Vercel logs for `strict_transcription_successful` and `applying_light_edits` markers.

## Follow-Up Considerations
- Optionally add retries or timeouts to `apply_light_edit` if Gemini hiccups impact UX.
- Add unit/integration tests that mock Gemini responses to catch regressions in JSON parsing and light-edit fallbacks.
- Document the light-edit workflow for future prompt tuning (e.g., adjusting `max_move_ratio`).

## Prompt Reference
```
Coding Task: Add Sentence-Reordering to Transcription Service

  Context

  I have a transcription service that uses Gemini AI. Currently it returns 4 variants of transcriptions, but I
  need to enhance the "Light" variants with sentence-reordering logic.

  File to Modify

  /Users/stewartalsop/Dropbox/Crazy 
  Wisdom/Business/Coding_Projects/prototypes-2025/triumphant-transcripts/backend/api/services/transcription.py

  Current Behavior

  The transcribe_audio() function sends audio to Gemini and gets back 4 variants in one API call:
  - originalStrict - verbatim transcription
  - originalLight - cleaned up transcription
  - englishStrict - verbatim English translation
  - englishLight - cleaned up English translation

  Required Changes (Option A: Two-Step Process)

  Step 1: Update the PROMPT constant (lines 15-53)

  Change it to ONLY request the two strict variants:

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

  Step 2: Add a new function apply_light_edit()

  Insert this function between the PROMPT and the transcribe_audio() function:

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

          # Strip code blocks if present
          if result_text.startswith("```"):
              segments = result_text.split("```")
              if len(segments) >= 2:
                  result_text = segments[1]
                  if result_text.startswith("json") or result_text.startswith("text"):
                      result_text = result_text[4:]
              result_text = result_text.strip()

          return result_text
      except Exception as exc:
          logger.error("light_edit_failed: %s", exc, exc_info=True)
          # Return original text if editing fails
          return text

  Step 3: Rewrite the transcribe_audio() function

  Replace the entire function (currently lines 56-106) with this:

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

          result_text = (response.text or "").strip()

          # Strip code blocks if present
          if result_text.startswith("```"):
              segments = result_text.split("```")
              if len(segments) >= 2:
                  result_text = segments[1]
                  if result_text.startswith("json"):
                      result_text = result_text[4:]
              result_text = result_text.strip()

          strict_variants = json.loads(result_text)
          logger.info("strict_transcription_successful")

          # Step 2: Apply light editing to create light variants
          logger.info("applying_light_edits")
          original_light = await apply_light_edit(strict_variants["originalStrict"])
          english_light = await apply_light_edit(strict_variants["englishStrict"])

          # Step 3: Return all 4 variants
          result = {
              "originalStrict": strict_variants["originalStrict"],
              "originalLight": original_light,
              "englishStrict": strict_variants["englishStrict"],
              "englishLight": english_light,
          }

          logger.info("transcription_successful")
          return result

      except json.JSONDecodeError as exc:
          logger.error("json_parse_failed: %s", exc, exc_info=True)
          raise ValueError(f"Failed to parse Gemini response as JSON: {exc}") from exc
      except Exception as exc:  # pragma: no cover - defensive logging
          logger.error("transcription_failed: %s", exc, exc_info=True)
          raise

  Expected Result

  - The API still returns the same 4-key JSON structure
  - originalLight and englishLight now have sentence reordering applied (up to 30% of sentences can be reordered)
  - Total of 3 Gemini API calls: 1 for transcription, 2 for light editing
  - All existing error handling and logging preserved
 Please ask me one clarifying question at a time until you're sure that we are aligned on the goal.
```
