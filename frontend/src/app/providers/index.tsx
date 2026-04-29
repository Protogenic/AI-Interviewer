import React, { PropsWithChildren } from 'react';
import { RouterProviderComponent } from './router';
import { AuthBootstrap } from './AuthBootstrap';

export const Providers: React.FC<PropsWithChildren> = ({ children }) => {
  return (
    <>
      <AuthBootstrap />
      <RouterProviderComponent />
      {children}
    </>
  );
};