import { Router, Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import * as interviewService from '../../services/interviewService';

export const interviewsRouter = Router();

const CreateSessionSchema = z.object({
  journalistId: z.string().min(1),
  userName: z.string().optional(),
  userInfo: z.string().optional(),
  maxNumberQuestions: z.number().int().positive().optional(),
});

// POST /api/interviews
interviewsRouter.post('/', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const body = CreateSessionSchema.parse(req.body);
    const session = await interviewService.createSession(
      body.journalistId,
      body.userName ?? 'Гость',
      body.userInfo  ?? '',
      body.maxNumberQuestions,
    );
    res.status(201).json(session);
  } catch (err) {
    if (err instanceof z.ZodError) {
      res.status(422).json({ error: err.errors });
      return;
    }
    next(err);
  }
});

// GET /api/interviews/:id
interviewsRouter.get('/:id', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const session = await interviewService.getSession(req.params.id);
    if (!session) {
      res.status(404).json({ error: 'Session not found' });
      return;
    }
    res.json(session);
  } catch (err) {
    next(err);
  }
});

// GET /api/interviews/:id/history
interviewsRouter.get('/:id/history', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const turns = await interviewService.getHistory(req.params.id);
    res.json(turns);
  } catch (err) {
    next(err);
  }
});
