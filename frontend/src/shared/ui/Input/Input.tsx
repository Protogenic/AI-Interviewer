import React from 'react';
import styled from 'styled-components';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  rightSlot?: React.ReactNode;
}

const Wrapper = styled.div`
  display: flex;
  flex-direction: column;
  gap: 6px;
`;

const Label = styled.label`
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  letter-spacing: 0.02em;
  text-transform: uppercase;
`;

const InputWrapper = styled.div`
  position: relative;
  display: flex;
  align-items: center;
`;

const StyledInput = styled.input<{ $hasRightSlot?: boolean }>`
  width: 100%;
  padding: 11px ${({ $hasRightSlot }) => ($hasRightSlot ? '50px' : '16px')} 11px 16px;
  font-size: 15px;
  color: #1e293b;
  background: #ffffff;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;

  &::placeholder {
    color: #94a3b8;
  }

  &:focus {
    border-color: #6366f1;
    box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.12);
  }

  &:disabled {
    background: #f8fafc;
    color: #94a3b8;
    cursor: not-allowed;
  }
`;

const RightSlot = styled.div`
  position: absolute;
  right: 9px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
`;

export const Input: React.FC<InputProps> = ({ label, rightSlot, ...props }) => {
  return (
    <Wrapper>
      {label && <Label>{label}</Label>}
      <InputWrapper>
        <StyledInput $hasRightSlot={Boolean(rightSlot)} {...props} />
        {rightSlot && <RightSlot>{rightSlot}</RightSlot>}
      </InputWrapper>
    </Wrapper>
  );
};
