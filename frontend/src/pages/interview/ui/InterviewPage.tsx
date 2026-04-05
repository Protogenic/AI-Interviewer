import React, { useEffect, useRef, useState } from 'react';
import { useUnit } from 'effector-react';
import { useParams, useNavigate } from 'react-router-dom';
import styled, { keyframes } from 'styled-components';
import {
  $messages,
  $currentSession,
  addMessage,
  setCurrentSession,
  clearSession,
} from '~/entities/session';
import { answerSent } from '~/features/send-answer/model';
import { socketManager } from '~/shared/api/socket';
import { ChatBubble } from '~/shared/ui/ChatBubble/ChatBubble';
import { Button } from '~/shared/ui/Button/Button';
import { Input } from '~/shared/ui/Input/Input';

// ─── Layout ───────────────────────────────────────────────────────────────────

const PageWrapper = styled.div`
  min-height: 100vh;
  background: linear-gradient(160deg, #0f0c29, #302b63, #24243e);
  display: flex;
  flex-direction: column;
`;

const Header = styled.header`
  padding: 18px 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(8px);
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgba(15, 12, 41, 0.7);
`;

const HeaderLeft = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
`;

const BackButton = styled.button`
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #94a3b8;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.12);
    color: #f1f5f9;
  }
`;

const HeaderTitle = styled.h1`
  font-family: 'Inter', ui-sans-serif, sans-serif;
  font-size: 17px;
  font-weight: 700;
  color: #f1f5f9;
  letter-spacing: -0.02em;
`;

const SessionBadge = styled.span<{ $isError?: boolean }>`
  padding: 4px 10px;
  background: ${({ $isError }) =>
    $isError ? 'rgba(239, 68, 68, 0.2)' : 'rgba(99, 102, 241, 0.2)'};
  border: 1px solid ${({ $isError }) =>
    $isError ? 'rgba(239, 68, 68, 0.4)' : 'rgba(99, 102, 241, 0.3)'};
  border-radius: 100px;
  font-size: 11px;
  font-weight: 600;
  color: ${({ $isError }) => ($isError ? '#fca5a5' : '#a5b4fc')};
  letter-spacing: 0.06em;
  text-transform: uppercase;
`;

// ─── Chat area ────────────────────────────────────────────────────────────────

const ChatArea = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 32px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 780px;
  width: 100%;
  margin: 0 auto;
  box-sizing: border-box;

  &::-webkit-scrollbar {
    width: 6px;
  }
  &::-webkit-scrollbar-track {
    background: transparent;
  }
  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 3px;
  }
`;

const fadeUp = keyframes`
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
`;

const EmptyChat = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: 12px;
  color: #475569;
  animation: ${fadeUp} 0.4s ease;
  padding: 48px 0;

  span:first-child {
    font-size: 40px;
  }

  span:last-child {
    font-family: 'Inter', ui-sans-serif, sans-serif;
    font-size: 15px;
  }
`;

const ConnectingDot = styled.span`
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #6366f1;
  margin-right: 8px;
  animation: pulse 1.4s ease-in-out infinite;

  @keyframes pulse {
    0%, 100% { opacity: 0.4; }
    50% { opacity: 1; }
  }
`;

// ─── Input panel ──────────────────────────────────────────────────────────────

const InputPanel = styled.div`
  padding: 16px 24px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(15, 12, 41, 0.6);
  backdrop-filter: blur(8px);
`;

const InputInner = styled.div`
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 780px;
  margin: 0 auto;
`;

const ButtonRow = styled.div`
  display: flex;
  gap: 10px;
  justify-content: flex-end;
`;

// ─── Component ────────────────────────────────────────────────────────────────

type ConnectionStatus = 'connecting' | 'live' | 'error';

export const InterviewPage: React.FC = () => {
  // Параметр URL изначально содержит journalistId (до получения реального sessionId)
  const { sessionId: journalistId } = useParams<{ sessionId: string }>();
  const messages = useUnit($messages);
  const currentSession = useUnit($currentSession);
  const navigate = useNavigate();
  const [answer, setAnswer] = useState('');
  const [status, setStatus] = useState<ConnectionStatus>('connecting');
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!journalistId) return;

    socketManager.connect();
    socketManager.emit('interview:start', { journalistId });

    const handleQuestion = ({ question, sessionId }: { question: string; sessionId: string }) => {
      setStatus('live');
      // Сохраняем реальный sessionId в стор при первом вопросе
      if (!currentSession || currentSession.id !== sessionId) {
        setCurrentSession({
          id: sessionId,
          journalistId: journalistId!,
          userName: 'Гость',
          userInfo: '',
          status: 'active',
          createdAt: new Date().toISOString(),
        });
      }
      addMessage({
        id: `${Date.now()}-${Math.random()}`,
        role: 'assistant',
        content: question,
        timestamp: new Date(),
      });
    };

    const handleError = ({ message }: { message: string }) => {
      setStatus('error');
      addMessage({
        id: `${Date.now()}-err`,
        role: 'assistant',
        content: `⚠️ ${message}`,
        timestamp: new Date(),
      });
    };

    socketManager.on('interview:question', handleQuestion);
    socketManager.on('interview:error', handleError);

    return () => {
      socketManager.off('interview:question', handleQuestion);
      socketManager.off('interview:error', handleError);
    };
  }, [journalistId]);

  // Скролл к последнему сообщению
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (!answer.trim()) return;
    answerSent(answer);
    setAnswer('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleComplete = () => {
    if (currentSession?.id) {
      socketManager.emit('interview:complete', { sessionId: currentSession.id });
    }
    clearSession();
    navigate('/');
  };

  const statusLabel: Record<ConnectionStatus, string> = {
    connecting: 'Подключение...',
    live: 'Live',
    error: 'Ошибка',
  };

  return (
    <PageWrapper>
      <Header>
        <HeaderLeft>
          <BackButton onClick={handleComplete} title="Завершить и выйти">
            ←
          </BackButton>
          <HeaderTitle>Интервью</HeaderTitle>
        </HeaderLeft>
        <SessionBadge $isError={status === 'error'}>
          {status === 'connecting' && <ConnectingDot />}
          {statusLabel[status]}
        </SessionBadge>
      </Header>

      <ChatArea>
        {messages.length === 0 ? (
          <EmptyChat>
            <span>🎙</span>
            <span>
              {status === 'connecting'
                ? 'Подключаемся к журналисту...'
                : 'Интервью начнётся с первого вопроса'}
            </span>
          </EmptyChat>
        ) : (
          messages.map((msg) => <ChatBubble key={msg.id} message={msg} />)
        )}
        <div ref={bottomRef} />
      </ChatArea>

      <InputPanel>
        <InputInner>
          <Input
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ваш ответ... (Enter для отправки)"
            disabled={status === 'connecting'}
          />
          <ButtonRow>
            <Button variant="secondary" onClick={handleComplete}>
              Завершить интервью
            </Button>
            <Button
              onClick={handleSend}
              disabled={!answer.trim() || status === 'connecting'}
            >
              Отправить →
            </Button>
          </ButtonRow>
        </InputInner>
      </InputPanel>
    </PageWrapper>
  );
};
