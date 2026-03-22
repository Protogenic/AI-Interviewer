import { Server, Socket } from 'socket.io';
import * as interviewService from '../services/interviewService';
import {
  InterviewStartPayload,
  InterviewAnswerPayload,
  InterviewCompletePayload,
} from '../types';

export function setupWebSocket(io: Server): void {
  io.on('connection', (socket: Socket) => {
    console.log(`[WS] connected  ${socket.id}`);

    socket.on('interview:start', async (data: InterviewStartPayload) => {
      try {
        const session = await interviewService.createSession(
          data.journalistId,
          data.userName ?? 'Гость',
          data.userInfo  ?? '',
        );

        const question = await interviewService.generateFirstQuestion(session.id);

        socket.emit('interview:question', { question, sessionId: session.id });
      } catch (err) {
        console.error('[WS] interview:start error', err);
        socket.emit('interview:error', { message: 'Не удалось начать интервью' });
      }
    });

    socket.on('interview:answer', async (data: InterviewAnswerPayload) => {
      try {
        const question = await interviewService.processAnswer(data.sessionId, data.answer);
        socket.emit('interview:question', { question, sessionId: data.sessionId });
      } catch (err) {
        console.error('[WS] interview:answer error', err);
        socket.emit('interview:error', { message: 'Не удалось сгенерировать вопрос' });
      }
    });

    socket.on('interview:complete', async (data: InterviewCompletePayload) => {
      try {
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
