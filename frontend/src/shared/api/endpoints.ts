export const ENDPOINTS = {
  JOURNALISTS: '/journalists',
  /** POST — создать сессию (то же тело, что и interview:start по смыслу) */
  INTERVIEWS: '/interviews',
  INTERVIEW: (id: string) => `/interviews/${id}`,
  INTERVIEW_HISTORY: (id: string) => `/interviews/${id}/history`,

  AUTH_REGISTER: '/auth/register',
  AUTH_LOGIN: '/auth/login',
  AUTH_REFRESH: '/auth/refresh',
  AUTH_LOGOUT: '/auth/logout',
  AUTH_ME: '/auth/me',
} as const;