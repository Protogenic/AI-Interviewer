import { createEvent, sample } from 'effector';
import { createSession } from '~/entities/session';

export const formSubmitted = createEvent<{ journalistId: string }>();

sample({
  clock: formSubmitted,
  fn: ({ journalistId }) => journalistId,
  target: createSession,
});