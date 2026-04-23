"""FastAPI server that wraps the hermes agent for internal API use.

Exposes two endpoints (see api_server.main):
  POST /v1/prompts/improve        — synchronous prompt rewriting
  POST /v1/content-strategy       — async content-strategy planning (returns job_id)
  GET  /v1/jobs/{job_id}          — poll a strategy job's status + result
  GET  /health                   — liveness + DB connectivity

Reads env vars:
  OPENROUTER_API_KEY              — LLM provider key (required)
  OPENROUTER_BASE_URL             — optional override (default openrouter.ai)
  HERMES_MODEL_DEFAULT            — default model slug (optional)
  HERMES_MODEL_IMPROVE            — model slug for /v1/prompts/improve (optional)
  HERMES_MODEL_STRATEGY           — model slug for /v1/content-strategy (optional)

  DB_HOST / DB_PORT / DB_DATABASE — shared RDS coordinates
  DB_RW_USERNAME / DB_RW_PASSWORD — writer credentials (this app's DB user)

The LLM-facing postgres-reader plugin reads its own (read-only) credentials
separately from DB_USERNAME/DB_PASSWORD or HERMES_PG_READER_URL.
"""
