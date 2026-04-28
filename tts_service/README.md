# tts_service

TTS-сервис для AI Interviewer. Озвучка ответов интервьюера выбранным голосом (zero-shot voice cloning через XTTS-v2).

## API

- `GET /api/health/get_health` — healthcheck
- `GET /api/voices` — список доступных голосов
- `GET /api/voices/{voice_id}/reference` — референс-аудио для превью
- `POST /api/synthesize` — `{text, voice_id}` → `audio/wav`

## Движки

- `ENGINE=dummy` — генерирует синусоиду. Не требует моделей. Используется для проверки интеграции.
- `ENGINE=xtts` — XTTS-v2, voice cloning по `reference.wav`. На CPU фраза ~10–60 сек, на GPU ~0.5–2 сек.

## Запуск (dummy)

```bash
pip install -r requirements.txt
uvicorn tts_service.main:app --reload --port 8100
```

## Запуск (XTTS, локально)

```bash
pip install -r requirements-xtts.txt
cp tts_service/.env.example tts_service/.env
uvicorn tts_service.main:app --port 8100
```

Первый запуск тянет модель (~2 ГБ) в `~/.local/share/tts/`. Следующие запуски — мгновенно.

## Голоса

Каждый голос — поддиректория в `tts_service/data/voices/<id>/` с файлами:
- `meta.json` — `{ "name", "description", "language" }`
- `reference.wav` — 6–20 сек чистой речи (моно/стерео, любая частота — XTTS нормализует сам).

См. `tts_service/data/voices/README.md`.

## Проверка

```bash
curl http://localhost:8100/api/voices

curl -X POST http://localhost:8100/api/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text":"Здравствуйте, начнём наше интервью.","voice_id":"dud"}' \
  --output out.wav
```

## Лицензия модели

XTTS-v2 распространяется под Coqui Public Model License (CPML) — некоммерческое использование. Переменная `COQUI_TOS_AGREED=1` подтверждает согласие. В рамках академической работы это допустимо.
