<!-- last_verified: 2026-06-09 -->
# Feature: Sticker Generation

## Purpose
Turn one theme prompt + a style preset into N consistently-styled, transparent (die-cut) stickers, stored in B2 with a manifest.

## Used By
- UI: `/generate` page
- API: `POST /generate`

## Core Functions
- `apps/web/src/components/generate/generate-form.tsx` — creation form (theme, style, pack size, quality)
- `apps/web/src/lib/queries.ts` — `useGeneratePack()`
- `services/api/app/runtime/stickers.py` — `POST /generate` handler
- `services/api/app/service/stickers.py` — `generate_pack()` orchestration, prompt building, pose list
- `services/api/app/repo/image_client.py` — `generate_sticker_image()` (OpenAI `gpt-image-1`, SDK imported lazily)
- `services/api/app/repo/b2_client.py` — `put_bytes()` (store each PNG + `pack.json`)

## Canonical Files
- Generation orchestration: `services/api/app/service/stickers.py`
- OpenAI adapter: `services/api/app/repo/image_client.py`

## Inputs
- theme: string (form) — 2–200 chars
- style: StylePreset (form) — one of kawaii, pixel-art, flat-vector, watercolor, retro-cartoon, 3d-clay
- pack_size: int (form) — 1–30, default 12
- quality: Quality (form) — low | medium | high, default low

## Outputs
- `POST /generate` → `PackManifest` (pack_id, theme, style, quality, created_at, sticker_count, stickers[])
- Side effects: writes `sticker-packs/<id>/stickers/NN.png` per sticker and `sticker-packs/<id>/pack.json` to B2

## Flow
- Build a per-sticker prompt: a fixed, detailed **style descriptor** for the chosen preset is prepended to every prompt; the subject (theme) stays fixed; the **pose/expression** is varied from a built-in list (not LLM-expanded). This keeps the whole pack in one coherent style with no second model.
- For each sticker: call the image_client adapter → OpenAI `gpt-image-1` with `size=1024x1024`, `background="transparent"`, `output_format="png"`, and the requested `quality`.
- Store each transparent PNG to B2 via `put_bytes`.
- Write the `pack.json` manifest last (the source of truth) so a pack only appears in the library once complete.

## Edge Cases
- `OPENAI_API_KEY` missing → first sticker raises `ImageGenerationError`; the request aborts with a clear message (no empty pack stored).
- A later sticker fails → logged and skipped; a partial pack is stored with the stickers that succeeded (manifest reflects the real count). See [RELIABILITY.md](../RELIABILITY.md).
- `gpt-image-1` org-verification error → surfaced as an authorization error; verify your OpenAI org (see README setup gotcha).
- Cost guardrail: defaults cap at `low` quality and a 16-sticker safe size; larger/higher is opt-in with an in-UI cost note.

## UX States
- Empty: form ready
- Loading: full-card generating loader ("Generating your pack…")
- Error: toast with the failure detail; form preserved
- Success: toast + redirect to the new pack's detail page

## Verification
- Test files: `services/api/tests/test_stickers.py`
- Required cases: stores stickers + manifest under the scoped prefix; prompts share style and vary pose; aborts on first failure; tolerates partial failure
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green (the OpenAI + B2 repo layer is mocked — no real API calls)

## Related Docs
- [Pack Library](sticker-packs.md)
- [Pack Export](pack-export.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
