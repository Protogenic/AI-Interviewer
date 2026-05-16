import { createEffect, createEvent, createStore, sample } from 'effector';
import { apiClient, configureAuthHandlers, setApiAccessToken } from '~/shared/api/client';
import { ENDPOINTS } from '~/shared/api/endpoints';
import { User } from '~/shared/types';
import { socketManager } from '~/shared/api/socket';

type Credentials = { email: string; password: string };

export const $user = createStore<User | null>(null);
export const $accessToken = createStore<string | null>(null);
export const $authChecked = createStore(false);

const setUser = createEvent<User | null>();
const setAccessToken = createEvent<string | null>();
const setAuthChecked = createEvent<boolean>();

$user.on(setUser, (_, u) => u);
$accessToken.on(setAccessToken, (_, t) => t);
$authChecked.on(setAuthChecked, (_, v) => v);

export const registerFx = createEffect(async (payload: Credentials) => {
  const res = await apiClient.post<{ user: User; accessToken: string }>(
    ENDPOINTS.AUTH_REGISTER,
    payload
  );
  return res.data;
});

export const loginFx = createEffect(async (payload: Credentials) => {
  const res = await apiClient.post<{ user: User; accessToken: string }>(
    ENDPOINTS.AUTH_LOGIN,
    payload
  );
  return res.data;
});

export const refreshFx = createEffect(async () => {
  const res = await apiClient.post<{ accessToken: string }>(ENDPOINTS.AUTH_REFRESH);
  return res.data;
});

export const fetchMeFx = createEffect(async () => {
  const res = await apiClient.get<{ user: User }>(ENDPOINTS.AUTH_ME);
  return res.data.user;
});

export const logoutFx = createEffect(async () => {
  await apiClient.post(ENDPOINTS.AUTH_LOGOUT);
});

sample({
  clock: [loginFx.doneData, registerFx.doneData],
  fn: ({ accessToken }) => accessToken,
  target: setAccessToken,
});

sample({
  clock: [loginFx.doneData, registerFx.doneData],
  fn: ({ user }) => user,
  target: setUser,
});

sample({
  clock: refreshFx.doneData,
  fn: ({ accessToken }) => accessToken,
  target: setAccessToken,
});

sample({
  clock: refreshFx.doneData,
  target: fetchMeFx,
});

sample({
  clock: fetchMeFx.doneData,
  target: setUser,
});

sample({
  clock: logoutFx.done,
  fn: () => null,
  target: [setUser, setAccessToken],
});

// Keep apiClient token + websocket auth in sync with store
$accessToken.watch((token) => {
  setApiAccessToken(token);
  socketManager.setAuthToken(token);
});

// On auth failure from interceptor: cleanup + redirect
configureAuthHandlers({
  onAccessToken: (token) => {
    // interceptor refresh updates token first; store mirrors it here
    if ($accessToken.getState() !== token) setAccessToken(token);
  },
  onAuthFailure: () => {
    socketManager.disconnect();
    setUser(null);
    setAccessToken(null);
    setAuthChecked(true);
    window.location.assign('/login');
  },
});

export const bootstrapAuthFx = createEffect(async () => {
  try {
    const { accessToken } = await refreshFx();
    setAuthChecked(true);
    return accessToken;
  } catch {
    setAuthChecked(true);
    return null;
  }
});

