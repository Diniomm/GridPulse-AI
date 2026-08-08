# Next Product Phases

These phases extend the current product while keeping the existing demo mode available as a reliable fallback.

## Phase 9: Custom incident intake

Add a form for entering an incident title, description, asset, location, severity, and optional field files. Validate the values before starting an investigation.

**Exit gate:** A user can create and investigate a custom incident without changing source code, while the two existing demo incidents still work.

## Phase 10: Local audio transcription

Replace the synthetic audio note with optional local Whisper transcription. Install `pip install -e ".[audio]"` and set `GRIDPULSE_USE_LOCAL_WHISPER=true` to enable it. If the model or required hardware is unavailable, retain the current clearly labeled fallback.

**Exit gate:** A supported audio file produces a transcript locally, and provider failures do not break the investigation.

## Phase 11: Local image analysis

Add an optional local image model for field-photo observations. Keep the provider behind the existing interface and retain a deterministic fallback for lightweight deployments.

**Exit gate:** A supported image produces a labeled observation locally, with model failures recorded safely.

## Phase 12: Persistent local data

Store incidents, investigation reports, review decisions, and reviewer comments in SQLite. Add a history view and migration-safe schema initialization.

**Exit gate:** Reports remain available after an application restart, with clear documentation for hosted storage limitations.
