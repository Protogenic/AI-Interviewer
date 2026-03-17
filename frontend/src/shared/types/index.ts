export interface Journalist {
  id: string;
  name: string;
  description: string;
}

export interface Session {
  id: string;
  journalistId: string;
  status: 'active' | 'completed';
  createdAt: string;
}

export interface Message {
  id: string;
  role: 'assistant' | 'user';
  content: string;
  timestamp: Date;
}

// WebSocket (заглушка)
export interface ServerToClientEvents {
  'interview:question': (data: { question: string }) => void;
  'interview:error': (data: { message: string }) => void;
}

export interface ClientToServerEvents {
  'interview:start': (data: { journalistId: string; userInfo?: any }) => void;
  'interview:answer': (data: { sessionId: string; answer: string }) => void;
  'interview:complete': (data: { sessionId: string }) => void;
}