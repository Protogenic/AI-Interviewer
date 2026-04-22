# Подготовка и запуск api

## 1. Создайте файл .env
Нужно создать файл:
ai_service_api/ai_service/.env
с такими переменными:
LLM_PROVIDER=
OPENAI_API_KEY=ваш_токен
OPENAI_MODEL=gpt-4o-mini
OLLAMA_BASE_URL=http://host.docker.internal:11434/v1
OLLAMA_MODEL=qwen2.5:7b-instruct
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=150

## 2. Подключение LLM: GPT или Ollama
### GPT:
- В файле .env укажите:
LLM_PROVIDER=openai
OPENAI_API_KEY=ваш_токен
OPENAI_MODEL=gpt-4o-mini
### Ollama:
- Установите Ollama на компьютер
- Запустите Ollama
- Скачайте модель: ollama pull qwen2.5:7b-instruct
- В файле .env укажите:
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434/v1
OLLAMA_MODEL=qwen2.5:7b-instruct

## 3. Сборка dockerfile из корня репозитория:
docker build -t ai-service -f ai_service_api/Dockerfile .

## 4. Запуск dockerfile:
docker run -d --name ai-service-container -p 8000:8000 ai-service

## 5. После этого сервис будет доступен на http://localhost:8000

## Если требуются зависисмости, установить зависимости из папки ai_service с помощью:
py -m pip install -e .

# Offline pipeline:
## 1. clean_interviews.py

Скрипт `clean_interviews.py` читает сырые расшифровки интервью в формате .txt, чистит их от мусора, выделяет реплики по спикерам и склеивает подряд идущие строки одного спикера в один блок. Результат сохраняется в формате JSONL, где одна строка это один блок спикера.

### 1) Подготовка входных данных

- Создать папку с транскриптами
- Формат файлов: .txt
- Требования к формату транскрипта:
  - Реплики должны иметь маркер говорящего в одном из форматов: [СПИКЕР], СПИКЕР: текст, СПИКЕР: (текст на след. строке)

### 2) Запуск

Нужно перейти в папку, где лежит файл, и запустить:

python clean_interviews.py "path\to\input_dir" "path\to\out_dir"
- input_dir - корневая папка с .txt 
- out_dir - папка, куда будут записаны .jsonl

### 3) Выходные файлы

Для каждого входного .txt создаётся отдельный файл, где:

- Имя: <interview_id>.jsonl, где interview_id = имя_файла
- На каждой строке: interview_id - ID из имени файла, source_file - имя файла, replica_id - номер реплики, speaker - нормализованная роль (interviewer или guest), speaker_raw - оригинальная метка спикера (для отладки ошибок), text - очищенный и склеенный текст реплики.

## 2. run_offline_pipeline.py

Скрипт `run_offline_pipeline.py` читает очищенные json файлы интервью и на их основе составляет профиль интервьюера.

### 1) Подготовка входных данных

- Запустить clean_interviews.py
- Очищенные файлы должны храниться в `ai_service_api/ai_service/data/cleaned`

### 2) Запуск

Из ai_service_api:
python -m ai_service.offline_pipeline.run_offline_pipeline

### 3) Выходные файлы

Для каждого входного .txt создаётся отдельный файл, где:

- Имя: <interview_id>.jsonl, где interview_id = имя_файла
- На каждой строке: interview_id - ID из имени файла, source_file - имя файла, replica_id - номер реплики, speaker - нормализованная роль (interviewer или guest), speaker_raw - оригинальная метка спикера (для отладки ошибок), text - очищенный и склеенный текст реплики.
