import type { MAICEChatRequest } from '$lib/api';

export interface ChatMessage {
	id: number;
	type: 'user' | 'ai';
	content: string;
	timestamp: string;
	isClarification?: boolean;
	isStreaming?: boolean;
	requestId?: string; // 각 메시지를 고유하게 식별
}

export interface ChatState {
	messages: ChatMessage[];
	isLoading: boolean;
	sessionId: number | null;
	requestId: string | null;
}

export interface SSEHandler {
	onConnected: (data: any) => void;
	onClarificationQuestion: (data: any) => void;
	onAnswerChunk: (data: any) => void;
	onAnswerComplete: (data: any) => void;
	onComplete: (data: any) => void;
	onProcessing: (data: any) => void;
	onMessage: (data: any) => void;
	// 모드 구분 없이 통일된 핸들러 사용
}

export function createDefaultMessage(): ChatMessage {
	return {
		id: 1,
		type: 'ai',
		content: '안녕하세요! MAICE AI 학습 도우미입니다. 무엇을 도와드릴까요?\n\n**사용 예시:**\n\n### 1. 정의와 공식\n등차수열의 일반항 공식이 뭐예요?\n\n### 2. 관계와 원리\n등차수열과 등비수열의 차이점은 무엇인가요?\n\n### 3. 해결 방법\n`$a_n = 2n + 1$`의 첫 10항의 합을 구하는 방법을 알려주세요\n\n### 4. 문제 접근법\n수열 문제를 풀 때 어떤 순서로 접근해야 할까요?\n\n마크다운과 LaTeX 수식을 모두 지원합니다! 📚✨',
		timestamp: new Date().toLocaleTimeString()
	};
}

export function createUserMessage(content: string, messageId: number): ChatMessage {
	return {
		id: messageId,
		type: 'user',
		content,
		timestamp: new Date().toLocaleTimeString()
	};
}

export function createAIMessage(content: string, messageId: number, isClarification = false): ChatMessage {
	return {
		id: messageId,
		type: 'ai',
		content,
		timestamp: new Date().toLocaleTimeString(),
		isClarification
	};
}

// 에러 타입 정의
export interface ErrorInfo {
	type: 'network' | 'server' | 'client' | 'timeout' | 'unknown';
	message: string;
	userMessage: string;
	retryable: boolean;
	code?: string;
}

// 에러 분류 함수
export function classifyError(error: any): ErrorInfo {
	console.error('🔍 에러 분석 중:', error);
	
	// 네트워크 에러
	if (error.name === 'TypeError' && error.message && error.message.includes('fetch')) {
		return {
			type: 'network',
			message: error.message,
			userMessage: '🌐 네트워크 연결을 확인해주세요. 인터넷 연결이 불안정할 수 있습니다.',
			retryable: true,
			code: 'NETWORK_ERROR'
		};
	}
	
	// HTTP 상태 코드 기반 에러
	if (error.response) {
		const status = error.response.status;
		switch (status) {
			case 401:
				return {
					type: 'client',
					message: '인증이 필요합니다',
					userMessage: '🔐 로그인이 필요합니다. 다시 로그인해주세요.',
					retryable: false,
					code: 'UNAUTHORIZED'
				};
			case 403:
				return {
					type: 'client',
					message: '접근 권한이 없습니다',
					userMessage: '🚫 접근 권한이 없습니다. 관리자에게 문의해주세요.',
					retryable: false,
					code: 'FORBIDDEN'
				};
			case 404:
				return {
					type: 'client',
					message: '요청한 리소스를 찾을 수 없습니다',
					userMessage: '🔍 요청한 서비스를 찾을 수 없습니다. 잠시 후 다시 시도해주세요.',
					retryable: true,
					code: 'NOT_FOUND'
				};
			case 429:
				return {
					type: 'server',
					message: '요청 한도 초과',
					userMessage: '⏰ 요청이 너무 많습니다. 잠시 후 다시 시도해주세요.',
					retryable: true,
					code: 'RATE_LIMITED'
				};
			case 500:
				return {
					type: 'server',
					message: '서버 내부 오류',
					userMessage: '🔧 서버에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해주세요.',
					retryable: true,
					code: 'INTERNAL_ERROR'
				};
			case 503:
				return {
					type: 'server',
					message: '서비스 이용 불가',
					userMessage: '🚫 서비스가 일시적으로 이용 불가능합니다. 잠시 후 다시 시도해주세요.',
					retryable: true,
					code: 'SERVICE_UNAVAILABLE'
				};
			default:
				return {
					type: 'server',
					message: `HTTP ${status} 오류`,
					userMessage: `⚠️ 서버 오류가 발생했습니다 (${status}). 잠시 후 다시 시도해주세요.`,
					retryable: true,
					code: `HTTP_${status}`
				};
		}
	}
	
	// 타임아웃 에러
	if (error.name === 'AbortError' || (error.message && error.message.includes('timeout'))) {
		return {
			type: 'timeout',
			message: error.message,
			userMessage: '⏱️ 요청 시간이 초과되었습니다. 네트워크 상태를 확인하고 다시 시도해주세요.',
			retryable: true,
			code: 'TIMEOUT'
		};
	}
	
	// 기타 에러
	return {
		type: 'unknown',
		message: error.message || String(error),
		userMessage: '❌ 예상치 못한 오류가 발생했습니다. 문제가 지속되면 관리자에게 문의해주세요.',
		retryable: false,
		code: 'UNKNOWN_ERROR'
	};
}

export function createErrorMessage(error: any, messageId: number): ChatMessage {
	const errorInfo = classifyError(error);
	
	// 에러 로깅 강화
	console.error('💥 에러 상세 정보:', {
		type: errorInfo.type,
		message: errorInfo.message,
		code: errorInfo.code,
		retryable: errorInfo.retryable,
		originalError: error
	});
	
	return {
		id: messageId,
		type: 'ai',
		content: errorInfo.userMessage,
		timestamp: new Date().toLocaleTimeString()
	};
}

export function handleSSEMessage(data: any, handlers: SSEHandler, state: ChatState) {
	console.log('📨 SSE 메시지 수신:', data);
	console.log('📊 메시지 타입:', data.type);
	console.log('📊 메시지 내용:', data);
	
	switch (data.type) {
		case 'connected':
			handlers.onConnected(data);
			break;
		case 'clarification_question':
			handlers.onClarificationQuestion(data);
			break;
		case 'streaming_chunk':
			// 통일된 스트리밍 청크 처리 (모드 구분 없음)
			handlers.onAnswerChunk(data);
			break;
		case 'streaming_complete':
		case 'answer_complete':
			// 통일된 완료 처리 (모드 구분 없음)
			handlers.onAnswerComplete(data);
			return; // 중복 방지: onMessage 호출 방지
		case 'complete':
			handlers.onComplete(data);
			break;
		case 'processing':
			handlers.onProcessing(data);
			break;
		case 'error':
		case 'freepass_error':
			// 에러는 onMessage로 전달 (모드 구분 없음)
			if (data.message) {
				handlers.onMessage(data);
			}
			break;
		default:
			if (data.message) {
				handlers.onMessage(data);
			}
			break;
	}
}
