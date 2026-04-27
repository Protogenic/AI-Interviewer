import { Router, Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import * as interviewService from '../../services/interviewService';
import { optionalAuth, requireAuth } from '../../middleware/authMiddleware';
import { authConfig } from '../../config/auth';

export const interviewsRouter = Router();

const CreateSessionSchema = z.object({
  journalistId: z.string().min(1),
  userName: z.string().optional(),
  userInfo: z.string().optional(),
  maxNumberQuestions: z.number().int().positive().optional(),
});

function setAnonCookie(res: Response, secret: string): void {
  res.cookie(authConfig.anonCookieName, secret, {
    httpOnly: true,
    secure: authConfig.cookieSecure,
    sameSite: 'lax',
    path: authConfig.anonCookiePath,
    maxAge: authConfig.anonCookieMaxAgeMs,
  });
}

function readAnonCookie(req: Request): string | null {
  return req.cookies?.[authConfig.anonCookieName] ?? null;
}

// POST /api/interviews
interviewsRouter.post('/', optionalAuth, async (req: Request, res: Response, next: NextFunction) => {
  try {
    const body = CreateSessionSchema.parse(req.body);
    const { session, anonSecret } = await interviewService.createSession(
      body.journalistId,
      body.userName ?? 'Гость',
      body.userInfo  ?? '',
      body.maxNumberQuestions,
      req.user?.id ?? null,
    );
    if (anonSecret) setAnonCookie(res, anonSecret);
    res.status(201).json(session);
  } catch (err) {
    if (err instanceof z.ZodError) {
      res.status(422).json({ error: err.errors });
      return;
    }
    next(err);
  }
});

// GET /api/interviews — история залогиненного пользователя
interviewsRouter.get('/', requireAuth, async (req: Request, res: Response, next: NextFunction) => {
  try {
    const sessions = await interviewService.listSessionsByUser(req.user!.id);
    res.json(sessions);
  } catch (err) {
    next(err);
  }
});

// GET /api/interviews/:id
interviewsRouter.get('/:id', optionalAuth, async (req: Request, res: Response, next: NextFunction) => {
  try {
    const session = await interviewService.getSession(req.params.id);
    const ok = session && interviewService.canAccessSession(
      session,
      req.user?.id ?? null,
      readAnonCookie(req),
    );
    if (!ok) {
      res.status(404).json({ error: 'Session not found' });
      return;
    }
    res.json(session);
  } catch (err) {
    next(err);
  }
});

// GET /api/interviews/:id/history
interviewsRouter.get('/:id/history', optionalAuth, async (req: Request, res: Response, next: NextFunction) => {
  try {
    const session = await interviewService.getSession(req.params.id);
    const ok = session && interviewService.canAccessSession(
      session,
      req.user?.id ?? null,
      readAnonCookie(req),
    );
    if (!ok) {
      res.status(404).json({ error: 'Session not found' });
      return;
    }
    const turns = await interviewService.getHistory(req.params.id);
    res.json(turns);
  } catch (err) {
    next(err);
  }
});
