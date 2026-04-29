import axios from 'axios';

type AuthHandlers = {
  onAccessToken?: (token: string | null) => void;
  onAuthFailure?: () => void;
};

let accessToken: string | null = null;
let handlers: AuthHandlers = {};
let refreshInFlight: Promise<string> | null = null;

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:3001/api',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

export function setApiAccessToken(token: string | null): void {
  accessToken = token;
  handlers.onAccessToken?.(token);
}

export function configureAuthHandlers(next: AuthHandlers): void {
  handlers = next;
}

apiClient.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers = config.headers ?? {};
    config.headers.authorization = `Bearer ${accessToken}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error?.response?.status;
    const original = error?.config as (typeof error.config & { _retry?: boolean }) | undefined;
    if (!original || status !== 401) {
      console.error('API Error:', error);
      return Promise.reject(error);
    }

    const url: string = original.url ?? '';
    const isAuthCall =
      url.includes('/auth/login') ||
      url.includes('/auth/register') ||
      url.includes('/auth/refresh') ||
      url.includes('/auth/logout');

    if (original._retry || isAuthCall) {
      return Promise.reject(error);
    }
    original._retry = true;

    try {
      if (!refreshInFlight) {
        refreshInFlight = apiClient
          .post<{ accessToken: string }>('/auth/refresh')
          .then((r) => r.data.accessToken)
          .finally(() => {
            refreshInFlight = null;
          });
      }
      const newToken = await refreshInFlight;
      setApiAccessToken(newToken);
      original.headers = original.headers ?? {};
      original.headers.authorization = `Bearer ${newToken}`;
      return apiClient(original);
    } catch (refreshErr) {
      setApiAccessToken(null);
      handlers.onAuthFailure?.();
      return Promise.reject(refreshErr);
    }
  }
);