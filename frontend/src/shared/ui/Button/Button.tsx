import React from 'react';
import styled, { css } from 'styled-components';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
}

const StyledButton = styled.button<{ $variant: string; $size: string }>`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-weight: 600;
  border-radius: 10px;
  transition: all 0.2s ease;
  white-space: nowrap;
  border: 2px solid transparent;

  ${({ $size }) =>
    $size === 'sm' &&
    css`
      padding: 6px 14px;
      font-size: 13px;
    `}

  ${({ $size }) =>
    $size === 'md' &&
    css`
      padding: 10px 20px;
      font-size: 15px;
    `}

  ${({ $size }) =>
    $size === 'lg' &&
    css`
      padding: 14px 28px;
      font-size: 16px;
    `}

  ${({ $variant }) =>
    $variant === 'primary' &&
    css`
      background: linear-gradient(135deg, #6366f1, #4f46e5);
      color: #ffffff;
      box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);

      &:hover:not(:disabled) {
        background: linear-gradient(135deg, #4f46e5, #4338ca);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.45);
        transform: translateY(-1px);
      }

      &:active:not(:disabled) {
        transform: translateY(0);
        box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
      }
    `}

  ${({ $variant }) =>
    $variant === 'secondary' &&
    css`
      background: #ffffff;
      color: #4f46e5;
      border-color: #c7d2fe;

      &:hover:not(:disabled) {
        background: #eef2ff;
        border-color: #a5b4fc;
      }

      &:active:not(:disabled) {
        background: #e0e7ff;
      }
    `}

  ${({ $variant }) =>
    $variant === 'ghost' &&
    css`
      background: transparent;
      color: #64748b;

      &:hover:not(:disabled) {
        background: #f1f5f9;
        color: #1e293b;
      }
    `}

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  children,
  ...props
}) => {
  return (
    <StyledButton $variant={variant} $size={size} {...props}>
      {children}
    </StyledButton>
  );
};
