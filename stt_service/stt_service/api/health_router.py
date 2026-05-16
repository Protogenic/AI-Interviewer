from fastapi import APIRouter

from stt_service.core.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    s = get_settings()
    return {"ok": True, "model": s.whisper_model}
