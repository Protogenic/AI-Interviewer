/* eslint-disable no-console */

function safeSerialize(value: unknown): unknown {
  try {
    if (value instanceof Error) {
      return { name: value.name, message: value.message, stack: value.stack };
    }
    if (typeof value === 'bigint') return value.toString();
    return value;
  } catch {
    return String(value);
  }
}

export function forwardConsoleToTerminal() {
  if (!import.meta.env.DEV) return;

  const original = {
    log: console.log,
    warn: console.warn,
    error: console.error,
  };

  const send = (level: 'log' | 'warn' | 'error', args: unknown[]) => {
    // важно: не использовать console.* внутри send, чтобы не уйти в рекурсию
    fetch('/__client_log', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        level,
        ts: Date.now(),
        args: args.map(safeSerialize),
      }),
      keepalive: true,
    }).catch(() => {
      // ignore
    });
  };

  console.log = (...args: unknown[]) => {
    original.log(...args);
    send('log', args);
  };
  console.warn = (...args: unknown[]) => {
    original.warn(...args);
    send('warn', args);
  };
  console.error = (...args: unknown[]) => {
    original.error(...args);
    send('error', args);
  };
}

