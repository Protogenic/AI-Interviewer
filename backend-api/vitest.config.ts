import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['src/__tests__/**/*.test.ts'],
    globals: false,
    pool: 'forks',
    forks: { singleFork: true },
    fileParallelism: false,
    setupFiles: [
      './src/__tests__/env.ts',
      './src/__tests__/setup.ts',
    ],
    globalSetup: ['./src/__tests__/global-setup.ts'],
    hookTimeout: 30000,
    testTimeout: 20000,
  },
});
