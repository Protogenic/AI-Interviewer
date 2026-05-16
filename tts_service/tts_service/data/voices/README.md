# Voices

Каждый голос — поддиректория с двумя файлами:
- `meta.json` — `{ "name", "description", "language" }`
- `reference.wav` — 6–20 секунд чистой речи, 22050 Hz, mono, без музыки и шума.

Подготовка референса:
1. `yt-dlp -x --audio-format wav <url>` — скачать аудио.
2. Нарезать чистый кусок речи (Audacity / ffmpeg).
3. Привести к моно 22050: `ffmpeg -i in.wav -ac 1 -ar 22050 reference.wav`.

В zero-shot режиме XTTS-v2 хватает одного хорошего сэмпла. Для лучшего качества можно положить несколько `reference_*.wav` и усреднять эмбеддинги в движке.
