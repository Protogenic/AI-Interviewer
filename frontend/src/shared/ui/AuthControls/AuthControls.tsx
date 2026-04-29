import React from 'react';
import { useUnit } from 'effector-react';
import { Link } from 'react-router-dom';
import styled from 'styled-components';
import { $user, logoutFx } from '~/entities/user';

const Wrap = styled.div`
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: 'Inter', ui-sans-serif, sans-serif;
  font-size: 13px;
  color: #cbd5e1;
`;

const NavLink = styled(Link)`
  color: #cbd5e1;
  text-decoration: none;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.10);
  background: rgba(2, 6, 23, 0.25);

  &:hover {
    border-color: rgba(129, 140, 248, 0.45);
    background: rgba(99, 102, 241, 0.08);
  }
`;

const Button = styled.button`
  height: 34px;
  padding: 0 10px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.10);
  background: rgba(2, 6, 23, 0.25);
  color: #e2e8f0;
  cursor: pointer;

  &:hover {
    border-color: rgba(129, 140, 248, 0.45);
    background: rgba(99, 102, 241, 0.08);
  }
`;

export const AuthControls: React.FC = () => {
  const user = useUnit($user);

  if (user) {
    return (
      <Wrap>
        <span>{user.email}</span>
        <NavLink to="/account">Аккаунт</NavLink>
        <Button
          onClick={async () => {
            await logoutFx();
            window.location.assign('/');
          }}
        >
          Выйти
        </Button>
      </Wrap>
    );
  }

  return (
    <Wrap>
      <NavLink to="/login">Войти</NavLink>
      <NavLink to="/register">Регистрация</NavLink>
    </Wrap>
  );
};

