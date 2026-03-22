import { prisma } from '../database/prisma';
import { generateQuestion } from './aiServiceClient';
import { InterviewPart } from '../types';

export async function createSession(
  journalistId: string,
  userName: string,
  userInfo: string,
) {
  return prisma.interviewSession.create({
    data: { journalistId, userName, userInfo },
    include: { journalist: true },
  });
}

export async function getSession(sessionId: string) {
  return prisma.interviewSession.findUnique({
    where: { id: sessionId },
    include: { journalist: true },
  });
}

export async function getHistory(sessionId: string) {
  return prisma.conversationTurn.findMany({
    where: { sessionId },
    orderBy: { createdAt: 'asc' },
  });
}

export async function completeSession(sessionId: string) {
  await prisma.interviewSession.update({
    where: { id: sessionId },
    data: { status: 'completed' },
  });
}

export async function processAnswer(sessionId: string, answer: string): Promise<string> {
  // берём историю до того, как сохранили новый ответ
  const session = await prisma.interviewSession.findUniqueOrThrow({
    where: { id: sessionId },
    include: { turns: { orderBy: { createdAt: 'asc' } } },
  });

  await prisma.conversationTurn.create({
    data: { sessionId, role: 'user', content: answer },
  });

  const question = await generateQuestion({
    session_id: sessionId,
    character_id: session.journalistId,
    user_name: session.userName,
    user_info: session.userInfo,
    last_answer: answer,
    full_interview_history: session.turns.map((t) => ({ role: t.role, text: t.content })),
  });

  await prisma.conversationTurn.create({
    data: { sessionId, role: 'assistant', content: question },
  });

  return question;
}

export async function generateFirstQuestion(sessionId: string): Promise<string> {
  // история пустая, просто нужны параметры сессии
  const { journalistId, userName, userInfo } = await prisma.interviewSession.findUniqueOrThrow({
    where: { id: sessionId },
  });

  const question = await generateQuestion({
    session_id: sessionId,
    character_id: journalistId,
    user_name: userName,
    user_info: userInfo,
    last_answer: '',
    full_interview_history: [],
  });

  await prisma.conversationTurn.create({
    data: { sessionId, role: 'assistant', content: question },
  });

  return question;
}
