import { vi, beforeEach, afterAll } from 'vitest';

vi.mock('../services/aiServiceClient', () => ({
  generateQuestion: vi.fn().mockResolvedValue({
    question: 'Mocked question?',
    used_template_id: 'tpl_test',
    consecutive_followups: 0,
  }),
}));

import { prisma } from '../database/prisma';

beforeEach(async () => {
  await prisma.refreshToken.deleteMany();
  await prisma.conversationTurn.deleteMany();
  await prisma.interviewSession.deleteMany();
  await prisma.user.deleteMany();
  await prisma.journalist.deleteMany();
  await prisma.journalist.create({
    data: { id: 'dud', name: 'Юрий Дудь', description: 'Тестовый журналист' },
  });
});

afterAll(async () => {
  await prisma.$disconnect();
});
