import { createEvent, sample } from 'effector';
import { addMessage } from '~/entities/session';
import { Message } from '~/shared/types';

export const answerSent = createEvent<string>();

// Заглушка: добавляем ответ пользователя и эмулируем ответ ассистента
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

// Эмуляция ответа ассистента (через 1 секунду)
answerSent.watch(() => {
  setTimeout(() => {
    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: 'Интересно, расскажите подробнее...',
      timestamp: new Date(),
    };
    addMessage(assistantMessage);
  }, 1000);
});