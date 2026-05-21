import React, { useEffect, useMemo, useRef, useState } from 'react';
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
import { $journalists, loadJournalists } from '~/entities/journalist';
import { answerSent } from '~/features/send-answer/model';
import { useVoiceRecorder, VoiceInputButton, AudioPreview } from '~/features/voice-input';
import { socketManager } from '~/shared/api/socket';
import { transcribeAudio } from '~/shared/api/stt';
import { ChatBubble } from '~/shared/ui/ChatBubble/ChatBubble';
import { Button } from '~/shared/ui/Button/Button';
import { Input } from '~/shared/ui/Input/Input';
import { Modal } from '~/shared/ui/Modal';

// ─── Layout ───────────────────────────────────────────────────────────────────

const PageWrapper = styled.div`
  min-height: 100vh;
  background: linear-gradient(160deg, #0f0c29, #302b63, #24243e);
  display: flex;
  flex-direction: column;
  font-family: 'Inter', ui-sans-serif, sans-serif;
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

const JournalistBadge = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #e2e8f0;
`;

const JournalistAvatar = styled.div`
  width: 28px;
  height: 28px;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #a855f7);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 800;
  color: #ffffff;
  flex-shrink: 0;
  letter-spacing: -0.02em;
`;

const JournalistName = styled.span`
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
  white-space: nowrap;
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
  padding: 32px 24px 140px;
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
  position: sticky;
  bottom: 0;
  z-index: 9;
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

const VoiceError = styled.div`
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.22);
  color: #fecaca;
  font-size: 13px;
  line-height: 1.45;
`;

const SttError = styled(VoiceError)`
  background: rgba(245, 158, 11, 0.12);
  border-color: rgba(245, 158, 11, 0.22);
  color: #fde68a;
`;

const AnswerCounter = styled.span<{ $isLimitReached: boolean }>`
  display: block;
  margin-top: 6px;
  font-size: 13px;
  color: ${({ $isLimitReached }) => ($isLimitReached ? '#fbbf24' : '#94a3b8')};
  text-align: right;
`;

const GeneratingHint = styled.div`
  align-self: flex-start;
  color: #c7d2fe;
  font-size: 13px;
  line-height: 1.4;
`;

const ModalText = styled.p`
  margin: 0;
  font-size: 15px;
  line-height: 1.6;
  color: #cbd5e1;
`;

// ─── Component ────────────────────────────────────────────────────────────────

type ConnectionStatus = 'idle' | 'connecting' | 'live' | 'error';

const ANSWER_MAX_LENGTH = 2000;
const INTERVIEW_TOPIC_MAX_LENGTH = 1000;

type StartPayload = {
  userName?: string;
  userInfo?: string;
  interviewTopic?: string;
  maxNumberQuestions?: number;
  displayName: string;
  displayInfo: string;
};

export const InterviewPage: React.FC = () => {
  const { sessionId: journalistId } = useParams<{ sessionId: string }>();
  const messages = useUnit($messages);
  const currentSession = useUnit($currentSession);
  const journalists = useUnit($journalists);
  const navigate = useNavigate();
  const [answer, setAnswer] = useState('');
  const [status, setStatus] = useState<ConnectionStatus>('idle');
  const [hasStarted, setHasStarted] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const [userName, setUserName] = useState('');
  const [userInfo, setUserInfo] = useState('');
  const [interviewTopic, setInterviewTopic] = useState('');
  const [unlimitedQuestions, setUnlimitedQuestions] = useState(false);
  const [questionCountRaw, setQuestionCountRaw] = useState('');
  const [submitAttempted, setSubmitAttempted] = useState(false);
  const [sttError, setSttError] = useState<string | null>(null);
  const [recognizedText, setRecognizedText] = useState('');
  const [isVoiceRecognizing, setIsVoiceRecognizing] = useState(false);
  const [answersSentCount, setAnswersSentCount] = useState(0);
  const [showLimitReachedModal, setShowLimitReachedModal] = useState(false);
  const [isAwaitingNextQuestion, setIsAwaitingNextQuestion] = useState(false);
  const [generatingDots, setGeneratingDots] = useState('.');

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

  useEffect(() => {
    if (journalists.length === 0) loadJournalists();
  }, [journalists.length]);

  const journalist = useMemo(() => {
    if (!journalistId) return null;
    return journalists.find((j) => j.id === journalistId) ?? null;
  }, [journalists, journalistId]);

  const journalistInitials = useMemo(() => {
    const name = journalist?.name?.trim();
    if (!name) return 'AI';
    return name
      .split(/\s+/)
      .map((w) => w[0])
      .slice(0, 2)
      .join('')
      .toUpperCase();
  }, [journalist?.name]);

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
  const activeQuestionLimit = !unlimitedQuestions ? parsedCount : undefined;
  const answerCharsCount = answer.length;
  const isAnswerLimitReached = answerCharsCount >= ANSWER_MAX_LENGTH;

  useEffect(() => {
    if (!journalistId || !hasStarted) return;

    const p = startPayloadRef.current;
    if (!p) return;

    const handleQuestion = ({ question, sessionId, audio }: { question: string; sessionId: string; audio: string | null }) => {
      setIsAwaitingNextQuestion(false);
      if (audio) {
        const bytes = Uint8Array.from(atob(audio), c => c.charCodeAt(0));
        const url = URL.createObjectURL(new Blob([bytes], { type: 'audio/wav' }));
        const player = new Audio(url);
        player.onended = () => URL.revokeObjectURL(url);
        player.play().catch(() => {});
      }
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
        role: 'interviewer',
        content: question,
        timestamp: new Date(),
      });
    };

    const handleError = ({ message }: { message: string }) => {
      setIsAwaitingNextQuestion(false);
      setStatus('error');
      addMessage({
        id: `${Date.now()}-err`,
        role: 'interviewer',
        content: `⚠️ ${message}`,
        timestamp: new Date(),
      });
    };

    const handleConnectError = (err: Error) => {
      setIsAwaitingNextQuestion(false);
      setStatus('error');
      addMessage({
        id: `${Date.now()}-ws-err`,
        role: 'interviewer',
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
        interviewTopic: p.interviewTopic,
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

  useEffect(() => {
    if (!isAwaitingNextQuestion || showLimitReachedModal) {
      setGeneratingDots('.');
      return;
    }

    const intervalId = window.setInterval(() => {
      setGeneratingDots((prev) => (prev.length >= 3 ? '.' : `${prev}.`));
    }, 450);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [isAwaitingNextQuestion, showLimitReachedModal]);

  const {
    state: voiceState,
    audioUrl,
    transcript,
    error: voiceError,
    isArmingMic,
    startRecording,
    stopRecording,
    clearRecording,
    isSupported: isVoiceSupported,
  } = useVoiceRecorder();

  useEffect(() => {
    if (voiceState === 'done') return;
    setRecognizedText('');
    setIsVoiceRecognizing(false);
    setSttError(null);
  }, [voiceState]);

  useEffect(() => {
    if (voiceState !== 'done' || !audioUrl) return;

    let cancelled = false;
    setIsVoiceRecognizing(true);
    setRecognizedText('');
    setSttError(null);

    (async () => {
      try {
        const blob = await fetch(audioUrl).then((r) => r.blob());
        const text = await transcribeAudio(blob, { language: 'ru', filename: 'voice.webm' });
        if (cancelled) return;
        setRecognizedText(text.trim().slice(0, ANSWER_MAX_LENGTH));
      } catch (e) {
        if (cancelled) return;
        setSttError(e instanceof Error ? e.message : 'Ошибка распознавания речи');
        setRecognizedText(transcript.trim().slice(0, ANSWER_MAX_LENGTH));
      } finally {
        if (!cancelled) setIsVoiceRecognizing(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [voiceState, audioUrl, transcript]);

  useEffect(() => {
    if (voiceState !== 'done' || audioUrl) return;

    setIsVoiceRecognizing(false);
    setRecognizedText(transcript.trim().slice(0, ANSWER_MAX_LENGTH));
    setSttError(null);
  }, [voiceState, audioUrl, transcript]);

  const handleSend = () => {
    const normalizedAnswer = answer.slice(0, ANSWER_MAX_LENGTH);
    if (!normalizedAnswer.trim()) return;

    const nextAnswersCount = answersSentCount + 1;
    const reachedLimit =
      typeof activeQuestionLimit === 'number' &&
      Number.isFinite(activeQuestionLimit) &&
      activeQuestionLimit > 0 &&
      nextAnswersCount >= activeQuestionLimit;

    answerSent(normalizedAnswer);
    setAnswersSentCount(nextAnswersCount);
    setIsAwaitingNextQuestion(true);
    setAnswer('');

    if (reachedLimit) {
      setShowLimitReachedModal(true);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleMicClick = () => {
    if (voiceState === 'recording') {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const handleVoiceSend = () => {
    const text = recognizedText.trim().slice(0, ANSWER_MAX_LENGTH);
    if (!text || isVoiceRecognizing) return;

    const nextAnswersCount = answersSentCount + 1;
    const reachedLimit =
      typeof activeQuestionLimit === 'number' &&
      Number.isFinite(activeQuestionLimit) &&
      activeQuestionLimit > 0 &&
      nextAnswersCount >= activeQuestionLimit;

    answerSent(text);
    setAnswersSentCount(nextAnswersCount);
    setIsAwaitingNextQuestion(true);
    clearRecording();

    if (reachedLimit) {
      setShowLimitReachedModal(true);
    }
  };

  const handleComplete = () => {
    setShowLimitReachedModal(false);
    setIsAwaitingNextQuestion(false);
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
    const normalizedInterviewTopic = interviewTopic.trim().slice(0, INTERVIEW_TOPIC_MAX_LENGTH);
    const payload: StartPayload = {
      displayName,
      displayInfo,
      userName: userName.trim() || undefined,
      userInfo: displayInfo || undefined,
      interviewTopic: normalizedInterviewTopic || undefined,
      maxNumberQuestions: unlimitedQuestions ? undefined : parsedCount,
    };
    startPayloadRef.current = payload;
    sessionMetaRef.current = { displayName, displayInfo };
    setAnswersSentCount(0);
    setShowLimitReachedModal(false);
    setIsAwaitingNextQuestion(false);
    setHasStarted(true);
  };

  const handleContinueAfterLimit = () => {
    setShowLimitReachedModal(false);
    setUnlimitedQuestions(true);
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
          <JournalistBadge title={journalist?.name ?? 'Журналист'}>
            <JournalistAvatar aria-hidden>{journalistInitials}</JournalistAvatar>
            <JournalistName>{journalist?.name ?? 'Журналист'}</JournalistName>
          </JournalistBadge>
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
                <TextAreaLabel htmlFor="interview-topic">Тема интервью</TextAreaLabel>
                <TextArea
                  id="interview-topic"
                  placeholder="Например: frontend architecture, system design, подготовка к собеседованию"
                  value={interviewTopic}
                  onChange={(e) => setInterviewTopic(e.target.value.slice(0, INTERVIEW_TOPIC_MAX_LENGTH))}
                  rows={3}
                  maxLength={INTERVIEW_TOPIC_MAX_LENGTH}
                />
                <FieldHint>Необязательно. До {INTERVIEW_TOPIC_MAX_LENGTH} символов.</FieldHint>
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
              messages.map((msg) => (
                <ChatBubble key={msg.id} message={msg} interviewerLabel={journalistInitials} />
              ))
            )}
            <div ref={bottomRef} />
          </ChatArea>

          <InputPanel>
            <InputInner>
              {voiceError && <VoiceError>{voiceError}</VoiceError>}
              {sttError && <SttError>{sttError}</SttError>}
              {isAwaitingNextQuestion && !showLimitReachedModal && (
                <GeneratingHint>Готовлю следующий вопрос{generatingDots}</GeneratingHint>
              )}
              {voiceState === 'done' && (audioUrl || transcript.trim()) ? (
                <AudioPreview
                  audioUrl={audioUrl}
                  recognizedText={recognizedText}
                  isRecognizing={isVoiceRecognizing}
                  onDelete={clearRecording}
                  onSend={handleVoiceSend}
                />
              ) : (
                <>
                  <Input
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value.slice(0, ANSWER_MAX_LENGTH))}
                    onKeyDown={handleKeyDown}
                    placeholder={
                      voiceState === 'recording'
                        ? '🎙 Идёт запись...'
                        : 'Ваш ответ... (Enter для отправки)'
                    }
                    disabled={status === 'connecting' || voiceState === 'recording'}
                    maxLength={ANSWER_MAX_LENGTH}
                    rightSlot={
                      isVoiceSupported ? (
                        <VoiceInputButton
                          isRecording={voiceState === 'recording'}
                          isArming={voiceState === 'recording' && isArmingMic}
                          onClick={handleMicClick}
                          disabled={false}
                        />
                      ) : undefined
                    }
                  />
                  <AnswerCounter $isLimitReached={isAnswerLimitReached}>
                    Символов: {answerCharsCount}/{ANSWER_MAX_LENGTH}
                  </AnswerCounter>
                </>
              )}
              <ButtonRow>
                <Button variant="secondary" onClick={handleComplete}>
                  Завершить интервью
                </Button>
                {voiceState !== 'done' && (
                  <Button
                    onClick={handleSend}
                    disabled={!answer.trim() || status === 'connecting' || voiceState === 'recording'}
                  >
                    Отправить →
                  </Button>
                )}
              </ButtonRow>
            </InputInner>
          </InputPanel>
          <Modal
            open={Boolean(showLimitReachedModal && activeQuestionLimit)}
            title="Лимит вопросов достигнут"
            onClose={handleContinueAfterLimit}
            closeOnBackdrop={false}
            actions={
              <>
                <Button variant="secondary" onClick={handleContinueAfterLimit}>
                  Нет, продолжить интервью
                </Button>
                <Button onClick={handleComplete}>Да</Button>
              </>
            }
          >
            <ModalText>
              Вы ограничивали интервью (количество вопросов - {activeQuestionLimit}). Желаете завершить?
            </ModalText>
          </Modal>
        </>
      )}
    </PageWrapper>
  );
};
