import crypto from 'crypto';
import jwt, { SignOptions } from 'jsonwebtoken';
import { authConfig } from '../config/auth';

export interface AccessTokenPayload {
  sub: string;
  email: string;
}

export function signAccessToken(payload: AccessTokenPayload): string {
  return jwt.sign(payload, authConfig.jwtAccessSecret, {
    expiresIn: authConfig.accessTtl,
  } as SignOptions);
}

export function verifyAccessToken(token: string): AccessTokenPayload {
  const decoded = jwt.verify(token, authConfig.jwtAccessSecret) as jwt.JwtPayload & AccessTokenPayload;
  return { sub: decoded.sub as string, email: decoded.email };
}

export function generateRefreshToken(): string {
  return crypto.randomBytes(48).toString('hex');
}

export function hashRefreshToken(raw: string): string {
  return crypto.createHash('sha256').update(raw).digest('hex');
}

export function refreshExpiryDate(): Date {
  const ms = authConfig.refreshTtlDays * 24 * 60 * 60 * 1000;
  return new Date(Date.now() + ms);
}
