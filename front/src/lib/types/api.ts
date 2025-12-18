/**
 * 표준화된 API 타입 정의
 * 프론트엔드와 백엔드 간의 통신을 위한 공통 타입
 */

// ============================================================================
// 기본 요청/응답 타입
// ============================================================================

export interface BaseRequest {
  session_id?: number;
  request_id?: string;
  timestamp?: string;
}

export interface BaseResponse<T = any> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
  meta?: {
    timestamp: string;
    request_id: string;
    session_id?: number;
  };
}

// ============================================================================
// 에러 코드 상수
// ============================================================================

export const ErrorCode = {
  // 인증 관련
  UNAUTHORIZED: 'AUTH_001',
  TOKEN_EXPIRED: 'AUTH_002',
  
  // 세션 관련
  SESSION_NOT_FOUND: 'SESSION_001',
  SESSION_EXPIRED: 'SESSION_002',
  
  // 질문 처리 관련
  QUESTION_INVALID: 'QUESTION_001',
  CLARIFICATION_NEEDED: 'QUESTION_002',
  
  // 시스템 관련
  INTERNAL_ERROR: 'SYS_001',
  SERVICE_UNAVAILABLE: 'SYS_002'
} as const;

export type ErrorCodeType = typeof ErrorCode[keyof typeof ErrorCode];

// ============================================================================
// MAICE 채팅 관련 타입
// ============================================================================

export interface ChatRequest extends BaseRequest {
  message: string;
  message_type?: 'question' | 'clarification_response'; // 백엔드에서 판단하므로 선택적
  conversation_history?: string[];
}

export interface ClarificationRequest extends BaseRequest {
  clarification_answer: string;
  question_index: number;
  total_questions: number;
}

export interface SessionRequest {
  initial_question?: string;
}

// ============================================================================
// 이미지 → LaTeX 변환 관련 타입
// ============================================================================

export interface ImageToLatexResponse {
  type: 'image_to_latex_conversion';
  latex: string;
  filename: string;
  file_size: number;
  content_type: string;
  success: boolean;
}

// ============================================================================
// SSE 메시지 타입
// ============================================================================

export type SSEMessageType = 
  | 'connected'
  | 'processing'
  | 'clarification'
  | 'clarification_question'
  | 'answer'
  | 'streaming_chunk'
  | 'streaming_complete'
  | 'answer_complete'
  | 'complete'
  | 'error'
  | 'session_status'
  | 'session_created'
  | 'session_info'
  | 'question_status'
  | 'clarification_status'
  | 'summary_complete'
  | 'freepass_error';

export interface SSEMessage<T = any> {
  type: SSEMessageType;
  data?: T;
  timestamp?: string;
  session_id?: number;
  request_id?: string;
  message?: string;
  
  // session_status 전용 필드
  current_stage?: string;
  last_message_type?: string;
  
  // streaming_chunk 전용 필드
  content?: string;  // 통일된 필드명
  chunk_index?: number;
  is_final?: boolean;
  
  // clarification 전용 필드
  question_index?: number;
  total_questions?: number;
  
  // 기타 필드
  status?: string;
  progress?: number;
  summary?: string;
  error?: string;
}

// ============================================================================
// 채팅 응답 타입
// ============================================================================

export interface ChatResponse {
  message: string;
  session_id: number;
  completed: boolean;
  clarification_needed?: boolean;
  clarification_questions?: string[];
  metadata?: {
    knowledge_code?: string;
    quality?: string;
    reasoning?: string;
  };
}

export interface ClarificationResponse {
  type: 'clarification_complete';
  message: string;
  result: {
    improved_question: string;
    user_responses: string[];
  };
}

export interface SessionResponse {
  type: 'session_created' | 'session_info' | 'session_deleted';
  session_id: number;
  message: string;
  initial_question?: string;
  session?: {
    id: number;
    user_id: number;
    created_at: string;
    updated_at: string;
    current_stage: string;
    last_message_type: string;
    conversation_count: number;
  };
}

// ============================================================================
// API 클라이언트 인터페이스
// ============================================================================

export interface MaiceAPIClient {
  // 채팅 관련
  chat(request: ChatRequest): Promise<Response>;
  submitClarification(request: ClarificationRequest): Promise<BaseResponse<ClarificationResponse>>;
  
  // 세션 관련
  createSession(request: SessionRequest): Promise<BaseResponse<SessionResponse>>;
  getSession(sessionId: number): Promise<BaseResponse<SessionResponse>>;
  deleteSession(sessionId: number): Promise<BaseResponse<SessionResponse>>;
  
  // 이미지 → LaTeX 변환
  convertImageToLatex(imageFile: File): Promise<BaseResponse<ImageToLatexResponse>>;
  
  // 헬스 체크
  healthCheck(): Promise<BaseResponse>;
}

// ============================================================================
// 이벤트 핸들러 타입
// ============================================================================

export interface ChatEventHandlers {
  onConnected?: (data: any) => void;
  onProcessing?: (data: any) => void;
  onClarification?: (data: any) => void;
  onAnswer?: (data: any) => void;
  onAnswerComplete?: (data: any) => void;
  onMessage?: (data: any) => void;
  onComplete?: () => void;
  onError?: (error: string) => void;
  // 모드 구분 없이 통일된 핸들러 사용
}

// ============================================================================
// 유틸리티 타입
// ============================================================================

export interface DebugInfo {
  request_id: string;
  session_id?: number;
  timestamp: string;
  duration: number;
  status: 'success' | 'error';
  endpoint: string;
}

export interface APILog {
  level: 'debug' | 'info' | 'warn' | 'error';
  message: string;
  context: {
    request_id: string;
    session_id?: number;
    user_id?: number;
    endpoint: string;
    duration: number;
  };
}


// ============================================================================
// 기존 호환성을 위한 타입 (점진적 마이그레이션용)
// ============================================================================

// 레거시 타입들 제거됨 - 새로운 SessionMessage 기반 타입 사용
