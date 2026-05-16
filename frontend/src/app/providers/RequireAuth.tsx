import React from 'react';
import { useUnit } from 'effector-react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { $authChecked, $user } from '~/entities/user';

export const RequireAuth: React.FC = () => {
  const user = useUnit($user);
  const checked = useUnit($authChecked);
  const location = useLocation();

  if (!checked) return null;
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
};

