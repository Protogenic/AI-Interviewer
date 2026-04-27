import bcrypt from 'bcryptjs';
import { authConfig } from '../config/auth';

export function hashPassword(plain: string): Promise<string> {
  return bcrypt.hash(plain, authConfig.bcryptRounds);
}

export function verifyPassword(plain: string, hash: string): Promise<boolean> {
  return bcrypt.compare(plain, hash);
}
