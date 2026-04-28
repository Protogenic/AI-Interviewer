FROM python:3.11-slim

WORKDIR /app

COPY tts_service/requirements.txt /app/requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip && \
    python -m pip install -r /app/requirements.txt

COPY tts_service/ /app/

EXPOSE 8100

CMD ["uvicorn", "tts_service.main:app", "--host", "0.0.0.0", "--port", "8100"]
