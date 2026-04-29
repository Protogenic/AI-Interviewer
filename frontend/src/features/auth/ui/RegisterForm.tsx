import React, { useEffect, useMemo, useState } from 'react';
import { useUnit } from 'effector-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { $user, registerFx } from '~/entities/user';
import { Card, Title, Field, Input, SubmitButton, ErrorText, FormHint } from './styles';

export const RegisterForm: React.FC = () => {
  const user = useUnit($user);
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const from = useMemo(() => {
    const state = location.state as { from?: string } | null;
    return state?.from ?? '/';
  }, [location.state]);

  useEffect(() => {
    if (user) navigate(from, { replace: true });
  }, [user, from, navigate]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await registerFx({ email: email.trim(), password });
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(err?.response?.data?.error ?? 'Не удалось зарегистрироваться');
    } finally {
      setSubmitting(false);
    }
  };

  const passwordTooShort = password.length > 0 && password.length < 8;
  const disabled = submitting || email.trim().length === 0 || password.length < 8;

  return (
    <Card>
      <Title>Регистрация</Title>
      <form onSubmit={onSubmit}>
        <Field>
          Email
          <Input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            placeholder="you@example.com"
          />
        </Field>
        <Field>
          Пароль
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            placeholder="минимум 8 символов"
          />
        </Field>
        {passwordTooShort && <ErrorText>Пароль должен быть не короче 8 символов</ErrorText>}
        {error && <ErrorText>{error}</ErrorText>}
        <SubmitButton disabled={disabled} type="submit">
          {submitting ? 'Создаём…' : 'Зарегистрироваться'}
        </SubmitButton>
      </form>
      <FormHint>Зарегистрируйтесь, чтобы сохранять историю интервью</FormHint>
    </Card>
  );
};
