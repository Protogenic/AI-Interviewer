import React from 'react';
import styled, { keyframes } from 'styled-components';

const slideIn = keyframes`
  from { opacity: 0; transform: translateY(5px); }
  to   { opacity: 1; transform: translateY(0); }
`;

const spin = keyframes`
  to {
    transform: rotate(360deg);
  }
`;

const Wrap = styled.div`
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 12px 12px;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.09);
  animation: ${slideIn} 0.22s ease both;
`;

const AudioRow = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
`;

const MicIcon = styled.span`
  font-size: 16px;
  flex-shrink: 0;
  line-height: 1;
`;

const StyledAudio = styled.audio`
  flex: 1;
  height: 30px;
  min-width: 0;

  &::-webkit-media-controls-panel {
    background: rgba(30, 41, 59, 0.95);
  }
  &::-webkit-media-controls-play-button,
  &::-webkit-media-controls-timeline,
  &::-webkit-media-controls-current-time-display,
  &::-webkit-media-controls-time-remaining-display {
    filter: invert(0.85);
  }
`;

const TranscriptRow = styled.div`
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.05);
`;

const TranscriptLabel = styled.span`
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #64748b;
  white-space: nowrap;
  margin-top: 1px;
  flex-shrink: 0;
`;

const TranscriptText = styled.p`
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  color: #cbd5e1;
  flex: 1;
  min-width: 0;
`;

const NoTranscriptText = styled.p`
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: #475569;
  font-style: italic;
  flex: 1;
`;

const RecognizingRow = styled.div`
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 8px;
  border-radius: 8px;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.15);
`;

const Spinner = styled.span`
  width: 18px;
  height: 18px;
  border: 2px solid rgba(129, 140, 248, 0.25);
  border-top-color: #a5b4fc;
  border-radius: 50%;
  animation: ${spin} 0.65s linear infinite;
  flex-shrink: 0;
`;

const RecognizingLabel = styled.span`
  font-size: 13px;
  font-weight: 500;
  color: #a5b4fc;
  line-height: 1.4;
`;

const ActionRow = styled.div`
  display: flex;
  gap: 8px;
  justify-content: flex-end;
`;

const Btn = styled.button<{ $variant: 'danger' | 'primary' }>`
  padding: 6px 14px;
  border-radius: 8px;
  border: 1px solid
    ${({ $variant }) =>
      $variant === 'danger' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(99, 102, 241, 0.4)'};
  background: ${({ $variant }) =>
    $variant === 'danger' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(99, 102, 241, 0.18)'};
  color: ${({ $variant }) => ($variant === 'danger' ? '#fca5a5' : '#a5b4fc')};
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  transition:
    background 0.18s ease,
    border-color 0.18s ease;

  &:hover:not(:disabled) {
    background: ${({ $variant }) =>
      $variant === 'danger' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(99, 102, 241, 0.3)'};
    border-color: ${({ $variant }) =>
      $variant === 'danger' ? 'rgba(239, 68, 68, 0.5)' : 'rgba(99, 102, 241, 0.6)'};
  }

  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
`;

interface AudioPreviewProps {
  audioUrl?: string | null;
  /** Текст после распознавания (сервер или Web Speech) */
  recognizedText: string;
  isRecognizing: boolean;
  onDelete: () => void;
  onSend: () => void;
}

export const AudioPreview: React.FC<AudioPreviewProps> = ({
  audioUrl,
  recognizedText,
  isRecognizing,
  onDelete,
  onSend,
}) => {
  const trimmed = recognizedText.trim();
  const sendDisabled = isRecognizing || !trimmed;

  return (
    <Wrap>
      <AudioRow>
        <MicIcon>🎙</MicIcon>
        {audioUrl ? (
          <StyledAudio src={audioUrl} controls preload="metadata" />
        ) : (
          <NoTranscriptText>
            Аудио недоступно в этом браузере — текст берётся из распознавания в браузере
          </NoTranscriptText>
        )}
      </AudioRow>

      <TranscriptRow>
        <TranscriptLabel>Текст</TranscriptLabel>
        {isRecognizing ? (
          <NoTranscriptText>—</NoTranscriptText>
        ) : trimmed ? (
          <TranscriptText>{trimmed}</TranscriptText>
        ) : audioUrl ? (
          <NoTranscriptText>Не удалось получить текст — попробуйте записать снова</NoTranscriptText>
        ) : (
          <NoTranscriptText>Речь не распознана — попробуйте записать снова</NoTranscriptText>
        )}
      </TranscriptRow>

      {isRecognizing && (
        <RecognizingRow>
          <Spinner aria-hidden />
          <RecognizingLabel>Идёт распознавание</RecognizingLabel>
        </RecognizingRow>
      )}

      <ActionRow>
        <Btn type="button" $variant="danger" onClick={onDelete}>
          🗑 Удалить
        </Btn>
        <Btn
          type="button"
          $variant="primary"
          onClick={onSend}
          disabled={sendDisabled}
          title={sendDisabled && !isRecognizing ? 'Нет текста для отправки' : undefined}
        >
          Отправить →
        </Btn>
      </ActionRow>
    </Wrap>
  );
};
