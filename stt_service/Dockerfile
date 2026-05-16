FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY stt_service/requirements.txt /app/requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip && \
    python -m pip install -r /app/requirements.txt

COPY stt_service/ /app/

EXPOSE 8010

CMD ["uvicorn", "stt_service.main:app", "--host", "0.0.0.0", "--port", "8010"]

