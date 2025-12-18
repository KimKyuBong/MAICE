/**
 * 표준화된 MAICE API 클라이언트
 * 프론트엔드와 백엔드 간의 통신을 최적화하고 표준화
 */

import type {
  BaseResponse,
  ChatRequest,
  ClarificationRequest,
  SessionRequest,
  ChatResponse,
  ClarificationResponse,
  SessionResponse,
  MaiceAPIClient,
  ChatEventHandlers,
  SSEMessage,
  ErrorCodeType
} from '../types/api';
import { log } from '../utils/logger';

// ============================================================================
// API 설정
// ============================================================================

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
const USE_MOCK_API = import.meta.env.VITE_USE_MOCK_API === 'true';

// ============================================================================
// 유틸리티 함수
// ============================================================================

const getHeaders = (token?: string): Record<string, string> => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  return headers;
};

const handleApiError = (error: any): never => {
  log.error('API 오류:', error);
  throw new Error(error.message || 'API 호출 중 오류가 발생했습니다.');
};

// 토큰 만료 시 자동 로그아웃 처리
const handleUnauthorized = () => {
  if (typeof window !== 'undefined') {
    console.warn('⚠️ 인증되지 않은 요청입니다. 로그아웃 처리합니다.');
    import('../stores/auth').then(({ authActions }) => {
      authActions.logout();
    });
  }
};

// 안전한 fetch 래퍼 함수
const safeFetch = async (url: string, options: RequestInit = {}): Promise<Response> => {
  const response = await fetch(url, options);
  
  // 401 에러 발생 시 자동 로그아웃 처리
  if (response.status === 401) {
    handleUnauthorized();
    throw new Error('인증이 만료되었습니다. 다시 로그인해주세요.');
  }
  
  return response;
};

// ============================================================================
// 표준화된 MAICE API 클라이언트
// ============================================================================

export class MaiceAPIClientImpl implements MaiceAPIClient {
  private token?: string;
  private baseUrl: string;

  constructor(token?: string) {
    this.token = token;
    this.baseUrl = `${API_BASE_URL}/api`;
  }

  setToken(token: string): void {
    this.token = token;
  }

  // ========================================================================
  // 유틸리티 메서드
  // ========================================================================

  private isValidJSON(str: string): boolean {
    try {
      JSON.parse(str);
      return true;
    } catch {
      return false;
    }
  }

  // ========================================================================
  // 채팅 관련 메서드
  // ========================================================================

  async chat(request: ChatRequest): Promise<Response> {
    if (USE_MOCK_API) {
      return this.createMockChatResponse(request);
    }

    try {
      console.log('🚀 MAICE 채팅 요청:', {
        message: request.message.substring(0, 50) + '...',
        session_id: request.session_id,
        message_type: request.message_type
      });

      const response = await safeFetch(`${this.baseUrl}/chat`, {
        method: 'POST',
        headers: getHeaders(this.token),
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error?.message || `채팅 요청 실패: ${response.status}`);
      }

      return response;
    } catch (error) {
      console.error('❌ 채팅 요청 오류:', error);
      throw error;
    }
  }

  async chatStream(request: ChatRequest, handlers: ChatEventHandlers, abortController?: AbortController): Promise<{ sessionId?: number; requestId?: string }> {
    if (USE_MOCK_API) {
      // Mock SSE stream
      let mockSessionId = request.session_id || Math.floor(Math.random() * 1000) + 1;
      let mockRequestId = request.request_id || `mock_${Date.now()}`;
      
      handlers.onMessage?.({ type: 'session_created', session_id: mockSessionId, request_id: mockRequestId, timestamp: new Date().toISOString() });
      handlers.onMessage?.({ type: 'processing', message: '질문을 처리 중입니다...', session_id: mockSessionId, request_id: mockRequestId, timestamp: new Date().toISOString() });
      
      const mockAnswer = `"${request.message}"에 대한 모의 답변입니다. MAICE AI가 학습을 도와드리겠습니다! 📚\n\n**모의 응답:**\n이것은 테스트용 모의 응답입니다. 실제 백엔드 연결 시 정확한 답변이 제공됩니다.`;
      const chunks = mockAnswer.split(' ');
      for (let i = 0; i < chunks.length; i++) {
        await new Promise(resolve => setTimeout(resolve, 50));
        handlers.onMessage?.({ type: 'streaming_chunk', content: chunks[i] + ' ', chunk_index: i, is_final: i === chunks.length - 1, session_id: mockSessionId, request_id: mockRequestId, timestamp: new Date().toISOString() });
      }
      handlers.onMessage?.({ type: 'answer_complete', session_id: mockSessionId, request_id: mockRequestId, timestamp: new Date().toISOString() });
      handlers.onComplete?.();
      return { sessionId: mockSessionId, requestId: mockRequestId };
    }

    // 테스트 모드 확인 (개발 환경에서만 허용)
    const isTestMode = import.meta.env.DEV && window.location.search.includes('test=true');
    console.log('🔍 MaiceAPIClient 테스트 모드 체크:', {
      hasTestParam: window.location.search.includes('test=true'),
      isDev: import.meta.env.DEV,
      viteEnv: import.meta.env.VITE_ENVIRONMENT,
      isTestMode: isTestMode
    });
    
    const url = isTestMode ? 
      `${this.baseUrl}/student/chat-test` : 
      `${this.baseUrl}/student/chat`;
    // 테스트 모드에서는 인증 헤더 없이 호출
    const headers = isTestMode ? 
      { 'Content-Type': 'application/json' } : 
      getHeaders(this.token);
    
    const response = await safeFetch(url, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify({
        message: request.message,
        session_id: request.session_id,
        request_id: request.request_id,
        message_type: request.message_type,
        conversation_history: request.conversation_history,
      }),
      signal: abortController?.signal, // AbortController 신호 추가
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      handlers.onError?.(errorData.error?.message || `채팅 스트림 시작 실패: ${response.status}`);
      throw new Error(errorData.error?.message || `채팅 스트림 시작 실패: ${response.status}`);
    }

    if (!response.body) {
      handlers.onError?.('Response body가 없습니다.');
      throw new Error('Response body가 없습니다.');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let currentSessionId = request.session_id;
    let currentRequestId = request.request_id;

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          handlers.onComplete?.();
          return { sessionId: currentSessionId, requestId: currentRequestId };
        }

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (!line.trim() || line.startsWith(':')) {
            continue;
          }

          if (line.startsWith('data: ')) {
            try {
              const jsonStr = line.slice(6).trim();
              if (!jsonStr) continue;
              
              // JSON 파싱 전에 문자열 검증
              if (!this.isValidJSON(jsonStr)) {
                console.warn('⚠️ 유효하지 않은 JSON 문자열:', jsonStr.substring(0, 100) + '...');
                continue;
              }
              
              const data: SSEMessage = JSON.parse(jsonStr);
              
              // 세션 ID 필터링 - session_info는 항상 허용 (새 세션 생성 시)
              if (data.type !== 'session_info' && data.session_id !== undefined && currentSessionId !== undefined && 
                  data.session_id !== currentSessionId) {
                console.log('⚠️ 다른 세션의 메시지 무시:', data.session_id, '!==', currentSessionId, '타입:', data.type);
                continue;
              }
              
              // 세션 ID 업데이트 처리
              if ((data.type === 'session_created' || data.type === 'session_status' || data.type === 'session_info') && data.session_id !== undefined) {
                currentSessionId = data.session_id;
                console.log('✅ 세션 ID 업데이트:', currentSessionId, '타입:', data.type);
              }
              if (data.request_id) {
                currentRequestId = data.request_id;
              }
              
              // 메시지 타입에 따라 적절한 핸들러 호출
              this.handleSSEMessage(data, handlers);

              if (data.type === 'complete' || data.type === 'error') {
                handlers.onComplete?.();
                return { sessionId: currentSessionId, requestId: currentRequestId };
              }
            } catch (parseError) {
              console.error('❌ SSE 데이터 파싱 오류:', parseError);
              console.error('❌ 원본 라인:', line);
              handlers.onError?.(`SSE 데이터 파싱 오류: ${parseError}`);
              continue;
            }
          }
        }
      }
    } catch (error: any) {
      // AbortError는 정상적인 중단이므로 에러로 처리하지 않음
      if (error.name === 'AbortError') {
        console.log('🔌 SSE 스트림이 정상적으로 중단됨');
        handlers.onComplete?.();
        return { sessionId: currentSessionId, requestId: currentRequestId };
      }
      
      console.error('💥 SSE 스트림 처리 오류:', error);
      handlers.onError?.(error.message || 'SSE 스트림 처리 중 오류가 발생했습니다.');
      throw error;
    }
  }

  async submitClarification(request: ClarificationRequest): Promise<BaseResponse<ClarificationResponse>> {
    if (USE_MOCK_API) {
      return this.createMockClarificationResponse(request);
    }

    try {
      console.log('🔄 명료화 답변 제출:', {
        clarification_answer: request.clarification_answer.substring(0, 50) + '...',
        session_id: request.session_id
      });

      const response = await safeFetch(`${this.baseUrl}/clarification`, {
        method: 'POST',
        headers: getHeaders(this.token),
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error?.message || `명료화 답변 제출 실패: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('❌ 명료화 답변 제출 오류:', error);
      throw error;
    }
  }

  // ========================================================================
  // 세션 관련 메서드
  // ========================================================================

  async createSession(request: SessionRequest): Promise<BaseResponse<SessionResponse>> {
    if (USE_MOCK_API) {
      return this.createMockSessionResponse(request);
    }

    try {
      console.log('🆕 세션 생성 요청:', request);

      const response = await safeFetch(`${this.baseUrl}/sessions`, {
        method: 'POST',
        headers: getHeaders(this.token),
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error?.message || `세션 생성 실패: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('❌ 세션 생성 오류:', error);
      throw error;
    }
  }

  async getSession(sessionId: number): Promise<BaseResponse<SessionResponse>> {
    if (USE_MOCK_API) {
      return this.createMockSessionInfoResponse(sessionId);
    }

    try {
      console.log('📊 세션 정보 조회:', sessionId);

      const response = await safeFetch(`${this.baseUrl}/sessions/${sessionId}`, {
        method: 'GET',
        headers: getHeaders(this.token),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error?.message || `세션 조회 실패: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('❌ 세션 조회 오류:', error);
      throw error;
    }
  }

  async deleteSession(sessionId: number): Promise<BaseResponse<SessionResponse>> {
    if (USE_MOCK_API) {
      return this.createMockSessionDeleteResponse(sessionId);
    }

    try {
      console.log('🗑️ 세션 삭제:', sessionId);

      const response = await safeFetch(`${this.baseUrl}/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: getHeaders(this.token),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error?.message || `세션 삭제 실패: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('❌ 세션 삭제 오류:', error);
      throw error;
    }
  }

  // ========================================================================
  // 이미지 → LaTeX 변환
  // ========================================================================

  async convertImageToLatex(imageFile: File): Promise<BaseResponse<{ latex: string; filename: string; file_size: number; content_type: string }>> {
    try {
      console.log('🖼️ 이미지 → LaTeX 변환 요청:', {
        filename: imageFile.name,
        size: imageFile.size,
        type: imageFile.type
      });

      const formData = new FormData();
      formData.append('image', imageFile);

      const response = await safeFetch(`${this.baseUrl}/student/convert-image-to-latex`, {
        method: 'POST',
        headers: {
          // FormData 사용 시 Content-Type 헤더는 자동으로 설정됨
          ...(this.token && { 'Authorization': `Bearer ${this.token}` })
        },
        body: formData,
        credentials: 'include'
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `이미지 변환 실패: ${response.status}`);
      }

      const result = await response.json();
      console.log('✅ 이미지 → LaTeX 변환 성공:', result);
      return result;
    } catch (error) {
      console.error('❌ 이미지 → LaTeX 변환 오류:', error);
      throw error;
    }
  }

  // ========================================================================
  // 헬스 체크
  // ========================================================================

  async healthCheck(): Promise<BaseResponse> {
    try {
      const response = await safeFetch(`${this.baseUrl}/health`, {
        method: 'GET',
        headers: getHeaders(this.token),
      });

      if (!response.ok) {
        throw new Error(`헬스 체크 실패: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('❌ 헬스 체크 오류:', error);
      throw error;
    }
  }

  // ========================================================================
  // SSE 스트리밍 메서드
  // ========================================================================

  async startChatStream(
    request: ChatRequest,
    handlers: ChatEventHandlers
  ): Promise<{ sessionId?: number; requestId?: string }> {
    try {
      const response = await this.chat(request);
      
      if (!response.body) {
        throw new Error('Response body가 없습니다.');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      
      let currentSessionId = request.session_id;
      let currentRequestId = request.request_id;

      try {
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) {
            if (handlers.onComplete) handlers.onComplete();
            return { sessionId: currentSessionId, requestId: currentRequestId };
          }
          
          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');
          
          for (const line of lines) {
            if (!line.trim() || line.startsWith(':')) {
              continue;
            }
            
            if (line.startsWith('data: ')) {
              try {
                const jsonStr = line.slice(6).trim();
                if (!jsonStr) continue;
                
                const data: SSEMessage = JSON.parse(jsonStr);
                
                // 세션 정보 업데이트
                if (data.type === 'connected' && data.data?.session_id) {
                  currentSessionId = data.data.session_id;
                }
                if (data.request_id) {
                  currentRequestId = data.request_id;
                }
                
                // 이벤트 핸들러 호출
                this.handleSSEMessage(data, handlers);
                
                // 완료 또는 에러 시 종료
                if (data.type === 'complete' || data.type === 'error') {
                  if (handlers.onComplete) handlers.onComplete();
                  return { sessionId: currentSessionId, requestId: currentRequestId };
                }
                
              } catch (parseError) {
                console.error('❌ SSE 데이터 파싱 오류:', parseError);
                continue;
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }
    } catch (error) {
      console.error('❌ 채팅 스트림 오류:', error);
      if (handlers.onError) handlers.onError(error instanceof Error ? error.message : String(error));
      throw error;
    }
  }

  private handleSSEMessage(data: SSEMessage, handlers: ChatEventHandlers): void {
    console.log('🔍 SSE 메시지 처리:', data.type, data);
    
    switch (data.type) {
      case 'connected':
        if (handlers.onConnected) handlers.onConnected(data.data);
        break;
      case 'session_status':
        // 세션 상태 정보 처리 - onConnected로 전달하여 session_id 저장
        if (handlers.onConnected) {
          handlers.onConnected({
            session_id: data.session_id,
            request_id: data.request_id,
            current_stage: data.current_stage,
            last_message_type: data.last_message_type,
            message: data.message
          });
        }
        break;
      case 'session_info':
        // 세션 정보 처리 - onConnected로 전달하여 session_id 저장
        if (handlers.onConnected) {
          handlers.onConnected({
            session_id: data.session_id,
            request_id: data.request_id,
            message: data.message
          });
        }
        break;
      case 'processing':
        if (handlers.onProcessing) handlers.onProcessing(data.data);
        break;
      case 'clarification':
      case 'clarification_question':
        if (handlers.onClarification) handlers.onClarification(data);
        break;
      case 'streaming_chunk':
        // 통일된 스트리밍 청크 처리 (모드 구분 없음)
        if (handlers.onAnswer) handlers.onAnswer(data);
        break;
      case 'answer':
        // answer는 완료된 전체 답변 처리 (필요시)
        console.log('📝 완전한 답변 수신:', data);
        // 필요하다면 별도 핸들러로 처리
        break;
      case 'streaming_complete':
      case 'complete':
      case 'answer_complete':
        // 스트리밍 완료 처리 (모드 구분 없음)
        if (handlers.onAnswerComplete) {
          handlers.onAnswerComplete(data);
        } else if (handlers.onComplete) {
          handlers.onComplete();
        }
        break;
      case 'summary_complete':
        // 요약 완료 - onMessage로 전달하여 프론트에서 처리
        if (handlers.onMessage) {
          handlers.onMessage(data);
        }
        break;
      case 'error':
      case 'freepass_error':
        // 에러 처리 (모드 구분 없음)
        if (handlers.onError) handlers.onError(data.data?.message || data.error || '알 수 없는 오류');
        break;
      default:
        console.log('⚠️ 알 수 없는 메시지 타입:', data.type);
        // 알 수 없는 타입도 onMessage로 전달
        if (handlers.onMessage) handlers.onMessage(data);
        break;
    }
  }

  // ========================================================================
  // Mock 응답 생성 (개발/테스트용)
  // ========================================================================

  private async createMockChatResponse(request: ChatRequest): Promise<Response> {
    const mockData = {
      success: true,
      data: {
        type: 'connected',
        message: 'MAICE 연결됨 (Mock)'
      },
      meta: {
        timestamp: new Date().toISOString(),
        request_id: request.request_id || 'mock_' + Date.now(),
        session_id: request.session_id
      }
    };

    return new Response(
      `data: ${JSON.stringify(mockData)}\n\n`,
      {
        status: 200,
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
        }
      }
    );
  }

  private createMockClarificationResponse(request: ClarificationRequest): BaseResponse<ClarificationResponse> {
    return {
      success: true,
      data: {
        type: 'clarification_complete',
        message: '명료화 답변이 처리되었습니다 (Mock)',
        result: {
          improved_question: `개선된 질문: ${request.clarification_answer}`,
          user_responses: [request.clarification_answer]
        }
      },
      meta: {
        timestamp: new Date().toISOString(),
        request_id: request.request_id || 'mock_' + Date.now(),
        session_id: request.session_id
      }
    };
  }

  private createMockSessionResponse(request: SessionRequest): BaseResponse<SessionResponse> {
    const sessionId = Math.floor(Math.random() * 1000) + 1;
    return {
      success: true,
      data: {
        type: 'session_created',
        session_id: sessionId,
        message: '새 세션이 생성되었습니다 (Mock)',
        initial_question: request.initial_question
      },
      meta: {
        timestamp: new Date().toISOString(),
        request_id: 'mock_' + Date.now(),
        session_id: sessionId
      }
    };
  }

  private createMockSessionInfoResponse(sessionId: number): BaseResponse<SessionResponse> {
    return {
      success: true,
      data: {
        type: 'session_info',
        session_id: sessionId,
        message: '세션 정보 조회 완료 (Mock)',
        session: {
          id: sessionId,
          user_id: 1,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          current_stage: 'initial_question',
          last_message_type: 'question',
          conversation_count: 0
        }
      },
      meta: {
        timestamp: new Date().toISOString(),
        request_id: 'mock_' + Date.now(),
        session_id: sessionId
      }
    };
  }

  private createMockSessionDeleteResponse(sessionId: number): BaseResponse<SessionResponse> {
    return {
      success: true,
      data: {
        type: 'session_deleted',
        session_id: sessionId,
        message: '세션이 삭제되었습니다 (Mock)'
      },
      meta: {
        timestamp: new Date().toISOString(),
        request_id: 'mock_' + Date.now(),
        session_id: sessionId
      }
    };
  }
}

// ============================================================================
// 싱글톤 인스턴스 및 팩토리 함수
// ============================================================================

let instance: MaiceAPIClientImpl | null = null;

export const createMaiceAPIClient = (token?: string): MaiceAPIClientImpl => {
  if (!instance) {
    instance = new MaiceAPIClientImpl(token);
  } else if (token) {
    instance.setToken(token);
  }
  return instance;
};

export const getMaiceAPIClient = (): MaiceAPIClientImpl => {
  if (!instance) {
    throw new Error('MAICE API 클라이언트가 초기화되지 않았습니다.');
  }
  return instance;
};
