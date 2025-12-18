/**
 * 개선된 세션 관리 클라이언트 서비스
 * 다양한 세션 관리 방식을 지원하는 TypeScript 클라이언트
 */

import { writable, type Writable } from 'svelte/store';

// 타입 정의
export interface SessionMessage {
  id: number;
  sender: 'user' | 'maice';
  content: string;
  message_type: string;
  parent_message_id?: number;
  request_id?: string;
  created_at: string;
}

export interface SessionState {
  session_id: number;
  current_stage: string;
  last_message_type?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PaginatedHistory {
  messages: SessionMessage[];
  pagination: {
    page: number;
    page_size: number;
    total_count: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

export interface SessionAnalytics {
  period_days: number;
  total_sessions: number;
  avg_messages_per_session: number;
  avg_duration_minutes: number;
  completion_rate: number;
  stages_used: string[];
  message_type_distribution: Array<{
    type: string;
    count: number;
    avg_length: number;
  }>;
}

export interface WebSocketMessage {
  type: string;
  session_id?: number;
  data?: any;
  timestamp: string;
}

// 세션 백엔드 타입
export enum SessionBackendType {
  DATABASE_ONLY = 'database_only',
  HYBRID = 'hybrid',
  JWT_STATELESS = 'jwt_stateless',
  WEBSOCKET = 'websocket'
}

// 설정
interface SessionConfig {
  apiBaseUrl: string;
  wsBaseUrl: string;
  backendType: SessionBackendType;
  enableWebSocket: boolean;
  enableJwtTokens: boolean;
  cacheEnabled: boolean;
}

class EnhancedSessionService {
  private config: SessionConfig;
  private websocket: WebSocket | null = null;
  private jwtToken: string | null = null;
  private contextToken: string | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  
  // Svelte stores
  public currentSession: Writable<SessionState | null> = writable(null);
  public messages: Writable<SessionMessage[]> = writable([]);
  public connectionStatus: Writable<'connected' | 'disconnected' | 'reconnecting'> = writable('disconnected');
  public typingUsers: Writable<Set<number>> = writable(new Set());
  
  constructor(config: SessionConfig) {
    this.config = config;
  }

  // HTTP 요청 헬퍼
  private async makeRequest(
    endpoint: string, 
    options: RequestInit = {},
    useJwtAuth = false
  ): Promise<Response> {
    const url = `${this.config.apiBaseUrl}${endpoint}`;
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers
    };

    // JWT 토큰 인증
    if (useJwtAuth && this.jwtToken) {
      headers['Authorization'] = `Bearer ${this.jwtToken}`;
    }

    const response = await fetch(url, {
      ...options,
      headers
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response;
  }

  // 세션 생성 (개선된 버전)
  async createSessionEnhanced(initialQuestion: string): Promise<number> {
    const response = await this.makeRequest('/api/v1/sessions/create', {
      method: 'POST',
      body: JSON.stringify({ initial_question: initialQuestion })
    });

    const data = await response.json();
    console.log('✅ 개선된 세션 생성:', data);
    
    return data.session_id;
  }

  // JWT 토큰 기반 세션 관리
  async createSessionToken(sessionId: number): Promise<string> {
    if (!this.config.enableJwtTokens) {
      throw new Error('JWT 토큰이 비활성화되어 있습니다');
    }

    const response = await this.makeRequest('/api/v1/sessions/jwt/create-token', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId })
    });

    const data = await response.json();
    this.jwtToken = data.session_token;
    
    return data.session_token;
  }

  async createContextToken(sessionId: number): Promise<string> {
    if (!this.config.enableJwtTokens) {
      throw new Error('JWT 토큰이 비활성화되어 있습니다');
    }

    const response = await this.makeRequest('/api/v1/sessions/jwt/create-context-token', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId })
    });

    const data = await response.json();
    this.contextToken = data.context_token;
    
    return data.context_token;
  }

  async validateToken(): Promise<SessionState | null> {
    if (!this.jwtToken) return null;

    try {
      const response = await this.makeRequest('/api/v1/sessions/jwt/validate', {
        method: 'GET'
      }, true);

      return await response.json();
    } catch (error) {
      console.warn('토큰 검증 실패:', error);
      this.jwtToken = null;
      return null;
    }
  }

  // 페이지네이션 지원 히스토리 조회
  async getConversationHistory(
    sessionId: number,
    page = 1,
    pageSize = 20,
    messageTypes?: string[]
  ): Promise<PaginatedHistory> {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString()
    });

    if (messageTypes && messageTypes.length > 0) {
      messageTypes.forEach(type => params.append('message_types', type));
    }

    const response = await this.makeRequest(
      `/api/v1/sessions/${sessionId}/history?${params.toString()}`,
      { method: 'GET' }
    );

    return await response.json();
  }

  // 최적화된 세션 목록 조회
  async getUserSessionsOptimized(): Promise<SessionState[]> {
    const response = await this.makeRequest('/api/v1/sessions/my-sessions', {
      method: 'GET'
    });

    return await response.json();
  }

  // 세션 패턴 분석
  async getSessionAnalytics(days = 30): Promise<SessionAnalytics> {
    const response = await this.makeRequest(
      `/api/v1/sessions/analytics/patterns?days=${days}`,
      { method: 'GET' }
    );

    return await response.json();
  }

  // WebSocket 연결 관리
  async connectWebSocket(sessionId: number, userId: number): Promise<void> {
    if (!this.config.enableWebSocket) {
      throw new Error('WebSocket이 비활성화되어 있습니다');
    }

    const wsUrl = `${this.config.wsBaseUrl}/api/v1/sessions/ws/${sessionId}?user_id=${userId}`;
    
    this.websocket = new WebSocket(wsUrl);

    this.websocket.onopen = () => {
      console.log('✅ WebSocket 연결됨');
      this.connectionStatus.set('connected');
      this.reconnectAttempts = 0;
      
      // 하트비트 시작
      this.startHeartbeat();
    };

    this.websocket.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        this.handleWebSocketMessage(message);
      } catch (error) {
        console.error('WebSocket 메시지 파싱 오류:', error);
      }
    };

    this.websocket.onclose = () => {
      console.log('❌ WebSocket 연결 종료');
      this.connectionStatus.set('disconnected');
      this.attemptReconnect(sessionId, userId);
    };

    this.websocket.onerror = (error) => {
      console.error('WebSocket 오류:', error);
    };
  }

  private handleWebSocketMessage(message: WebSocketMessage): void {
    switch (message.type) {
      case 'new_message':
        // 새 메시지 수신
        this.messages.update(messages => [...messages, message.data]);
        break;
        
      case 'session_state':
        // 세션 상태 업데이트
        this.currentSession.set(message.data);
        break;
        
      case 'user_typing':
        // 타이핑 상태 업데이트
        if (message.data?.is_typing) {
          this.typingUsers.update(users => users.add(message.data.user_id));
        } else {
          this.typingUsers.update(users => {
            users.delete(message.data.user_id);
            return users;
          });
        }
        break;
        
      case 'pong':
        // 하트비트 응답
        break;
        
      default:
        console.log('알 수 없는 WebSocket 메시지:', message);
    }
  }

  private startHeartbeat(): void {
    const heartbeatInterval = setInterval(() => {
      if (this.websocket?.readyState === WebSocket.OPEN) {
        this.websocket.send(JSON.stringify({
          type: 'ping',
          timestamp: new Date().toISOString()
        }));
      } else {
        clearInterval(heartbeatInterval);
      }
    }, 30000); // 30초마다
  }

  private attemptReconnect(sessionId: number, userId: number): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      this.connectionStatus.set('reconnecting');
      
      setTimeout(() => {
        console.log(`재연결 시도 ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
        this.connectWebSocket(sessionId, userId);
      }, 1000 * this.reconnectAttempts); // 점진적 지연
    }
  }

  // 타이핑 상태 전송
  sendTypingStatus(isTyping: boolean): void {
    if (this.websocket?.readyState === WebSocket.OPEN) {
      this.websocket.send(JSON.stringify({
        type: isTyping ? 'typing_start' : 'typing_stop',
        timestamp: new Date().toISOString()
      }));
    }
  }

  // WebSocket 연결 종료
  disconnectWebSocket(): void {
    if (this.websocket) {
      this.websocket.close();
      this.websocket = null;
    }
    this.connectionStatus.set('disconnected');
  }

  // 서비스 상태 확인
  async checkHealth(): Promise<any> {
    const response = await this.makeRequest('/api/v1/sessions/health', {
      method: 'GET'
    });

    return await response.json();
  }

  // 리소스 정리
  cleanup(): void {
    this.disconnectWebSocket();
    this.jwtToken = null;
    this.contextToken = null;
  }
}

// 팩토리 함수
export function createEnhancedSessionService(): EnhancedSessionService {
  const config: SessionConfig = {
    apiBaseUrl: import.meta.env.VITE_API_BASE_URL || '',
    wsBaseUrl: import.meta.env.VITE_WS_BASE_URL ?? 'ws://localhost:8000',
    backendType: (import.meta.env.VITE_SESSION_BACKEND as SessionBackendType) || SessionBackendType.DATABASE_ONLY,
    enableWebSocket: import.meta.env.VITE_ENABLE_WEBSOCKET === 'true',
    enableJwtTokens: import.meta.env.VITE_ENABLE_JWT_TOKENS === 'true',
    cacheEnabled: import.meta.env.VITE_CACHE_ENABLED !== 'false'
  };

  return new EnhancedSessionService(config);
}

// 전역 서비스 인스턴스
export const sessionService = createEnhancedSessionService();
