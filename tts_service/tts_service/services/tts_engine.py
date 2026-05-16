import io
import math
import os
import struct
import wave
from pathlib import Path
from typing import Dict, Protocol, Tuple

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
    def __init__(
        self,
        voice_repository: VoiceRepository,
        model_name: str,
        device: str,
        language: str,
        models_dir: str,
    ) -> None:
        os.environ.setdefault("COQUI_TOS_AGREED", "1")
        self.__patch_torchaudio_load()

        from TTS.api import TTS
        from TTS.tts.models.xtts import Xtts

        self.__voice_repository = voice_repository
        self.__language = language
        self.__sample_rate = 24000
        self.__models: Dict[str, Xtts] = {}
        self.__latents: Dict[str, Tuple] = {}

        print(f"INFO: loading base XTTS model '{model_name}' on device '{device}'")
        base_tts = TTS(model_name, progress_bar=False).to(device)
        base_model = base_tts.synthesizer.tts_model
        config = base_tts.synthesizer.tts_config
        models_path = Path(models_dir)

        for voice in voice_repository.list():
            ref_paths = [str(p) for p in voice_repository.reference_paths(voice.id) if p.exists()]
            if not ref_paths:
                print(f"WARNING: no reference audio for '{voice.id}', skipping")
                continue

            pth_path = models_path / f"{voice.id}.pth"
            if pth_path.exists():
                print(f"INFO: loading fine-tuned model for '{voice.id}'")
                model = Xtts.init_from_config(config)
                model.load_checkpoint(config, checkpoint_path=str(pth_path), eval=True, strict=False)
                model.to(device)
            else:
                print(f"INFO: no checkpoint for '{voice.id}', using base model")
                model = base_model

            gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(audio_path=ref_paths)
            self.__models[voice.id] = model
            self.__latents[voice.id] = (gpt_cond_latent, speaker_embedding)
            print(f"INFO: voice '{voice.id}' ready")

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

        if voice_id not in self.__models:
            raise VoiceNotFound(voice_id=voice_id)

        model = self.__models[voice_id]
        gpt_cond_latent, speaker_embedding = self.__latents[voice_id]

        out = model.inference(
            text=text,
            language=self.__language,
            gpt_cond_latent=gpt_cond_latent,
            speaker_embedding=speaker_embedding,
        )

        audio = np.asarray(out["wav"], dtype=np.float32)
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
    models_dir: str = "",
) -> TtsEngine:
    if name == "dummy":
        return DummyEngine(voice_repository, sample_rate)
    if name == "xtts":
        return XttsEngine(voice_repository, xtts_model, device, language, models_dir)
    raise UnknownEngine(engine=name)
