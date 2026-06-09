<!-- last_verified: 2026-06-09 -->
# Security

Security principles and implementation for the AI Sticker Pack Generator.

## Trust Boundaries

- **Frontend -> API**: CORS-restricted to configured origins, scoped to `GET/POST/DELETE/OPTIONS`
- **API -> B2**: Authenticated via `B2_APPLICATION_KEY_ID` + `B2_APPLICATION_KEY`, signature v4
- **API -> OpenAI**: `OPENAI_API_KEY` used server-side only by `repo/image_client.py`; never sent to the browser
- **Client -> B2**: Presigned URLs for download (`Content-Disposition: attachment`)

## Upload Validation

- Filename sanitization: path traversal, null bytes, unsafe chars stripped
- MIME/extension consistency check against allowlist
- Chunked streaming with size enforcement (100MB default)
- Content-type allowlist (images, PDFs, text, archives, audio/video)
- Empty file rejection

## File Key Validation

- Empty keys rejected
- Path traversal patterns rejected (`../`, `%2e%2e`, backslashes, null bytes)
- The bucket is the only access boundary — add prefix scoping in
  `services/api/app/service/files.py::validate_key` if your deployment
  shares a bucket with other workloads

## Download Safety

- Presigned URLs force `Content-Disposition: attachment`
- Prevents inline rendering of user-uploaded content (XSS mitigation)

## Secrets Management

- All secrets loaded via environment variables (pydantic-settings)
- Never committed to source control
- `.env.example` documents required variables without values
- **`OPENAI_API_KEY`** is read only by the backend (`config/settings.py` → `repo/image_client.py`). It is never included in any API response and never reaches the frontend bundle. Image generation happens entirely server-side; the browser only ever receives finished stickers via presigned B2 URLs.

## AI Generation Inputs

- The theme prompt is user-supplied free text, bounded to 2–200 characters (validated by Pydantic at the boundary)
- Prompts are only used to call the image model; they are stored in the pack manifest for provenance, not executed
- Generated images are stored under the validated `sticker-packs/<pack-id>/` prefix; pack IDs are server-generated (not user-controlled)

## Agent Security Rules

- Never commit `.env`, credentials, or API keys
- Never weaken validation without explicit instruction
- Never bypass CORS, auth, or input sanitization
- Always validate at system boundaries
