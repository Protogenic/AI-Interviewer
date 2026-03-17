import { createStore, createEvent, createEffect, sample } from 'effector';
import { apiClient } from '~/shared/api/client';
import { ENDPOINTS } from '~/shared/api/endpoints';
import { Session, Message } from '~/shared/types';

// Создание сессии
export const createSessionFx = createEffect(
  async (journalistId: string): Promise<Session> => {
    // Заглушка
    return {
      id: Math.random().toString(36).substring(7),
      journalistId,
      status: 'active',
      createdAt: new Date().toISOString(),
    };
  }
);

// Загрузка истории сообщений
export const fetchHistoryFx = createEffect(async (sessionId: string): Promise<Message[]> => {
  // Заглушка
  return [
    {
      id: '1',
      role: 'assistant',
      content: 'Здравствуйте! Расскажите о себе.',
      timestamp: new Date(),
    },
  ];
});

export const $currentSession = createStore<Session | null>(null)
  .on(createSessionFx.doneData, (_, session) => session);

export const $messages = createStore<Message[]>([])
  .on(fetchHistoryFx.doneData, (_, messages) => messages);

export const addMessage = createEvent<Message>();
$messages.on(addMessage, (state, message) => [...state, message]);

export const clearSession = createEvent();
$currentSession.reset(clearSession);
$messages.reset(clearSession);

export const createSession = createEvent<string>();
sample({
  clock: createSession,
  target: createSessionFx,
});