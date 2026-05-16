import React from 'react';
import { AuthPageLayout, BackLink, Center, RegisterForm, TopBar } from '~/features/auth';

export const RegisterPage: React.FC = () => {
  return (
    <AuthPageLayout>
      <TopBar>
        <BackLink to="/">← Назад</BackLink>
      </TopBar>
      <Center>
        <RegisterForm />
      </Center>
    </AuthPageLayout>
  );
};
