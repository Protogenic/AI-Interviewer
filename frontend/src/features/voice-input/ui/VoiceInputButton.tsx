import React from 'react';
import styled, { css, keyframes } from 'styled-components';

const recordingPulse = keyframes`
  0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.45); }
  50%       { box-shadow: 0 0 0 7px rgba(239, 68, 68, 0); }
`;

const armSpin = keyframes`
  to { transform: rotate(360deg); }
`;

const Wrap = styled.span`
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  flex-shrink: 0;
`;

const ArmRing = styled.span`
  position: absolute;
  inset: -3px;
  border-radius: 11px;
  border: 2px solid transparent;
  border-top-color: #6366f1;
  border-right-color: rgba(99, 102, 241, 0.35);
  animation: ${armSpin} 0.75s linear infinite;
  pointer-events: none;
`;

const Btn = styled.button<{ $recording: boolean; $pulse: boolean }>`
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background: ${({ $recording }) =>
    $recording ? 'rgba(239, 68, 68, 0.12)' : 'rgba(99, 102, 241, 0.08)'};
  color: ${({ $recording }) => ($recording ? '#ef4444' : '#6366f1')};
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition:
    background 0.2s ease,
    color 0.2s ease;
  flex-shrink: 0;

  ${({ $pulse }) =>
    $pulse &&
    css`
      animation: ${recordingPulse} 1.4s ease-in-out infinite;
    `}

  &:hover {
    background: ${({ $recording }) =>
      $recording ? 'rgba(239, 68, 68, 0.2)' : 'rgba(99, 102, 241, 0.15)'};
    color: ${({ $recording }) => ($recording ? '#dc2626' : '#4f46e5')};
  }

  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
    animation: none;
  }

  svg {
    width: 17px;
    height: 17px;
    flex-shrink: 0;
  }
`;

interface VoiceInputButtonProps {
  isRecording: boolean;
  /** Подключение микрофона / старт MediaRecorder */
  isArming?: boolean;
  onClick: () => void;
  disabled?: boolean;
}

export const VoiceInputButton: React.FC<VoiceInputButtonProps> = ({
  isRecording,
  isArming = false,
  onClick,
  disabled,
}) => {
  const showArmRing = isArming && isRecording;
  return (
    <Wrap>
      {showArmRing && <ArmRing aria-hidden />}
      <Btn
        type="button"
        $recording={isRecording}
        $pulse={isRecording && !showArmRing}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          onClick();
        }}
        disabled={disabled}
        title={
          showArmRing
            ? 'Подключение микрофона…'
            : isRecording
              ? 'Остановить запись'
              : 'Голосовой ввод'
        }
        aria-label={
          showArmRing
            ? 'Подключение микрофона'
            : isRecording
              ? 'Остановить запись'
              : 'Начать запись голоса'
        }
      >
        {isRecording ? (
          <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden>
            <rect x="5" y="5" width="14" height="14" rx="2.5" />
          </svg>
        ) : (
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden
          >
            <path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z" />
            <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
            <line x1="12" y1="19" x2="12" y2="22" />
            <line x1="8" y1="22" x2="16" y2="22" />
          </svg>
        )}
      </Btn>
    </Wrap>
  );
};
