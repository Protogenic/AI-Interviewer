import { execSync } from 'child_process';
import { Client } from 'pg';

const DEFAULT_TEST_URL = 'postgresql://postgres:postgres@localhost:5432/ai_interviewer_test';

async function ensureDatabase(connectionString: string): Promise<void> {
  const url = new URL(connectionString);
  const dbName = url.pathname.replace(/^\//, '');
  const adminUrl = new URL(connectionString);
  adminUrl.pathname = '/postgres';

  const client = new Client({ connectionString: adminUrl.toString() });
  await client.connect();
  try {
    const exists = await client.query('SELECT 1 FROM pg_database WHERE datname = $1', [dbName]);
    if (exists.rowCount === 0) {
      await client.query(`CREATE DATABASE "${dbName}"`);
      console.log(`[test] created database ${dbName}`);
    }
  } finally {
    await client.end();
  }
}

export async function setup(): Promise<void> {
  const url = process.env.DATABASE_URL ?? DEFAULT_TEST_URL;
  await ensureDatabase(url);
  console.log(`[test] applying migrations to ${url}`);
  execSync('npx prisma migrate deploy', {
    stdio: 'inherit',
    env: { ...process.env, DATABASE_URL: url },
  });
}
