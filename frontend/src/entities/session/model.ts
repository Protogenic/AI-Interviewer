import { createStore, createEvent, createEffect, sample } from 'effector';
import { apiClient } from '~/shared/api/client';
import { ENDPOINTS } from '~/shared/api/endpoints';
import { Session, Message, ConversationTurn } from '~/shared/types';

/** Загрузка истории реплик из БД (для восстановления после перезагрузки) */
export const fetchHistoryFx = createEffect(async (sessionId: string): Promise<Message[]> => {
  const response = await apiClient.get<ConversationTurn[]>(
    ENDPOINTS.INTERVIEW_HISTORY(sessionId)
  );
  return response.data.map((turn): Message => ({
    id: turn.id,
    role: turn.role as 'assistant' | 'user',
    content: turn.content,
    timestamp: new Date(turn.createdAt),
  }));
});

export const $currentSession = createStore<Session | null>(null);
export const setCurrentSession = createEvent<Session>();
$currentSession.on(setCurrentSession, (_, session) => session);

export const $messages = createStore<Message[]>([])
  .on(fetchHistoryFx.doneData, (_, messages) => messages);

export const addMessage = createEvent<Message>();
$messages.on(addMessage, (state, message) => [...state, message]);

export const clearSession = createEvent();
$currentSession.reset(clearSession);
$messages.reset(clearSession);
