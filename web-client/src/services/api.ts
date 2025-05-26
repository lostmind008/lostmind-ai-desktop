/**
 * API service layer for communicating with the LostMindAI FastAPI backend.
 * 
 * Provides type-safe methods for all backend endpoints with proper error handling,
 * request/response transformation, and loading states.
 */

import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios';
import {
  ChatSession,
  ChatSessionCreate,
  ChatSessionUpdate,
  ChatMessage,
  ChatMessageCreate,
  ChatResponse,
  ModelSelection,
  Document,
  DocumentCreate,
  SearchQuery,
  SearchResult,
  RAGRequest,
  RAGResponse,
  UsageStats,
  KnowledgeStats,
  CacheStats,
  HealthStatus,
  FileUpload,
  APIError,
  APIResponse,
  PaginatedResponse,
} from '@/types/api';
import { createRetryInterceptor, rateLimitTracker } from '@/utils/retry';

class APIService {
  private client: AxiosInstance;
  private baseURL: string;

  constructor(baseURL?: string) {
    this.baseURL = baseURL || process.env.BACKEND_URL || 'http://localhost:8000';
    
    this.client = axios.create({
      baseURL: `${this.baseURL}/api/v1`,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });

    // Request interceptor for logging and authentication
    this.client.interceptors.request.use(
      (config) => {
        // Add timestamp to requests for debugging
        config.metadata = { startTime: Date.now() };
        
        // Add authentication header if available
        const token = this.getAuthToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        
        console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        console.error('[API] Request error:', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling and logging
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        const duration = Date.now() - (response.config.metadata?.startTime || 0);
        console.log(`[API] ${response.config.method?.toUpperCase()} ${response.config.url} - ${response.status} (${duration}ms)`);
        
        // Update rate limit tracking
        if (response.config.url) {
          rateLimitTracker.updateFromResponse(response.config.url, response);
        }
        
        return response;
      },
      (error: AxiosError) => {
        const duration = Date.now() - (error.config?.metadata?.startTime || 0);
        console.error(`[API] ${error.config?.method?.toUpperCase()} ${error.config?.url} - ${error.response?.status || 'NETWORK_ERROR'} (${duration}ms)`);
        
        // Transform error to our standard format
        const apiError: APIError = {
          detail: this.getErrorMessage(error),
          status_code: error.response?.status || 0,
          timestamp: new Date().toISOString(),
          path: error.config?.url,
        };
        
        return Promise.reject(apiError);
      }
    );
    
    // Add retry interceptor
    const retryInterceptor = createRetryInterceptor({
      maxAttempts: 3,
      onRetry: (error, attempt) => {
        console.log(`[API Retry] Attempt ${attempt} for ${error.config?.url} after ${error.response?.status || 'network error'}`);
      },
    });
    this.client.interceptors.response.use(
      retryInterceptor.fulfilled,
      retryInterceptor.rejected
    );
  }

  private getAuthToken(): string | null {
    // For now, return null - authentication will be added later
    return null;
  }

  private getErrorMessage(error: AxiosError): string {
    if (error.response?.data) {
      const data = error.response.data as any;
      return data.detail || data.message || 'An error occurred';
    }
    if (error.request) {
      return 'Network error - please check your connection';
    }
    return error.message || 'Unknown error occurred';
  }

  private handleResponse<T>(response: AxiosResponse<T>): T {
    return response.data;
  }

  // Health and Status
  async getHealth(): Promise<HealthStatus> {
    const response = await this.client.get<HealthStatus>('/health');
    return this.handleResponse(response);
  }

  async getDetailedStatus(): Promise<HealthStatus> {
    const response = await this.client.get<HealthStatus>('/health/status');
    return this.handleResponse(response);
  }

  // Chat Session Management
  async createSession(sessionData: ChatSessionCreate): Promise<ChatSession> {
    const response = await this.client.post<ChatSession>('/chat/sessions', sessionData);
    return this.handleResponse(response);
  }

  async getSession(sessionId: string): Promise<ChatSession> {
    const response = await this.client.get<ChatSession>(`/chat/sessions/${sessionId}`);
    return this.handleResponse(response);
  }

  async listSessions(): Promise<ChatSession[]> {
    const response = await this.client.get<{ sessions: ChatSession[] }>('/chat/sessions');
    return response.data.sessions;
  }

  async updateSession(sessionId: string, updates: ChatSessionUpdate): Promise<ChatSession> {
    const response = await this.client.put<ChatSession>(`/chat/sessions/${sessionId}`, updates);
    return this.handleResponse(response);
  }

  async deleteSession(sessionId: string): Promise<void> {
    await this.client.delete(`/chat/sessions/${sessionId}`);
  }

  async clearSessionHistory(sessionId: string): Promise<void> {
    await this.client.post(`/chat/sessions/${sessionId}/clear`);
  }

  // Message Handling
  async sendMessage(sessionId: string, messageData: ChatMessageCreate): Promise<ChatResponse> {
    const response = await this.client.post<ChatResponse>(
      `/chat/sessions/${sessionId}/messages`,
      messageData
    );
    return this.handleResponse(response);
  }

  async sendCachedMessage(sessionId: string, messageData: ChatMessageCreate): Promise<ChatResponse> {
    const response = await this.client.post<ChatResponse>(
      `/chat/sessions/${sessionId}/messages/cached`,
      messageData
    );
    return this.handleResponse(response);
  }

  async sendRAGMessage(sessionId: string, ragRequest: RAGRequest): Promise<ChatResponse> {
    const response = await this.client.post<ChatResponse>(
      `/chat/sessions/${sessionId}/rag`,
      ragRequest
    );
    return this.handleResponse(response);
  }

  async getSessionMessages(sessionId: string): Promise<ChatMessage[]> {
    const response = await this.client.get<{ messages: ChatMessage[] }>(
      `/chat/sessions/${sessionId}/messages`
    );
    return response.data.messages;
  }

  async regenerateResponse(sessionId: string): Promise<ChatResponse> {
    const response = await this.client.post<ChatResponse>(`/chat/sessions/${sessionId}/regenerate`);
    return this.handleResponse(response);
  }

  // Model Management
  async listModels(): Promise<ModelSelection[]> {
    const response = await this.client.get<ModelSelection[]>('/chat/models');
    return this.handleResponse(response);
  }

  // File Operations
  async uploadFile(file: File, sessionId?: string): Promise<FileUpload> {
    const formData = new FormData();
    formData.append('file', file);
    if (sessionId) {
      formData.append('session_id', sessionId);
    }

    const response = await this.client.post<FileUpload>('/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return this.handleResponse(response);
  }

  // Knowledge Management
  async createDocument(documentData: DocumentCreate): Promise<Document> {
    const response = await this.client.post<Document>('/knowledge/documents', documentData);
    return this.handleResponse(response);
  }

  async getDocument(documentId: string): Promise<Document> {
    const response = await this.client.get<Document>(`/knowledge/documents/${documentId}`);
    return this.handleResponse(response);
  }

  async updateDocument(documentId: string, updates: Partial<DocumentCreate>): Promise<Document> {
    const response = await this.client.put<Document>(`/knowledge/documents/${documentId}`, updates);
    return this.handleResponse(response);
  }

  async deleteDocument(documentId: string): Promise<void> {
    await this.client.delete(`/knowledge/documents/${documentId}`);
  }

  async uploadDocument(
    file: File,
    title?: string,
    documentType?: string,
    author?: string,
    tags?: string
  ): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);
    if (title) formData.append('title', title);
    if (documentType) formData.append('document_type', documentType);
    if (author) formData.append('author', author);
    if (tags) formData.append('tags', tags);

    const response = await this.client.post<Document>('/knowledge/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return this.handleResponse(response);
  }

  async searchKnowledge(searchQuery: SearchQuery): Promise<SearchResult> {
    const response = await this.client.post<SearchResult>('/knowledge/search', searchQuery);
    return this.handleResponse(response);
  }

  async getKnowledgeStats(): Promise<KnowledgeStats> {
    const response = await this.client.get<KnowledgeStats>('/knowledge/stats');
    return this.handleResponse(response);
  }

  async resetKnowledgeBase(): Promise<void> {
    await this.client.post('/knowledge/reset');
  }

  // Cache Management
  async getCacheStats(): Promise<CacheStats> {
    const response = await this.client.get<CacheStats>('/knowledge/cache/stats');
    return this.handleResponse(response);
  }

  async clearCache(): Promise<void> {
    await this.client.post('/knowledge/cache/clear');
  }

  async getSessionCache(sessionId: string): Promise<any> {
    const response = await this.client.get(`/chat/sessions/${sessionId}/cache`);
    return this.handleResponse(response);
  }

  async clearSessionCache(sessionId: string): Promise<void> {
    await this.client.delete(`/chat/sessions/${sessionId}/cache`);
  }

  // Statistics
  async getSessionStats(sessionId: string): Promise<UsageStats> {
    const response = await this.client.get<UsageStats>(`/chat/sessions/${sessionId}/stats`);
    return this.handleResponse(response);
  }

  async getGlobalStats(): Promise<UsageStats> {
    const response = await this.client.get<UsageStats>('/chat/stats');
    return this.handleResponse(response);
  }

  // Export functionality
  async exportSession(sessionId: string, format: 'json' | 'markdown' | 'html'): Promise<Blob> {
    const response = await this.client.get(`/chat/sessions/${sessionId}/export`, {
      params: { format },
      responseType: 'blob',
    });
    return response.data;
  }

  // Utility methods
  getWebSocketURL(): string {
    const wsProtocol = this.baseURL.startsWith('https') ? 'wss' : 'ws';
    const wsBaseURL = this.baseURL.replace(/^https?/, wsProtocol);
    return `${wsBaseURL}/ws`;
  }

  // Health check with retry logic
  async healthCheck(retries: number = 3): Promise<boolean> {
    for (let i = 0; i < retries; i++) {
      try {
        const health = await this.getHealth();
        return health.status === 'healthy';
      } catch (error) {
        if (i === retries - 1) {
          console.error('Health check failed after all retries:', error);
          return false;
        }
        await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
      }
    }
    return false;
  }
}

// Export singleton instance
export const apiService = new APIService();

// Export class for testing or custom instances
export { APIService };

// Helper function to check if backend is available
export const checkBackendAvailability = async (): Promise<boolean> => {
  try {
    return await apiService.healthCheck();
  } catch {
    return false;
  }
};