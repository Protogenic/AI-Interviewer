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
    if (this.socket) {
      this.socket.emit(event, ...args);
    } else {
      console.warn(`[WS] Socket not connected, cannot emit "${event}"`);
    }
  }

  on<Event extends keyof ServerToClientEvents>(
    event: Event,
    handler: ServerToClientEvents[Event]
  ) {
    if (this.socket) {
      this.socket.on(event, handler as any);
    } else {
      console.warn(`[WS] Socket not connected, cannot subscribe to "${event}"`);
    }
  }

  off<Event extends keyof ServerToClientEvents>(
    event: Event,
    handler?: ServerToClientEvents[Event]
  ) {
    if (this.socket) {
      this.socket.off(event, handler as any);
    }
  }
}

export const socketManager = new SocketManager();
