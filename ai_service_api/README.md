# AI Service

Python/FastAPI сервис, который генерирует вопросы интервьюера. Принимает историю диалога и последний ответ пользователя, возвращает следующий вопрос в виде текста.

---

## Локальный запуск

**Требования:** Python 3.11+

```bash
cd ai_service_api
pip install -e .
```

Создайте файл `ai_service/.env` (можно скопировать из `.enx.example` в корне папки):

```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=mistralai/mistral-small-3.1-24b-instruct
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=700
```

Запуск:

```bash
cd ai_service_api
uvicorn ai_service.main:app --reload --port 8000
```

После этого сервис доступен на [http://localhost:8000](http://localhost:8000), документация API — на [http://localhost:8000/docs](http://localhost:8000/docs).

---

## Сборка и запуск через Docker

Dockerfile рассчитан на сборку из корня репозитория:

```bash
docker build -t ai-service -f ai_service_api/Dockerfile .
docker run -d --name ai-service -p 8000:8000 --env-file ai_service_api/ai_service/.env ai-service
```

---

## Тесты

```bash
cd ai_service_api
pytest unit_tests/
```

Интеграционные тесты требуют запущенного сервиса и реального LLM-провайдера:

```bash
pytest integration_tests/
```

---

## Offline pipeline:
### 1. clean_interviews.py

Скрипт `clean_interviews.py` читает сырые расшифровки интервью в формате .txt, чистит их от мусора, выделяет реплики по спикерам и склеивает подряд идущие строки одного спикера в один блок. Результат сохраняется в формате JSONL, где одна строка это один блок спикера.

1) Подготовка входных данных

- Создать папку с транскриптами
- Формат файлов: .txt
- Требования к формату транскрипта:
  - Реплики должны иметь маркер говорящего в одном из форматов: [СПИКЕР], СПИКЕР: текст, СПИКЕР: (текст на след. строке)

2) Запуск

Нужно перейти в папку, где лежит файл, и запустить:

python clean_interviews.py "path\to\input_dir" "path\to\out_dir"
- input_dir - корневая папка с .txt 
- out_dir - папка, куда будут записаны .jsonl

3) Выходные файлы

Для каждого входного .txt создаётся отдельный файл, где:

- Имя: <interview_id>.jsonl, где interview_id = имя_файла
- На каждой строке: interview_id - ID из имени файла, source_file - имя файла, replica_id - номер реплики, speaker - нормализованная роль (interviewer или guest), speaker_raw - оригинальная метка спикера (для отладки ошибок), text - очищенный и склеенный текст реплики.

### 2. run_offline_pipeline.py

Скрипт `run_offline_pipeline.py` читает очищенные json файлы интервью и на их основе составляет профиль интервьюера.

1) Подготовка входных данных

- Запустить clean_interviews.py
- Очищенные файлы должны храниться в `ai_service_api/ai_service/data/cleaned`

2) Запуск

Из ai_service_api:
python -m ai_service.offline_pipeline.run_offline_pipeline

3) Выходные файлы

Для каждого входного .txt создаётся отдельный файл, где:

- Имя: <interview_id>.jsonl, где interview_id = имя_файла
- На каждой строке: interview_id - ID из имени файла, source_file - имя файла, replica_id - номер реплики, speaker - нормализованная роль (interviewer или guest), speaker_raw - оригинальная метка спикера (для отладки ошибок), text - очищенный и склеенный текст реплики.
