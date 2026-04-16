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

// ─── Setup form ────────────────────────────────────────────────────────────────

const fadeUp = keyframes`
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
`;

const SetupMain = styled.main`
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 28px 20px 40px;
  width: 100%;
  box-sizing: border-box;
`;

const SetupCard = styled.div`
  width: 100%;
  max-width: 520px;
  margin: 0 auto;
  padding: 36px 32px 32px;
  border-radius: 20px;
  font-family: 'Inter', ui-sans-serif, sans-serif;
  font-size: 16px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow:
    0 24px 48px rgba(0, 0, 0, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(16px);
  animation: ${fadeUp} 0.45s ease both;
  box-sizing: border-box;
`;

const SetupEyebrow = styled.p`
  margin: 0 0 10px;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #a5b4fc;
`;

const SetupTitle = styled.h2`
  margin: 0 0 10px;
  font-family: 'Inter', ui-sans-serif, sans-serif;
  font-size: clamp(1.5rem, 4vw, 1.75rem);
  font-weight: 800;
  color: #f8fafc;
  letter-spacing: -0.03em;
  line-height: 1.25;
`;

const SetupSubtitle = styled.p`
  margin: 0 0 32px;
  font-size: 17px;
  line-height: 1.6;
  color: #94a3b8;
`;

const FieldStack = styled.div`
  display: flex;
  flex-direction: column;
  gap: 24px;
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
`;

const FieldBlock = styled.div`
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
`;

const TextAreaLabel = styled.label`
  display: block;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #cbd5e1;
  margin-bottom: 10px;
`;

const TextArea = styled.textarea`
  display: block;
  width: 100%;
  min-width: 0;
  min-height: 108px;
  padding: 14px 16px;
  font-size: 16px;
  line-height: 1.5;
  color: #f1f5f9;
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  outline: none;
  resize: vertical;
  box-sizing: border-box;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;

  &::placeholder {
    color: #64748b;
  }

  &:focus {
    border-color: rgba(129, 140, 248, 0.65);
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
  }

  &:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
`;

const LimitSection = styled.div`
  padding: 20px 18px;
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.06);
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
`;

const LimitSectionTitle = styled.div`
  font-size: 16px;
  font-weight: 700;
  color: #f1f5f9;
  letter-spacing: -0.01em;
  margin-bottom: 10px;
`;

const LimitSectionLead = styled.div`
  font-size: 14px;
  line-height: 1.5;
  color: #94a3b8;
  margin-bottom: 18px;
`;

const CheckboxRow = styled.label`
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  user-select: none;
`;

const HiddenCheckbox = styled.input`
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
`;

const CheckboxVisual = styled.span<{ $checked: boolean }>`
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  margin-top: 0;
  border-radius: 7px;
  border: 2px solid ${({ $checked }) =>
    $checked ? '#818cf8' : 'rgba(148, 163, 184, 0.45)'};
  background: ${({ $checked }) =>
    $checked ? 'linear-gradient(135deg, #6366f1, #4f46e5)' : 'rgba(15, 23, 42, 0.6)'};
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.2s ease, background 0.2s ease;

  &::after {
    content: '';
    display: ${({ $checked }) => ($checked ? 'block' : 'none')};
    width: 6px;
    height: 10px;
    border: solid white;
    border-width: 0 2px 2px 0;
    transform: rotate(45deg) translate(-1px, -1px);
  }
`;

const CheckboxText = styled.span`
  font-size: 13px;
  line-height: 1.5;
  color: #e2e8f0;
`;

const NumberFieldWrap = styled.div`
  width: 100%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 0;
`;

const NumberFieldLabel = styled.label`
  display: block;
  font-size: 16px;
  line-height: 1.25;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: #e2e8f0;
  margin: 0 0 10px;
`;

const NumberInput = styled.input`
  display: block;
  width: 100%;
  min-width: 0;
  margin-top: 5px;
  padding: 13px 16px;
  font-size: 16px;
  color: #f1f5f9;
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
  -moz-appearance: textfield;

  &::-webkit-outer-spin-button,
  &::-webkit-inner-spin-button {
    -webkit-appearance: none;
    margin: 0;
  }

  &::placeholder {
    color: #64748b;
  }

  &:focus {
    border-color: rgba(129, 140, 248, 0.65);
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
  }

  &:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
`;

const FieldHint = styled.span`
  display: block;
  font-size: 14px;
  line-height: 1.45;
  color: #64748b;
`;

const FieldError = styled.span`
  display: block;
  margin-top: 8px;
  font-size: 15px;
  font-weight: 500;
  color: #fca5a5;
`;

const SetupActions = styled.div`
  margin-top: 32px;
  display: flex;
  flex-direction: column;
  gap: 12px;
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

const EmptyChat = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: 14px;
  color: #94a3b8;
  animation: ${fadeUp} 0.4s ease;
  padding: 48px 16px;
  text-align: center;
  max-width: 420px;
  margin: 0 auto;
  box-sizing: border-box;

  span:first-child {
    font-size: 44px;
  }
`;

const EmptyChatPrimary = styled.span`
  font-family: 'Inter', ui-sans-serif, sans-serif;
  font-size: 17px;
  line-height: 1.5;
  color: #e2e8f0;
`;

const EmptyChatHint = styled.span`
  font-family: 'Inter', ui-sans-serif, sans-serif;
  font-size: 14px;
  line-height: 1.55;
  color: #64748b;
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
    0%,
    100% {
      opacity: 0.4;
    }
    50% {
      opacity: 1;
    }
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

const TextFieldLabel = styled.label`
  display: block;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #cbd5e1;
  margin-bottom: 10px;
`;

const TextFieldInput = styled.input`
  display: block;
  width: 100%;
  min-width: 0;
  padding: 13px 16px;
  font-size: 16px;
  color: #f1f5f9;
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;

  &::placeholder {
    color: #64748b;
  }

  &:focus {
    border-color: rgba(129, 140, 248, 0.65);
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
  }
`;

// ─── Component ────────────────────────────────────────────────────────────────

type ConnectionStatus = 'idle' | 'connecting' | 'live' | 'error';

type StartPayload = {
  userName?: string;
  userInfo?: string;
  maxNumberQuestions?: number;
  displayName: string;
  displayInfo: string;
};

export const InterviewPage: React.FC = () => {
  const { sessionId: journalistId } = useParams<{ sessionId: string }>();
  const messages = useUnit($messages);
  const currentSession = useUnit($currentSession);
  const navigate = useNavigate();
  const [answer, setAnswer] = useState('');
  const [status, setStatus] = useState<ConnectionStatus>('idle');
  const [hasStarted, setHasStarted] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const [userName, setUserName] = useState('');
  const [userInfo, setUserInfo] = useState('');
  const [unlimitedQuestions, setUnlimitedQuestions] = useState(false);
  const [questionCountRaw, setQuestionCountRaw] = useState('');
  const [submitAttempted, setSubmitAttempted] = useState(false);

  const startPayloadRef = useRef<StartPayload | null>(null);
  const sessionMetaRef = useRef<{ displayName: string; displayInfo: string }>({
    displayName: 'Гость',
    displayInfo: '',
  });
  const emittedStartRef = useRef(false);
  const wiredSessionIdRef = useRef<string | null>(null);
  const [showSlowHint, setShowSlowHint] = useState(false);

  useEffect(() => {
    clearSession();
  }, []);

  const trimmedCount = questionCountRaw.trim();
  const parsedCount = unlimitedQuestions ? NaN : parseInt(trimmedCount, 10);
  const showZeroError =
    !unlimitedQuestions && trimmedCount !== '' && !Number.isNaN(parsedCount) && parsedCount === 0;
  const showEmptyCountError =
    submitAttempted && !unlimitedQuestions && trimmedCount === '';
  const showInvalidCountError =
    submitAttempted &&
    !unlimitedQuestions &&
    trimmedCount !== '' &&
    (Number.isNaN(parsedCount) || parsedCount < 1);

  useEffect(() => {
    if (!journalistId || !hasStarted) return;

    const p = startPayloadRef.current;
    if (!p) return;

    const handleQuestion = ({ question, sessionId }: { question: string; sessionId: string }) => {
      setStatus('live');
      const meta = sessionMetaRef.current;
      if (wiredSessionIdRef.current !== sessionId) {
        wiredSessionIdRef.current = sessionId;
        setCurrentSession({
          id: sessionId,
          journalistId: journalistId!,
          userName: meta.displayName,
          userInfo: meta.displayInfo,
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

    const handleConnectError = (err: Error) => {
      setStatus('error');
      addMessage({
        id: `${Date.now()}-ws-err`,
        role: 'assistant',
        content: `⚠️ Не удалось подключиться к серверу: ${err.message}. Проверьте адрес WebSocket (VITE_WS_URL) и что бэкенд запущен.`,
        timestamp: new Date(),
      });
    };

    socketManager.on('interview:question', handleQuestion);
    socketManager.on('interview:error', handleError);
    socketManager.onConnectError(handleConnectError);

    setStatus('connecting');
    socketManager.whenConnected(() => {
      if (emittedStartRef.current) return;
      emittedStartRef.current = true;
      socketManager.emit('interview:start', {
        journalistId: journalistId!,
        userName: p.userName,
        userInfo: p.userInfo,
        maxNumberQuestions: p.maxNumberQuestions,
      });
    });

    return () => {
      socketManager.off('interview:question', handleQuestion);
      socketManager.off('interview:error', handleError);
      socketManager.offConnectError(handleConnectError);
    };
  }, [journalistId, hasStarted]);

  useEffect(() => {
    if (!hasStarted || status !== 'connecting' || messages.length > 0) {
      setShowSlowHint(false);
      return;
    }
    const t = window.setTimeout(() => setShowSlowHint(true), 25000);
    return () => {
      window.clearTimeout(t);
      setShowSlowHint(false);
    };
  }, [hasStarted, status, messages.length]);

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

  const handleBackFromSetup = () => {
    navigate('/');
  };

  const handleStartInterview = (e: React.FormEvent) => {
    e.preventDefault();
    if (!journalistId) return;

    if (!unlimitedQuestions) {
      setSubmitAttempted(true);
      if (trimmedCount === '') return;
      if (Number.isNaN(parsedCount) || parsedCount < 1) return;
    }

    const displayName = userName.trim() || 'Гость';
    const displayInfo = userInfo.trim();
    const payload: StartPayload = {
      displayName,
      displayInfo,
      userName: userName.trim() || undefined,
      userInfo: displayInfo || undefined,
      maxNumberQuestions: unlimitedQuestions ? undefined : parsedCount,
    };
    startPayloadRef.current = payload;
    sessionMetaRef.current = { displayName, displayInfo };
    setHasStarted(true);
  };

  const statusLabel: Record<ConnectionStatus, string> = {
    idle: 'Подготовка',
    connecting: 'Подключение...',
    live: 'Live',
    error: 'Ошибка',
  };

  const showSetup = !hasStarted;

  return (
    <PageWrapper>
      <Header>
        <HeaderLeft>
          <BackButton
            onClick={showSetup ? handleBackFromSetup : handleComplete}
            title={showSetup ? 'Назад' : 'Завершить и выйти'}
          >
            ←
          </BackButton>
          <HeaderTitle>{showSetup ? 'Перед интервью' : 'Интервью'}</HeaderTitle>
        </HeaderLeft>
        <SessionBadge $isError={status === 'error'}>
          {status === 'connecting' && <ConnectingDot />}
          {statusLabel[status]}
        </SessionBadge>
      </Header>

      {showSetup ? (
        <SetupMain>
          <SetupCard as="form" onSubmit={handleStartInterview}>
            <SetupEyebrow>Настройка</SetupEyebrow>
            <SetupTitle>Расскажите о себе</SetupTitle>
            <SetupSubtitle>
              Эти данные передаются журналисту, чтобы диалог был персональным и по делу.
            </SetupSubtitle>

            <FieldStack>
              <FieldBlock>
                <TextFieldLabel htmlFor="user-name">Представьтесь! Как вас зовут?</TextFieldLabel>
                <TextFieldInput
                  id="user-name"
                  type="text"
                  placeholder="Введите имя"
                  value={userName}
                  onChange={(e) => setUserName(e.target.value)}
                  autoComplete="name"
                />
              </FieldBlock>

              <FieldBlock>
                <TextAreaLabel htmlFor="user-info">Немного о себе</TextAreaLabel>
                <TextArea
                  id="user-info"
                  placeholder="Кем работаете, что хотите обсудить, опыт — по желанию"
                  value={userInfo}
                  onChange={(e) => setUserInfo(e.target.value)}
                  rows={4}
                />
                <FieldHint>Можно оставить пустым — тогда контекст будет общим.</FieldHint>
              </FieldBlock>

              <FieldBlock>
                <TextAreaLabel>Длина интервью</TextAreaLabel>
                <FieldHint>Можно ограничить количество вопросов или оставить без ограничений.</FieldHint>
              </FieldBlock>

              <LimitSection>
                <NumberFieldWrap>
                  <NumberFieldLabel htmlFor="q-count">Введите желаемое число вопросов</NumberFieldLabel>
                  <NumberInput
                    id="q-count"
                    type="number"
                    inputMode="numeric"
                    min={1}
                    step={1}
                    placeholder="Например, 5"
                    value={questionCountRaw}
                    disabled={unlimitedQuestions}
                    onChange={(e) => {
                      setQuestionCountRaw(e.target.value);
                      setSubmitAttempted(false);
                    }}
                  />
                  {showZeroError && <FieldError>Число должно быть больше 0</FieldError>}
                  {showEmptyCountError && (
                    <FieldError>Укажите количество вопросов или включите режим без ограничений</FieldError>
                  )}
                  {showInvalidCountError && !showZeroError && (
                    <FieldError>Введите целое число не меньше 1</FieldError>
                  )}
                  {!unlimitedQuestions &&
                    !showZeroError &&
                    !showEmptyCountError &&
                    !showInvalidCountError && <FieldHint>Можно задать любое целое число от 1 и выше.</FieldHint>}
                </NumberFieldWrap>

                <CheckboxRow>
                  <HiddenCheckbox
                    type="checkbox"
                    checked={unlimitedQuestions}
                    onChange={(ev) => {
                      setUnlimitedQuestions(ev.target.checked);
                      if (ev.target.checked) setSubmitAttempted(false);
                    }}
                  />
                  <CheckboxVisual $checked={unlimitedQuestions} aria-hidden />
                  <CheckboxText>Без ограничения по числу вопросов</CheckboxText>
                </CheckboxRow>
              </LimitSection>
            </FieldStack>

            <SetupActions>
              <Button type="submit" size="lg" variant="primary">
                Начать интервью
              </Button>
            </SetupActions>
          </SetupCard>
        </SetupMain>
      ) : (
        <>
          <ChatArea>
            {messages.length === 0 ? (
              <EmptyChat>
                <span>🎙</span>
                <EmptyChatPrimary>
                  {status === 'connecting'
                    ? 'Подключаемся к журналисту...'
                    : status === 'error'
                      ? 'Не удалось получить ответ'
                      : 'Интервью начнётся с первого вопроса'}
                </EmptyChatPrimary>
                {status === 'connecting' && showSlowHint && (
                  <EmptyChatHint>
                    Долго нет первого вопроса? Чаще всего не запущен или не настроен AI-сервис (ключ OpenAI,
                    Ollama и т.д.), либо бэкенд ждёт ответа от модели.
                  </EmptyChatHint>
                )}
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
        </>
      )}
    </PageWrapper>
  );
};
