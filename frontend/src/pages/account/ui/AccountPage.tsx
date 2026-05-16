import React, { useEffect } from 'react';
import { useUnit } from 'effector-react';
import { Link } from 'react-router-dom';
import styled from 'styled-components';
import { $user, logoutFx } from '~/entities/user';
import {
  $myInterviews,
  $myInterviewsError,
  $myInterviewsLoading,
  loadMyInterviews,
} from '../model';

const Page = styled.div`
  min-height: 100vh;
  background: linear-gradient(160deg, #0f0c29, #302b63, #24243e);
  padding: 28px 24px 64px;
`;

const Top = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  max-width: 960px;
  margin: 0 auto 18px;
`;

const TopBar = styled.div`
  width: 100%;
  margin: 0 0 16px;
  display: flex;
  justify-content: flex-start;
`;

const BackLink = styled(Link)`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: 'Inter', ui-sans-serif, sans-serif;
  font-size: 14px;
  color: #cbd5e1;
  text-decoration: none;
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(2, 6, 23, 0.25);
  cursor: pointer;
  width: fit-content;

  &:hover {
    border-color: rgba(129, 140, 248, 0.45);
    background: rgba(99, 102, 241, 0.08);
    color: #e2e8f0;
  }
`;

const Title = styled.h1`
  margin: 0;
  color: #fff;
  font-family: 'Inter', ui-sans-serif, sans-serif;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -0.02em;
`;

const Actions = styled.div`
  display: flex;
  gap: 10px;
  align-items: center;
  color: #cbd5e1;
  font-family: 'Inter', ui-sans-serif, sans-serif;
  font-size: 13px;
`;

const Button = styled.button`
  height: 36px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(2, 6, 23, 0.35);
  color: #e2e8f0;
  cursor: pointer;
`;

const Card = styled.div`
  max-width: 960px;
  margin: 0 auto;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  padding: 22px;
  backdrop-filter: blur(10px);
`;

const List = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
`;

const Item = styled(Link)`
  text-decoration: none;
  padding: 16px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(2, 6, 23, 0.25);
  color: #e2e8f0;
  transition: transform 0.2s ease, border-color 0.2s ease, background 0.2s ease;

  &:hover {
    transform: translateY(-2px);
    border-color: rgba(129, 140, 248, 0.45);
    background: rgba(99, 102, 241, 0.08);
  }
`;

const Muted = styled.div`
  color: #94a3b8;
  font-size: 13px;
  font-family: 'Inter', ui-sans-serif, sans-serif;
`;

const ErrorBox = styled.div`
  color: #fca5a5;
  font-family: 'Inter', ui-sans-serif, sans-serif;
  font-size: 13px;
`;

export const AccountPage: React.FC = () => {
  const user = useUnit($user);
  const items = useUnit($myInterviews);
  const loading = useUnit($myInterviewsLoading);
  const error = useUnit($myInterviewsError);

  useEffect(() => {
    loadMyInterviews();
  }, []);

  return (
    <Page>
      <TopBar>
        <BackLink to="/">← Назад</BackLink>
      </TopBar>
      <Top>
        <Title>Аккаунт</Title>
        <Actions>
          <span>{user?.email}</span>
          <Button
            onClick={async () => {
              await logoutFx();
              window.location.assign('/');
            }}
          >
            Выйти
          </Button>
        </Actions>
      </Top>

      <Card>
        {loading && <Muted>Загрузка интервью…</Muted>}
        {error && <ErrorBox>{error}</ErrorBox>}
        {!loading && !error && items.length === 0 && <Muted>У вас пока нет интервью.</Muted>}

        {!loading && !error && items.length > 0 && (
          <List>
            {items.map((s) => (
              <Item key={s.id} to={`/account/interviews/${s.id}`}>
                <div style={{ fontWeight: 700, marginBottom: 6 }}>{s.userName}</div>
                <Muted>
                  {new Date(s.createdAt).toLocaleString()} · {s.status}
                </Muted>
              </Item>
            ))}
          </List>
        )}
      </Card>
    </Page>
  );
};

