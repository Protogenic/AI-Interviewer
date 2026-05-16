import React from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import HomePage from '~/pages/home';
import InterviewPage from '~/pages/interview';
import LoginPage from '~/pages/login';
import RegisterPage from '~/pages/register';
import AccountPage, { AccountSessionPage } from '~/pages/account';
import { RequireAuth } from './RequireAuth';

const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/register',
    element: <RegisterPage />,
  },
  {
    path: '/',
    element: <HomePage />,
  },
  {
    path: '/interview/:sessionId',
    element: <InterviewPage />,
  },
  {
    path: '/account',
    element: <RequireAuth />,
    children: [
      { index: true, element: <AccountPage /> },
      { path: 'interviews/:id', element: <AccountSessionPage /> },
    ],
  },
]);

export const RouterProviderComponent: React.FC = () => {
  return <RouterProvider router={router} />;
};