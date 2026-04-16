# AI Интервьюер — Документация API

> Backend стек: **Express + Socket.IO + Prisma (PostgreSQL) + Zod**
> REST: `http://localhost:3001` (переменная `PORT_REST`)
> WebSocket: `ws://localhost:3002` (переменная `PORT_WS`)

---

## Модели данных (Prisma)

### Journalist
| Поле | Тип | Описание |
|------|-----|----------|
| `id` | `String` | Идентификатор (задаётся вручную, напр. `"pozner"`) |
| `name` | `String` | Полное имя журналиста |
| `description` | `String` | Краткое описание стиля |

### InterviewSession
| Поле | Тип | Описание |
|------|-----|----------|
| `id` | `String` (UUID) | Автогенерируемый идентификатор сессии |
| `journalistId` | `String` | Ссылка на `Journalist.id` |
| `userName` | `String` | Имя пользователя, дефолт `"Гость"` |
| `userInfo` | `String` | Доп. информация о пользователе, дефолт `""` |
| `status` | `String` | Статус сессии, дефолт `"active"` |
| `createdAt` | `DateTime` | Дата создания (ISO-строка в JSON) |

### ConversationTurn
| Поле | Тип | Описание |
|------|-----|----------|
| `id` | `String` (UUID) | Автогенерируемый идентификатор реплики |
| `sessionId` | `String` | Ссылка на `InterviewSession.id` |
| `role` | `String` | `"assistant"` или `"user"` |
| `content` | `String` | Текст реплики |
| `createdAt` | `DateTime` | Дата создания (ISO-строка в JSON) |

---

## REST API

Base URL: `http://localhost:3001/api`

---

### GET `/api/journalists`

Возвращает список всех журналистов, упорядоченных по имени.

**Запрос:** тело не требуется.

**Ответ `200 OK`:**
```json
[
  {
    "id": "pozner",
    "name": "Владимир Познер",
    "description": "Интеллигентный и глубокий стиль..."
  },
  {
    "id": "dud",
    "name": "Юрий Дудь",
    "description": "Прямолинейный и дерзкий стиль..."
  }
]
```

---

### GET `/api/journalists/:id`

Возвращает одного журналиста по идентификатору.

**Параметры пути:**
| Параметр | Тип | Описание |
|----------|-----|----------|
| `id` | `string` | Идентификатор журналиста |

**Ответ `200 OK`:**
```json
{
  "id": "pozner",
  "name": "Владимир Познер",
  "description": "Интеллигентный и глубокий стиль..."
}
```

**Ответ `404 Not Found`:**
```json
{ "error": "Journalist not found" }
```

---

### POST `/api/interviews`

Создаёт новую сессию интервью (REST-вариант без генерации вопроса).

**Тело запроса (JSON):**
| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `journalistId` | `string` (min 1 символ) | ✅ | Идентификатор журналиста |
| `userName` | `string` | ❌ | Имя пользователя (дефолт `"Гость"`) |
| `userInfo` | `string` | ❌ | Доп. информация (дефолт `""`) |

**Пример запроса:**
```json
{
  "journalistId": "pozner",
  "userName": "Анна",
  "userInfo": "Студентка, 22 года"
}
```

**Ответ `201 Created`:** объект сессии с вложенным журналистом:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "journalistId": "pozner",
  "userName": "Анна",
  "userInfo": "Студентка, 22 года",
  "status": "active",
  "createdAt": "2026-03-16T10:00:00.000Z",
  "journalist": {
    "id": "pozner",
    "name": "Владимир Познер",
    "description": "Интеллигентный и глубокий стиль..."
  }
}
```

**Ответ `422 Unprocessable Entity`** (ошибка валидации Zod):
```json
{ "error": [{ "code": "too_small", "path": ["journalistId"], "message": "String must contain at least 1 character(s)" }] }
```

---

### GET `/api/interviews/:id`

Возвращает сессию интервью по UUID.

**Параметры пути:**
| Параметр | Тип | Описание |
|----------|-----|----------|
| `id` | `string` (UUID) | Идентификатор сессии |

**Ответ `200 OK`:** та же структура, что и `POST /api/interviews` (`201`).

**Ответ `404 Not Found`:**
```json
{ "error": "Session not found" }
```

---

### GET `/api/interviews/:id/history`

Возвращает историю реплик интервью, упорядоченных по времени создания.

**Параметры пути:**
| Параметр | Тип | Описание |
|----------|-----|----------|
| `id` | `string` (UUID) | Идентификатор сессии |

**Ответ `200 OK`:**
```json
[
  {
    "id": "aaaa-...",
    "sessionId": "550e8400-...",
    "role": "assistant",
    "content": "Здравствуйте! Расскажите о себе.",
    "createdAt": "2026-03-16T10:00:01.000Z"
  },
  {
    "id": "bbbb-...",
    "sessionId": "550e8400-...",
    "role": "user",
    "content": "Меня зовут Анна, я студентка.",
    "createdAt": "2026-03-16T10:00:15.000Z"
  }
]
```

---

### Общие ошибки (REST)

| Код | Тело | Причина |
|-----|------|---------|
| `404` | `{ "error": "..." }` | Ресурс не найден |
| `422` | `{ "error": [...] }` | Ошибка валидации Zod |
| `500` | `{ "error": "..." }` | Внутренняя ошибка сервера |

---

## WebSocket API (Socket.IO)

**URL:** `ws://localhost:3002`

Socket.IO клиент подключается к этому URL. CORS разрешён для любого origin (`*`).

---

### События, которые **отправляет клиент** (emit)

#### `interview:start`

Создаёт новую сессию и запрашивает первый вопрос от ИИ-журналиста.

**Payload:**
```typescript
{
  journalistId: string;   // обязательно — id журналиста
  userName?: string;      // опционально — имя пользователя
  userInfo?: string;      // опционально — доп. информация
}
```

**Пример:**
```js
socket.emit('interview:start', { journalistId: 'pozner', userName: 'Анна' });
```

После успеха сервер отвечает событием `interview:question`.
При ошибке сервер отвечает событием `interview:error` с сообщением `"Не удалось начать интервью"`.

---

#### `interview:answer`

Отправляет ответ пользователя и запрашивает следующий вопрос.

**Payload:**
```typescript
{
  sessionId: string;  // UUID сессии, полученный из interview:question
  answer: string;     // текст ответа пользователя
}
```

**Пример:**
```js
socket.emit('interview:answer', { sessionId: '550e8400-...', answer: 'Меня зовут Анна.' });
```

После успеха сервер отвечает событием `interview:question`.
При ошибке — `interview:error` с `"Не удалось сгенерировать вопрос"`.

---

#### `interview:complete`

Завершает интервью (обновляет статус сессии в БД). Сервер **не отправляет** ответное событие.

**Payload:**
```typescript
{
  sessionId: string;  // UUID сессии
}
```

**Пример:**
```js
socket.emit('interview:complete', { sessionId: '550e8400-...' });
```

---

### События, которые **сервер отправляет клиенту** (on)

#### `interview:question`

Приходит в ответ на `interview:start` или `interview:answer`.

**Payload:**
```typescript
{
  question: string;   // текст вопроса от ИИ-журналиста
  sessionId: string;  // UUID сессии (важно: содержит реальный id из БД)
}
```

**Пример:**
```js
socket.on('interview:question', ({ question, sessionId }) => {
  console.log('Вопрос:', question);
  console.log('Session ID:', sessionId);
});
```

---

#### `interview:error`

Приходит при ошибке обработки на сервере.

**Payload:**
```typescript
{
  message: string;  // человекочитаемое описание ошибки
}
```

Возможные значения `message`:
- `"Не удалось начать интервью"`
- `"Не удалось сгенерировать вопрос"`

---

## Типичный сценарий работы

```
Клиент                                      Сервер (WS)
  │                                              │
  │─── interview:start { journalistId } ────────▶│ createSession() + AI generate
  │                                              │
  │◀── interview:question { question, sessionId }│
  │                                              │
  │─── interview:answer { sessionId, answer } ──▶│ saveTurn() + AI generate
  │                                              │
  │◀── interview:question { question, sessionId }│
  │                                              │
  │    (повтор n раз)                            │
  │                                              │
  │─── interview:complete { sessionId } ────────▶│ updateStatus("completed")
  │                                              │
```

---

## Переменные окружения (backend)

| Переменная | Дефолт | Описание |
|------------|--------|----------|
| `PORT_REST` | `3001` | Порт REST-сервера |
| `PORT_WS` | `3002` | Порт WebSocket-сервера |
| `DATABASE_URL` | — | PostgreSQL connection string |
| `AI_SERVICE_URL` | `http://localhost:8000` | URL AI-сервиса генерации вопросов |

## Переменные окружения (frontend)

| Переменная | Дефолт | Описание |
|------------|--------|----------|
| `VITE_API_BASE_URL` | `http://localhost:3001/api` | Base URL для REST-запросов |
| `VITE_WS_URL` | `http://localhost:3002` | URL WebSocket-сервера |
