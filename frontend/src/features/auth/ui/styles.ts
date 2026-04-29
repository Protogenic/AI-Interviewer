import { Link } from 'react-router-dom';
import styled from 'styled-components';

export const Page = styled.div`
  min-height: 100vh;
  background: linear-gradient(160deg, #0f0c29, #302b63, #24243e);
  display: flex;
  flex-direction: column;
  padding: 32px 16px;
`;

export const TopBar = styled.div`
  width: 100%;
  margin: 0 0 16px;
  display: flex;
  justify-content: flex-start;
`;

export const BackLink = styled(Link)`
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

export const Center = styled.div`
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
`;

export const Card = styled.div`
  width: 100%;
  max-width: 480px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  padding: 34px;
  backdrop-filter: blur(10px);
`;

export const Title = styled.h1`
  margin: 0 0 18px;
  color: #fff;
  font-family: 'Inter', ui-sans-serif, sans-serif;
  font-size: 26px;
  font-weight: 800;
  letter-spacing: -0.02em;
`;

export const Field = styled.label`
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 14px 0;
  color: #cbd5e1;
  font-size: 15px;
  font-family: 'Inter', ui-sans-serif, sans-serif;
`;

export const Input = styled.input`
  height: 48px;
  padding: 0 14px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(2, 6, 23, 0.35);
  color: #e2e8f0;
  font-size: 15px;
  outline: none;

  &:focus {
    border-color: rgba(129, 140, 248, 0.65);
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
  }
`;

export const SubmitButton = styled.button`
  width: 100%;
  height: 50px;
  margin-top: 18px;
  border-radius: 12px;
  border: 0;
  background: linear-gradient(135deg, #6366f1, #a855f7);
  color: white;
  font-weight: 700;
  font-size: 16px;
  font-family: 'Inter', ui-sans-serif, sans-serif;
  cursor: pointer;

  &:disabled {
    opacity: 0.6;
    cursor: default;
  }
`;

export const ErrorText = styled.div`
  margin-top: 12px;
  color: #fca5a5;
  font-size: 14px;
  font-family: 'Inter', ui-sans-serif, sans-serif;
`;

export const FormHint = styled.p`
  margin: 14px 0 0;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  color: #94a3b8;
  font-size: 14px;
  line-height: 1.5;
  font-family: 'Inter', ui-sans-serif, sans-serif;
`;
