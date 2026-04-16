export const ENDPOINTS = {
  JOURNALISTS: '/journalists',
  /** POST — создать сессию (то же тело, что и interview:start по смыслу) */
  INTERVIEWS: '/interviews',
  INTERVIEW: (id: string) => `/interviews/${id}`,
  INTERVIEW_HISTORY: (id: string) => `/interviews/${id}/history`,
} as const;