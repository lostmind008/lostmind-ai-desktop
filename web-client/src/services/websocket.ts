/**
 * WebSocket service for real-time chat communication with the LostMindAI backend.
 * 
 * Provides type-safe WebSocket communication with automatic reconnection,
 * message queuing, and event handling for chat functionality.
 */

import { io, Socket } from 'socket.io-client';
import {
  WebSocketMessage,
  ChatMessageWS,
  ChatResponseWS,
  ChatStreamChunk,
  MessageRole,
} from '@/types/api';

type EventCallback<T = any> = (data: T) => void;

interface WebSocketEvents {
  'message': ChatResponseWS;
  'stream-chunk': ChatStreamChunk;
  'thinking': { content: string; session_id: string };
  'error': { message: string; session_id?: string };
  'connected': { session_id: string };
  'disconnected': { session_id: string };
  'status': { status: string; session_id: string };
}

export class WebSocketService {
  private socket: Socket | null = null;
  private baseURL: string;
  private sessionId: string | null = null;
  private eventListeners: Map<keyof WebSocketEvents, Set<EventCallback>> = new Map();
  private messageQueue: WebSocketMessage[] = [];
  private isConnecting: boolean = false;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private reconnectDelay: number = 1000;

  constructor(baseURL?: string) {
    this.baseURL = baseURL || process.env.WEBSOCKET_URL || 'ws://localhost:8000';
    this.initializeEventListeners();
  }

  private initializeEventListeners(): void {
    Object.keys({
      message: null,
      'stream-chunk': null,
      thinking: null,
      error: null,
      connected: null,
      disconnected: null,
      status: null,
    } as WebSocketEvents).forEach(event => {
      this.eventListeners.set(event as keyof WebSocketEvents, new Set());
    });
  }

  /**
   * Connect to WebSocket for a specific chat session
   */
  async connect(sessionId: string): Promise<void> {
    if (this.isConnecting || (this.socket?.connected && this.sessionId === sessionId)) {
      return;
    }

    this.isConnecting = true;
    this.sessionId = sessionId;

    try {
      // Disconnect existing connection if any
      await this.disconnect();

      // Create new socket connection
      const wsUrl = `${this.baseURL}/ws/${sessionId}`;
      console.log(`[WebSocket] Connecting to ${wsUrl}`);

      this.socket = io(wsUrl, {
        transports: ['websocket'],
        timeout: 10000,
        autoConnect: false,
      });

      this.setupSocketEventListeners();
      
      return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new Error('WebSocket connection timeout'));
        }, 10000);

        this.socket!.on('connect', () => {
          clearTimeout(timeout);
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          console.log(`[WebSocket] Connected to session ${sessionId}`);
          
          // Process queued messages
          this.processMessageQueue();
          
          this.emit('connected', { session_id: sessionId });
          resolve();
        });

        this.socket!.on('connect_error', (error) => {
          clearTimeout(timeout);
          this.isConnecting = false;
          console.error('[WebSocket] Connection error:', error);
          reject(error);
        });

        this.socket!.connect();
      });

    } catch (error) {
      this.isConnecting = false;
      console.error('[WebSocket] Failed to connect:', error);
      throw error;
    }
  }

  /**
   * Disconnect from WebSocket
   */
  async disconnect(): Promise<void> {
    if (this.socket) {
      console.log('[WebSocket] Disconnecting...');
      
      if (this.sessionId) {
        this.emit('disconnected', { session_id: this.sessionId });
      }

      this.socket.disconnect();
      this.socket = null;
      this.sessionId = null;
      this.isConnecting = false;
    }
  }

  /**
   * Send a chat message through WebSocket
   */
  async sendMessage(
    message: string,
    files: string[] = [],
    useThinking: boolean = true,
    enableSearch: boolean = false
  ): Promise<void> {
    if (!this.sessionId) {
      throw new Error('No active session');
    }

    const messageData: ChatMessageWS = {
      type: 'chat_message',
      message,
      files,
      session_id: this.sessionId,
      use_thinking: useThinking,
      enable_search: enableSearch,
    };

    await this.sendRawMessage(messageData);
  }

  /**
   * Send raw WebSocket message
   */
  private async sendRawMessage(message: WebSocketMessage): Promise<void> {
    if (!this.socket?.connected) {
      // Queue message if not connected
      this.messageQueue.push(message);
      console.log('[WebSocket] Message queued (not connected)');
      return;
    }

    try {
      this.socket.emit('message', message);
      console.log('[WebSocket] Message sent:', message.type);
    } catch (error) {
      console.error('[WebSocket] Failed to send message:', error);
      throw error;
    }
  }

  /**
   * Process queued messages when connection is established
   */
  private processMessageQueue(): void {
    if (this.messageQueue.length > 0 && this.socket?.connected) {
      console.log(`[WebSocket] Processing ${this.messageQueue.length} queued messages`);
      
      this.messageQueue.forEach(message => {
        this.socket!.emit('message', message);
      });
      
      this.messageQueue = [];
    }
  }

  /**
   * Setup socket event listeners
   */
  private setupSocketEventListeners(): void {
    if (!this.socket) return;

    // Chat response
    this.socket.on('chat_response', (data: ChatResponseWS) => {
      console.log('[WebSocket] Received chat response');
      this.emit('message', data);
    });

    // Streaming chunks
    this.socket.on('stream_chunk', (data: ChatStreamChunk) => {
      console.log('[WebSocket] Received stream chunk:', data.type);
      this.emit('stream-chunk', data);
    });

    // Thinking updates
    this.socket.on('thinking', (data: { content: string }) => {
      if (this.sessionId) {
        this.emit('thinking', { content: data.content, session_id: this.sessionId });
      }
    });

    // Status updates
    this.socket.on('status', (data: { status: string }) => {
      if (this.sessionId) {
        this.emit('status', { status: data.status, session_id: this.sessionId });
      }
    });

    // Error handling
    this.socket.on('error', (data: { message: string }) => {
      console.error('[WebSocket] Received error:', data.message);
      this.emit('error', { message: data.message, session_id: this.sessionId || undefined });
    });

    // Connection events
    this.socket.on('disconnect', (reason) => {
      console.log('[WebSocket] Disconnected:', reason);
      if (this.sessionId) {
        this.emit('disconnected', { session_id: this.sessionId });
      }
      
      // Attempt reconnection for certain disconnect reasons
      if (reason === 'io server disconnect' || reason === 'transport close') {
        this.attemptReconnection();
      }
    });

    // Ping/pong for connection health
    this.socket.on('pong', () => {
      console.log('[WebSocket] Pong received');
    });
  }

  /**
   * Attempt to reconnect with exponential backoff
   */
  private async attemptReconnection(): Promise<void> {
    if (this.reconnectAttempts >= this.maxReconnectAttempts || !this.sessionId) {
      console.error('[WebSocket] Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`[WebSocket] Attempting reconnection ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`);
    
    setTimeout(async () => {
      try {
        if (this.sessionId) {
          await this.connect(this.sessionId);
        }
      } catch (error) {
        console.error('[WebSocket] Reconnection failed:', error);
        this.attemptReconnection();
      }
    }, delay);
  }

  /**
   * Add event listener
   */
  on<K extends keyof WebSocketEvents>(
    event: K,
    callback: EventCallback<WebSocketEvents[K]>
  ): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.add(callback);
    }
  }

  /**
   * Remove event listener
   */
  off<K extends keyof WebSocketEvents>(
    event: K,
    callback: EventCallback<WebSocketEvents[K]>
  ): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.delete(callback);
    }
  }

  /**
   * Emit event to all listeners
   */
  private emit<K extends keyof WebSocketEvents>(
    event: K,
    data: WebSocketEvents[K]
  ): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`[WebSocket] Error in ${event} listener:`, error);
        }
      });
    }
  }

  /**
   * Send ping to check connection health
   */
  ping(): void {
    if (this.socket?.connected) {
      this.socket.emit('ping');
      console.log('[WebSocket] Ping sent');
    }
  }

  /**
   * Get connection status
   */
  get isConnected(): boolean {
    return this.socket?.connected || false;
  }

  /**
   * Get current session ID
   */
  get currentSessionId(): string | null {
    return this.sessionId;
  }

  /**
   * Get connection state
   */
  get connectionState(): 'connected' | 'connecting' | 'disconnected' {
    if (this.isConnecting) return 'connecting';
    if (this.socket?.connected) return 'connected';
    return 'disconnected';
  }
}

// Export singleton instance
export const webSocketService = new WebSocketService();

// Export class for testing or custom instances
export { WebSocketService };

// Helper function to check WebSocket connectivity
export const checkWebSocketConnectivity = async (sessionId: string): Promise<boolean> => {
  try {
    const testService = new WebSocketService();
    await testService.connect(sessionId);
    await testService.disconnect();
    return true;
  } catch {
    return false;
  }
};