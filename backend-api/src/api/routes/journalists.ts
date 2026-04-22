import { Router, Request, Response, NextFunction } from 'express';
import { prisma } from '../../database/prisma';

export const journalistsRouter = Router();

// GET /api/journalists
journalistsRouter.get('/', async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const journalists = await prisma.journalist.findMany({
      orderBy: { name: 'asc' },
    });
    res.json(journalists);
  } catch (err) {
    next(err);
  }
});

// GET /api/journalists/:id
journalistsRouter.get('/:id', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const journalist = await prisma.journalist.findUnique({
      where: { id: req.params.id },
    });
    if (!journalist) {
      res.status(404).json({ error: 'Journalist not found' });
      return;
    }
    res.json(journalist);
  } catch (err) {
    next(err);
  }
});
