-- Rename legacy roles in ConversationTurn to match ai_service expectations
UPDATE "ConversationTurn" SET "role" = 'guest' WHERE "role" = 'user';
UPDATE "ConversationTurn" SET "role" = 'interviewer' WHERE "role" = 'assistant';
