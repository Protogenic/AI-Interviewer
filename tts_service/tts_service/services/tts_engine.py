import io
import math
import os
import struct
import wave
from typing import Protocol

from tts_service.services.voice_repository import VoiceRepository
from tts_service.exeptions.tts_error import UnknownEngine, VoiceNotFound


class TtsEngine(Protocol):
    def synthesize(self, text: str, voice_id: str) -> bytes: ...


class DummyEngine:
    def __init__(self, voice_repository: VoiceRepository, sample_rate: int) -> None:
        self.__voice_repository = voice_repository
        self.__sample_rate = sample_rate

    def synthesize(self, text: str, voice_id: str) -> bytes:
        self.__voice_repository.get(voice_id)

        duration = max(0.5, min(len(text) * 0.06, 15.0))
        freq = 220.0 + (hash(voice_id) % 200)
        n_samples = int(duration * self.__sample_rate)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self.__sample_rate)
            for i in range(n_samples):
                value = int(0.3 * 32767 * math.sin(2 * math.pi * freq * i / self.__sample_rate))
                wav.writeframes(struct.pack("<h", value))
        return buf.getvalue()


class XttsEngine:
    def __init__(self, voice_repository: VoiceRepository, model_name: str, device: str, language: str) -> None:
        os.environ.setdefault("COQUI_TOS_AGREED", "1")

        self.__patch_torchaudio_load()

        from TTS.api import TTS

        self.__voice_repository = voice_repository
        self.__language = language
        self.__sample_rate = 24000

        print(f"INFO: loading XTTS model '{model_name}' on device '{device}'")
        self.__tts = TTS(model_name, progress_bar=False).to(device)

    @staticmethod
    def __patch_torchaudio_load() -> None:
        import torch
        import torchaudio
        import soundfile as sf

        def load(uri, *args, **kwargs):
            audio, sr = sf.read(str(uri), dtype="float32", always_2d=True)
            return torch.from_numpy(audio).t().contiguous(), sr

        torchaudio.load = load

    def synthesize(self, text: str, voice_id: str) -> bytes:
        import numpy as np

        ref_path = self.__voice_repository.reference_path(voice_id)
        if not ref_path.exists():
            raise VoiceNotFound(voice_id=voice_id)

        wav = self.__tts.tts(
            text=text,
            speaker_wav=str(ref_path),
            language=self.__language,
        )

        audio = np.asarray(wav, dtype=np.float32)
        audio_int16 = (np.clip(audio, -1.0, 1.0) * 32767.0).astype(np.int16)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(self.__sample_rate)
            f.writeframes(audio_int16.tobytes())
        return buf.getvalue()


def build_engine(
    name: str,
    voice_repository: VoiceRepository,
    sample_rate: int,
    device: str,
    xtts_model: str,
    language: str,
) -> TtsEngine:
    if name == "dummy":
        return DummyEngine(voice_repository, sample_rate)
    if name == "xtts":
        return XttsEngine(voice_repository, xtts_model, device, language)
    raise UnknownEngine(engine=name)
