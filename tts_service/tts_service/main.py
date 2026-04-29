from fastapi import FastAPI, Request, Response
from pathlib import Path
from dotenv import load_dotenv
import logging
import time

load_dotenv(Path(__file__).resolve().parent / ".env")

from tts_service.api import health_router, voices_router, synthesize_router
from tts_service.core import settings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")


def create_app() -> FastAPI:
    settings_proj = settings.get_proj_settings()
    app = FastAPI(title = settings_proj.proj_name)

    @app.middleware("http")
    async def log_request_response(request: Request, call_next):
        start = time.time()

        req_body = await request.body()

        async def receive():
            return {"type": "http.request", "body": req_body, "more_body": False}

        request._receive = receive

        logger.info(
            "-> %s %s query=%s body=%s",
            request.method,
            request.url.path,
            dict(request.query_params),
            req_body.decode("utf-8", "ignore")[:2000],
        )

        response = await call_next(request)

        is_binary = response.media_type and not response.media_type.startswith(("application/json", "text/"))
        duration = time.time() - start

        if is_binary:
            logger.info(
                "<- %s %s status=%s time=%.3fs body=<binary %s>",
                request.method,
                request.url.path,
                response.status_code,
                duration,
                response.media_type,
            )
            return response

        resp_body = b""
        async for chunk in response.body_iterator:
            resp_body += chunk

        logger.info(
            "<- %s %s status=%s time=%.3fs body=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration,
            resp_body.decode("utf-8", "ignore")[:2000],
        )

        return Response(
            content=resp_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )

    app.include_router(health_router.router, prefix="/api")
    app.include_router(voices_router.router, prefix="/api")
    app.include_router(synthesize_router.router, prefix="/api")

    return app


app = create_app()
