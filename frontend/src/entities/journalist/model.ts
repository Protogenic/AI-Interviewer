import { createStore, createEvent, createEffect, sample } from 'effector';
import { apiClient } from '~/shared/api/client';
import { ENDPOINTS } from '~/shared/api/endpoints';
import { Journalist } from '~/shared/types';

export const fetchJournalistsFx = createEffect(async (): Promise<Journalist[]> => {
  const response = await apiClient.get<Journalist[]>(ENDPOINTS.JOURNALISTS);
  return response.data;
});

export const $journalists = createStore<Journalist[]>([])
  .on(fetchJournalistsFx.doneData, (_, journalists) => journalists);

export const $journalistsLoading = createStore(false)
  .on(fetchJournalistsFx.pending, (_, pending) => pending);

export const $journalistsError = createStore<string | null>(null)
  .on(fetchJournalistsFx.failData, (_, error) => error.message)
  .reset(fetchJournalistsFx);

export const loadJournalists = createEvent();

sample({
  clock: loadJournalists,
  target: fetchJournalistsFx,
});
