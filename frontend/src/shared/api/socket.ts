import { io, Socket } from 'socket.io-client';
import { ClientToServerEvents, ServerToClientEvents } from '~/shared/types';

const WS_URL = import.meta.env.VITE_WS_URL || 'http://localhost:3002';

class SocketManager {
  private socket: Socket<ServerToClientEvents, ClientToServerEvents> | null = null;

  connect() {
    if (this.socket) return;
    this.socket = io(WS_URL, {
      transports: ['websocket'],
      reconnectionAttempts: 5,
    });

    this.socket.on('connect', () => {
      console.log('[WS] Connected:', this.socket?.id);
    });
    this.socket.on('disconnect', (reason) => {
      console.log('[WS] Disconnected:', reason);
    });
    this.socket.on('connect_error', (err) => {
      console.error('[WS] Connection error:', err.message);
    });
  }

  /** Вызвать callback, когда сокет подключён (сразу или после connect). */
  whenConnected(callback: () => void): void {
    this.connect();
    const socket = this.socket;
    if (!socket) return;
    if (socket.connected) {
      callback();
    } else {
      socket.once('connect', callback);
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  emit<Event extends keyof ClientToServerEvents>(
    event: Event,
    ...args: Parameters<ClientToServerEvents[Event]>
  ) {
    this.connect();
    this.socket?.emit(event, ...args);
  }

  on<Event extends keyof ServerToClientEvents>(
    event: Event,
    handler: ServerToClientEvents[Event]
  ) {
    this.connect();
    this.socket?.on(event, handler as any);
  }

  off<Event extends keyof ServerToClientEvents>(
    event: Event,
    handler?: ServerToClientEvents[Event]
  ) {
    this.socket?.off(event, handler as any);
  }

  onConnectError(handler: (err: Error) => void): void {
    this.connect();
    this.socket?.on('connect_error', handler);
  }

  offConnectError(handler: (err: Error) => void): void {
    this.socket?.off('connect_error', handler);
  }
}

export const socketManager = new SocketManager();
