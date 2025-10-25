# Gemini JSON Parse Edge Case

## Context
- Blob store slug: `triumphant-transcripts-back-blob`.
- Prefix in env vars: `ARCHIVE_BLOB_PREFIX=triumphant-transcripts-back-blob/sessions`.
- `ARCHIVE_STORAGE=vercel_blob` so every transcription writes artifacts to Vercel Blob.
- Secrets now flow through `VERCEL_BLOB_READ_WRITE_TOKEN` only; old `BLOB_READ_WRITE_TOKEN` entries were removed via storage → projects reconnection.
- Production redeployed (`vercel --prod`) after the secret rotation and code updates.

## Symptom
- Gemini sometimes returns malformed JSON containing literal control characters, leading to `Invalid control character` errors when parsing the strict transcript payload.
- Previously the backend threw a 500 before archiving could run, leaving no session artifacts.

## Mitigation (Oct 25, 2025)
1. Added logging that captures the session ID and an escaped snippet of the bad payload.
2. Wrapped parsing in a two-step strategy:
   - First attempt uses default `json.loads`.
   - On `Invalid control character`, retry with `json.loads(..., strict=False)`.
   - If the loose parse also fails, raise while logging the escaped payload for inspection.
3. Passed `session_id` into `_request_strict_variants` so log lines map back to the UI error.
4. Confirmed the fallback works end-to-end; successful runs show both the blob upload logs and the new `strict_transcription_parse_recovered` warning if recovery happens.

## How to Investigate If It Reappears
1. Run `vercel logs https://triumphant-transcripts-backend.vercel.app` soon after the failure.
2. Search for `strict_transcription_parse_failed` or `strict_transcription_parse_recovered` with the reported `sessionId`.
3. If parsing still fails, copy the escaped snippet from the logs for debugging and consider storing the raw text in the blob for that session (editing `raw_response.txt`).
4. Artifacts live under `https://blob.vercel-storage.com/triumphant-transcripts-back-blob/sessions/<sessionId>/` for manual inspection.

## Next Steps / Open Questions
- Monitor how often Gemini triggers the loose parser; if frequent, consider wrapping the response in a schema validator or requesting a fix from Google.
- Decide whether to persist raw malformed payloads for future training data.
- Keep the Vercel CLI updated (>=48.6.0) once convenient so the newer logging flags work without deprecation warnings.
