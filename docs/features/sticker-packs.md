<!-- last_verified: 2026-06-09 -->
# Feature: Pack Library

## Purpose
Browse generated packs (scoped to the `sticker-packs/` B2 prefix) and drill into a pack to view its stickers, download them, export bundles, or delete the pack. This is the sample-specific, scoped counterpart to the full-bucket `/files` explorer.

## Used By
- UI: `/packs` (library grid), `/packs/[id]` (pack detail)
- API: `GET /packs`, `GET /packs/{id}`, `POST /packs/{id}/sticker-url`, `DELETE /packs/{id}`

## Core Functions
- `apps/web/src/components/packs/pack-library.tsx` — library grid (cover sticker + theme + count)
- `apps/web/src/components/packs/pack-detail.tsx` — sticker grid, per-sticker download, export buttons, delete
- `apps/web/src/components/packs/sticker-image.tsx` — renders a sticker via its presigned URL with a transparency checkerboard
- `apps/web/src/lib/queries.ts` — `usePacks()`, `usePack()`, `useStickerUrl()`, `useDeletePack()`
- `services/api/app/runtime/packs.py` — pack routes
- `services/api/app/service/packs.py` — `list_packs()`, `get_pack()`, `get_sticker_url()`, `delete_pack()`
- `services/api/app/repo/b2_client.py` — `list_files()`, `get_object_bytes()`, `get_presigned_url()`, `delete_prefix()`

## Canonical Files
- Library logic: `services/api/app/service/packs.py`
- Library grid: `apps/web/src/components/packs/pack-library.tsx`

## Inputs
- pack_id: string (route param, for detail/delete)
- key: string (sticker object key, for `sticker-url`)

## Outputs
- `GET /packs` → `PackSummary[]` (read from each `pack.json` under the prefix), newest-first
- `GET /packs/{id}` → `PackManifest`
- `POST /packs/{id}/sticker-url` → `{ url }` (presigned, validated against the manifest's sticker keys)
- `DELETE /packs/{id}` → `{ deleted, pack_id, objects }` (batched `delete_objects` over the pack prefix)

## Flow
- Library: list `sticker-packs/`, read each `pack.json`, build summaries; the cover is the first sticker.
- Detail: read `pack.json`; render the sticker grid; each sticker resolves a short-lived presigned URL on demand.
- Delete: verify the manifest exists (clean 404 if not), then batch-delete every object under `sticker-packs/<id>/`.

## Edge Cases
- Pack not found → 404
- `sticker-url` requested for a key not in the manifest → 404 (prevents arbitrary-key presigning)
- Empty library → empty state with a "Generate a pack" CTA
- Sticker object missing during render → image falls back to a placeholder icon

## UX States
- Loading: skeleton grid
- Empty: "No packs yet"
- Error: inline error state with retry
- Loaded: grid / detail with hover download buttons

## Verification
- Test files: `services/api/tests/test_packs.py`
- Required cases: list reads manifests; missing pack raises; delete returns object count; stats counting
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green (repo layer mocked — no real B2 calls)

## Related Docs
- [Sticker Generation](sticker-generation.md)
- [Pack Export](pack-export.md)
- [File Browser](file-browser.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
