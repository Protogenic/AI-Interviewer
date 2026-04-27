import crypto from 'crypto';
import { prisma } from '../database/prisma';
import { generateQuestion } from './aiServiceClient';
import { InterviewPart } from '../types';

function hashAnonSecret(secret: string): string {
  return crypto.createHash('sha256').update(secret).digest('hex');
}

export async function createSession(
  journalistId: string,
  userName: string,
  userInfo: string,
  maxNumberQuestions?: number,
  userId?: string | null,
) {
  const anonSecret = userId ? null : crypto.randomBytes(32).toString('hex');
  const session = await prisma.interviewSession.create({
    data: {
      journalistId,
      userName,
      userInfo,
      maxNumberQuestions: maxNumberQuestions ?? null,
      userId: userId ?? null,
      anonSecretHash: anonSecret ? hashAnonSecret(anonSecret) : null,
    },
    include: { journalist: true },
  });
  return { session, anonSecret };
}

export async function getSession(sessionId: string) {
  return prisma.interviewSession.findUnique({
    where: { id: sessionId },
    include: { journalist: true },
  });
}

export async function listSessionsByUser(userId: string) {
  return prisma.interviewSession.findMany({
    where: { userId },
    include: { journalist: true },
    orderBy: { createdAt: 'desc' },
  });
}

export async function getHistory(sessionId: string) {
  return prisma.conversationTurn.findMany({
    where: { sessionId },
    orderBy: { createdAt: 'asc' },
  });
}

export function canAccessSession(
  session: { userId: string | null; anonSecretHash: string | null },
  userId: string | null,
  anonSecret: string | null,
): boolean {
  if (session.userId !== null) {
    return session.userId === userId;
  }
  if (session.anonSecretHash === null) {
    // legacy-сессии до введения cookie-привязки
    return true;
  }
  if (!anonSecret) return false;
  return hashAnonSecret(anonSecret) === session.anonSecretHash;
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
    data: { sessionId, role: 'guest', content: answer },
  });

  const result = await generateQuestion({
    session_id: sessionId,
    character_id: session.journalistId,
    user_name: session.userName,
    user_info: session.userInfo,
    last_answer: answer,
    full_interview_history: session.turns.map((t) => ({ role: t.role, text: t.content })),
    phrase_id: session.questionId,
    previous_template_id: session.previousTemplateId ?? '',
    consecutive_followups: session.consecutiveFollowups,
    max_number_questions: session.maxNumberQuestions ?? 999,
  });

  await prisma.conversationTurn.create({
    data: { sessionId, role: 'interviewer', content: result.question },
  });

  await prisma.interviewSession.update({
    where: { id: sessionId },
    data: {
      questionId: session.questionId + 1,
      previousTemplateId: result.used_template_id,
      consecutiveFollowups: result.consecutive_followups,
    },
  });

  return result.question;
}

export async function generateFirstQuestion(sessionId: string): Promise<string> {
  // история пустая, просто нужны параметры сессии
  const session = await prisma.interviewSession.findUniqueOrThrow({
    where: { id: sessionId },
  });

  const result = await generateQuestion({
    session_id: sessionId,
    character_id: session.journalistId,
    user_name: session.userName,
    user_info: session.userInfo,
    last_answer: '',
    full_interview_history: [],
    phrase_id: session.questionId,
    previous_template_id: session.previousTemplateId ?? '',
    consecutive_followups: session.consecutiveFollowups,
    max_number_questions: session.maxNumberQuestions ?? 999,
  });

  await prisma.conversationTurn.create({
    data: { sessionId, role: 'interviewer', content: result.question },
  });

  await prisma.interviewSession.update({
    where: { id: sessionId },
    data: {
      questionId: session.questionId + 1,
      previousTemplateId: result.used_template_id,
      consecutiveFollowups: result.consecutive_followups,
    },
  });

  return result.question;
}
