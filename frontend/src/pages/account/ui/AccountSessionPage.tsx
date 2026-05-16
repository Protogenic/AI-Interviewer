import React, { useEffect } from 'react';
import { useUnit } from 'effector-react';
import { Link, useParams } from 'react-router-dom';
import styled from 'styled-components';
import { $selectedHistory, $selectedSession, fetchHistoryFx, fetchSessionFx } from '../model';

const Page = styled.div`
  min-height: 100vh;
  background: linear-gradient(160deg, #0f0c29, #302b63, #24243e);
  padding: 28px 24px 64px;
`;

const Wrap = styled.div`
  max-width: 960px;
  margin: 0 auto;
`;

const Top = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
`;

const Title = styled.h1`
  margin: 0;
  color: #fff;
  font-family: 'Inter', ui-sans-serif, sans-serif;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -0.02em;
`;

const Back = styled(Link)`
  color: #cbd5e1;
  text-decoration: none;
  font-family: 'Inter', ui-sans-serif, sans-serif;
  font-size: 13px;
`;

const Card = styled.div`
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  padding: 22px;
  backdrop-filter: blur(10px);
`;

const Bubble = styled.div<{ $role: 'interviewer' | 'guest' }>`
  max-width: 760px;
  padding: 14px 16px;
  border-radius: 16px;
  margin: 10px 0;
  background: ${({ $role }) =>
    $role === 'guest' ? 'rgba(99, 102, 241, 0.16)' : 'rgba(255, 255, 255, 0.06)'};
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #e2e8f0;
  font-family: 'Inter', ui-sans-serif, sans-serif;
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
`;

const Muted = styled.div`
  color: #94a3b8;
  font-size: 13px;
  font-family: 'Inter', ui-sans-serif, sans-serif;
`;

export const AccountSessionPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const sessionPending = useUnit(fetchSessionFx.pending);
  const historyPending = useUnit(fetchHistoryFx.pending);
  const session = useUnit($selectedSession);
  const history = useUnit($selectedHistory);

  useEffect(() => {
    if (!id) return;
    fetchSessionFx(id);
    fetchHistoryFx(id);
  }, [id]);

  return (
    <Page>
      <Wrap>
        <Top>
          <Title>Сессия</Title>
          <Back to="/account">← Назад</Back>
        </Top>

        <Card>
          {(sessionPending || historyPending) && <Muted>Загрузка…</Muted>}

          {session && (
            <Muted style={{ marginBottom: 12 }}>
              {new Date(session.createdAt).toLocaleString()} · {session.status}
            </Muted>
          )}

          {history?.length ? (
            history.map((m) => (
              <Bubble key={m.id} $role={m.role}>
                {m.content}
              </Bubble>
            ))
          ) : (
            !historyPending && <Muted>История пуста.</Muted>
          )}
        </Card>
      </Wrap>
    </Page>
  );
};

