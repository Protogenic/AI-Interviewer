import React from 'react';
import styled from 'styled-components';

interface ModalProps {
  open: boolean;
  title?: string;
  children: React.ReactNode;
  actions?: React.ReactNode;
  onClose?: () => void;
  closeOnBackdrop?: boolean;
  maxWidth?: string;
}

const Backdrop = styled.div`
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.66);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 30;
`;

const Card = styled.div<{ $maxWidth: string }>`
  width: 100%;
  max-width: ${({ $maxWidth }) => $maxWidth};
  border-radius: 16px;
  padding: 20px 18px;
  background: rgba(15, 23, 42, 0.97);
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.45);
`;

const Title = styled.h3`
  margin: 0 0 10px;
  font-size: 19px;
  font-weight: 700;
  color: #f8fafc;
`;

const Content = styled.div`
  font-size: 15px;
  line-height: 1.6;
  color: #cbd5e1;
`;

const Actions = styled.div`
  margin-top: 18px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
`;

export const Modal: React.FC<ModalProps> = ({
  open,
  title,
  children,
  actions,
  onClose,
  closeOnBackdrop = true,
  maxWidth = '460px',
}) => {
  if (!open) return null;

  const handleBackdropClick = () => {
    if (closeOnBackdrop) onClose?.();
  };

  return (
    <Backdrop onClick={handleBackdropClick}>
      <Card
        role="dialog"
        aria-modal="true"
        aria-label={title}
        $maxWidth={maxWidth}
        onClick={(e) => e.stopPropagation()}
      >
        {title ? <Title>{title}</Title> : null}
        <Content>{children}</Content>
        {actions ? <Actions>{actions}</Actions> : null}
      </Card>
    </Backdrop>
  );
};
