// ─── REST types ───────────────────────────────────────────────────────────────

export interface JournalistDTO {
  id: string;
  name: string;
  description: string;
}

export interface SessionDTO {
  id: string;
  journalistId: string;
  userName: string;
  userInfo: string;
  status: string;
  createdAt: string;
}

export interface MessageDTO {
  id: string;
  role: 'assistant' | 'user';
  content: string;
  createdAt: string;
}

export interface CreateSessionBody {
  journalistId: string;
  userName?: string;
  userInfo?: string;
}

// ─── WebSocket event payloads ──────────────────────────────────────────────────

export interface InterviewStartPayload {
  journalistId: string;
  userName?: string;
  userInfo?: string;
  maxNumberQuestions?: number;
}

export interface InterviewAnswerPayload {
  sessionId: string;
  answer: string;
}

export interface InterviewCompletePayload {
  sessionId: string;
}

export interface InterviewQuestionPayload {
  question: string;
  sessionId: string;
}

export interface InterviewErrorPayload {
  message: string;
}

// ─── AI Service types ──────────────────────────────────────────────────────────

export interface InterviewPart {
  role: string;
  text: string;
}

export interface GenerateQuestionRequest {
  session_id: string;
  character_id: string;
  user_name: string;
  user_info: string;
  last_answer: string;
  full_interview_history: InterviewPart[];
  phrase_id: number;
  previous_template_id: string;
  consecutive_followups: number;
  max_number_questions: number;
}

export interface GenerateQuestionResponse {
  question: string;
  used_template_id: string;
  consecutive_followups: number;
}
