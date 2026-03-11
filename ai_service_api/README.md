Установить зависимости из папки ai_service:
py -m pip install -e .

Сборка dockerfile из корня репозитория:
docker build -t ai-service -f ai_service_api/Dockerfile .

Запуск dockerfile:
docker run -d --name ai-service-container -p 8000:8000 ai-service

После этого сервис будет доступен на http://localhost:8000
