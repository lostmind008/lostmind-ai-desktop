'use client';

import React, { useState, useEffect, useRef } from 'react';
import { ChatMessage, ChatSession } from '@/types/api';
import { websocketService } from '@/services/websocket';
import { apiService } from '@/services/api';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import SessionSidebar from './SessionSidebar';
import { toast } from 'react-hot-toast';

interface ChatInterfaceProps {
  initialSessionId?: string;
}

export default function ChatInterface({ initialSessionId }: ChatInterfaceProps) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // initialize websocket connection
  useEffect(() => {
    const initializeWebSocket = async () => {
      try {
        await websocketService.connect();
        setIsConnected(true);
        
        // set up event listeners
        websocketService.onMessage((message: ChatMessage) => {
          setMessages(prev => [...prev, message]);
          setIsTyping(false);
        });

        websocketService.onTyping((typing: boolean) => {
          setIsTyping(typing);
        });

        websocketService.onError((error: string) => {
          toast.error(`WebSocket error: ${error}`);
          setIsConnected(false);
        });

        websocketService.onDisconnect(() => {
          setIsConnected(false);
          toast.error('Disconnected from server');
        });

        websocketService.onReconnect(() => {
          setIsConnected(true);
          toast.success('Reconnected to server');
        });

      } catch (error) {
        console.error('Failed to initialize WebSocket:', error);
        toast.error('Failed to connect to chat service');
      }
    };

    initializeWebSocket();

    return () => {
      websocketService.disconnect();
    };
  }, []);

  // load sessions on component mount
  useEffect(() => {
    loadSessions();
  }, []);

  // load specific session if provided
  useEffect(() => {
    if (initialSessionId && sessions.length > 0) {
      const session = sessions.find(s => s.id === initialSessionId);
      if (session) {
        selectSession(session);
      }
    }
  }, [initialSessionId, sessions]);

  const loadSessions = async () => {
    try {
      const loadedSessions = await apiService.getChatSessions();
      setSessions(loadedSessions);
      
      // if no current session and we have sessions, select the most recent
      if (!currentSession && loadedSessions.length > 0) {
        selectSession(loadedSessions[0]);
      }
    } catch (error) {
      console.error('Failed to load sessions:', error);
      toast.error('Failed to load chat sessions');
    }
  };

  const selectSession = async (session: ChatSession) => {
    try {
      setIsLoading(true);
      setCurrentSession(session);
      
      // load messages for this session
      const sessionMessages = await apiService.getChatHistory(session.id);
      setMessages(sessionMessages);
      
      // join websocket room for this session
      await websocketService.joinSession(session.id);
      
    } catch (error) {
      console.error('Failed to select session:', error);
      toast.error('Failed to load session');
    } finally {
      setIsLoading(false);
    }
  };

  const createNewSession = async () => {
    try {
      const newSession = await apiService.createChatSession({
        title: 'New Chat',
        model_name: 'gemini-2.0-flash'
      });
      
      setSessions(prev => [newSession, ...prev]);
      selectSession(newSession);
      toast.success('New chat created');
    } catch (error) {
      console.error('Failed to create session:', error);
      toast.error('Failed to create new chat');
    }
  };

  const deleteSession = async (sessionId: string) => {
    try {
      await apiService.deleteChatSession(sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      
      // if deleted session was current, select another or create new
      if (currentSession?.id === sessionId) {
        const remainingSessions = sessions.filter(s => s.id !== sessionId);
        if (remainingSessions.length > 0) {
          selectSession(remainingSessions[0]);
        } else {
          setCurrentSession(null);
          setMessages([]);
        }
      }
      
      toast.success('Chat deleted');
    } catch (error) {
      console.error('Failed to delete session:', error);
      toast.error('Failed to delete chat');
    }
  };

  const sendMessage = async (
    content: string, 
    files: string[] = [], 
    useThinking: boolean = true,
    enableSearch: boolean = false
  ) => {
    if (!currentSession || !content.trim()) return;

    try {
      // add user message immediately to UI
      const userMessage: ChatMessage = {
        id: Date.now().toString(),
        content: content.trim(),
        role: 'user',
        session_id: currentSession.id,
        timestamp: new Date().toISOString(),
        files
      };
      
      setMessages(prev => [...prev, userMessage]);
      setIsTyping(true);

      // send via websocket
      await websocketService.sendMessage(content, files, useThinking, enableSearch);
      
    } catch (error) {
      console.error('Failed to send message:', error);
      toast.error('Failed to send message');
      setIsTyping(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Session Sidebar */}
      <SessionSidebar
        sessions={sessions}
        currentSession={currentSession}
        onSelectSession={selectSession}
        onCreateSession={createNewSession}
        onDeleteSession={deleteSession}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              {!sidebarOpen && (
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                </button>
              )}
              <h1 className="text-xl font-semibold text-gray-900">
                {currentSession?.title || 'Select a chat'}
              </h1>
            </div>
            
            <div className="flex items-center space-x-2">
              {/* Connection Status */}
              <div className={`flex items-center space-x-2 px-3 py-1 rounded-full text-sm ${
                isConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
              }`}>
                <div className={`w-2 h-2 rounded-full ${
                  isConnected ? 'bg-green-500' : 'bg-red-500'
                }`} />
                <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-hidden">
          {currentSession ? (
            <MessageList 
              messages={messages}
              isLoading={isLoading}
              isTyping={isTyping}
            />
          ) : (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center">
                  <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">Welcome to LostMindAI</h3>
                <p className="text-gray-500 mb-4">Create a new chat or select an existing one to get started</p>
                <button
                  onClick={createNewSession}
                  className="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-6 py-2 rounded-lg font-medium hover:from-purple-700 hover:to-pink-700 transition-all duration-200"
                >
                  Start New Chat
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Message Input */}
        {currentSession && (
          <MessageInput
            onSendMessage={sendMessage}
            disabled={!isConnected}
          />
        )}
      </div>
    </div>
  );
}