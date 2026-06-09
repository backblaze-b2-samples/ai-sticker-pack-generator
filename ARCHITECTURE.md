<!-- last_verified: 2026-06-09 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Dashboard with sticker metrics, packs-per-day chart, recent packs
  - Generate page — sticker-pack creation form
  - Packs library (scoped to the `sticker-packs/` prefix) + pack detail
  - File upload with drag-and-drop, progress tracking (drop in reference images)
  - Full-bucket file browser with preview, download, delete
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - REST API for sticker generation, pack library, per-platform export
  - REST API for file upload, listing, deletion
  - B2 S3 integration via boto3
  - OpenAI `gpt-image-1` integration via the `repo/image_client.py` adapter
  - File metadata extraction (images, PDFs)
  - Health check endpoint with B2 connectivity verification
  - Structured JSON logging with request tracing
  - Prometheus-format metrics endpoint
- **packages/shared/** — TypeScript type definitions
  - Mirrors Pydantic models from the API
  - Consumed by `apps/web/` as workspace dependency

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client) — no business logic
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only allowed in `repo/` layer
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Each file stays under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (stickers, files, upload, stats)
    config/                Settings loaded from environment
    repo/                  B2 S3 client + OpenAI image_client (data access layer)
    service/               Business logic (stickers, packs, upload, files, metadata)
    runtime/               FastAPI route handlers
  tests/                   pytest tests (structural + integration + service units)
```

## Boundary Invariants

- **No external SDK leakage**: `boto3` is only imported in `app/repo/`. All other layers interact with B2 through the repo interface.
- **No raw dicts at boundaries**: All data crossing layer boundaries uses typed Pydantic models.
- **No mutable globals**: Configuration is read-only after init. No module-level mutable state shared between layers.
- **Validated inputs**: All HTTP inputs validated by FastAPI/Pydantic. All file keys validated against prefix allowlist.

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently`
  - Web: `localhost:3000`
  - API: `localhost:8000`
- **Railway** — two services from the same repo
  - See `infra/railway/README.md` for configuration

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API)
  - Every artifact (stickers, manifests, export ZIPs, generic uploads) stored in a single bucket
  - File listing and metadata via S3 `list_objects_v2` / `head_object`
  - Sticker reads/exports via `get_object`; whole-pack deletes via batched `delete_objects`
  - No application database — B2 is the sole data store; `pack.json` is the per-pack source of truth

### B2 layout

```
sticker-packs/<pack-id>/pack.json                 # manifest (source of truth)
sticker-packs/<pack-id>/stickers/01.png … NN.png  # transparent PNG, 1024²
sticker-packs/<pack-id>/exports/<platform>.zip    # built on demand, cached
uploads/<filename>                                 # generic Upload page output
```

The `/packs` library is scoped to the `sticker-packs/` prefix; the `/files`
explorer browses the entire bucket.

## External Services

- **Backblaze B2 S3 API** — object storage, retrieval, deletion, presigned URLs
- **OpenAI `gpt-image-1`** — image generation (transparent backgrounds, `quality` cost tier). Wrapped in `repo/image_client.py`; the SDK is imported lazily inside the function. `OPENAI_API_KEY` is server-side only and never sent to the browser.

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins
- **API -> B2** — authenticated via application keys, signature v4
- **API -> OpenAI** — `OPENAI_API_KEY` used server-side only; never exposed to the browser
- **Client -> B2** — presigned URLs for download (forced attachment)

## Data Flows

- **Generate**: Browser -> `POST /generate` -> service builds per-sticker prompts (fixed style descriptor + varied poses) -> repo `image_client` calls OpenAI per sticker -> repo writes each PNG + `pack.json` to B2 -> manifest returned
- **List packs**: Browser -> `GET /packs` -> service lists `sticker-packs/` -> reads each `pack.json` -> returns pack summaries
- **Pack detail**: Browser -> `GET /packs/{id}` -> service reads `pack.json` -> returns manifest; stickers render via per-sticker presigned URLs (`POST /packs/{id}/sticker-url`)
- **Export**: Browser -> `POST /packs/{id}/export` -> service reads stickers (`get_object`), resizes with Pillow, zips per platform, caches the ZIP to B2 -> returns presigned URL
- **Delete pack**: Browser -> `DELETE /packs/{id}` -> service batches `delete_objects` over the pack prefix
- **Upload**: Browser -> `POST /upload` (multipart) -> API validates -> service orchestrates -> repo writes to B2 -> metadata extracted -> response
- **List**: Browser -> `GET /files` -> service calls repo -> returns file list
- **Download**: Browser -> `GET /files/{key}/download` -> service validates key -> repo generates presigned URL -> browser downloads
- **Delete**: Browser -> `DELETE /files/{key}` -> service validates key -> repo deletes from B2

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (logs duration per request)
- `/metrics` endpoint (Prometheus format: request count, latency, upload count)
- `/health` endpoint (B2 connectivity check)

## Canonical Files

- Layered API handler: `services/api/app/runtime/stickers.py`, `runtime/packs.py`, `runtime/upload.py`
- Service orchestration: `services/api/app/service/stickers.py`, `service/packs.py`, `service/upload.py`
- B2 data access (repo layer): `services/api/app/repo/b2_client.py`
- OpenAI adapter (repo layer): `services/api/app/repo/image_client.py`
- Pydantic models: `services/api/app/types/` (`stickers.py`, `files.py`, `upload.py`, `stats.py`, `formatting.py`)
- Config (pydantic-settings): `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`
- Frontend API client: `apps/web/src/lib/api-client.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [Sticker Generation](docs/features/sticker-generation.md)
- [Pack Library](docs/features/sticker-packs.md)
- [Pack Export](docs/features/pack-export.md)
- [Dashboard](docs/features/dashboard.md)
- [File Upload](docs/features/file-upload.md)
- [File Browser](docs/features/file-browser.md)
- [Metadata Extraction](docs/features/metadata-extraction.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
