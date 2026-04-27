import { describe, it, expect } from 'vitest';
import request from 'supertest';
import { createApp } from '../app';

const app = createApp();

function getCookie(headers: Record<string, unknown>, name: string): string | undefined {
  const raw = headers['set-cookie'];
  const list = Array.isArray(raw) ? raw : raw ? [String(raw)] : [];
  return list.find((c) => c.startsWith(`${name}=`));
}

async function registerUser(email: string, password = 'password123') {
  return request(app).post('/api/auth/register').send({ email, password });
}

describe('POST /api/auth/register', () => {
  it('создаёт пользователя и выдаёт токены', async () => {
    const res = await registerUser('a@b.com');
    expect(res.status).toBe(201);
    expect(res.body.user.email).toBe('a@b.com');
    expect(res.body.user.id).toBeDefined();
    expect(res.body.accessToken).toBeDefined();
    expect(getCookie(res.headers, 'refresh_token')).toBeDefined();
  });

  it('422 при коротком пароле', async () => {
    const res = await request(app).post('/api/auth/register').send({
      email: 'a@b.com',
      password: 'short',
    });
    expect(res.status).toBe(422);
  });

  it('422 при невалидном email', async () => {
    const res = await request(app).post('/api/auth/register').send({
      email: 'not-an-email',
      password: 'password123',
    });
    expect(res.status).toBe(422);
  });

  it('409 при дубликате email', async () => {
    await registerUser('a@b.com');
    const res = await registerUser('a@b.com');
    expect(res.status).toBe(409);
  });

  it('email нормализуется в lowercase', async () => {
    const res = await registerUser('Mixed@CASE.com');
    expect(res.status).toBe(201);
    expect(res.body.user.email).toBe('mixed@case.com');
  });
});

describe('POST /api/auth/login', () => {
  it('успешный логин', async () => {
    await registerUser('a@b.com');
    const res = await request(app).post('/api/auth/login').send({
      email: 'a@b.com',
      password: 'password123',
    });
    expect(res.status).toBe(200);
    expect(res.body.user.email).toBe('a@b.com');
    expect(res.body.accessToken).toBeDefined();
    expect(getCookie(res.headers, 'refresh_token')).toBeDefined();
  });

  it('401 при неверном пароле', async () => {
    await registerUser('a@b.com');
    const res = await request(app).post('/api/auth/login').send({
      email: 'a@b.com',
      password: 'wrong-password',
    });
    expect(res.status).toBe(401);
  });

  it('401 для несуществующего email', async () => {
    const res = await request(app).post('/api/auth/login').send({
      email: 'nobody@nowhere.com',
      password: 'password123',
    });
    expect(res.status).toBe(401);
  });
});

describe('GET /api/auth/me', () => {
  it('401 без токена', async () => {
    const res = await request(app).get('/api/auth/me');
    expect(res.status).toBe(401);
  });

  it('401 с битым токеном', async () => {
    const res = await request(app).get('/api/auth/me').set('Authorization', 'Bearer not-a-jwt');
    expect(res.status).toBe(401);
  });

  it('возвращает текущего пользователя по валидному токену', async () => {
    const reg = await registerUser('a@b.com');
    const res = await request(app)
      .get('/api/auth/me')
      .set('Authorization', `Bearer ${reg.body.accessToken}`);
    expect(res.status).toBe(200);
    expect(res.body.user.email).toBe('a@b.com');
  });
});

describe('POST /api/auth/refresh', () => {
  it('ротация: после refresh старый токен становится невалидным', async () => {
    const reg = await registerUser('a@b.com');
    const oldCookie = getCookie(reg.headers, 'refresh_token')!;

    const r1 = await request(app).post('/api/auth/refresh').set('Cookie', oldCookie);
    expect(r1.status).toBe(200);
    expect(r1.body.accessToken).toBeDefined();
    const newCookie = getCookie(r1.headers, 'refresh_token')!;
    expect(newCookie).not.toBe(oldCookie);

    const replay = await request(app).post('/api/auth/refresh').set('Cookie', oldCookie);
    expect(replay.status).toBe(401);

    const r2 = await request(app).post('/api/auth/refresh').set('Cookie', newCookie);
    expect(r2.status).toBe(200);
  });

  it('401 без cookie', async () => {
    const res = await request(app).post('/api/auth/refresh');
    expect(res.status).toBe(401);
  });
});

describe('POST /api/auth/logout', () => {
  it('инвалидирует refresh-токен', async () => {
    const reg = await registerUser('a@b.com');
    const cookie = getCookie(reg.headers, 'refresh_token')!;

    const logout = await request(app).post('/api/auth/logout').set('Cookie', cookie);
    expect(logout.status).toBe(204);

    const refreshAfter = await request(app).post('/api/auth/refresh').set('Cookie', cookie);
    expect(refreshAfter.status).toBe(401);
  });

  it('идемпотентен (logout без cookie не падает)', async () => {
    const res = await request(app).post('/api/auth/logout');
    expect(res.status).toBe(204);
  });
});
