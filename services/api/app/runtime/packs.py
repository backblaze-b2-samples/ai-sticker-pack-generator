import logging

from fastapi import APIRouter, HTTPException

from app.service.packs import (
    PackNotFoundError,
    delete_pack,
    export_pack,
    get_pack,
    get_pack_activity,
    get_pack_stats,
    get_sticker_url,
    list_packs,
)
from app.types import (
    DailyPackCount,
    ExportRequest,
    ExportResult,
    PackManifest,
    PackStats,
    PackSummary,
    StickerUrlRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/packs", response_model=list[PackSummary])
async def list_packs_endpoint():
    """Scoped library of generated packs (sticker-packs/ prefix)."""
    return list_packs()


@router.get("/packs/stats", response_model=PackStats)
async def pack_stats_endpoint():
    return get_pack_stats()


@router.get("/packs/stats/activity", response_model=list[DailyPackCount])
async def pack_activity_endpoint(days: int = 7):
    if days < 1 or days > 90:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 90")
    return get_pack_activity(days=days)


@router.get("/packs/{pack_id}", response_model=PackManifest)
async def get_pack_endpoint(pack_id: str):
    try:
        return get_pack(pack_id)
    except PackNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.post("/packs/{pack_id}/sticker-url")
async def sticker_url_endpoint(pack_id: str, request: StickerUrlRequest):
    if not request.key:
        raise HTTPException(status_code=400, detail="Missing sticker key")
    try:
        url = get_sticker_url(pack_id, request.key)
    except PackNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    return {"url": url}


@router.post("/packs/{pack_id}/export", response_model=ExportResult)
async def export_pack_endpoint(pack_id: str, request: ExportRequest):
    try:
        return export_pack(pack_id, request.platform)
    except PackNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except RuntimeError as e:
        logger.error("Export failure for pack %s: %s", pack_id, e)
        raise HTTPException(status_code=500, detail="Failed to build export") from None


@router.delete("/packs/{pack_id}")
async def delete_pack_endpoint(pack_id: str):
    try:
        deleted = delete_pack(pack_id)
    except PackNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Failed to delete pack") from None
    return {"deleted": True, "pack_id": pack_id, "objects": deleted}
