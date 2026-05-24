# AI-Interviewer

Веб-приложение для интерактивных AI-интервью в стиле известных журналистов. Пользователь выбирает журналиста, после чего ведётся диалог: система задаёт вопросы голосом и текстом, пользователь отвечает. Стиль вопросов формируется на основе реальных транскриптов интервью.

## Архитектура

| Сервис | Стек | Порт |
|---|---|---|
| `frontend` | React + TypeScript (Vite) | 5173 |
| `backend-api` | Node.js + TypeScript + Prisma | 3001 (REST), 3002 (WS) |
| `ai-service` | Python + FastAPI + LLM/RAG | 8000 |
| `stt-service` | Python + Whisper (faster-whisper) | 8010 |
| `tts-service` | Python + XTTS-v2 | 8100 |
| `postgres` | PostgreSQL 16 | 5432 |

## Деплой на сервере

Приложение уже развёрнуто и доступно по адресу: **http://aiinterviewer.ru**

## Локальный запуск через Docker

### Требования

- Docker и Docker Compose
- API-ключ [OpenRouter](https://openrouter.ai/) (или другого LLM-провайдера)

### 1. Настроить переменные окружения

Скопировать `.env.example` в `.env` для двух сервисов:

```bash
cp backend-api/.env.example backend-api/.env
cp ai_service_api/ai_service/.env.example ai_service_api/ai_service/.env
```

В `backend-api/.env` заполнить JWT-секреты:

```env
JWT_ACCESS_SECRET=<случайная строка>
JWT_REFRESH_SECRET=<случайная строка>
```

В `ai_service_api/ai_service/.env` указать LLM-провайдера. Пример для OpenRouter:

```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=mistralai/mistral-small-3.1-24b-instruct
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=10000
```

### 2. Собрать и запустить

```bash
docker compose up --build
```

Первый запуск займёт несколько минут — скачиваются модели Whisper.

### 3. Открыть приложение

[http://localhost:5173](http://localhost:5173)

### Остановка

```bash
docker compose down
```

Для удаления данных БД:

```bash
docker compose down -v
```
