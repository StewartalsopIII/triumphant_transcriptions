# Custom Prompt Soft-Constraint Implementation Plan

Last updated: 2025-11-15

## 1. Goal
Introduce a “soft constraint” wrapper for custom prompt transformations so Gemini naturally returns concise, single-paragraph responses without blocking users when they go off-script.

## 2. Planned Changes (by directory)

### `backend/`
- **`api/index.py`**
  - Add a helper to build the soft-constraint template around the user instruction.
  - Normalize Gemini output (trim whitespace, collapse double spaces).
  - Optionally compute simple diagnostics (word count, list detection) and return them in the JSON payload (`violations` array).
- **`api/services` (optional)**
  - If logic grows, move template helpers or validators into a dedicated module for future reuse.

### `app-expo/audio-recorder/`
- **`services/api.js`**
  - Update the transform response type to forward any metadata such as `violations`.
- **`screens/TransformScreen.js`**
  - Display subtle warnings (e.g., yellow banner) whenever the backend flags a soft violation.
  - Show the current word count so users understand why the warning appeared.
  - Cache violation metadata alongside the transformed text so revisits show the same context.

### `docs/`
- Reference this plan plus future retro notes so anyone can trace why the constraint exists.

## 3. Implementation Steps
1. **Template helper**
   - Define a constant describing the rules (“≤120 words, single paragraph, no bullets”) and embed the user prompt + transcript inside it.
2. **Backend response shaping**
   - After Gemini responds, trim whitespace and calculate diagnostics (word count, presence of list markers, paragraph breaks).
   - Return `{"text": "...", "violations": ["word_count_exceeded"]}` when rules are broken.
3. **Expo client updates**
   - Extend the API client to accept the new JSON structure.
   - In `TransformScreen`, surface warnings (text + icon) and show word counts.
4. **Manual testing**
   - Run backend locally with `uvicorn`.
   - Use Expo Go or web preview to submit custom prompts; confirm warnings appear when exceeding limits.
5. **Deployment**
   - Commit changes, push to GitHub (triggers Vercel).
   - Run `npx eas update --branch production --message "Custom prompt soft constraints"` to ship the new client bundle.

## 4. Documentation Strategy
- **Create a `docs/` index (`docs/README.md`)**  
  Outline categories (Architecture, Operational Runbooks, Change Plans, Retrospectives) and link to each Markdown file.
- **Adopt naming convention**  
  `YYYY-MM-DD-topic.md` for dated plans/retros, and `guide-topic.md` for evergreen docs.
- **Reference from PRs**  
  When opening a PR or commit, mention the relevant doc so history shows how implementation decisions evolved.
- **Periodic cleanup**  
  Once a plan is fully executed, summarize learnings in a “retro” section and archive older step-by-step instructions if they’re no longer accurate.

Following this structure keeps every change tied to a document and gives newcomers a roadmap of how the project has evolved.

