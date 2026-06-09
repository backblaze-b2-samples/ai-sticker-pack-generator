"""Pack library + multi-platform export (service layer).

Reads pack manifests from B2 (the source of truth), builds the scoped /packs
library, assembles per-platform export ZIPs on demand (Pillow resize +
zipfile), caches them back to B2, and deletes whole packs via the repo's
batch delete. No database — B2 is the sole store.
"""

import io
import logging
import zipfile

from app.repo import (
    delete_prefix,
    get_object_bytes,
    get_presigned_url,
    list_files,
    put_bytes,
)
from app.service.stickers import parse_manifest
from app.types import (
    PACKS_PREFIX,
    DailyPackCount,
    ExportResult,
    PackManifest,
    PackStats,
    PackSummary,
    Platform,
)
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)

# Per-platform export specs: (size, image format, file extension). One
# lightweight ZIP builder honors all four target platforms with no platform
# SDK — just Pillow resizing into the dimensions each importer expects.
_PLATFORM_SPECS: dict[Platform, dict] = {
    Platform.TELEGRAM: {"size": (512, 512), "format": "WEBP", "ext": "webp"},
    Platform.WHATSAPP: {"size": (512, 512), "format": "WEBP", "ext": "webp"},
    Platform.DISCORD: {"size": (128, 128), "format": "PNG", "ext": "png"},
    Platform.IMESSAGE: {"size": (408, 408), "format": "PNG", "ext": "png"},
}

_IMPORT_NOTES: dict[Platform, str] = {
    Platform.TELEGRAM: (
        "Telegram: open @Stickers, send /newpack, then upload each .webp and "
        "assign an emoji. 512x512 transparent WebP."
    ),
    Platform.WHATSAPP: (
        "WhatsApp: use a third-party sticker-maker app to import these "
        "512x512 WebP files; tray.webp (96x96) is the pack icon."
    ),
    Platform.DISCORD: (
        "Discord: Server Settings -> Emoji / Stickers -> Upload. 128x128 PNG, "
        "must be under 256 KB each."
    ),
    Platform.IMESSAGE: (
        "iMessage: these 408x408 PNGs are import-ready images. A built sticker "
        "pack needs an Xcode Messages Extension; drop these into its asset "
        "catalog. (We ship images, not a compiled .app.)"
    ),
}


class PackNotFoundError(Exception):
    def __init__(self, pack_id: str):
        self.detail = f"Pack '{pack_id}' not found"
        super().__init__(self.detail)


def _manifest_key(pack_id: str) -> str:
    return f"{PACKS_PREFIX}{pack_id}/pack.json"


def _export_key(pack_id: str, platform: Platform) -> str:
    return f"{PACKS_PREFIX}{pack_id}/exports/{platform.value}.zip"


def _load_manifest(pack_id: str) -> PackManifest:
    raw = get_object_bytes(_manifest_key(pack_id))
    if raw is None:
        raise PackNotFoundError(pack_id)
    return parse_manifest(raw)


def list_packs() -> list[PackSummary]:
    """List every pack by reading manifests under the sticker-packs/ prefix."""
    files = list_files(prefix=PACKS_PREFIX, max_keys=1000)
    summaries: list[PackSummary] = []
    for f in files:
        if not f.key.endswith("/pack.json"):
            continue
        raw = get_object_bytes(f.key)
        if raw is None:
            continue
        manifest = parse_manifest(raw)
        cover = manifest.stickers[0].key if manifest.stickers else None
        summaries.append(
            PackSummary(
                pack_id=manifest.pack_id,
                theme=manifest.theme,
                style=manifest.style,
                created_at=manifest.created_at,
                sticker_count=manifest.sticker_count,
                cover_key=cover,
            )
        )
    summaries.sort(key=lambda p: p.created_at, reverse=True)
    return summaries


def get_pack(pack_id: str) -> PackManifest:
    """Return the full manifest (sticker grid) for one pack."""
    return _load_manifest(pack_id)


def get_sticker_url(pack_id: str, key: str) -> str:
    """Presigned download URL for a single sticker, scoped to the pack prefix."""
    manifest = _load_manifest(pack_id)
    if key not in {s.key for s in manifest.stickers}:
        raise PackNotFoundError(pack_id)
    filename = key.rsplit("/", 1)[-1]
    return get_presigned_url(key, filename=filename)


def _resize_png(png: bytes, spec: dict) -> bytes:
    """Resize a transparent PNG to a platform spec, preserving transparency."""
    from PIL import Image

    with Image.open(io.BytesIO(png)) as img:
        img = img.convert("RGBA")
        img.thumbnail(spec["size"], Image.LANCZOS)
        # Center on a transparent canvas of the exact target size.
        canvas = Image.new("RGBA", spec["size"], (0, 0, 0, 0))
        offset = (
            (spec["size"][0] - img.width) // 2,
            (spec["size"][1] - img.height) // 2,
        )
        canvas.paste(img, offset, img)
        out = io.BytesIO()
        canvas.save(out, format=spec["format"])
        return out.getvalue()


def _build_export_zip(manifest: PackManifest, platform: Platform) -> bytes:
    """Assemble the per-platform ZIP: resized stickers, originals, IMPORT.md."""
    spec = _PLATFORM_SPECS[platform]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "IMPORT.md",
            f"# {manifest.theme} — {platform.value} pack\n\n"
            f"{manifest.sticker_count} stickers, style: {manifest.style.value}.\n\n"
            f"{_IMPORT_NOTES[platform]}\n",
        )
        tray_written = False
        for sticker in manifest.stickers:
            png = get_object_bytes(sticker.key)
            if png is None:
                logger.warning("Sticker missing during export: %s", sticker.key)
                continue
            resized = _resize_png(png, spec)
            name = f"{platform.value}/{sticker.index:02d}.{spec['ext']}"
            zf.writestr(name, resized)
            # WhatsApp needs a 96x96 tray icon; use the first sticker.
            if platform == Platform.WHATSAPP and not tray_written:
                tray = _resize_png(
                    png, {"size": (96, 96), "format": "WEBP", "ext": "webp"}
                )
                zf.writestr(f"{platform.value}/tray.webp", tray)
                tray_written = True
            # Always include the 1024² transparent original.
            zf.writestr(f"originals/{sticker.index:02d}.png", png)
    return buf.getvalue()


def export_pack(pack_id: str, platform: Platform) -> ExportResult:
    """Build (or reuse a cached) per-platform export ZIP and return its URL."""
    manifest = _load_manifest(pack_id)
    key = _export_key(pack_id, platform)

    cached = get_object_bytes(key)
    if cached is not None:
        size = len(cached)
        url = get_presigned_url(key, filename=f"{manifest.theme}-{platform.value}.zip")
        return ExportResult(
            pack_id=pack_id,
            platform=platform,
            key=key,
            url=url,
            size_bytes=size,
            size_human=humanize_bytes(size),
            cached=True,
        )

    data = _build_export_zip(manifest, platform)
    put_bytes(key, data, "application/zip")
    url = get_presigned_url(key, filename=f"{manifest.theme}-{platform.value}.zip")
    logger.info("Export built: pack_id=%s platform=%s", pack_id, platform.value)
    return ExportResult(
        pack_id=pack_id,
        platform=platform,
        key=key,
        url=url,
        size_bytes=len(data),
        size_human=humanize_bytes(len(data)),
        cached=False,
    )


def delete_pack(pack_id: str) -> int:
    """Delete an entire pack (all stickers, manifest, exports) from B2."""
    # Verify it exists first so we can return a clean 404.
    _load_manifest(pack_id)
    deleted = delete_prefix(f"{PACKS_PREFIX}{pack_id}/")
    logger.info("Pack deleted: pack_id=%s objects=%d", pack_id, deleted)
    return deleted


def get_pack_stats() -> PackStats:
    """Dashboard aggregations scoped to the sticker-packs/ prefix."""
    from datetime import UTC, datetime, timedelta

    files = list_files(prefix=PACKS_PREFIX, max_keys=1000)
    total_stickers = sum(
        1 for f in files if "/stickers/" in f.key and f.key.endswith(".png")
    )
    storage_bytes = sum(f.size_bytes for f in files)
    pack_count = sum(1 for f in files if f.key.endswith("/pack.json"))

    week_ago = datetime.now(UTC) - timedelta(days=7)
    stickers_this_week = sum(
        1
        for f in files
        if "/stickers/" in f.key
        and f.key.endswith(".png")
        and f.uploaded_at >= week_ago
    )
    return PackStats(
        total_packs=pack_count,
        total_stickers=total_stickers,
        stickers_this_week=stickers_this_week,
        storage_bytes=storage_bytes,
        storage_human=humanize_bytes(storage_bytes),
    )


def get_pack_activity(days: int = 7) -> list[DailyPackCount]:
    """Daily pack-creation counts for the last N days (manifest createdAt)."""
    from collections import defaultdict
    from datetime import UTC, datetime, timedelta

    files = list_files(prefix=PACKS_PREFIX, max_keys=1000)
    today = datetime.now(UTC).date()
    cutoff = today - timedelta(days=days - 1)

    counts: dict[str, int] = defaultdict(int)
    for f in files:
        if not f.key.endswith("/pack.json"):
            continue
        d = f.uploaded_at.date()
        if d >= cutoff:
            counts[d.isoformat()] += 1

    return [
        DailyPackCount(
            date=(cutoff + timedelta(days=i)).isoformat(),
            packs=counts.get((cutoff + timedelta(days=i)).isoformat(), 0),
        )
        for i in range(days)
    ]
