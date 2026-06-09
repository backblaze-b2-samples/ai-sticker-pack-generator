<!-- last_verified: 2026-06-09 -->
# App Workflows

User journeys inside the application.

## Generate a Sticker Pack

- User navigates to `/generate`
- Enters a theme prompt (e.g. "a grumpy orange cat"), picks a style preset, a pack size, and a quality tier
- A cost note appears if the choices exceed the demo's safe defaults (>16 stickers or above Low quality)
- On submit: a generating loader shows while the backend creates each sticker and stores it in B2
- On success: a toast confirms, and the app redirects to the new pack's detail page
- On failure (e.g. missing `OPENAI_API_KEY`, org not verified): a toast surfaces the error and the form is preserved
- See: [Sticker Generation](features/sticker-generation.md)

## Browse the Pack Library

- User navigates to `/packs`
- The library grid shows every generated pack (cover sticker, theme, style, sticker count, date), scoped to the `sticker-packs/` prefix
- Click a pack to open its detail page (`/packs/[id]`)
- Detail shows the full sticker grid; hover a sticker to download it individually
- Empty library shows a "Generate a pack" prompt
- See: [Pack Library](features/sticker-packs.md)

## Export a Pack to a Platform

- On a pack's detail page, click a platform button (Telegram, WhatsApp, Discord, iMessage)
- The button shows "Building…" while the backend resizes stickers, zips a per-platform bundle (with an IMPORT.md how-to), and stores it in B2
- The browser opens the presigned download for the ZIP; a toast confirms the bundle size
- Re-exporting the same platform serves the cached ZIP instantly
- See: [Pack Export](features/pack-export.md)

## Delete a Pack

- On a pack's detail page, click "Delete pack" and confirm
- The backend batch-deletes every object under the pack's prefix (stickers, manifest, cached exports) from B2
- On success: a toast confirms and the app returns to the library
- See: [Pack Library](features/sticker-packs.md)

## View Dashboard

- User navigates to `/` (home)
- Parallel API calls load pack stats, pack activity, and the pack list
- Stats cards show: total packs, total stickers, stickers generated this week, pack storage used
- The chart shows packs created over the last 7 days
- The recent-packs table shows the last 10 packs (rows link to detail)
- A "New pack" CTA links to `/generate`
- Empty state: "No packs yet" messages
- See: [Dashboard](features/dashboard.md)

## Upload Reference Images / Files

- User navigates to `/upload`
- Drops or selects files in the dropzone (drop in your own reference images, or any file)
- Client validates file size (max 100MB) and type
- Progress bar shows per-file upload status; success/error toasts
- See: [File Upload](features/file-upload.md)

## Browse and Manage Files (full bucket)

- User navigates to `/files`
- The tree view lists everything in the bucket (including `sticker-packs/` and `uploads/`)
- Hover a file row to preview, download, or delete
- See: [File Browser](features/file-browser.md)
