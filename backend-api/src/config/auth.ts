function required(name: string): string {
  const value = process.env[name];
  if (!value || value.length === 0) {
    throw new Error(`Missing required env variable: ${name}`);
  }
  return value;
}

export const authConfig = {
  jwtAccessSecret: required('JWT_ACCESS_SECRET'),
  jwtRefreshSecret: required('JWT_REFRESH_SECRET'),
  accessTtl: process.env.ACCESS_TTL ?? '15m',
  refreshTtlDays: parseInt(process.env.REFRESH_TTL_DAYS ?? '30', 10),
  bcryptRounds: parseInt(process.env.BCRYPT_ROUNDS ?? '10', 10),
  frontendOrigin: process.env.FRONTEND_ORIGIN ?? 'http://localhost:5173',
  cookieSecure: process.env.COOKIE_SECURE === 'true',
  refreshCookieName: 'refresh_token',
  refreshCookiePath: '/api/auth',
  anonCookieName: 'anon_session',
  anonCookiePath: '/api/interviews',
  anonCookieMaxAgeMs: 7 * 24 * 60 * 60 * 1000,
};
