# Sustained Use Transcription Reliability Roadmap

## Goal
Ensure every recording and Gemini response is captured end-to-end so truncated transcripts can be diagnosed and prevented.

## Phase 1 – Instrument Current Pipeline
- **Add request/response logging**: Write raw Gemini payloads (audio metadata, prompts, and JSON responses) to secure blob storage with per-session IDs.
- **Persist app events**: Log recorder start/stop timestamps and audio file sizes from the Expo client to verify capture completeness.
- **Centralize log access**: Decide on storage (S3, Supabase, or Vercel Log Drain) and retention window; document access process.
- **Success criteria**: For any session ID we can retrieve the exact audio file, strict/light outputs, and Gemini raw response.

## Phase 2 – Storage & Retrieval Enhancements
- **Recording archive**: Upload original audio to durable storage (e.g., S3 + lifecycle policy) when the backend receives it; save storage URL in DB.
- **Transcription snapshots**: Save strict and light text variants in the database along with timestamps and prompt versions.
- **Dashboard tooling**: Build an internal view to search sessions, download audio, and inspect Gemini responses.
- **Success criteria**: Given a timestamp, ops can load the session in <2 minutes and compare all variants.

## Phase 3 – Prompt & Model Hardening
- **Strict prompt guardrails**: Add completion checks (e.g., require JSON fields to end with terminal punctuation) and fallbacks when Gemini stops early.
- **Light-edit behavior**: Adjust instructions so incomplete sentences are surfaced as warnings rather than padded with ellipses.
- **Automated regression tests**: Add fixtures that simulate long-form audio and verify prompt changes don’t regress accuracy.
- **Success criteria**: No truncation without an alert; light edit output matches validation rules.

## Phase 4 – Monitoring & Alerting
- **Timeout detection**: Emit metrics for Gemini request duration and failures; set alerts for spikes in truncation flags.
- **Client analytics**: Track network failures and premature recording stops in the app (anonymous telemetry).
- **Incident runbook**: Document triage steps, including how to pull logs, replay audio, and file bug reports.
- **Success criteria**: Team receives actionable alerts within 5 minutes of an incident.

## Phase 5 – Backlog / Stretch Goals
- **Offline fallback transcription** using Whisper for redundancy.
- **User-facing health status** within the app to notify when a recording didn’t process fully.
- **Anonymized dataset** for evaluating prompt tweaks on real conversations.

## Immediate Next Actions
1. Choose logging destination and configure minimal payload capture (Phase 1 kickoff).
2. Define session identifier schema shared between client and backend.
3. Schedule prompt review meeting once logging is in place.

Owners and timelines can be added once the team confirms resources.
