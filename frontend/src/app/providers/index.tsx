import React, { PropsWithChildren } from 'react';
import { RouterProviderComponent } from './router';

export const Providers: React.FC<PropsWithChildren> = ({ children }) => {
  return (
    <>
      <RouterProviderComponent />
      {children}
    </>
  );
};