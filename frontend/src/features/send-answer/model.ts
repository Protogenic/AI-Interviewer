import { createEvent, createEffect, sample } from 'effector';
import { addMessage, $currentSession } from '~/entities/session';
import { socketManager } from '~/shared/api/socket';
import { Message } from '~/shared/types';

export const answerSent = createEvent<string>();

/** Добавляем сообщение пользователя в стор сразу (optimistic) */
sample({
  clock: answerSent,
  fn: (answer): Message => ({
    id: Date.now().toString(),
    role: 'user',
    content: answer,
    timestamp: new Date(),
  }),
  target: addMessage,
});

/** Отправляем ответ на сервер через WebSocket */
const emitAnswerFx = createEffect(
  ({ sessionId, answer }: { sessionId: string; answer: string }) => {
    socketManager.emit('interview:answer', { sessionId, answer });
  }
);

sample({
  clock: answerSent,
  source: $currentSession,
  filter: (session): session is NonNullable<typeof session> =>
    session !== null && session.id.length > 0,
  fn: (session, answer) => ({ sessionId: session!.id, answer }),
  target: emitAnswerFx,
});
