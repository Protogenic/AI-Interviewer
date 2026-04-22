FROM python:3.11-slim

WORKDIR /app

ENV HF_HOME=/app/.cache/huggingface
ENV SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence_transformers

COPY ai_service_api/requirements.txt /app/requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip && \
    python -m pip install --index-url https://download.pytorch.org/whl/cpu torch && \
    python -m pip install -r /app/requirements.txt

RUN python -c "from huggingface_hub import snapshot_download; \
snapshot_download(repo_id='intfloat/multilingual-e5-small', \
local_dir='/app/models/multilingual-e5-small', \
local_dir_use_symlinks=False)"

COPY ai_service_api/ /app/

EXPOSE 8000

CMD ["uvicorn", "ai_service.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "debug"]