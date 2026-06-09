<!-- last_verified: 2026-06-09 -->
# Feature: Dashboard

## Purpose
Provide an at-a-glance overview of sticker-pack activity and B2 storage usage scoped to the `sticker-packs/` prefix.

## Used By
- UI: `/` page (dashboard home)
- API: `GET /packs/stats`, `GET /packs/stats/activity`, `GET /packs`

## Core Functions
- `apps/web/src/components/dashboard/stats-cards.tsx` — 4 stat cards (total packs, total stickers, generated this week, pack storage)
- `apps/web/src/components/dashboard/pack-chart.tsx` — bar chart of packs created per day
- `apps/web/src/components/dashboard/recent-packs-table.tsx` — last 10 packs
- `apps/web/src/lib/queries.ts` — `usePackStats()`, `usePackActivity()`, `usePacks()`
- `services/api/app/runtime/packs.py` — `GET /packs/stats`, `GET /packs/stats/activity`
- `services/api/app/service/packs.py` — `get_pack_stats()`, `get_pack_activity()`
- `services/api/app/repo/b2_client.py` — `list_files()` (scoped to `sticker-packs/`)

## Canonical Files
- Dashboard page layout: `apps/web/src/app/page.tsx`
- Stats service logic: `services/api/app/service/packs.py`

## Inputs
- None (dashboard loads data automatically)

## Outputs
- `GET /packs/stats` → `PackStats` (total_packs, total_stickers, stickers_this_week, storage_bytes, storage_human)
- `GET /packs/stats/activity?days=7` → `DailyPackCount[]` for the chart (server-side aggregation by manifest date)
- `GET /packs` → `PackSummary[]` for the recent-packs table (sorted newest-first)

## Flow
- Page loads → parallel API calls (pack stats, pack activity, pack list)
- Stats cards display total packs, total stickers, stickers generated this week, storage used under `sticker-packs/`
- Pack chart displays server-aggregated daily pack-creation counts for the last 7 days
- Recent packs table shows the last 10 packs with theme, style, sticker count, and date; rows link to pack detail
- A prominent "New pack" CTA links to `/generate`

## Edge Cases
- API unavailable → inline error state with retry (cards/table don't render misleading zeros)
- No packs yet → empty chart message, empty table message with a "Generate a pack" prompt
- Large object count → stats endpoint reads via `list_objects_v2` over the `sticker-packs/` prefix

## UX States
- Loading: skeleton placeholders for cards, chart, and table
- Empty: "No packs yet" messages
- Loaded: populated cards, chart, table

## Verification
- Test files: `services/api/tests/test_packs.py`
- Required cases: stats counting (packs vs stickers), empty bucket, library read
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
- [Sticker Generation](sticker-generation.md)
- [Pack Library](sticker-packs.md)
