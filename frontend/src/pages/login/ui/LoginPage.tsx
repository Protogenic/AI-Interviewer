import React from 'react';
import { AuthPageLayout, BackLink, Center, LoginForm, TopBar } from '~/features/auth';

export const LoginPage: React.FC = () => {
  return (
    <AuthPageLayout>
      <TopBar>
        <BackLink to="/">← Назад</BackLink>
      </TopBar>
      <Center>
        <LoginForm />
      </Center>
    </AuthPageLayout>
  );
};
