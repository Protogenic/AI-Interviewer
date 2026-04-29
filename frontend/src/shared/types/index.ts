export interface Journalist {
  id: string;
  name: string;
  description: string;
}

export interface Session {
  id: string;
  journalistId: string;
  userName: string;
  userInfo: string;
  status: 'active' | 'completed';
  createdAt: string;
  journalist?: Journalist;
}

/** Тело POST /api/interviews — совпадает с полями WebSocket interview:start */
export interface CreateSessionBody {
  journalistId: string;
  userName?: string;
  userInfo?: string;
  maxNumberQuestions?: number;
}

/** Реплика из БД (GET /api/interviews/:id/history) */
export interface ConversationTurn {
  id: string;
  sessionId: string;
  role: 'interviewer' | 'guest';
  content: string;
  createdAt: string;
}

/** Сообщение для отображения в UI */
export interface Message {
  id: string;
  role: 'interviewer' | 'guest';
  content: string;
  timestamp: Date;
}

export interface User {
  id: string;
  email: string;
  createdAt: string;
}

// ─── WebSocket events ──────────────────────────────────────────────────────────

/** События, которые сервер отправляет клиенту */
export interface ServerToClientEvents {
  'interview:question': (data: { question: string; sessionId: string }) => void;
  'interview:error': (data: { message: string }) => void;
}

/** События, которые клиент отправляет серверу */
export interface ClientToServerEvents {
  'interview:start': (data: {
    journalistId: string;
    userName?: string;
    userInfo?: string;
    /** Если не передано — без ограничения (как на бэкенде: null). */
    maxNumberQuestions?: number;
  }) => void;
  'interview:answer': (data: { sessionId: string; answer: string }) => void;
  'interview:complete': (data: { sessionId: string }) => void;
}
