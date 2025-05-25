/**
 * WebSocket service for real-time chat communication with the LostMindAI backend.
 * 
 * Provides type-safe WebSocket communication with automatic reconnection,
 * message queuing, and event handling for chat functionality.
 * 
 * Uses native WebSockets for compatibility with FastAPI backend.
 */

import {
  WebSocketMessage,
  ChatMessage,
  ChatResponse,
  MessageRole,
} from '@/types/api';

// Define WebSocket-specific message types
interface ChatMessageWS extends ChatMessage {
  type: 'chat_message';
  session_id: string;
  use_thinking?: boolean;
  enable_search?: boolean;
}

interface ChatResponseWS extends ChatResponse {
  type: 'chat_response';
}

interface ChatStreamChunk {
  type: 'stream_chunk';
  chunk_type: 'thinking' | 'content' | 'complete';
  content: string;
  session_id: string;
}

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
  private socket: WebSocket | null = null;
  private baseURL: string;
  private sessionId: string | null = null;
  private eventListeners: Map<keyof WebSocketEvents, Set<EventCallback>> = new Map();
  private messageQueue: WebSocketMessage[] = [];
  private isConnecting: boolean = false;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private reconnectDelay: number = 1000;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private heartbeatFrequency: number = 30000; // 30 seconds

  constructor(baseURL?: string) {
    this.baseURL = baseURL || process.env.NEXT_PUBLIC_WEBSOCKET_URL || 'ws://localhost:8000';
    this.initializeEventListeners();
  }

  private initializeEventListeners(): void {
    const eventKeys: (keyof WebSocketEvents)[] = [
      'message',
      'stream-chunk', 
      'thinking',
      'error',
      'connected',
      'disconnected',
      'status'
    ];
    
    eventKeys.forEach(event => {
      this.eventListeners.set(event, new Set());
    });
  }

  /**
   * Connect to WebSocket for a specific chat session
   */
  async connect(sessionId: string): Promise<void> {
    if (this.isConnecting || (this.socket?.readyState === WebSocket.OPEN && this.sessionId === sessionId)) {
      return;
    }

    this.isConnecting = true;
    this.sessionId = sessionId;

    try {
      // Disconnect existing connection if any
      await this.disconnect();

      // Create new WebSocket connection
      const wsUrl = `${this.baseURL}/ws/${sessionId}`;
      console.log(`[WebSocket] Connecting to ${wsUrl}`);

      return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          this.isConnecting = false;
          reject(new Error('WebSocket connection timeout'));
        }, 10000);

        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
          clearTimeout(timeout);
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          console.log(`[WebSocket] Connected to session ${sessionId}`);
          
          // Start heartbeat
          this.startHeartbeat();
          
          // Process queued messages
          this.processMessageQueue();
          
          this.emit('connected', { session_id: sessionId });
          resolve();
        };

        this.socket.onerror = (error) => {
          clearTimeout(timeout);
          this.isConnecting = false;
          console.error('[WebSocket] Connection error:', error);
          reject(new Error('WebSocket connection failed'));
        };

        this.socket.onclose = (event) => {
          clearTimeout(timeout);
          this.isConnecting = false;
          this.stopHeartbeat();
          
          console.log(`[WebSocket] Connection closed: ${event.code} ${event.reason}`);
          
          if (this.sessionId) {
            this.emit('disconnected', { session_id: this.sessionId });
          }
          
          // Attempt reconnection for unexpected closes
          if (event.code !== 1000 && event.code !== 1001) {
            this.attemptReconnection();
          }
        };

        this.socket.onmessage = (event) => {
          this.handleMessage(event);
        };
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
      
      this.stopHeartbeat();
      
      if (this.sessionId) {
        this.emit('disconnected', { session_id: this.sessionId });
      }

      // Close with normal closure code
      if (this.socket.readyState === WebSocket.OPEN) {
        this.socket.close(1000, 'Normal closure');
      }
      
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
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      // Queue message if not connected
      this.messageQueue.push(message);
      console.log('[WebSocket] Message queued (not connected)');
      return;
    }

    try {
      this.socket.send(JSON.stringify(message));
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
    if (this.messageQueue.length > 0 && this.socket?.readyState === WebSocket.OPEN) {
      console.log(`[WebSocket] Processing ${this.messageQueue.length} queued messages`);
      
      this.messageQueue.forEach(message => {
        this.socket!.send(JSON.stringify(message));
      });
      
      this.messageQueue = [];
    }
  }

  /**
   * Handle incoming WebSocket messages
   */
  private handleMessage(event: MessageEvent): void {
    try {
      const data = JSON.parse(event.data);
      console.log('[WebSocket] Received message:', data.type);

      switch (data.type) {
        case 'chat_response':
          this.emit('message', data as ChatResponseWS);
          break;
        case 'stream_chunk':
          this.emit('stream-chunk', data as ChatStreamChunk);
          break;
        case 'thinking':
          if (this.sessionId) {
            this.emit('thinking', { content: data.content, session_id: this.sessionId });
          }
          break;
        case 'status':
          if (this.sessionId) {
            this.emit('status', { status: data.status, session_id: this.sessionId });
          }
          break;
        case 'error':
          console.error('[WebSocket] Received error:', data.message);
          this.emit('error', { message: data.message, session_id: this.sessionId || undefined });
          break;
        case 'pong':
          console.log('[WebSocket] Pong received');
          break;
        default:
          console.warn('[WebSocket] Unknown message type:', data.type);
      }
    } catch (error) {
      console.error('[WebSocket] Failed to parse message:', error);
    }
  }

  /**
   * Start heartbeat to keep connection alive
   */
  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatInterval = setInterval(() => {
      this.ping();
    }, this.heartbeatFrequency);
  }

  /**
   * Stop heartbeat
   */
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
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
    if (this.socket?.readyState === WebSocket.OPEN) {
      const pingMessage = { type: 'ping' };
      this.socket.send(JSON.stringify(pingMessage));
      console.log('[WebSocket] Ping sent');
    }
  }

  /**
   * Get connection status
   */
  get isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN || false;
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
    if (this.socket?.readyState === WebSocket.OPEN) return 'connected';
    return 'disconnected';
  }
}

// Export singleton instance
export const webSocketService = new WebSocketService();

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