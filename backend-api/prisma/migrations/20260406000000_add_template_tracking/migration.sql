-- AlterTable
ALTER TABLE "InterviewSession" ADD COLUMN "questionId" INTEGER NOT NULL DEFAULT 1;
ALTER TABLE "InterviewSession" ADD COLUMN "previousTemplateId" TEXT;
ALTER TABLE "InterviewSession" ADD COLUMN "consecutiveFollowups" INTEGER NOT NULL DEFAULT 0;
