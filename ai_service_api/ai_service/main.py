from fastapi import FastAPI
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from ai_service.api import generation_router, health_router
from ai_service.core import config


def create_app() -> FastAPI:
    settings_proj = config.get_proj_settings()
    app = FastAPI(title = settings_proj.proj_name)

    app.include_router(health_router.router, prefix="/api")
    app.include_router(generation_router.router, prefix="/api")

    return app


app = create_app()