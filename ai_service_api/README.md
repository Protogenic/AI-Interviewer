Установить зависимости из папки ai_service:
py -m pip install -e .

Сборка dockerfile:
docker build -f ai_service/Dockerfile -t ai-service .

Запуск dockerfile:
docker run -p 8000:8000 ai-service

После этого сервис будет доступен на http://localhost:8000