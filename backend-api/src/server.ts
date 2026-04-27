import 'dotenv/config';
import { createServer } from 'http';
import { Server } from 'socket.io';

import { createApp } from './app';
import { setupWebSocket } from './api/websocket';
import { authConfig } from './config/auth';

const PORT_REST = parseInt(process.env.PORT_REST ?? '3001', 10);
const PORT_WS   = parseInt(process.env.PORT_WS   ?? '3002', 10);

const app = createApp();

const httpServer = createServer(app);
httpServer.listen(PORT_REST, () => {
  console.log(`REST API  →  http://localhost:${PORT_REST}/api`);
});

const io = new Server({
  cors: { origin: authConfig.frontendOrigin, credentials: true },
});
setupWebSocket(io);
io.listen(PORT_WS);
console.log(`WebSocket →  ws://localhost:${PORT_WS}`);
