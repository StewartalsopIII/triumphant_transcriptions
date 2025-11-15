# Gemini Integration Lessons Learned

Integrating Google Gemini into the Triumphant Transcripts backend exposed a number of pitfalls. This document captures the key challenges, the root causes, and the final solutions so future iterations proceed smoothly.

## 1. Missing Upload API (`upload_file`)

**Symptom:** Runtime errors reported `module 'google.generativeai' has no attribute 'upload_file'`.

**Cause:** The `google-generativeai==0.3.2` client (the version recommended by the docs we followed) does not expose `upload_file`. Earlier blog posts and examples referenced an API that existed in older or experimental builds but was removed from the current package.

**Resolution:** Skip the upload helper entirely and send the audio bytes inline when calling `GenerativeModel.generate_content`. Gemini accepts a structured payload containing `{"inline_data": {"mime_type": ..., "data": ...}}` followed by the prompt.

## 2. Vercel Runtime Constraints

**Symptom:** Requests returned `FUNCTION_INVOCATION_FAILED` with minimal diagnostics, and repeated log tails showed no additional detail.

**Cause:** The combination of missing API methods and the scoring step failing inside Gemini caused the runtime errors, but Vercel’s serverless functions also have timeouts and limited log buffers, making it difficult to capture the exact stack trace.

**Resolution:** Instrumented detailed logging on the backend (start/end markers, payload metadata). Triggered the endpoint manually via `curl` while a log tail streamed to capture the first failing entry. Once the upload approach was fixed, the runtime stabilized.

## 3. Mirroring Deploy URLs in Expo

**Symptom:** Expo continued to call stale deployment URLs, producing 404s or hitting older endpoints.

**Cause:** Every successful `vercel --prod` issues a new hostname. Forgetting to update `.env` meant the client never reached the latest code.

**Resolution:** After each deploy, immediately update `app-expo/audio-recorder/.env` with the new URL and restart Expo so the change takes effect.

## 4. Gemini Response Format

**Symptom:** When Gemini finally returned a response, it occasionally wrapped payloads in Markdown code fences.

**Cause:** Gemini models sometimes format JSON in triple backtick blocks even when instructed otherwise.

**Resolution:** Strip optional Markdown fences and `json` language tags before parsing. Keep robust error handling (`json.JSONDecodeError`) to surface malformed responses.

## 5. Environment Configuration

**Symptom:** The backend failed to boot locally once we enforced the Gemini key requirement.

**Cause:** Raising an exception during module import ensures secrets are present, but it also breaks local development if `.env` isn’t sourced before running the app.

**Resolution:** Updated the README and `.env.example` with explicit instructions to set `GEMINI_API_KEY` / `GEMINI_MODEL_NAME` before launching the server. Vercel environment variables must be added via `vercel env add` so deployment machines receive them.

## Takeaways

- Cross-check SDK docs against the actual installed version; generated docs may reference APIs that were removed.
- When integrating third-party APIs in serverless environments, add verbose logging around each external call and capture logs while reproducing requests.
- Automate or script client-side environment updates to match backend deploys, especially when using ephemeral URLs.
- Expect LLM responses to deviate from requested formats; always sanitize and validate before parsing.

These lessons cost time during Milestone 5, but they provide a solid foundation for future enhancements (e.g., streaming partial transcripts or swapping models).
