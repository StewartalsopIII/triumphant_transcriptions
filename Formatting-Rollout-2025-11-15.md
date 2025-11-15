# Formatting + Results Screen Rollout — 2025-11-15

## Scope
- `backend/api/services/transcription.py`: tightened the strict transcript prompt so Gemini groups sentences into short paragraphs with double newlines and no headings/bullets.
- `app-expo/audio-recorder/screens/ResultsScreen.js`: normalizes paragraph spacing on-device and preserves the dark theme layout.

## Motivation
1. Strict transcripts were returning long wall-of-text blocks that were hard to read on mobile.  
2. The Expo UI rendered those strings with single-line spacing, so even well-formatted text looked cramped.  
3. Screenshot QA surfaced the issue and we needed a quick fix before testing via the production Expo build.

## Local Verification
1. `cd backend && source venv/bin/activate`
2. `export GEMINI_API_KEY="<key>"` (or `source backend.env` with `set -a`)
3. `uvicorn api.index:app --reload --port 8000`
4. In another terminal: `curl -F "audio=@/path/to/sample.m4a" http://127.0.0.1:8000/api/transcribe` and inspect `originalStrict`.
5. `cd app-expo/audio-recorder && npx expo start` → open Results screen and confirm multi-paragraph rendering.

## Deployment Plan
1. `git add backend/api/services/transcription.py app-expo/audio-recorder/screens/ResultsScreen.js Formatting-Rollout-2025-11-15.md`
2. `git commit -m "Improve strict transcript formatting + ResultsScreen spacing"`
3. `git push origin main`
4. Vercel auto-builds the backend; Expo OTA picks up the JS change (no native rebuild needed).

## Rollback Plan
1. `git revert <commit-sha>` locally if issues appear; push the revert to `main`.
2. In Vercel dashboard, redeploy the previous build if the new one misbehaves.
3. Expo clients will automatically re-fetch the prior JS bundle after the revert.

## Outstanding Follow-ups
- Decide how strictly to constrain the custom prompt transformation output (length, structure, etc.).  
- Gather user feedback on readability once the new formatting is in prod.

