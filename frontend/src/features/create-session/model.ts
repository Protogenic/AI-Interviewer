import { createEvent } from 'effector';

/**
 * Триггер выбора журналиста на главной странице.
 * Навигация и WS-старт интервью управляются в UI-слое (HomePage / InterviewPage).
 */
export const formSubmitted = createEvent<{ journalistId: string }>();
