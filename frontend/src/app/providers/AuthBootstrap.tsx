import React, { useEffect } from 'react';
import { useUnit } from 'effector-react';
import { $authChecked, bootstrapAuthFx } from '~/entities/user';

export const AuthBootstrap: React.FC = () => {
  const checked = useUnit($authChecked);

  useEffect(() => {
    if (checked) return;
    bootstrapAuthFx();
  }, [checked]);

  return null;
};

