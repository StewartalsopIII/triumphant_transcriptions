# Unexpected Issues & Improved Prompts

A reference for the bumps we hit while delivering the Triumphant Transcripts milestones, plus suggested prompt revisions for future runs.

## Milestone 1 – Project Scaffolding
- **Issue:** None beyond baseline setup.
- **Better Prompting:** Current directions were already explicit; no changes needed.

## Milestone 2 – File Upload Endpoint
- **Issue:** None beyond expected implementation.
- **Better Prompting:** Consider adding an optional verification step (e.g., request for `curl` command) to ensure the endpoint returns JSON before moving on.

## Milestone 3 – Expo Audio Recorder
- **Issue:** Expo environment URLs changed with each backend deploy, causing manual updates and confusion.
- **Better Prompting:** Add a bullet instructing, “Provision a stable backend alias (e.g., using `vercel alias`) and update `.env` accordingly.”

## Milestone 4 – Fake Transcription Response
- **Issue:** No major blockers.
- **Better Prompting:** Highlight that Expo should reset cached results when starting a new recording to avoid stale UI states.

## Milestone 5 – Real Gemini Transcription
- **Issue:** `google-generativeai` no longer exposes `upload_file`; runtime crashed with `AttributeError` and later with generic `FUNCTION_INVOCATION_FAILED` messages.
  - **Root Cause:** Following outdated docs; Gemini v0.3.2 requires inline `inline_data` parts instead of file uploads.
  - **Better Prompting:** Explicitly state which SDK version to use and provide the inline request structure in the prompt.
- **Issue:** Expo app remained tied to short-lived Vercel URLs.
  - **Better Prompting:** Instruct to configure a permanent alias before integrating the mobile client.
- **Issue:** Streaming Vercel logs timed out.
  - **Better Prompting:** Ask for direct `vercel logs <deployment>` output snippets so diagnosing doesn’t rely on long-running tails.

## Milestone 6 – Transform Screen & Hosting
- **Issue:** Expo Go stopped working after laptop shutdown because the app only ran on the local dev server.
  - **Better Prompting:** Add a final milestone directive to publish via EAS Update (or clarify the goal is hosted, not just dev mode).
- **Issue:** EAS CLI required multiple manual configuration tweaks (project ID, owner, updates URL) because of dynamic `app.config.js`.
  - **Better Prompting:** Include the exact config keys (`extra.eas.projectId`, `owner`, `runtimeVersion`, `updates.url`) in the milestone instructions.
- **Issue:** `expo publish` deprecated; had to switch to `eas update`.
  - **Better Prompting:** Reference `npx eas update` directly instead of `expo publish`.

## General Lessons
- Stable environment URLs prevent cascading updates in the mobile app.
- When using dynamic Expo configs, prompts should list every required key so the CLI can run non-interactively.
- For third-party SDK integrations, provide the specific API surface/structure to avoid chasing breaking changes.
