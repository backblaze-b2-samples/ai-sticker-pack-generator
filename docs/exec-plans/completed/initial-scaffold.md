# Scaffold plan — `ai-sticker-pack-generator`

Forked from `vibe-coding-starter-kit`. Source of truth for the delta:
`.claude/scratch/vcsk-716cc5da-09fc-406a-acc5-72e8ffae052e/` (pristine clone).

---

## 1. Purpose

`ai-sticker-pack-generator` is a B2 sample app that generates **themed sticker /
emoji packs in a consistent visual style** from a single text prompt, stores
every sticker and pack archive in Backblaze B2, and exports
ready-to-import bundles for **iMessage, Telegram, WhatsApp, and Discord**.

It's aimed at vibe coders and AI-app builders evaluating B2 as the storage
layer for a *high-volume, accumulating* media workload: each pack is 12–30
images, packs pile up over time, and every artifact (individual stickers, the
pack manifest, and per-platform export ZIPs) lives in object storage with no
database. It's deliberately a **lightweight "first sample to try"** — one
external API key (OpenAI), one new capability (image generation), and the rest
is the starter kit's batteries-included B2 surface.

---

## 2. Architecture delta from `vibe-coding-starter-kit`

The starter is the ceiling. We keep the entire B2-backed scaffolding, **adapt**
the dashboard, and **add** the sticker-generation + export + library layer on
top. Almost nothing is trimmed — the starter is already minimal.

### KEEP (as-is — do not strip, rename internals, or restyle)
- **UI kit / design system**: `apps/web/src/components/ui/` (shadcn), design
  tokens in `globals.css`, the `/design` reference page. (Starter contract,
  AGENTS.md §2.)
- **Bucket explorer (full-bucket browse)** — `/files`, `apps/web/src/app/files/`,
  `apps/web/src/components/files/`. **NON-NEGOTIABLE KEEP.** Sidebar "Files"
  entry stays.
- **Upload** — `/upload`, `apps/web/src/app/upload/`, `components/upload/`,
  sidebar "Upload" entry. Both sibling samples keep it; it doubles here as the
  way to drop in your own reference images. Kept as-is.
- Sidebar nav shell, header, health-banner, command-palette, theme-provider.
- **Backend layering** (`types → config → repo → service → runtime`), structural
  tests, JSON logging, `/health`, `/metrics`, request-id middleware.
- Metadata extraction service (`service/metadata.py`) — still applies to the
  generic Upload path.
- Existing B2 repo methods (`upload_file`, `list_files`, `get_file_metadata`,
  `delete_file`, `get_presigned_url`, `get_upload_stats`, `check_connectivity`).

### ADD (new for the sticker app)
- **`/generate` page** — the creation form: theme prompt, style preset, pack
  size, target platforms. New sidebar "Generate" entry (Lucide `Wand2`/`Sparkles`).
- **`/packs` page = sample-specific asset explorer (scoped to `sticker-packs/`)** —
  **REQUIRED ADD.** Library grid of generated packs (cover sticker + theme +
  count). Sidebar "Packs" entry (Lucide `Sticker`). This is the scoped
  counterpart to the kept full-bucket `/files` explorer.
- **`/packs/[id]` page** — pack detail: sticker grid, per-sticker download,
  per-platform export buttons, delete pack.
- Backend `repo/image_client.py` — OpenAI image-generation adapter (SDK
  imported **lazily inside functions**, house style; keeps SDK out of module
  scope and out of non-repo layers).
- Backend `repo/b2_client.py` additions: `get_object_bytes(key)` (S3
  `get_object` — new op, used to read stickers back when assembling export
  ZIPs and to read `pack.json`), `put_bytes(key, data, content_type)` (thin
  raw-put for manifest + ZIP), `delete_prefix(prefix)` (S3 batch
  `delete_objects` — new op, used to delete a whole pack).
- Backend `service/stickers.py` — generation orchestration (build prompts →
  call image_client → store stickers + manifest to B2).
- Backend `service/packs.py` — list/get packs (read manifests), build + cache
  per-platform export ZIPs (Pillow resize → `zipfile` → B2 → presigned URL),
  delete pack.
- Backend `runtime/stickers.py` — routes (see §3).
- Backend `types/stickers.py` — Pydantic models (`StylePreset`,
  `GeneratePackRequest`, `Sticker`, `PackManifest`, `PackSummary`,
  `ExportRequest`, `ExportResult`).
- Frontend `components/packs/` + `components/generate/`, new query hooks in
  `lib/queries.ts`, new client fns in `lib/api-client.ts`, new shared types in
  `packages/shared/src/types.ts`.
- Dependency: `openai>=1.0` in `requirements.txt`. (Pillow already present —
  reused for resizing/WebP.)

### ADAPT
- **Dashboard `/`** — replace generic upload stats with sticker metrics: total
  packs, total stickers, stickers generated this week, storage used under
  `sticker-packs/`, recent-packs table, packs-per-day chart. New aggregations
  flow through `runtime → service → repo` and TanStack Query hooks (no bare
  `useEffect+fetch`). Add a prominent "New pack" CTA. Update
  `docs/features/dashboard.md` in the same change.

### TRIM (small)
- `docs/images/b2-starterkit-*.png` (starter screenshots) and their README
  references. **No new screenshots created** (skill constraint: stop & ask
  before binary assets) — README gets a "screenshots coming" placeholder; a
  later `/sample-screenshotter` run fills them in.
- `docs/exec-plans/completed/2026-02-*.md` (starter's own build history, not
  this app's). Reset `docs/exec-plans/tech-debt-tracker.md` to an empty
  tracker. Phase 5 drops our scaffold plan into `completed/initial-scaffold.md`.

---

## 3. B2 surface (S3-compatible only — no b2-native)

All operations go through the boto3 S3 client in `repo/b2_client.py`. No
b2-native API anywhere.

| S3 operation | Where | New? |
|---|---|---|
| `put_object` | store each sticker, `pack.json` manifest, export ZIPs | reused (`upload_file`) + thin `put_bytes` |
| `get_object` | read stickers to assemble export ZIPs; read `pack.json` | **NEW** (`get_object_bytes`) |
| `list_objects_v2` | list packs (`sticker-packs/` prefix), dashboard stats, scoped `/packs` explorer | reused (`list_files`, `get_upload_stats`) |
| `head_object` | sticker / object metadata | reused (`get_file_metadata`) |
| `delete_objects` (batch) | delete an entire pack | **NEW** (`delete_prefix`) |
| `delete_object` | single-object delete (Files page) | reused |
| `generate_presigned_url` | download stickers + export bundles | reused |
| `head_bucket` | `/health` connectivity | reused |

B2 layout (no database — B2 is the sole store, per starter ARCHITECTURE):
```
sticker-packs/<pack-id>/pack.json                 # manifest (source of truth)
sticker-packs/<pack-id>/stickers/01.png … NN.png  # transparent PNG, 1024²
sticker-packs/<pack-id>/exports/<platform>.zip    # built on demand, cached
```
Prefix convention matches siblings (lowercase, trailing slash:
`lora-training/`, `shows/` → **`sticker-packs/`**).

---

## 4. Key features (→ README list + `docs/features/*.md` stubs)

1. **Sticker pack generation** — one theme prompt + a style preset + pose/
   expression variations → N consistently-styled stickers. (`sticker-generation.md`)
2. **Consistent style** — a shared, detailed style-preset descriptor is
   prepended to every per-sticker prompt; subjects/poses vary, style stays
   fixed. No second model needed (built-in pose list, not LLM-expanded).
3. **Transparent, die-cut stickers** — generated transparent natively (see
   open-question resolution below). (`sticker-generation.md`)
4. **Pack library** — scoped `/packs` explorer over `sticker-packs/`, pack
   detail with per-sticker actions. (`sticker-packs.md`)
5. **Multi-platform export** — per-platform ZIP bundles (Telegram, WhatsApp,
   Discord, iMessage) built server-side with Pillow + `zipfile`, stored in B2,
   delivered via presigned URL. (`pack-export.md`)
6. **B2-backed, no database** — every artifact lives in object storage;
   accumulating high-volume media is the whole demo.

### External API provider (per `api-provider-selection.md`)
- **Provider:** OpenAI. *(Anthropic — first preference — has no image-generation
  model, so OpenAI is the next valid choice; it also natively supports
  transparent backgrounds and prompt-controlled style.)*
- **Model:** `gpt-image-1` — `size=1024x1024`, `background="transparent"`,
  `output_format="png"`, **`quality="low"` by default** (the cost-efficient tier;
  quality + size are the cost levers, surfaced in settings).
- **Env var:** `OPENAI_API_KEY` (separate from `B2_*`, placeholder in
  `.env.example`, documented in README, never committed).
- **Estimated cost, one full demo run:** default pack = **12 stickers @ `low`
  1024² ≈ ~$0.15** (~$0.011/img). At `medium` ≈ ~$0.50. **Well under the $1
  rule** with margin that covers estimate error. Guardrail: a 30-sticker pack at
  `medium`/`high` can exceed $1, so demo **defaults are capped at `low` quality
  and ≤16 stickers**; larger/higher is opt-in with an in-UI cost note.
- **Setup caveat (README):** `gpt-image-1` may require OpenAI **organization
  verification** on some accounts — documented as a setup gotcha.

---

## 5. Doc transforms

| Doc | Action |
|---|---|
| `README.md` | Rewrite for the sticker app: title, intro, features, quick start. **Keep** the B2 bucket/key setup section but rename env vars (§6) and add the `OPENAI_API_KEY` step + org-verification note. Remove starter-screenshot embeds → placeholder. |
| `AGENTS.md` | Keep invariants & layering verbatim. Update §2 (note new pages, dashboard still the "adapt" target), add pointers to new feature docs. |
| `ARCHITECTURE.md` | Add OpenAI image adapter to components/external services; add generate/export data flows; add `sticker-packs/` layout; keep layering rules. |
| `docs/features/dashboard.md` | Rewrite for sticker metrics. |
| `docs/features/file-upload.md`, `file-browser.md`, `metadata-extraction.md` | Keep (still accurate — Upload/Files kept). Light edits only if wording references "starter kit". |
| `docs/features/sticker-generation.md` | **NEW** (from `_template.md`). |
| `docs/features/sticker-packs.md` | **NEW** (scoped library). |
| `docs/features/pack-export.md` | **NEW**. |
| `docs/app-workflows.md` | Add "generate a pack" + "export to a platform" journeys. |
| `docs/SECURITY.md` | Add `OPENAI_API_KEY` handling (server-side only, never exposed to client). |
| `docs/RELIABILITY.md` | Add image-gen failure/partial-pack + export retry expectations. |
| `docs/design-system.md` | Keep as-is. |
| `docs/exec-plans/completed/2026-02-*.md` | Delete (starter history). Reset `tech-debt-tracker.md`. |
| `docs/images/*` | Remove starter PNGs. |

---

## 6. Rename table (`vibe-coding-starter-kit` → `ai-sticker-pack-generator`)

| Kind | From | To | Files |
|---|---|---|---|
| root pkg name | `vibe-coding-starter-kit` | `ai-sticker-pack-generator` | `package.json` |
| web pkg | `@vibe-coding-starter-kit/web` | `@ai-sticker-pack-generator/web` | `apps/web/package.json`, root scripts, `scripts/dev.sh`, README `test:e2e` |
| shared pkg | `@vibe-coding-starter-kit/shared` | `@ai-sticker-pack-generator/shared` | `packages/shared/package.json`, all TS imports (`queries.ts`, `api-client.ts`, others) |
| env: key id | `B2_KEY_ID` / `b2_key_id` | `B2_APPLICATION_KEY_ID` / `b2_application_key_id` | `.env.example`, `config/settings.py`, `main.py` (`REQUIRED_B2_SETTINGS`+placeholders), `repo/b2_client.py` (`aws_access_key_id=`), `scripts/doctor.mjs` (`REQUIRED_B2_VARS`+`PLACEHOLDERS`), README |
| env: region | *(absent)* | **add** `B2_REGION` / `b2_region`, passed `region_name=settings.b2_region or None` | same files as above + `b2_client.py` client init |
| user agent | `user_agent_extra="b2ai-oss-start"` | `b2ai-ai-sticker-pack-generator` | `repo/b2_client.py` |
| UTM content | `utm_content=b2ai-oss-start` | `utm_content=b2ai-ai-sticker-pack-generator` | README links, `app-sidebar.tsx` footer link, `doctor.mjs` app-keys link |
| API title | `"OSS Starter Kit API"` | `"AI Sticker Pack Generator API"` | `main.py` |
| sidebar/product name | `"OSS Starter Kit"` | `"Sticker Studio"` | `app-sidebar.tsx` header |

> **`user_agent_extra` / UTM value is provisional.** Standard #2 says this comes
> from the sub-issue's `user_agent_extra` field, which isn't in this invocation.
> `b2ai-ai-sticker-pack-generator` follows the mechanical `b2ai-<slug>` sibling
> pattern (note the `ai-` is part of the slug). If the sub-issue specifies a
> different tag, it overrides — flagged for confirmation.

---

## Open questions (resolved — redirect at approval if you disagree)

**Q1 — Which platforms for v1 export?** → **All four**, via one lightweight
mechanism. A single server-side ZIP builder (Pillow resize + `zipfile`, both
zero new heavy deps) emits per-platform folders sized to each target, plus an
`IMPORT.md` how-to inside the zip:
- `telegram/` — 512×512 WebP (transparent)
- `whatsapp/` — 512×512 WebP + 96×96 `tray.webp`
- `discord/` — 128×128 PNG (emoji, ≤256 KB each)
- `imessage/` — 408×408 PNG + note (iMessage packs need an Xcode Messages
  template; we provide import-ready images, not a built `.app`)
- `originals/` — 1024×1024 transparent PNG
This honors the concept's four platforms without any platform SDK. *(Alternative
if you want it even leaner: ship only Telegram+WhatsApp first-class.)*

**Q2 — Background removal: built-in step or sidecar?** → **Built-in via the
image model, no sidecar.** `gpt-image-1` generates transparent backgrounds
natively (`background="transparent"`), so stickers come out die-cut with zero
post-processing. Keeps the build lightweight; a `rembg`/sidecar step is
explicitly *not* added.

---

## Build / review notes for the subagents
- Respect all AGENTS.md invariants: no `boto3`/SDK imports outside `repo/`;
  no business logic in `runtime/`; Pydantic models at every boundary; files
  < 300 lines (split `service/stickers.py` / `service/packs.py` if needed).
- New endpoints touch the canonical three files: `runtime/<router>.py`,
  `lib/api-client.ts`, `lib/queries.ts`.
- Add backend unit tests for new services (mock the repo layer; **no real
  OpenAI or B2 calls in tests**). Structural tests must stay green.
- `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure` must pass.
- Do not push to any remote, create binary assets, or touch sibling samples.
