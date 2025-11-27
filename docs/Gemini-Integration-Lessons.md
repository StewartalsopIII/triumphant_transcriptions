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

## 6. Grounding Preflight

**Symptom:** Downstream prompts needed a way to ground unknown proper nouns without adding yet another Gemini transcription pass.

**Cause:** The original stack (google-generativeai 0.3.2) had no `google_search` tool support, so preflight research required a separate service.

**Resolution:** Upgraded to `google-generativeai==0.7.2`, added a single preflight helper that calls Gemini with the Google Search tool, and surfaced `ENABLE_GROUNDING` / `GROUNDING_MAX_TERMS` env toggles. The helper prepends background context to the strict prompt (and continuation prompt) and returns `groundingMetadata` so failures are observable while the transcription call count stays the same.

## 7. Grounding Doom Loop Retro (2025-11-27)

**Context.** In pursuit of automatic grounding we:
- Upgraded the SDK to `google-generativeai==0.7.2` and added feature flags/limits in `api/config.py`.
- Built `api/services/search_grounding.py` to extract `‹??term??›` markers, call Gemini with the `google_search` tool, and prepend the returned narrative to every transcription/transform prompt.
- Threaded optional `groundingText` through `/api/transcribe`, enabled per-request search inside `/api/transform`, and exposed `groundingMetadata` so the client could see what evidence was injected.
- Added `test_grounding_flow.py` to simulate the new control flow.

**Candidate doom-loop triggers (ranked).**
1. **Lack of upstream markers.** Nothing in the Expo client or backend currently inserts `‹??term??›` markers, yet the new flow only runs when those markers exist. That mismatch tempts repeated refactors (“why isn’t grounding triggering?”) and leads to yanking the feature on/off without observable results.
2. **Unbounded preflight latency.** Every transcription and transform call can now fire an additional Gemini request plus Google Search, multiplying cost and timeout risk. When a request runs long, Expo retries, which in turn repeats the grounding search—classic doom loop.
3. **Prompt bloat/regressions.** Injecting background paragraphs into both the strict prompt and continuation prompt enlarges every request. Longer prompts increase truncation risk, which then triggers continuation logic, compounding latency and frustration.
4. **SDK churn.** The jump from `google-generativeai==0.3.2` to `0.7.2` happened mid-integration. Any subtle API shift (e.g., new auth scopes for tools) can break existing flows, causing us to keep debugging the wrong layer.
5. **No caching or circuit breaker.** We neither cache search results nor short-circuit when terms repeat. Replaying the same transcript quickly re-issues identical searches, making failures feel systemic.
6. **UI/backend drift.** The backend now expects `groundingText`, but the Expo recorder never sends it. Product keeps toggling the env flag, sees no change, and repeats the cycle.
7. **Sparse validation.** `test_grounding_flow.py` only mocks the happy path; we lack tests around timeouts, malformed JSON, or missing citations. Each new failure forces another round of guesswork.

**Most likely culprits.**
- *Upstream marker gap (#1):* Until we actually emit `‹??…??›` markers (or auto-detect proper nouns), grounding stays inert. Engineers keep “fixing” backend code even though the trigger condition never fires.
- *Latency amplification (#2):* When grounding finally engages, it adds another LLM invocation that can exceed Vercel’s time budget. Retries from Expo or users pressing “Transform” again spawn even more preflights, making the system feel stuck.

**Attempted implementation snapshot.**

```83:126:backend/api/services/search_grounding.py
async def run_grounding_preflight(terms: Sequence[str], *, session_id: Optional[str] = None) -> GroundingResult:
    if not terms:
        ...
    prompt = _build_preflight_prompt(terms)
    model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    kwargs = _build_generate_kwargs(model)
    response = await asyncio.to_thread(model.generate_content, [{"text": prompt}], **kwargs)
    return _parse_grounding_response(response, default_terms=list(terms))
```

```141:188:backend/api/services/transcription.py
grounding_terms = extract_grounding_terms(grounding_text, GROUNDING_MAX_TERMS)
if ENABLE_GROUNDING:
    grounding_result = await run_grounding_preflight(grounding_terms, session_id=session_id)
    prompt_for_request = inject_background_context(PROMPT, grounding_result.context_text)
...
continuation_prompt = inject_background_context(continue_prompt, grounding_result.context_text)
result["groundingMetadata"] = grounding_metadata
```

Together these snippets show how the preflight context is gathered, spliced into both the initial and continuation prompts, and bubbled back to the client—useful artifacts even though the first rollout landed us in the loop described above.

## Takeaways

- Cross-check SDK docs against the actual installed version; generated docs may reference APIs that were removed.
- When integrating third-party APIs in serverless environments, add verbose logging around each external call and capture logs while reproducing requests.
- Automate or script client-side environment updates to match backend deploys, especially when using ephemeral URLs.
- Expect LLM responses to deviate from requested formats; always sanitize and validate before parsing.

These lessons cost time during Milestone 5, but they provide a solid foundation for future enhancements (e.g., streaming partial transcripts or swapping models).
