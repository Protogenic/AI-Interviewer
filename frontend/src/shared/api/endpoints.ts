export const ENDPOINTS = {
  JOURNALISTS: '/journalists',
  INTERVIEWS: '/interviews',
  INTERVIEW_HISTORY: (id: string) => `/interviews/${id}/history`,
} as const;