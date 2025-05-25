/**
 * TypeScript type definitions for LostMindAI API communication.
 * 
 * These types mirror the Pydantic models from the FastAPI backend
 * ensuring type safety between frontend and backend.
 */

// Base types
export interface BaseModel {
  id: string;
  created_at: string;
  updated_at: string;
}

// Message types
export enum MessageRole {
  USER = 'user',
  ASSISTANT = 'assistant',
  SYSTEM = 'system',
}

export interface ChatMessage extends BaseModel {
  content: string;
  role: MessageRole;
  session_id: string;
  files?: string[];
  thinking_content?: string;
  used_search?: boolean;
  metadata?: Record<string, any>;
  is_visible?: boolean;
  timestamp: string;
}

export interface ChatMessageCreate {
  content: string;
  files?: string[];
  use_thinking?: boolean;
  enable_search?: boolean;
  metadata?: Record<string, any>;
}

// Session types
export interface ChatSession extends BaseModel {
  title: string;
  model_id: string;
  system_instruction?: string;
  message_count: number;
  messages: ChatMessage[];
  settings: Record<string, any>;
  user_id?: string;
}

export interface ChatSessionCreate {
  title: string;
  model_name?: string;
  system_prompt?: string;
  temperature?: number;
  max_tokens?: number;
  settings?: Record<string, any>;
}

// Response types
export interface ChatResponse {
  response: ChatMessage;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  thinking_content?: string;
  search_results?: SearchResult[];
  processing_time_ms?: number;
}

// Model types
export interface ModelInfo {
  name: string;
  display_name: string;
  description: string;
  max_tokens: number;
  supports_thinking: boolean;
  supports_search: boolean;
  supports_vision: boolean;
  supports_function_calling: boolean;
  input_cost_per_token?: number;
  output_cost_per_token?: number;
  is_available: boolean;
}

export interface ModelSelection {
  model_name: string;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  top_k?: number;
}

// File types
export interface FileInfo {
  name: string;
  size: number;
  type: string;
  lastModified: number;
  path?: string;
}

export interface FileUploadResponse {
  file_id: string;
  filename: string;
  size: number;
  content_type: string;
  upload_url?: string;
  message: string;
}

// Search types
export interface SearchResult {
  title: string;
  url: string;
  snippet: string;
  source: string;
  timestamp?: string;
  relevance_score?: number;
  metadata?: Record<string, any>;
}

// RAG types  
export interface RAGRequest {
  query: string;
  k?: number;
  similarity_threshold?: number;
  include_metadata?: boolean;
  filter_criteria?: Record<string, any>;
}

export interface RAGResponse extends BaseModel {
  response: string;
  sources: SearchResult[];
  query: string;
  context_used: boolean;
  total_sources_found: number;
  processing_time_ms?: number;
}

// Knowledge Base Management
export interface KnowledgeBase extends BaseModel {
  name: string;
  description: string;
  document_count: number;
  total_chunks: number;
  settings: Record<string, any>;
}

export interface DocumentMetadata {
  title: string;
  source: string;
  document_type: string;
  author?: string;
  created_date?: string;
  file_size?: number;
  language: string;
  tags: string[];
  custom_fields: Record<string, any>;
}

export interface DocumentUploadRequest {
  knowledge_base_id: string;
  title: string;
  content: string;
  metadata: DocumentMetadata;
  process_immediately: boolean;
}

export interface DocumentUploadResponse {
  document_id: string;
  chunks_created: number;
  processing_status: string;
  message: string;
}

export interface ChatWithRAGRequest {
  message: string;
  session_id: string;
  knowledge_base_ids: string[];
  rag_config: RAGRequest;
  use_conversation_history: boolean;
  max_context_length: number;
}

export interface RAGChatResponse {
  response: string;
  sources_used: SearchResult[];
  context_length: number;
  tokens_used?: number;
  rag_confidence: number;
  session_id: string;
}

// User types
export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
  is_active: boolean;
  created_at: string;
  settings: {
    theme: 'light' | 'dark' | 'auto';
    language: string;
    timezone: string;
    notifications_enabled: boolean;
  };
}

export interface UserSettings {
  theme: 'light' | 'dark' | 'auto';
  language: string;
  timezone: string;
  notifications_enabled: boolean;
  auto_save: boolean;
  keyboard_shortcuts: boolean;
  typing_indicators: boolean;
  message_previews: boolean;
  sound_notifications: boolean;
  desktop_notifications: boolean;
  email_notifications: boolean;
  ai_personality: 'professional' | 'casual' | 'creative' | 'technical';
  default_model: string;
  max_context_length: number;
  temperature: number;
  response_format: 'markdown' | 'plain';
  show_thinking_process: boolean;
  enable_search_by_default: boolean;
  privacy_mode: boolean;
  data_retention_days: number;
}

// WebSocket types
export interface WebSocketMessage {
  type: 'message' | 'typing' | 'error' | 'connected' | 'disconnected';
  data?: any;
  timestamp: string;
  session_id?: string;
}

// Error types
export interface APIError {
  detail: string;
  status_code: number;
  timestamp: string;
  path?: string;
}

// Health check
export interface HealthCheck {
  status: 'healthy' | 'unhealthy';
  timestamp: string;
  version: string;
  uptime: number;
  services: {
    database: 'healthy' | 'unhealthy';
    redis: 'healthy' | 'unhealthy';
    genai: 'healthy' | 'unhealthy';
    vector_store: 'healthy' | 'unhealthy';
  };
}

// Usage stats
export interface UsageStats {
  total_messages: number;
  total_sessions: number;
  total_tokens_used: number;
  total_cost_usd?: number;
  models_used: Record<string, number>;
  features_used: {
    thinking_enabled: number;
    search_enabled: number;
    file_uploads: number;
    rag_queries: number;
  };
  time_period: {
    start: string;
    end: string;
  };
}

// Application settings
export interface AppSettings {
  app_name: string;
  app_version: string;
  api_version: string;
  environment: 'development' | 'staging' | 'production';
  features: {
    thinking_enabled: boolean;
    search_enabled: boolean;
    file_uploads_enabled: boolean;
    rag_enabled: boolean;
    user_accounts_enabled: boolean;
    billing_enabled: boolean;
    analytics_enabled: boolean;
    experimental_features: boolean;
  };
  limits: {
    max_message_length: number;
    max_file_size_mb: number;
    max_files_per_message: number;
    max_sessions_per_user: number;
    max_tokens_per_request: number;
    rate_limit_requests_per_minute: number;
  };
  ui: {
    default_theme: 'light' | 'dark' | 'auto';
    available_languages: string[];
    show_beta_features: boolean;
    enable_animations: boolean;
    compact_mode: boolean;
    sidebar_collapsed: boolean;
    message_timestamps: boolean;
    typing_indicators: boolean;
    read_receipts: boolean;
    message_reactions: boolean;
    threads_enabled: boolean;
    voice_messages: boolean;
    screen_sharing: boolean;
    collaborative_editing: boolean;
    real_time_collaboration: boolean;
    offline_mode: boolean;
    progressive_web_app: boolean;
    desktop_notifications: boolean;
    push_notifications: boolean;
    email_notifications: boolean;
    sms_notifications: boolean;
    webhook_notifications: boolean;
    zapier_integration: boolean;
    slack_integration: boolean;
    discord_integration: boolean;
    telegram_integration: boolean;
    whatsapp_integration: boolean;
    facebook_integration: boolean;
    twitter_integration: boolean;
    linkedin_integration: boolean;
    google_integration: boolean;
    microsoft_integration: boolean;
    apple_integration: boolean;
    github_integration: boolean;
    gitlab_integration: boolean;
    bitbucket_integration: boolean;
    jira_integration: boolean;
    confluence_integration: boolean;
    notion_integration: boolean;
    airtable_integration: boolean;
    monday_integration: boolean;
    asana_integration: boolean;
    trello_integration: boolean;
    basecamp_integration: boolean;
    clickup_integration: boolean;
    wrike_integration: boolean;
    smartsheet_integration: boolean;
    teamwork_integration: boolean;
    workfront_integration: boolean;
    clarizen_integration: boolean;
    workzone_integration: boolean;
    workamajig_integration: boolean;
    intervals_integration: boolean;
    harvest_integration: boolean;
    toggl_integration: boolean;
    clockwise_integration: boolean;
    rescuetime_integration: boolean;
    timely_integration: boolean;
    everhour_integration: boolean;
    clockify_integration: boolean;
    hubstaff_integration: boolean;
    desktime_integration: boolean;
    timecamp_integration: boolean;
    timeneye_integration: boolean;
    timedoctor_integration: boolean;
    workstack_integration: boolean;
    workpuls_integration: boolean;
    worksnaps_integration: boolean;
    workexaminer_integration: boolean;
    workmon_integration: boolean;
    worktime_integration: boolean;
    workplus_integration: boolean;
    workzoom_integration: boolean;
    worksight_integration: boolean;
    worklytics_integration: boolean;
    workboard_integration: boolean;
    workday_integration: boolean;
    workable_integration: boolean;
    workjam_integration: boolean;
    workplace_integration: boolean;
    workpath_integration: boolean;
    workfront_integration2: boolean;
    workhuman_integration: boolean;
    workiva_integration: boolean;
    workrise_integration: boolean;
    animations_enabled: boolean;
    sound_enabled: boolean;
  };
}

// Export utility types
export type ChatMessageWithoutId = Omit<ChatMessage, 'id' | 'created_at' | 'updated_at'>;
export type ChatSessionWithoutMessages = Omit<ChatSession, 'messages'>;
export type DocumentWithoutContent = Omit<Document, 'content'>;

// Type guards
export const isAPIError = (response: any): response is APIError => {
  return response && typeof response.detail === 'string' && typeof response.status_code === 'number';
};

export const isChatMessage = (obj: any): obj is ChatMessage => {
  return obj && typeof obj.content === 'string' && Object.values(MessageRole).includes(obj.role);
};

export const isWebSocketMessage = (obj: any): obj is WebSocketMessage => {
  return obj && typeof obj.type === 'string' && typeof obj.timestamp === 'string';
};