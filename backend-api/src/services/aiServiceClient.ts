import axios from 'axios';
import { GenerateQuestionRequest, GenerateQuestionResponse } from '../types';

const AI_SERVICE_URL = process.env.AI_SERVICE_URL ?? 'http://localhost:8000';

export async function generateQuestion(req: GenerateQuestionRequest): Promise<string> {
  const response = await axios.post<GenerateQuestionResponse>(
    `${AI_SERVICE_URL}/api/generation/generate_question`,
    req,
    { timeout: 30_000 },
  );
  return response.data.question;
}
