import logging

from fastapi import APIRouter, HTTPException

from app.service.stickers import StickerGenerationError, generate_pack
from app.types import GeneratePackRequest, PackManifest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate", response_model=PackManifest)
async def generate_pack_endpoint(request: GeneratePackRequest):
    """Generate a themed sticker pack and store it in B2."""
    try:
        return generate_pack(request)
    except StickerGenerationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    except RuntimeError as e:
        logger.error("Pack generation storage failure: %s", e)
        raise HTTPException(
            status_code=500, detail="Failed to store generated pack"
        ) from None
