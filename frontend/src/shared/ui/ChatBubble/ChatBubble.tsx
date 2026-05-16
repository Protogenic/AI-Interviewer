import React from 'react';
import styled, { css } from 'styled-components';
import { Message } from '~/shared/types';

interface ChatBubbleProps {
  message: Message;
  interviewerLabel?: string;
}

const Row = styled.div<{ $isUser: boolean }>`
  display: flex;
  align-items: flex-end;
  gap: 10px;
  ${({ $isUser }) => $isUser && css`flex-direction: row-reverse;`}
  margin-bottom: 4px;
`;

const Avatar = styled.div<{ $isUser: boolean }>`
  width: 34px;
  height: 34px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  ${({ $isUser }) =>
    $isUser
      ? css`
          background: linear-gradient(135deg, #6366f1, #4f46e5);
          color: #ffffff;
        `
      : css`
          background: linear-gradient(135deg, #f59e0b, #d97706);
          color: #ffffff;
        `}
`;

const Bubble = styled.div<{ $isUser: boolean }>`
  max-width: 68%;
  padding: 12px 16px;
  border-radius: 18px;
  font-size: 15px;
  line-height: 1.55;

  ${({ $isUser }) =>
    $isUser
      ? css`
          background: linear-gradient(135deg, #6366f1, #4f46e5);
          color: #ffffff;
          border-bottom-right-radius: 4px;
        `
      : css`
          background: #ffffff;
          color: #1e293b;
          border-bottom-left-radius: 4px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        `}

  p {
    margin: 0;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    word-break: break-word;
  }
`;

const Timestamp = styled.span<{ $isUser: boolean }>`
  display: block;
  font-size: 11px;
  margin-top: 5px;
  opacity: 0.65;
  text-align: ${({ $isUser }) => ($isUser ? 'right' : 'left')};
`;

export const ChatBubble: React.FC<ChatBubbleProps> = ({ message, interviewerLabel }) => {
  const isGuest = message.role === 'guest';
  const interviewer = interviewerLabel?.trim() || 'ИИ';
  return (
    <Row $isUser={isGuest}>
      <Avatar $isUser={isGuest}>{isGuest ? 'Вы' : interviewer}</Avatar>
      <Bubble $isUser={isGuest}>
        <p>{message.content}</p>
        <Timestamp $isUser={isGuest}>
          {message.timestamp.toLocaleTimeString('ru-RU', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </Timestamp>
      </Bubble>
    </Row>
  );
};
