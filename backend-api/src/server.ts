import 'dotenv/config';
import express from 'express';
import { createServer } from 'http';
import { Server } from 'socket.io';
import cors from 'cors';

import { journalistsRouter } from './api/routes/journalists';
import { interviewsRouter } from './api/routes/interviews';
import { setupWebSocket } from './api/websocket';
import { errorHandler } from './middleware/errorHandler';

const PORT_REST = parseInt(process.env.PORT_REST ?? '3001', 10);
const PORT_WS   = parseInt(process.env.PORT_WS   ?? '3002', 10);

const app = express();
app.use(cors());
app.use(express.json());

app.use('/api/journalists', journalistsRouter);
app.use('/api/interviews',  interviewsRouter);
app.use(errorHandler);

const httpServer = createServer(app);
httpServer.listen(PORT_REST, () => {
  console.log(`REST API  →  http://localhost:${PORT_REST}/api`);
});

const io = new Server({ cors: { origin: '*' } });
setupWebSocket(io);
io.listen(PORT_WS);
console.log(`WebSocket →  ws://localhost:${PORT_WS}`);
