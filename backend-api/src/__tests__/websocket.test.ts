import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { createServer, Server as HTTPServer } from 'http';
import { Server as IOServer } from 'socket.io';
import { io as ioClient, Socket as ClientSocket } from 'socket.io-client';
import request from 'supertest';
import { createApp } from '../app';
import { setupWebSocket } from '../api/websocket';

let httpServer: HTTPServer;
let io: IOServer;
let port: number;
const app = createApp();

beforeAll(async () => {
  httpServer = createServer();
  io = new IOServer(httpServer);
  setupWebSocket(io);
  await new Promise<void>((resolve) => {
    httpServer.listen(0, () => {
      const addr = httpServer.address();
      port = typeof addr === 'object' && addr ? addr.port : 0;
      resolve();
    });
  });
});

afterAll(async () => {
  io.close();
  await new Promise<void>((resolve) => httpServer.close(() => resolve()));
});

function connect(token?: string): ClientSocket {
  return ioClient(`http://localhost:${port}`, {
    auth: token ? { token } : undefined,
    transports: ['websocket'],
    forceNew: true,
  });
}

function waitFor<T = unknown>(socket: ClientSocket, event: string, timeout = 5000): Promise<T> {
  return new Promise((resolve, reject) => {
    const t = setTimeout(() => reject(new Error(`Timeout waiting for "${event}"`)), timeout);
    socket.once(event, (data: T) => {
      clearTimeout(t);
      resolve(data);
    });
  });
}

async function registerUser(email: string): Promise<string> {
  const res = await request(app).post('/api/auth/register').send({ email, password: 'password123' });
  return res.body.accessToken;
}

describe('WebSocket — анонимный сокет', () => {
  it('создаёт сессию и получает первый вопрос', async () => {
    const sock = connect();
    sock.emit('interview:start', { journalistId: 'dud' });
    const data = await waitFor<{ sessionId: string; question: string }>(sock, 'interview:question');
    expect(data.sessionId).toBeDefined();
    expect(data.question).toBeDefined();
    sock.disconnect();
  });

  it('может отвечать в свою сессию, но не в чужую', async () => {
    const sockA = connect();
    sockA.emit('interview:start', { journalistId: 'dud' });
    const startA = await waitFor<{ sessionId: string }>(sockA, 'interview:question');

    const sockB = connect();
    sockB.emit('interview:answer', { sessionId: startA.sessionId, answer: 'привет' });
    const errB = await waitFor<{ message: string }>(sockB, 'interview:error');
    expect(errB.message).toMatch(/доступ/i);

    // владелец сессии (sockA) — может
    sockA.emit('interview:answer', { sessionId: startA.sessionId, answer: 'ответ' });
    const next = await waitFor<{ sessionId: string }>(sockA, 'interview:question');
    expect(next.sessionId).toBe(startA.sessionId);

    sockA.disconnect();
    sockB.disconnect();
  });
});

describe('WebSocket — аутентифицированный сокет', () => {
  it('юзер не может отвечать в чужую сессию', async () => {
    const tokenA = await registerUser('wsa@a.com');
    const tokenB = await registerUser('wsb@b.com');

    const sockA = connect(tokenA);
    sockA.emit('interview:start', { journalistId: 'dud' });
    const startA = await waitFor<{ sessionId: string }>(sockA, 'interview:question');

    const sockB = connect(tokenB);
    sockB.emit('interview:answer', { sessionId: startA.sessionId, answer: 'хочу к чужой' });
    const err = await waitFor<{ message: string }>(sockB, 'interview:error');
    expect(err.message).toMatch(/доступ/i);

    sockA.disconnect();
    sockB.disconnect();
  });

  it('сокет без токена не может отвечать в привязанную сессию', async () => {
    const tokenA = await registerUser('wsa@a.com');
    const sockA = connect(tokenA);
    sockA.emit('interview:start', { journalistId: 'dud' });
    const startA = await waitFor<{ sessionId: string }>(sockA, 'interview:question');

    const sockAnon = connect();
    sockAnon.emit('interview:answer', { sessionId: startA.sessionId, answer: 'я случайный' });
    const err = await waitFor<{ message: string }>(sockAnon, 'interview:error');
    expect(err.message).toMatch(/доступ/i);

    sockA.disconnect();
    sockAnon.disconnect();
  });

  it('сессия привязывается к юзеру и попадает в его историю', async () => {
    const tokenA = await registerUser('wsa@a.com');
    const sockA = connect(tokenA);
    sockA.emit('interview:start', { journalistId: 'dud' });
    const startA = await waitFor<{ sessionId: string }>(sockA, 'interview:question');

    const history = await request(app).get('/api/interviews').set('Authorization', `Bearer ${tokenA}`);
    expect(history.status).toBe(200);
    expect(history.body).toHaveLength(1);
    expect(history.body[0].id).toBe(startA.sessionId);

    sockA.disconnect();
  });
});
