import { io, Socket } from 'socket.io-client';
import { ClientToServerEvents, ServerToClientEvents } from '~/shared/types';

class SocketManager {
  private socket: Socket<ServerToClientEvents, ClientToServerEvents> | null = null;

  connect() {
    if (this.socket) return;
    // Заглушка: пока не подключаемся к реальному серверу
    // this.socket = io(import.meta.env.VITE_WS_URL || 'http://localhost:3002');
    console.log('WebSocket connection stub');
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
      console.warn(`Socket not connected, cannot emit ${event}`);
    }
  }

  on<Event extends keyof ServerToClientEvents>(
    event: Event,
    handler: ServerToClientEvents[Event]
  ) {
    if (this.socket) {
      this.socket.on(event, handler as any);
    } else {
      console.warn(`Socket not connected, cannot listen to ${event}`);
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