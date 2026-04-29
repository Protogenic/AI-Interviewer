import express from 'express';
import cors from 'cors';
import cookieParser from 'cookie-parser';

import { journalistsRouter } from './api/routes/journalists';
import { interviewsRouter } from './api/routes/interviews';
import { authRouter } from './api/routes/auth';
import { errorHandler } from './middleware/errorHandler';
import { authConfig } from './config/auth';

export function createApp() {
  const app = express();
  app.use(cors({ origin: authConfig.frontendOrigins, credentials: true }));
  app.use(express.json());
  app.use(cookieParser());

  app.use('/api/auth',        authRouter);
  app.use('/api/journalists', journalistsRouter);
  app.use('/api/interviews',  interviewsRouter);
  app.use(errorHandler);

  return app;
}
