from fastapi import APIRouter, HTTPException, Response, status

from tts_service.core.settings import get_proj_settings
from tts_service.models.tts import SynthesizeRequest
from tts_service.services.tts_engine import build_engine
from tts_service.services.voice_repository import VoiceRepository
from tts_service.exeptions.tts_error import VoiceNotFound


router = APIRouter(
    prefix = "/synthesize",
    tags = ["synthesize"]
)

settings_proj = get_proj_settings()
voice_repository = VoiceRepository(settings_proj.voices_dir)
tts_engine = build_engine(
    name=settings_proj.engine,
    voice_repository=voice_repository,
    sample_rate=settings_proj.sample_rate,
    device=settings_proj.device,
    xtts_model=settings_proj.xtts_model,
    language=settings_proj.default_language,
)


@router.post("", responses={200: {"content": {"audio/wav": {}}}})
async def synthesize(input_data: SynthesizeRequest) -> Response:
    try:
        audio = tts_engine.synthesize(input_data.text, input_data.voice_id)
    except VoiceNotFound as vnf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(vnf)) from vnf
    return Response(content=audio, media_type="audio/wav")
