import axios from 'axios';
import { GenerateQuestionRequest, GenerateQuestionResponse } from '../types';

const AI_SERVICE_URL = process.env.AI_SERVICE_URL ?? 'http://localhost:8000';

export async function generateQuestion(
  req: GenerateQuestionRequest,
): Promise<{ question: string; used_template_id: string; consecutive_followups: number }> {
  const response = await axios.post<GenerateQuestionResponse>(
    `${AI_SERVICE_URL}/api/generation/generate_question`,
    req,
    { timeout: 30_000 },
  );
  return {
    question: response.data.question,
    used_template_id: response.data.used_template_id,
    consecutive_followups: response.data.consecutive_followups,
  };
}
