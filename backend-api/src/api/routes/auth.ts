import { Router, Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import * as authService from '../../services/authService';
import { AuthError } from '../../services/authService';
import { authConfig } from '../../config/auth';
import { requireAuth } from '../../middleware/authMiddleware';

export const authRouter = Router();

const CredentialsSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8).max(200),
});

function setRefreshCookie(res: Response, refreshToken: string): void {
  res.cookie(authConfig.refreshCookieName, refreshToken, {
    httpOnly: true,
    secure: authConfig.cookieSecure,
    sameSite: 'lax',
    path: authConfig.refreshCookiePath,
    maxAge: authConfig.refreshTtlDays * 24 * 60 * 60 * 1000,
  });
}

function clearRefreshCookie(res: Response): void {
  res.clearCookie(authConfig.refreshCookieName, {
    httpOnly: true,
    secure: authConfig.cookieSecure,
    sameSite: 'lax',
    path: authConfig.refreshCookiePath,
  });
}

function handleAuthError(err: unknown, res: Response, next: NextFunction): void {
  if (err instanceof z.ZodError) {
    res.status(422).json({ error: err.errors });
    return;
  }
  if (err instanceof AuthError) {
    res.status(err.status).json({ error: err.message });
    return;
  }
  next(err);
}

authRouter.post('/register', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { email, password } = CredentialsSchema.parse(req.body);
    const result = await authService.register(email, password);
    setRefreshCookie(res, result.refreshToken);
    res.status(201).json({ user: result.user, accessToken: result.accessToken });
  } catch (err) {
    handleAuthError(err, res, next);
  }
});

authRouter.post('/login', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { email, password } = CredentialsSchema.parse(req.body);
    const result = await authService.login(email, password);
    setRefreshCookie(res, result.refreshToken);
    res.json({ user: result.user, accessToken: result.accessToken });
  } catch (err) {
    handleAuthError(err, res, next);
  }
});

authRouter.post('/refresh', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const raw = req.cookies?.[authConfig.refreshCookieName];
    if (!raw) {
      res.status(401).json({ error: 'Refresh-токен отсутствует' });
      return;
    }
    const tokens = await authService.refresh(raw);
    setRefreshCookie(res, tokens.refreshToken);
    res.json({ accessToken: tokens.accessToken });
  } catch (err) {
    if (err instanceof AuthError) {
      clearRefreshCookie(res);
    }
    handleAuthError(err, res, next);
  }
});

authRouter.post('/logout', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const raw = req.cookies?.[authConfig.refreshCookieName];
    await authService.logout(raw);
    clearRefreshCookie(res);
    res.status(204).send();
  } catch (err) {
    next(err);
  }
});

authRouter.get('/me', requireAuth, async (req: Request, res: Response, next: NextFunction) => {
  try {
    const user = await authService.getCurrentUser(req.user!.id);
    if (!user) {
      res.status(404).json({ error: 'Пользователь не найден' });
      return;
    }
    res.json({ user });
  } catch (err) {
    next(err);
  }
});
