<!-- last_verified: 2026-06-09 -->
# Reliability

Reliability expectations and practices for this project.

## Health Checks

- `GET /health` verifies B2 connectivity and returns `healthy` or `degraded`
- Health endpoint is always available, even when B2 is down

## Error Handling

- HTTP handlers return structured error responses with appropriate status codes
- External service failures (B2) are caught and surfaced as 500/503 responses
- No unhandled exceptions leak stack traces to clients

## Logging

- Structured JSON logging via Python stdlib
- Every request gets a `request_id` for tracing
- Log levels: ERROR for failures, WARNING for degraded state, INFO for requests

## Observability

- Request timing middleware logs duration for every request
- `/metrics` endpoint exposes basic Prometheus-format counters
- Upload success/failure counts tracked

## Graceful Degradation

- File listing returns empty list (not error) when B2 has no objects
- Metadata extraction failures don't block upload (return partial metadata)
- Frontend shows skeleton states while loading, error states on failure

## Sticker Generation

- **Misconfiguration fails fast.** A missing `OPENAI_API_KEY` causes the first sticker to raise `ImageGenerationError`; the whole request aborts with a clear message before any partial pack is stored.
- **Partial packs are tolerated.** If a later sticker fails (transient model/API error), it is logged and skipped; the pack is stored with the stickers that succeeded and the manifest reflects the real count. The library never shows a pack with a missing `pack.json`, because the manifest is written last.
- **No retries inside a run.** A failed sticker is not auto-retried; re-running Generate produces a fresh pack. This keeps cost predictable and the flow simple.

## Pack Export

- **Exports are cached and idempotent.** A built `exports/<platform>.zip` is reused on subsequent requests for the same platform, so re-export is cheap and safe to retry.
- **Missing stickers don't break a bundle.** If an individual sticker object can't be read during assembly, it is logged and skipped; the rest of the ZIP still builds.
- Export build failures surface as a 500 with a generic message; details are logged server-side.

## Deployment

- Railway health checks on `/health`
- Zero-downtime deploys via rolling updates
- Environment-specific configuration via env vars (no config files in prod)
