from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

PERSONA_PATH = DATA_DIR / "interviewer_persona.json"

MODEL_NAME = "Qwen/Qwen3-1.7B"
DEVICE = "cpu"
USE_8BIT = False
ENABLE_THINKING = False

GENERATION_CONFIG = {
    "temperature": 0.7,r
    "top_p": 0.8,
    "top_k": 20,
    "max_new_tokens": 512,
    "do_sample": True,
}
