import { createStore, createEvent, createEffect, sample } from 'effector';
import { apiClient } from '~/shared/api/client';
import { ENDPOINTS } from '~/shared/api/endpoints';
import { Journalist } from '~/shared/types';

// Эффект загрузки журналистов
export const fetchJournalistsFx = createEffect(async (): Promise<Journalist[]> => {
  // Заглушка, пока бэк не готов
  // В будущем запрос:
  // const response = await apiClient.get(ENDPOINTS.JOURNALISTS);
  // return response.data;
  return [
    { id: 'pozner', name: 'Владимир Познер', description: 'Интеллигентный и глубокий стиль: философские вопросы, долгие паузы, поиск противоречий в словах собеседника.' },
    { id: 'dud', name: 'Юрий Дудь', description: 'Прямолинейный и дерзкий стиль: острые личные вопросы, факты из прошлого, неудобные темы без обиняков.' },
    { id: 'sobchak', name: 'Ксения Собчак', description: 'Провокационный и светский стиль: скандальные детали, светские темы, личная жизнь и эпатажные вопросы.' },
  ];
});

export const $journalists = createStore<Journalist[]>([])
  .on(fetchJournalistsFx.doneData, (_, journalists) => journalists);

export const loadJournalists = createEvent();

sample({
  clock: loadJournalists,
  target: fetchJournalistsFx,
});