FROM python:3.11-slim

WORKDIR /app

COPY ai_service_api/ /app/

RUN python -m pip install --upgrade pip && \
    python -m pip install .

EXPOSE 8000

CMD ["uvicorn", "ai_service.main:app", "--host", "0.0.0.0", "--port", "8000"]