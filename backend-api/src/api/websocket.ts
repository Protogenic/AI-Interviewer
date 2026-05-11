import { Server, Socket } from 'socket.io';
import * as interviewService from '../services/interviewService';
import { verifyAccessToken } from '../utils/tokens';
import {
  InterviewStartPayload,
  InterviewAnswerPayload,
  InterviewCompletePayload,
} from '../types';

interface SocketAuth {
  userId?: string;
  email?: string;
  anonSessionIds: Set<string>;
}

function authData(socket: Socket): SocketAuth {
  return socket.data as SocketAuth;
}

async function authorizeSession(
  socket: Socket,
  sessionId: string,
): Promise<{ ok: true } | { ok: false; reason: string }> {
  const session = await interviewService.getSession(sessionId);
  if (!session) return { ok: false, reason: 'Сессия не найдена' };

  const data = authData(socket);
  if (session.userId !== null) {
    if (session.userId !== data.userId) return { ok: false, reason: 'Нет доступа к сессии' };
  } else {
    if (!data.anonSessionIds.has(sessionId)) return { ok: false, reason: 'Нет доступа к сессии' };
  }
  return { ok: true };
}

export function setupWebSocket(io: Server): void {
  io.use((socket, next) => {
    const data = authData(socket);
    data.anonSessionIds = new Set();
    const token = socket.handshake.auth?.token;
    if (typeof token === 'string' && token.length > 0) {
      try {
        const payload = verifyAccessToken(token);
        data.userId = payload.sub;
        data.email = payload.email;
      } catch {
        // невалидный токен — продолжаем как анонимный сокет
      }
    }
    next();
  });

  io.on('connection', (socket: Socket) => {
    console.log(`[WS] connected  ${socket.id}`);

    socket.on('interview:start', async (data: InterviewStartPayload) => {
      try {
        const auth = authData(socket);
        const { session } = await interviewService.createSession(
          data.journalistId,
          data.userName ?? 'Гость',
          data.userInfo  ?? '',
          data.maxNumberQuestions,
          auth.userId ?? null,
        );

        if (!auth.userId) {
          auth.anonSessionIds.add(session.id);
        }

        const { question, audio } = await interviewService.generateFirstQuestion(session.id);

        socket.emit('interview:question', { question, sessionId: session.id, audio });
      } catch (err) {
        console.error('[WS] interview:start error', err);
        socket.emit('interview:error', { message: 'Не удалось начать интервью' });
      }
    });

    socket.on('interview:answer', async (data: InterviewAnswerPayload) => {
      try {
        const auth = await authorizeSession(socket, data.sessionId);
        if (!auth.ok) {
          socket.emit('interview:error', { message: auth.reason });
          return;
        }
        const { question, audio } = await interviewService.processAnswer(data.sessionId, data.answer);
        socket.emit('interview:question', { question, sessionId: data.sessionId, audio });
      } catch (err) {
        console.error('[WS] interview:answer error', err);
        socket.emit('interview:error', { message: 'Не удалось сгенерировать вопрос' });
      }
    });

    socket.on('interview:complete', async (data: InterviewCompletePayload) => {
      try {
        const auth = await authorizeSession(socket, data.sessionId);
        if (!auth.ok) {
          socket.emit('interview:error', { message: auth.reason });
          return;
        }
        await interviewService.completeSession(data.sessionId);
        console.log(`[WS] session ${data.sessionId} completed`);
      } catch (err) {
        console.error('[WS] interview:complete error', err);
      }
    });

    socket.on('disconnect', () => {
      console.log(`[WS] disconnected ${socket.id}`);
    });
  });
}
