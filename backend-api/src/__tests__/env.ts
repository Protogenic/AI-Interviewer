process.env.DATABASE_URL       ??= 'postgresql://postgres:postgres@localhost:5432/ai_interviewer_test';
process.env.JWT_ACCESS_SECRET  ??= 'test-access-secret';
process.env.JWT_REFRESH_SECRET ??= 'test-refresh-secret';
process.env.AI_SERVICE_URL     ??= 'http://localhost:8000';
process.env.FRONTEND_ORIGIN    ??= 'http://localhost:5173';
process.env.COOKIE_SECURE      ??= 'false';
process.env.BCRYPT_ROUNDS      ??= '4';
