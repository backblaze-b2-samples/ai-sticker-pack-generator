<!-- last_verified: 2026-06-09 -->
# Feature: Pack Export

## Purpose
Build a ready-to-import bundle for a target platform (Telegram, WhatsApp, Discord, iMessage), store it in B2, and deliver it via a presigned URL.

## Used By
- UI: `/packs/[id]` page (per-platform export buttons)
- API: `POST /packs/{id}/export`

## Core Functions
- `apps/web/src/components/packs/pack-detail.tsx` — export buttons + download
- `apps/web/src/lib/queries.ts` — `useExportPack()`
- `services/api/app/runtime/packs.py` — `POST /packs/{id}/export` handler
- `services/api/app/service/packs.py` — `export_pack()`, `_build_export_zip()`, `_resize_png()`
- `services/api/app/repo/b2_client.py` — `get_object_bytes()` (read stickers), `put_bytes()` (cache ZIP), `get_presigned_url()`

## Canonical Files
- Export builder: `services/api/app/service/packs.py`

## Inputs
- pack_id: string (route param)
- platform: Platform (request body) — telegram | whatsapp | discord | imessage

## Outputs
- `POST /packs/{id}/export` → `ExportResult` (pack_id, platform, key, url, size_bytes, size_human, cached)
- Side effect: writes `sticker-packs/<id>/exports/<platform>.zip` to B2 (cached for reuse)

## Flow
- Read the manifest and check for a cached `exports/<platform>.zip`. If present, return its presigned URL with `cached=true`.
- Otherwise: read each sticker (`get_object`), resize with Pillow to the platform's target size (preserving transparency, centered on a transparent canvas), and zip per-platform folders plus an `IMPORT.md` how-to and the 1024² originals.
- Store the ZIP to B2 and return its presigned URL.

### Per-platform specs (one lightweight server-side builder — no platform SDK)
- `telegram/` — 512×512 WebP (transparent)
- `whatsapp/` — 512×512 WebP + a 96×96 `tray.webp` pack icon
- `discord/` — 128×128 PNG (emoji, kept small)
- `imessage/` — 408×408 PNG + a note (a built `.app` needs an Xcode Messages extension; we ship import-ready images)
- `originals/` — 1024×1024 transparent PNG

## Edge Cases
- Pack not found → 404
- A sticker object missing during assembly → logged and skipped; the rest of the ZIP still builds
- Re-export of the same platform → served from the cached ZIP (no rebuild)
- Storage failure → 500 with a generic message (details logged)

## UX States
- Idle: per-platform buttons
- Building: button shows "Building…" and other buttons disable
- Success: toast with bundle size; the browser opens the presigned download
- Error: toast with the failure detail

## Verification
- Test files: `services/api/tests/test_packs.py`
- Required cases: builds an uncached ZIP; reuses a cached ZIP without rebuilding
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green (repo layer mocked — no real B2 calls; Pillow runs on synthetic in-memory PNGs)

## Related Docs
- [Pack Library](sticker-packs.md)
- [Sticker Generation](sticker-generation.md)
- [RELIABILITY.md](../RELIABILITY.md)
