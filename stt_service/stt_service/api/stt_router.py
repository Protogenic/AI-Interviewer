from __future__ import annotations

import os
import tempfile
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile

from stt_service.services.transcription_service import transcribe_file

router = APIRouter(tags=["stt"])


@router.post("/stt")
async def stt(audio: UploadFile = File(...), language: Optional[str] = "ru"):
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No file")

    suffix = os.path.splitext(audio.filename)[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await audio.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file")
        tmp.write(content)
        tmp_path = tmp.name

    try:
        return transcribe_file(tmp_path, language)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
