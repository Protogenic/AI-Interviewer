import React, { useEffect } from 'react';
import { useUnit } from 'effector-react';
import { useNavigate } from 'react-router-dom';
import styled, { keyframes } from 'styled-components';
import { $journalists, loadJournalists } from '~/entities/journalist';
import { formSubmitted } from '~/features/create-session/model';
import { Button } from '~/shared/ui/Button/Button';

// ─── Layout ──────────────────────────────────────────────────────────────────

const PageWrapper = styled.div`
  min-height: 100vh;
  background: linear-gradient(160deg, #0f0c29, #302b63, #24243e);
  display: flex;
  flex-direction: column;
`;

const Header = styled.header`
  padding: 24px 48px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
`;

const LogoBadge = styled.div`
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #a855f7);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
`;

const LogoText = styled.span`
  font-size: 18px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: -0.02em;
`;

const Main = styled.main`
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 48px 24px 64px;
`;

// ─── Hero ─────────────────────────────────────────────────────────────────────

const fadeUp = keyframes`
  from { opacity: 0; transform: translateY(24px); }
  to   { opacity: 1; transform: translateY(0); }
`;

const HeroSection = styled.section`
  text-align: center;
  max-width: 580px;
  margin-bottom: 48px;
  animation: ${fadeUp} 0.6s ease both;
`;

const HeroTitle = styled.h1`
  font-family: 'Inter', ui-sans-serif, sans-serif;
  font-size: clamp(1.8rem, 4vw, 2.8rem);
  font-weight: 800;
  color: #ffffff;
  line-height: 1.18;
  letter-spacing: -0.03em;
  margin-bottom: 16px;

  span {
    background: linear-gradient(90deg, #818cf8, #c084fc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
`;

const HeroSubtitle = styled.p`
  font-family: 'Inter', ui-sans-serif, sans-serif;
  font-size: 15px;
  color: #94a3b8;
  line-height: 1.7;
`;

// ─── Grid ─────────────────────────────────────────────────────────────────────

const SectionTitle = styled.h2`
  font-family: 'Inter', ui-sans-serif, sans-serif;
  font-size: 22px;
  font-weight: 700;
  color: #e2e8f0;
  letter-spacing: -0.01em;
  margin-bottom: 24px;
  text-align: center;
  width: 100%;
  max-width: 900px;
`;

const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
  width: 100%;
  max-width: 900px;
`;

// ─── Card ─────────────────────────────────────────────────────────────────────

const Card = styled.article`
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  cursor: pointer;
  transition: background 0.25s ease, border-color 0.25s ease, transform 0.25s ease, box-shadow 0.25s ease;
  backdrop-filter: blur(8px);
  animation: ${fadeUp} 0.6s ease both;

  &:hover {
    background: rgba(99, 102, 241, 0.1);
    border-color: rgba(99, 102, 241, 0.35);
    transform: translateY(-4px);
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.25);
  }
`;

const CardTop = styled.div`
  display: flex;
  align-items: center;
  gap: 14px;
`;

const AvatarCircle = styled.div<{ $color: string }>`
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: ${({ $color }) => $color};
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 800;
  color: #ffffff;
  flex-shrink: 0;
  letter-spacing: -0.02em;
`;

const CardName = styled.h2`
  font-family: 'Inter', ui-sans-serif, sans-serif;
  font-size: 17px;
  font-weight: 700;
  color: #f1f5f9;
  letter-spacing: -0.01em;
`;

const CardDescription = styled.p`
  font-family: 'Inter', ui-sans-serif, sans-serif;
  font-size: 13px;
  color: #94a3b8;
  line-height: 1.6;
  flex: 1;
`;

const CardFooter = styled.div`
  margin-top: 4px;
`;

// ─── Empty state ──────────────────────────────────────────────────────────────

const EmptyState = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 48px;
  color: #475569;
  font-size: 15px;
`;

// ─── Helpers ──────────────────────────────────────────────────────────────────

const AVATAR_COLORS = [
  'linear-gradient(135deg, #6366f1, #4f46e5)',
  'linear-gradient(135deg, #a855f7, #9333ea)',
  'linear-gradient(135deg, #ec4899, #db2777)',
  'linear-gradient(135deg, #f59e0b, #d97706)',
  'linear-gradient(135deg, #10b981, #059669)',
  'linear-gradient(135deg, #3b82f6, #2563eb)',
];

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

// ─── Component ────────────────────────────────────────────────────────────────

export const HomePage: React.FC = () => {
  const journalists = useUnit($journalists);
  const navigate = useNavigate();

  useEffect(() => {
    loadJournalists();
  }, []);

  const handleSelect = (journalistId: string) => {
    formSubmitted({ journalistId });
    navigate(`/interview/${journalistId}-temp`);
  };

  return (
    <PageWrapper>
      <Header>
        <LogoBadge>🎙</LogoBadge>
        <LogoText>AI Интервьюер</LogoText>
      </Header>

      <Main>
        <HeroSection>
          <HeroTitle>
            Интервью в стиле
            <br />
            <span>великих журналистов</span>
          </HeroTitle>
          <HeroSubtitle>
            Выберите журналиста-интервьюера — ИИ-агент соберёт информацию о вас
            и проведёт интервью в точном стиле выбранной ролевой модели.
          </HeroSubtitle>
        </HeroSection>

        <SectionTitle>Выберите журналиста</SectionTitle>

        {journalists.length === 0 ? (
          <EmptyState>
            <span>⏳</span>
            <span>Загрузка журналистов...</span>
          </EmptyState>
        ) : (
          <Grid>
            {journalists.map((journalist, index) => (
              <Card key={journalist.id} onClick={() => handleSelect(journalist.id)}>
                <CardTop>
                  <AvatarCircle $color={AVATAR_COLORS[index % AVATAR_COLORS.length]}>
                    {getInitials(journalist.name)}
                  </AvatarCircle>
                  <CardName>{journalist.name}</CardName>
                </CardTop>
                <CardDescription>{journalist.description}</CardDescription>
                <CardFooter>
                  <Button size="sm" onClick={(e) => { e.stopPropagation(); handleSelect(journalist.id); }}>
                    Начать интервью →
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </Grid>
        )}
      </Main>
    </PageWrapper>
  );
};
