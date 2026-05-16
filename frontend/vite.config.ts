import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'terminal-client-logs',
      configureServer(server) {
        server.middlewares.use('/__client_log', (req, res) => {
          if (req.method !== 'POST') {
            res.statusCode = 405;
            res.end('Method Not Allowed');
            return;
          }

          let body = '';
          req.on('data', (chunk) => {
            body += String(chunk);
          });
          req.on('end', () => {
            try {
              const payload = JSON.parse(body || '{}') as {
                level?: string;
                args?: unknown[];
                ts?: number;
              };
              const level = String(payload.level || 'log');
              const prefix = '[client]';
              const args = Array.isArray(payload.args) ? payload.args : [payload.args];
              const fn =
                level === 'error'
                  ? console.error
                  : level === 'warn'
                    ? console.warn
                    : console.log;
              fn(prefix, ...args);
            } catch (e) {
              console.warn('[client] failed to parse log payload', e);
            }
            res.statusCode = 204;
            res.end();
          });
        });
      },
    },
  ],
  resolve: {
    alias: {
      '~': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    open: true,
  },
});