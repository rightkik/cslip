# CLAUDE.md — Instructions for Claude Code

This file is read automatically by Claude Code. Follow these rules for **every** task in this project.

## Project summary
A self-hosted personal/SMB receipt manager (a DIY clone of paypers.ai core features).
Users send receipt photos/PDFs to a LINE bot; Gemini Vision extracts the data; the data is saved to
Supabase, the original file is uploaded to Google Drive, and a row is appended to a Google Sheet.
Goal: maximize free-tier usage, target ~0 THB/month for single-user use.

## Tech stack (do NOT change without asking)
- Backend: FastAPI (Python 3.11+), async.
- AI OCR: Gemini 2.0 Flash via `google-genai` SDK. Keep the OCR layer behind an interface
  (`app/ocr/base.py`) so the provider can be swapped (e.g. to Claude) later.
- DB: Supabase (Postgres). Use the `supabase-py` client or direct asyncpg — prefer `supabase-py` for simplicity.
- Storage: Google Drive API + Google Sheets API via service account.
- Bot: LINE Messaging API (`line-bot-sdk` v3). Prefer **reply messages** (free, no quota). Push messages
  are allowed when justified (e.g. reply token expired before background OCR finishes, or async notification).
  Always note in code when push is used and why.
- Hosting target: **Render** (free tier, keeps running through a request — safe for BackgroundTasks).
  Railway no longer has a free tier. Avoid Cloud Run for this pattern (background tasks are killed after
  HTTP response). See deployment notes in SETUP.md.

## Hard rules
1. **DEV LOG (mandatory):** After completing any meaningful task (new feature, bug fix, config change,
   architectural decision), append an entry to `DEV_LOG.txt` in **English**. Follow the format in
   `docs/DEV_LOG_GUIDE.md`. Never skip this. The log is the single source of truth for "what happened and why".
2. **Secrets:** Never hardcode keys. Read everything from environment variables via `app/config.py`.
   Update `.env.example` whenever a new env var is introduced.
3. **Cost awareness:** This project runs on free tiers. Avoid LINE push/broadcast messages (they consume quota).
   Avoid unnecessary Gemini calls. Cache/short-circuit where reasonable.
4. **Provider abstraction:** All AI calls go through `app/ocr/base.py`. No direct Gemini calls scattered in handlers.
5. **Idempotency:** A LINE webhook may be redelivered. De-duplicate by `messageId` before processing.
6. **Signature validation:** Always verify the `x-line-signature` header on the webhook before processing.
7. **Async webhook:** Acknowledge the webhook fast (return 200), do heavy work (OCR, uploads) in the background.
   **Reply ordering (critical):** LINE reply token expires in **30 seconds**. Always reply to the user
   *before* Drive upload or Sheets sync. Correct order: download → OCR → insert pending → **reply** → Drive upload.
   Sheets sync happens only after user confirmation, never block reply on it.
8. **Output style:** Concise, copy-pasteable code. Minimal prose. No long explanations unless asked.
9. **Tests:** Add a basic test when adding a module that has logic worth testing (parsing, repository).

## Coding conventions
- Type hints everywhere. Pydantic models for structured data (the receipt schema lives in `app/ocr/base.py`).
- Keep functions small. One responsibility per module per the folder structure in README.md.
- Log errors with context (which messageId, which step) so DEV_LOG and runtime logs are useful.

## When unsure
- Check `docs/ARCHITECTURE.md` for the data model and flow.
- Check `docs/ROADMAP.md` for what phase we're in and what's in/out of scope.
- Ask before adding a new external dependency or a new paid service.

## Definition of done for a task
- [ ] Code works and follows the folder structure.
- [ ] Env vars (if any) added to `.env.example`.
- [ ] `DEV_LOG.txt` updated in English.
- [ ] Basic test added if the module has logic.
