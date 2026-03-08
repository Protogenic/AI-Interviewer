from fastapi import FastAPI
from ai_service.api import generation_router
from ai_service.api import health_router
from ai_service.core import config


settings_proj = config.get_proj_settings()

app = FastAPI(title = settings_proj.proj_name)

app.include_router(health_router.router, prefix="/api")
app.include_router(generation_router.router, prefix="/api")
