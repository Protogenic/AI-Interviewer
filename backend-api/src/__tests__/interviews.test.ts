import { describe, it, expect } from 'vitest';
import request from 'supertest';
import { createApp } from '../app';

const app = createApp();

function getCookie(headers: Record<string, unknown>, name: string): string | undefined {
  const raw = headers['set-cookie'];
  const list = Array.isArray(raw) ? raw : raw ? [String(raw)] : [];
  return list.find((c) => c.startsWith(`${name}=`));
}

async function register(email: string) {
  const res = await request(app).post('/api/auth/register').send({ email, password: 'password123' });
  return { user: res.body.user, accessToken: res.body.accessToken as string };
}

describe('POST /api/interviews — анонимный флоу', () => {
  it('аноним создаёт сессию и получает anon_session cookie', async () => {
    const res = await request(app).post('/api/interviews').send({ journalistId: 'dud' });
    expect(res.status).toBe(201);
    expect(res.body.id).toBeDefined();
    expect(res.body.userId).toBeNull();
    expect(getCookie(res.headers, 'anon_session')).toBeDefined();
  });

  it('аноним читает свою сессию по cookie', async () => {
    const create = await request(app).post('/api/interviews').send({ journalistId: 'dud' });
    const cookie = getCookie(create.headers, 'anon_session')!;

    const get = await request(app).get(`/api/interviews/${create.body.id}`).set('Cookie', cookie);
    expect(get.status).toBe(200);
    expect(get.body.id).toBe(create.body.id);
  });

  it('аноним без cookie не видит чужую анонимную сессию (404)', async () => {
    const create = await request(app).post('/api/interviews').send({ journalistId: 'dud' });
    const get = await request(app).get(`/api/interviews/${create.body.id}`);
    expect(get.status).toBe(404);
  });

  it('аноним с чужой cookie не видит сессию (404)', async () => {
    const a = await request(app).post('/api/interviews').send({ journalistId: 'dud' });
    const b = await request(app).post('/api/interviews').send({ journalistId: 'dud' });
    const cookieB = getCookie(b.headers, 'anon_session')!;

    const get = await request(app).get(`/api/interviews/${a.body.id}`).set('Cookie', cookieB);
    expect(get.status).toBe(404);
  });
});

describe('POST /api/interviews — привязка к юзеру', () => {
  it('сессия логин-юзера получает userId, без anon-cookie', async () => {
    const a = await register('a@a.com');
    const res = await request(app)
      .post('/api/interviews')
      .set('Authorization', `Bearer ${a.accessToken}`)
      .send({ journalistId: 'dud' });
    expect(res.status).toBe(201);
    expect(res.body.userId).toBe(a.user.id);
    expect(getCookie(res.headers, 'anon_session')).toBeUndefined();
  });
});

describe('GET /api/interviews — история', () => {
  it('401 без аутентификации', async () => {
    const res = await request(app).get('/api/interviews');
    expect(res.status).toBe(401);
  });

  it('возвращает только сессии текущего юзера, без анонимных и чужих', async () => {
    const a = await register('a@a.com');
    const b = await register('b@b.com');

    await request(app).post('/api/interviews')
      .set('Authorization', `Bearer ${a.accessToken}`)
      .send({ journalistId: 'dud' });
    await request(app).post('/api/interviews')
      .set('Authorization', `Bearer ${a.accessToken}`)
      .send({ journalistId: 'dud' });
    await request(app).post('/api/interviews')
      .set('Authorization', `Bearer ${b.accessToken}`)
      .send({ journalistId: 'dud' });
    await request(app).post('/api/interviews').send({ journalistId: 'dud' });

    const aHistory = await request(app).get('/api/interviews')
      .set('Authorization', `Bearer ${a.accessToken}`);
    expect(aHistory.status).toBe(200);
    expect(aHistory.body).toHaveLength(2);
    for (const s of aHistory.body) {
      expect(s.userId).toBe(a.user.id);
    }
  });
});

describe('GET /api/interviews/:id — доступ к чужой сессии', () => {
  it('юзер не видит сессию другого юзера (404)', async () => {
    const a = await register('a@a.com');
    const b = await register('b@b.com');

    const aSession = await request(app).post('/api/interviews')
      .set('Authorization', `Bearer ${a.accessToken}`)
      .send({ journalistId: 'dud' });

    const res = await request(app).get(`/api/interviews/${aSession.body.id}`)
      .set('Authorization', `Bearer ${b.accessToken}`);
    expect(res.status).toBe(404);
  });

  it('аноним не видит привязанную к юзеру сессию (404)', async () => {
    const a = await register('a@a.com');
    const aSession = await request(app).post('/api/interviews')
      .set('Authorization', `Bearer ${a.accessToken}`)
      .send({ journalistId: 'dud' });

    const res = await request(app).get(`/api/interviews/${aSession.body.id}`);
    expect(res.status).toBe(404);
  });

  it('юзер видит свою сессию', async () => {
    const a = await register('a@a.com');
    const aSession = await request(app).post('/api/interviews')
      .set('Authorization', `Bearer ${a.accessToken}`)
      .send({ journalistId: 'dud' });

    const res = await request(app).get(`/api/interviews/${aSession.body.id}`)
      .set('Authorization', `Bearer ${a.accessToken}`);
    expect(res.status).toBe(200);
  });

  it('GET /:id/history следует тем же правилам', async () => {
    const a = await register('a@a.com');
    const b = await register('b@b.com');
    const aSession = await request(app).post('/api/interviews')
      .set('Authorization', `Bearer ${a.accessToken}`)
      .send({ journalistId: 'dud' });

    const ownerHistory = await request(app)
      .get(`/api/interviews/${aSession.body.id}/history`)
      .set('Authorization', `Bearer ${a.accessToken}`);
    expect(ownerHistory.status).toBe(200);

    const otherHistory = await request(app)
      .get(`/api/interviews/${aSession.body.id}/history`)
      .set('Authorization', `Bearer ${b.accessToken}`);
    expect(otherHistory.status).toBe(404);
  });
});
