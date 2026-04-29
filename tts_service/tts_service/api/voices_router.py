from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from tts_service.core.settings import get_proj_settings
from tts_service.models.tts import VoicesResponse
from tts_service.services.voice_repository import VoiceRepository
from tts_service.exeptions.tts_error import VoiceNotFound


router = APIRouter(
    prefix = "/voices",
    tags = ["voices"]
)

voice_repository = VoiceRepository(get_proj_settings().voices_dir)


@router.get("", response_model=VoicesResponse)
async def list_voices() -> VoicesResponse:
    return VoicesResponse(voices=voice_repository.list())


@router.get("/{voice_id}/reference")
async def get_reference(voice_id: str):
    try:
        path = voice_repository.reference_path(voice_id)
    except VoiceNotFound as vnf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(vnf)) from vnf
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="reference audio missing")
    return FileResponse(path, media_type="audio/wav")
