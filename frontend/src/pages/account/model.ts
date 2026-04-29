import { createEffect, createEvent, createStore, sample } from 'effector';
import { apiClient } from '~/shared/api/client';
import { ENDPOINTS } from '~/shared/api/endpoints';
import { ConversationTurn, Message, Session } from '~/shared/types';

export const loadMyInterviews = createEvent();

export const fetchMyInterviewsFx = createEffect(async () => {
  const res = await apiClient.get<Session[]>(ENDPOINTS.INTERVIEWS);
  return res.data;
});

export const $myInterviews = createStore<Session[]>([]).on(
  fetchMyInterviewsFx.doneData,
  (_, sessions) => sessions
);
export const $myInterviewsLoading = fetchMyInterviewsFx.pending;
export const $myInterviewsError = createStore<string | null>(null)
  .on(fetchMyInterviewsFx.failData, (_, err: any) => err?.response?.data?.error ?? 'Ошибка загрузки')
  .reset(fetchMyInterviewsFx.done);

sample({
  clock: loadMyInterviews,
  target: fetchMyInterviewsFx,
});

export const fetchSessionFx = createEffect(async (id: string) => {
  const res = await apiClient.get<Session>(ENDPOINTS.INTERVIEW(id));
  return res.data;
});

export const $selectedSession = createStore<Session | null>(null)
  .on(fetchSessionFx.doneData, (_, s) => s)
  .reset(fetchSessionFx.fail, fetchMyInterviewsFx.done);

export const fetchHistoryFx = createEffect(async (id: string): Promise<Message[]> => {
  const res = await apiClient.get<ConversationTurn[]>(ENDPOINTS.INTERVIEW_HISTORY(id));
  return res.data.map((turn) => ({
    id: turn.id,
    role: turn.role,
    content: turn.content,
    timestamp: new Date(turn.createdAt),
  }));
});

export const $selectedHistory = createStore<Message[]>([])
  .on(fetchHistoryFx.doneData, (_, items) => items)
  .reset(fetchHistoryFx.fail, fetchMyInterviewsFx.done);

