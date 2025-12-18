// API 기본 설정
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
const USE_MOCK_API = import.meta.env.VITE_USE_MOCK_API === 'true'; // 환경 변수로 Mock API 제어

// 새로운 표준화된 API 클라이언트 임포트
export { createMaiceAPIClient, getMaiceAPIClient } from './api/maice-client';
export type { 
  BaseResponse, 
  ChatRequest, 
  ClarificationRequest, 
  SessionRequest,
  ChatEventHandlers,
  SSEMessage 
} from './types/api';

// authStore에서 토큰 가져오기 (동적 import로 순환 참조 방지)
const getTokenFromStore = (): string | null => {
	if (typeof window === 'undefined') return null;
	
	try {
		const savedAuth = localStorage.getItem('maice_auth');
		if (savedAuth) {
			const authData = JSON.parse(savedAuth);
			return authData.access_token || null;
		}
	} catch (error) {
		console.error('토큰 조회 실패:', error);
	}
	return null;
};

// API 헤더 설정 (토큰이 없으면 authStore에서 자동으로 가져옴)
const getHeaders = (token?: string) => {
	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
	};
	
	// 토큰이 명시적으로 전달되지 않으면 authStore에서 가져오기
	const authToken = token || getTokenFromStore();
	
	if (authToken) {
		headers['Authorization'] = `Bearer ${authToken}`;
	}
	
	return headers;
};

// 토큰 만료 시 자동 로그아웃 처리
const handleUnauthorized = () => {
	// 401 에러 발생 시 자동으로 로그아웃 처리
	if (typeof window !== 'undefined') {
		console.warn('⚠️ 인증되지 않은 요청입니다. 로그아웃 처리합니다.');
		// authActions를 import하여 로그아웃 처리
		import('./stores/auth').then(({ authActions }) => {
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

// API 에러 처리
export const handleApiError = (error: any): never => {
	console.error('API Error:', error);
	
	if (error.response) {
		// HTTP 에러 응답
		throw new Error(`API Error: ${error.response.status} - ${error.response.statusText}`);
	} else if (error.request) {
		// 네트워크 에러
		throw new Error('네트워크 연결을 확인해주세요.');
	} else {
		// 기타 에러
		throw new Error(error.message || '알 수 없는 오류가 발생했습니다.');
	}
};

// Google OAuth API
export const googleLogin = async (): Promise<void> => {
	try {
		console.log('googleLogin 함수 시작');
		console.log('API_BASE_URL:', API_BASE_URL);
		// 백엔드의 Google OAuth 엔드포인트로 리다이렉트
		const apiUrl = `${API_BASE_URL}/api/auth/google/login`;
		console.log('리다이렉트할 URL:', apiUrl);
		window.location.href = apiUrl;
		console.log('리다이렉트 실행됨');
	} catch (error) {
		console.error('googleLogin 함수 오류:', error);
		handleApiError(error);
	}
};

export const verifyGoogleToken = async (token: string): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/auth/google/verify`, {
			method: 'POST',
			headers: getHeaders(),
			body: JSON.stringify({ token })
		});

		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}

		return await response.json();
	} catch (error) {
		handleApiError(error);
	}
};

// 현재 사용자 정보 조회
export const getCurrentUser = async (token: string): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/auth/me`, {
			method: 'GET',
			headers: getHeaders(token)
		});
		
		if (!response.ok) {
			throw new Error('사용자 정보 조회에 실패했습니다.');
		}
		
		return await response.json();
	} catch (error) {
		handleApiError(error);
	}
};

// 연구 참여 동의 상태 조회
export const getResearchConsentStatus = async (token: string): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/auth/research-consent`, {
			method: 'GET',
			headers: getHeaders(token)
		});
		
		if (!response.ok) {
			throw new Error('연구 동의 상태 조회에 실패했습니다.');
		}
		
		return await response.json();
	} catch (error) {
		handleApiError(error);
	}
};

// 연구 참여 동의 업데이트
export const updateResearchConsent = async (token: string, consent: boolean, version: string = '1.0'): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/auth/research-consent`, {
			method: 'PUT',
			headers: getHeaders(token),
			body: JSON.stringify({
				research_consent: consent,
				consent_version: version
			})
		});
		
		if (!response.ok) {
			throw new Error('연구 동의 업데이트에 실패했습니다.');
		}
		
		return await response.json();
	} catch (error) {
		handleApiError(error);
	}
};

// MAICE 세션 관리 API - 테스트 모드 지원
export const getMaiceSessions = async (token: string): Promise<any[]> => {
	try {
		// 테스트 모드 확인
		const isTestMode = import.meta.env.DEV && window.location.search.includes('test=true');
		const apiEndpoint = isTestMode ? 
			`${API_BASE_URL}/api/student/sessions-test` : 
			`${API_BASE_URL}/api/student/sessions`;
		
		const headers = isTestMode ? {} : getHeaders(token);
		
		const response = await safeFetch(apiEndpoint, {
			method: 'GET',
			headers: headers
		});
		
		if (!response.ok) {
			throw new Error('세션 목록 조회에 실패했습니다.');
		}
		
		const data = await response.json();
		console.log('🔍 세션 API 응답:', { data, sessions: data.data?.sessions?.length });
		// 백엔드에서 {data: {sessions: [...], total_count: ...}} 형태로 반환하므로 data.sessions 배열 추출
		return data.data?.sessions || [];
	} catch (error) {
		handleApiError(error);
		return [];
	}
};

export const getMaiceSessionHistory = async (sessionId: number, token: string): Promise<any> => {
	try {
		// 테스트 모드 확인
		const isTestMode = import.meta.env.DEV && window.location.search.includes('test=true');
		const apiEndpoint = isTestMode ? 
			`${API_BASE_URL}/api/student/sessions-test/${sessionId}/history` : 
			`${API_BASE_URL}/api/student/sessions/${sessionId}/history`;
		
		const headers = isTestMode ? {} : getHeaders(token);
		
		const response = await safeFetch(apiEndpoint, {
			method: 'GET',
			headers: headers
		});
		
		if (!response.ok) {
			throw new Error('세션 히스토리 조회에 실패했습니다.');
		}
		
		const data = await response.json();
		// 백엔드에서 직접 객체를 반환하므로 그대로 사용
		return data;
	} catch (error) {
		handleApiError(error);
		return null;
	}
};

export const deleteMaiceSession = async (sessionId: number, token: string): Promise<boolean> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/student/sessions/${sessionId}`, {
			method: 'DELETE',
			headers: getHeaders(token)
		});
		
		if (!response.ok) {
			throw new Error('세션 삭제에 실패했습니다.');
		}
		
		return true;
	} catch (error) {
		handleApiError(error);
		return false;
	}
};

// Mock API import
import { 
	getMockResponse, 
	simulateStreamingResponse, 
	generateMockSession, 
	generateMockQuestion 
} from './mock-api';

export interface ChatMessage {
	id: string;
	type: 'user' | 'ai';
	content: string;
	timestamp: Date;
	questionId?: string;
	metadata?: any;
}

export interface StudentInfo {
	token: string;
	name?: string;
	grade?: string;
	subject?: string;
	questionCount: number;
	maxQuestions: number;
	remainingQuestions: number;
}

export interface QuestionSubmission {
	question: string;
	subject?: string;
	grade?: string;
	imageData?: string;
	session_id?: number;
	request_id?: string;
}

export interface AIResponse {
	answer: string;
	session_id?: number;
	timestamp?: string;
	questionId?: string;
	metadata?: {
		confidence?: number;
		sources?: string[];
		processingTime?: number;
		completed?: boolean;
		summary_completed?: boolean;
		status?: string;
	};
}

// MAICE 채팅 응답 인터페이스 추가
export interface MAICEChatResponse {
	assistant_markdown: string;
	session_id?: number;
	request_id?: string;
	completed?: boolean;
	summary_completed?: boolean;
	status?: string;
	// 명료화 관련 필드 추가
	clarification_field?: string;
	clarification_question?: string;
}

// MAICE 채팅 요청 인터페이스
export interface MAICEChatRequest {
	question: string;
	session_id?: number;
	request_id?: string;
	message_type?: 'question' | 'clarification_response';  // 메시지 타입 추가
}

export interface FeedbackSubmission {
	questionId: string;
	helpfulRating: number;
	clarityRating: number;
	additionalComment?: string;
}

export interface ChatSession {
	id: number;
	title: string;
	createdAt: string;
	questionCount: number;
	lastActivity: string;
}

// 토큰 검증
export const verifyToken = async (token: string): Promise<StudentInfo> => {
	if (USE_MOCK_API) {
		return getMockResponse('verifyToken', { token });
	}
	
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/student/verify-token/${token}`, {
			method: 'GET',
			headers: getHeaders(),
		});
		
		if (!response.ok) {
			throw new Error(`토큰 검증 실패: ${response.status}`);
		}
		
		const data = await response.json();
		return data;
	} catch (error) {
		return handleApiError(error);
	}
};

// 질문 제출 (SSE 스트리밍) - 세션 기반 처리 개선
export const submitQuestionStream = async (
	token: string,
	question: string,
	sessionId?: number,
	messageType?: string,  // 메시지 타입 추가
	requestId?: string,    // request_id 추가
	onMessage?: (data: any) => void,
	onError?: (error: any) => void,
	onComplete?: () => void
): Promise<{ sessionId?: number; requestId?: string }> => {
	if (USE_MOCK_API) {
		return getMockResponse('submitQuestion', { question, sessionId });
	}
	
	try {
		console.log('🚀 질문 제출 시작:', {
			question: question.substring(0, 50) + '...',
			sessionId,
			messageType,
			requestId
		});
		
		// 테스트 모드 확인 (개발 환경에서만 허용)
		const isTestMode = import.meta.env.DEV && window.location.search.includes('test=true');
		console.log('🔍 API 테스트 모드 체크:', {
			hasTestParam: window.location.search.includes('test=true'),
			isDev: import.meta.env.DEV,
			viteEnv: import.meta.env.VITE_ENVIRONMENT,
			isTestMode: isTestMode
		});
		const apiEndpoint = isTestMode ? 
			`${API_BASE_URL}/api/student/chat-test` : 
			`${API_BASE_URL}/api/student/chat`;
		
		const response = await safeFetch(apiEndpoint, {
			method: 'POST',
			headers: getHeaders(token),
			body: JSON.stringify({
				question,
				session_id: sessionId,
				request_id: requestId,  // request_id 추가
				message_type: messageType || 'question',  // 메시지 타입 포함
			}),
		});
		
		if (!response.ok) {
			throw new Error(`질문 제출 실패: ${response.status}`);
		}
		
		if (!response.body) {
			throw new Error('Response body가 없습니다.');
		}
		
		const reader = response.body.getReader();
		const decoder = new TextDecoder();
		
		let currentSessionId = sessionId;
		let currentRequestId = requestId;
		
		try {
			while (true) {
				const { done, value } = await reader.read();
				
				if (done) {
					if (onComplete) onComplete();
					return { sessionId: currentSessionId, requestId: currentRequestId };
				}
				
				const chunk = decoder.decode(value);
				const lines = chunk.split('\n');
				
				for (const line of lines) {
					// 빈 라인이나 주석 라인은 건너뛰기
					if (!line.trim() || line.startsWith(':')) {
						continue;
					}
					
					// data: 접두사가 있는 경우만 처리
					if (line.startsWith('data: ')) {
						try {
							const jsonStr = line.slice(6).trim();
							
							// 빈 데이터는 건너뛰기
							if (!jsonStr) {
								continue;
							}
							
							const data = JSON.parse(jsonStr);
							
							// 세션 관련 메시지 처리
							if (data.type === 'session_created') {
								currentSessionId = data.session_id;
								console.log('🆕 새 세션 생성됨:', currentSessionId);
							} else if (data.type === 'session_status') {
								console.log('📊 세션 상태:', data);
							} else if (data.type === 'clarification_status') {
								console.log('🔄 명료화 상태:', data);
							} else if (data.type === 'question_status') {
								console.log('❓ 질문 처리 상태:', data);
							}
							
							if (onMessage) {
								onMessage(data);
							}
							
							// 완료 또는 에러 시 종료
							if (data.type === 'complete' || data.type === 'error') {
								if (onComplete) onComplete();
								return { sessionId: currentSessionId, requestId: currentRequestId };
							}
							
						} catch (parseError) {
							console.error('❌ SSE 데이터 파싱 오류:', parseError);
							console.error('❌ 원본 라인:', line);
							
							// 파싱 오류가 발생한 경우에도 계속 진행
							continue;
						}
					} 
					// data: 접두사가 없지만 JSON 형식인 경우 (백엔드에서 직접 전송)
					else if (line.trim() && line.trim().startsWith('{') && line.trim().endsWith('}')) {
						console.log('✅ 직접 JSON 메시지 감지됨');
						try {
							console.log('🔍 직접 JSON 메시지 감지:', line);
							const data = JSON.parse(line);
							console.log('✅ 직접 JSON 파싱 성공:', data);
							
							// 세션 관련 메시지 처리
							if (data.type === 'session_created') {
								currentSessionId = data.session_id;
								console.log('🆕 새 세션 생성됨:', currentSessionId);
							} else if (data.type === 'session_status') {
								console.log('📊 세션 상태:', data);
							} else if (data.type === 'clarification_status') {
								console.log('🔄 명료화 상태:', data);
							} else if (data.type === 'question_status') {
								console.log('❓ 질문 처리 상태:', data);
							}
							
							if (onMessage) {
								onMessage(data);
							}
							
							// 완료 또는 에러 시 종료
							if (data.type === 'complete' || data.type === 'error') {
								if (onComplete) onComplete();
								return { sessionId: currentSessionId, requestId: currentRequestId };
							}
							
						} catch (parseError) {
							console.error('❌ 직접 JSON 파싱 오류:', parseError);
							console.error('❌ 원본 라인:', line);
							continue;
						}
					} 
					// 빈 줄이 아닌 경우
					else if (line.trim()) {
						console.log('⚠️ 처리되지 않은 라인:', line);
						console.log('⚠️ 라인 타입:', typeof line);
						console.log('⚠️ 라인 길이:', line.length);
					} else {
						console.log('📝 빈 라인 또는 공백만 있는 라인');
					}
				}
			}
		} finally {
			reader.releaseLock();
		}
		
	} catch (error) {
		console.error('MAICE 채팅 SSE 오류:', error);
		if (onError) onError(error);
		throw error;
	}
};

// 질문 제출 (일반 - 하위 호환성)
export const submitQuestion = async (
	token: string,
	question: string,
	sessionId?: number
): Promise<AIResponse> => {
	if (USE_MOCK_API) {
		return getMockResponse('submitQuestion', { question, sessionId });
	}
	
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/student/chat`, {
			method: 'POST',
			headers: getHeaders(token),
			body: JSON.stringify({
				question,
				session_id: sessionId,
			}),
		});
		
		if (!response.ok) {
			throw new Error(`질문 제출 실패: ${response.status}`);
		}
		
		const data = await response.json();
		// 백엔드 응답 구조에 맞게 변환
		return {
			answer: data.assistant_markdown || '응답을 생성할 수 없습니다.',
			session_id: data.session_id,
			timestamp: new Date().toISOString(),
			questionId: data.request_id,
			metadata: {
				completed: data.completed,
				summary_completed: data.summary_completed,
				status: data.status
			}
		};
	} catch (error) {
		return handleApiError(error);
	}
};

// 중복된 submitQuestionStream 함수 제거됨

// MAICE 채팅 API 함수 추가
export const sendMAICEMessage = async (
	token: string,
	request: MAICEChatRequest
): Promise<MAICEChatResponse> => {
	if (USE_MOCK_API) {
		// 모의 응답 생성
		await new Promise(resolve => setTimeout(resolve, 1000));
		return {
			assistant_markdown: `"${request.question}"에 대한 답변입니다. MAICE AI가 학습을 도와드리겠습니다! 📚\n\n**모의 응답:**\n이것은 테스트용 모의 응답입니다. 실제 백엔드 연결 시 정확한 답변이 제공됩니다.`,
			session_id: request.session_id || Math.floor(Math.random() * 1000) + 1,
			request_id: `mock_${Date.now()}`,
			completed: true,
			summary_completed: true,
			status: 'completed'
		};
	}
	
	try {
		const apiUrl = `${API_BASE_URL}/api/student/chat`;
		console.log('🚀 MAICE API 호출:', {
			url: apiUrl,
			token: token ? `${token.substring(0, 10)}...` : '없음',
			request: request
		});
		
		const response = await safeFetch(apiUrl, {
			method: 'POST',
			headers: getHeaders(token),
			body: JSON.stringify(request),
		});
		
		console.log('📡 API 응답 상태:', {
			status: response.status,
			statusText: response.statusText,
			headers: Object.fromEntries(response.headers.entries())
		});
		
		if (!response.ok) {
			const errorData = await response.json().catch(() => ({}));
			console.error('❌ API 오류 응답:', errorData);
			throw new Error(errorData.detail || `MAICE 채팅 실패: ${response.status}`);
		}
		
		const data = await response.json();
		console.log('✅ API 성공 응답:', data);
		return data;
	} catch (error) {
		console.error('💥 API 호출 오류:', error);
		return handleApiError(error);
	}
};

// MAICE 채팅 세션 목록 조회
export const getMAICESessions = async (token: string): Promise<any[]> => {
	if (USE_MOCK_API) {
		await new Promise(resolve => setTimeout(resolve, 500));
		return [
			{
				id: 1,
				title: '수학 학습 세션',
				created_at: new Date().toISOString(),
				question_count: 5,
				last_activity: new Date().toISOString()
			}
		];
	}
	
	try {
		// 테스트 모드 확인
		const isTestMode = import.meta.env.DEV && window.location.search.includes('test=true');
		const apiEndpoint = isTestMode ? 
			`${API_BASE_URL}/api/student/sessions-test` : 
			`${API_BASE_URL}/api/student/sessions`;
		
		const response = await safeFetch(apiEndpoint, {
			method: 'GET',
			headers: getHeaders(token),
		});
		
		if (!response.ok) {
			throw new Error(`MAICE 세션 조회 실패: ${response.status}`);
		}
		
		const data = await response.json();
		return data;
	} catch (error) {
		return handleApiError(error);
	}
};

// MAICE 채팅 세션 삭제
export const deleteMAICESession = async (token: string, sessionId: number): Promise<void> => {
	if (USE_MOCK_API) {
		await new Promise(resolve => setTimeout(resolve, 500));
		return;
	}
	
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/student/sessions/${sessionId}`, {
			method: 'DELETE',
			headers: getHeaders(token),
		});
		
		if (!response.ok) {
			throw new Error(`MAICE 세션 삭제 실패: ${response.status}`);
		}
	} catch (error) {
		handleApiError(error);
	}
};

// 피드백 제출
export const submitFeedback = async (
	token: string,
	questionId: number,
	helpfulRating: number,
	clarityRating: number,
	comment?: string
): Promise<void> => {
	if (USE_MOCK_API) {
		// 모의 API에서는 지연만 시뮬레이션
		await new Promise(resolve => setTimeout(resolve, 500));
		return;
	}
	
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/student/feedback`, {
			method: 'POST',
			headers: getHeaders(token),
			body: JSON.stringify({
				question_id: questionId,
				helpful_rating: helpfulRating,
				clarity_rating: clarityRating,
				comment,
			}),
		});
		
		if (!response.ok) {
			throw new Error(`피드백 제출 실패: ${response.status}`);
		}
	} catch (error) {
		handleApiError(error);
	}
};

// 채팅 세션 목록 조회
export const getChatSessions = async (token: string): Promise<ChatSession[]> => {
	if (USE_MOCK_API) {
		return getMockResponse('getChatSessions', { token });
	}
	
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/student/sessions`, {
			method: 'GET',
			headers: getHeaders(token),
		});
		
		if (!response.ok) {
			throw new Error(`세션 조회 실패: ${response.status}`);
		}
		
		const data = await response.json();
		return data;
	} catch (error) {
		return handleApiError(error);
	}
};

// 새 채팅 세션 생성
export const createNewSession = async (token: string): Promise<ChatSession> => {
	if (USE_MOCK_API) {
		return getMockResponse('createNewSession', { token });
	}
	
	try {
		// 테스트 모드 확인
		const isTestMode = import.meta.env.DEV && window.location.search.includes('test=true');
		const apiEndpoint = isTestMode ? 
			`${API_BASE_URL}/api/student/sessions-test` : 
			`${API_BASE_URL}/api/student/sessions`;
		
		const response = await safeFetch(apiEndpoint, {
			method: 'POST',
			headers: getHeaders(token),
			body: JSON.stringify({
				title: '새로운 학습 세션',
			}),
		});
		
		if (!response.ok) {
			throw new Error(`세션 생성 실패: ${response.status}`);
		}
		
		const data = await response.json();
		return data;
	} catch (error) {
		return handleApiError(error);
	}
};

// 학생 정보 업데이트
export const updateStudentInfo = async (
	token: string,
	updates: Partial<StudentInfo>
): Promise<StudentInfo> => {
	if (USE_MOCK_API) {
		return getMockResponse('updateStudentInfo', { token, updates });
	}
	
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/student/profile`, {
			method: 'PUT',
			headers: getHeaders(token),
			body: JSON.stringify(updates),
		});
		
		if (!response.ok) {
			throw new Error(`정보 업데이트 실패: ${response.status}`);
		}
		
		const data = await response.json();
		return data;
	} catch (error) {
		return handleApiError(error);
	}
};

// 시스템 상태 조회
export const getSystemStatus = async (token?: string): Promise<any> => {
	if (USE_MOCK_API) {
		return getMockResponse('getSystemStatus', {});
	}
	
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/admin/system-status`, {
			method: 'GET',
			headers: getHeaders(token),  // 토큰이 없으면 자동으로 localStorage에서 가져옴
		});
		
		if (!response.ok) {
			throw new Error(`시스템 상태 조회 실패: ${response.status}`);
		}
		
		const data = await response.json();
		return data;
	} catch (error) {
		return handleApiError(error);
	}
};

// 백엔드 상태 확인
export const healthCheck = async (): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/health`, {
			method: 'GET',
		});
		
		if (!response.ok) {
			throw new Error(`헬스 체크 실패: ${response.status}`);
		}
		
		const result = await response.json();
		// BaseController 응답 구조에서 data 추출
		return result.data || result;
	} catch (error) {
		console.error('Health check failed:', error);
		return {
			status: 'unhealthy',
			api_status: 'unhealthy',
			database_status: 'unhealthy',
			redis_status: 'unhealthy'
		};
	}
};

// ========== 모니터링 API ==========

/**
 * 모든 에이전트 상태 조회
 */
export const getAgentsStatus = async (token: string): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/monitoring/agents/status`, {
			method: 'GET',
			headers: getHeaders(token)
		});
		
		if (!response.ok) {
			throw new Error('에이전트 상태 조회에 실패했습니다.');
		}
		
		return await response.json();
	} catch (error) {
		return handleApiError(error);
	}
};

/**
 * 특정 에이전트의 상세 메트릭 조회
 */
export const getAgentMetrics = async (token: string, agentName: string): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/monitoring/agents/${agentName}/metrics`, {
			method: 'GET',
			headers: getHeaders(token)
		});
		
		if (!response.ok) {
			throw new Error('에이전트 메트릭 조회에 실패했습니다.');
		}
		
		return await response.json();
	} catch (error) {
		return handleApiError(error);
	}
};

/**
 * 전체 시스템 메트릭 요약 조회
 */
export const getMetricsSummary = async (token: string): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/monitoring/metrics/summary`, {
			method: 'GET',
			headers: getHeaders(token)
		});
		
		if (!response.ok) {
			throw new Error('메트릭 요약 조회에 실패했습니다.');
		}
		
		return await response.json();
	} catch (error) {
		return handleApiError(error);
	}
};

/**
 * 성능 타임라인 조회
 */
export const getPerformanceTimeline = async (token: string, hours: number = 24): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/monitoring/performance/timeline?hours=${hours}`, {
			method: 'GET',
			headers: getHeaders(token)
		});
		
		if (!response.ok) {
			throw new Error('성능 타임라인 조회에 실패했습니다.');
		}
		
		return await response.json();
	} catch (error) {
		return handleApiError(error);
	}
};

/**
 * 상세 헬스 체크
 */
export const getDetailedHealth = async (token: string): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/monitoring/health/detailed`, {
			method: 'GET',
			headers: getHeaders(token)
		});
		
		if (!response.ok) {
			throw new Error('상세 헬스 체크에 실패했습니다.');
		}
		
		return await response.json();
	} catch (error) {
		return handleApiError(error);
	}
};

/**
 * 관리자 대시보드 통계 조회
 */
export const getAdminDashboardStats = async (token: string): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/admin/dashboard/stats`, {
			method: 'GET',
			headers: getHeaders(token)
		});
		
		if (!response.ok) {
			throw new Error('대시보드 통계 조회에 실패했습니다.');
		}
		
		return await response.json();
	} catch (error) {
		return handleApiError(error);
	}
};

/**
 * 학생 목록 조회
 */
export const getStudents = async (token: string, skip: number = 0, limit: number = 100): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/admin/students?skip=${skip}&limit=${limit}`, {
			method: 'GET',
			headers: getHeaders(token)
		});
		
		if (!response.ok) {
			throw new Error('학생 목록 조회에 실패했습니다.');
		}
		
		return await response.json();
	} catch (error) {
		return handleApiError(error);
	}
};

/**
 * 특정 학생의 세션 목록 조회
 */
export const getStudentSessions = async (token: string, userId: number): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/admin/students/${userId}/sessions`, {
			method: 'GET',
			headers: getHeaders(token)
		});
		
		if (!response.ok) {
			throw new Error('학생 세션 목록 조회에 실패했습니다.');
		}
		
		return await response.json();
	} catch (error) {
		return handleApiError(error);
	}
};

/**
 * 세션의 메시지 목록 조회
 */
export const getSessionMessages = async (token: string, sessionId: number): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/admin/sessions/${sessionId}/messages`, {
			method: 'GET',
			headers: getHeaders(token)
		});
		
		if (!response.ok) {
			throw new Error('세션 메시지 목록 조회에 실패했습니다.');
		}
		
		return await response.json();
	} catch (error) {
		return handleApiError(error);
	}
};

/**
 * 세션 평가 실행
 */
export const evaluateSession = async (token: string, sessionId: number): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/admin/evaluate-session/${sessionId}`, {
			method: 'POST',
			headers: getHeaders(token)
		});
		
		if (!response.ok) {
			throw new Error('세션 평가 실행에 실패했습니다.');
		}
		
		return await response.json();
	} catch (error) {
		return handleApiError(error);
	}
};

/**
 * 여러 세션에 대한 일괄 평가 실행
 */
export const batchEvaluateSessions = async (token: string, sessionIds: number[]): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/admin/evaluate-sessions/batch`, {
			method: 'POST',
			headers: getHeaders(token),
			body: JSON.stringify({ session_ids: sessionIds })
		});
		
		if (!response.ok) {
			throw new Error('일괄 평가 실행에 실패했습니다.');
		}
		
		return await response.json();
	} catch (error) {
		return handleApiError(error);
	}
};

/**
 * 모든 학생의 모든 세션 일괄 평가 (기본: 미평가 세션만)
 */
export const batchEvaluateAllSessions = async (token: string, onlyUnevaluated: boolean = true): Promise<any> => {
  try {
    const response = await safeFetch(`${API_BASE_URL}/api/admin/evaluate-sessions/all`, {
      method: 'POST',
      headers: getHeaders(token),
      body: JSON.stringify({ only_unevaluated: onlyUnevaluated })
    });
    
    if (!response.ok) {
      throw new Error('전체 일괄 평가 실행에 실패했습니다.');
    }
    
    return await response.json();
  } catch (error) {
    return handleApiError(error);
  }
};

/**
 * 세션의 평가 결과 조회
 */
export const getSessionEvaluations = async (token: string, sessionId: number): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/admin/sessions/${sessionId}/evaluations`, {
			method: 'GET',
			headers: getHeaders(token)
		});
		
		if (!response.ok) {
			throw new Error('평가 결과 조회에 실패했습니다.');
		}
		
		return await response.json();
	} catch (error) {
		return handleApiError(error);
	}
};

// ============================================================================
// 교사용 API 함수
// ============================================================================

/**
 * 교사용: 모든 학생의 세션 목록 조회
 */
export const getTeacherSessions = async (
	token: string,
	skip: number = 0,
	limit: number = 50,
	studentId?: number,
	hasEvaluation?: boolean
): Promise<any> => {
	try {
		let url = `${API_BASE_URL}/api/teacher/sessions?skip=${skip}&limit=${limit}`;
		if (studentId) url += `&student_id=${studentId}`;
		if (hasEvaluation !== undefined) url += `&has_evaluation=${hasEvaluation}`;
		
		const response = await safeFetch(url, {
			method: 'GET',
			headers: getHeaders(token)
		});
		
		if (!response.ok) {
			throw new Error('세션 목록 조회에 실패했습니다.');
		}
		
		return await response.json();
	} catch (error) {
		return handleApiError(error);
	}
};

/**
 * 교사용: 세션 상세 정보 조회 (대화 내용 포함)
 */
export const getTeacherSessionDetail = async (token: string, sessionId: number): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/teacher/sessions/${sessionId}`, {
			method: 'GET',
			headers: getHeaders(token)
		});
		
		if (!response.ok) {
			throw new Error('세션 상세 조회에 실패했습니다.');
		}
		
		return await response.json();
	} catch (error) {
		return handleApiError(error);
	}
};

/**
 * 교사용: 미평가 세션 중 랜덤하게 하나 가져오기
 */
export const getRandomUnevaluatedSession = async (token: string): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/teacher/sessions/random`, {
			method: 'GET',
			headers: getHeaders(token)
		});
		
		if (!response.ok) {
			if (response.status === 404) {
				throw new Error('평가할 세션이 없습니다. 모든 세션을 평가했습니다!');
			}
			throw new Error('랜덤 세션 조회에 실패했습니다.');
		}
		
		return await response.json();
	} catch (error) {
		return handleApiError(error);
	}
};

/**
 * 교사용: 세션 상세 조회 (대화 내용 + 평가 포함)
 */
export const getSessionDetail = async (token: string, sessionId: number): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/teacher/sessions/${sessionId}`, {
			method: 'GET',
			headers: getHeaders(token)
		});

		if (!response.ok) {
			throw new Error('세션 상세 조회에 실패했습니다.');
		}

		return await response.json();
	} catch (error) {
		return handleApiError(error);
	}
};

/**
 * 교사용: 평가 통계 조회
 */
export const getEvaluationStats = async (token: string): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/teacher/evaluation/stats`, {
			method: 'GET',
			headers: getHeaders(token)
		});

		if (!response.ok) {
			throw new Error('평가 통계 조회에 실패했습니다.');
		}

		return await response.json();
	} catch (error) {
		return handleApiError(error);
	}
};

/**
 * 관리자용: 교사별 평가 통계 조회
 */
export const getTeacherEvaluationStats = async (token: string): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/teacher/evaluation/teacher-stats`, {
			method: 'GET',
			headers: getHeaders(token)
		});

		if (!response.ok) {
			throw new Error('교사별 평가 통계 조회에 실패했습니다.');
		}

		return await response.json();
	} catch (error) {
		return handleApiError(error);
	}
};

/**
 * 교사용: 루브릭 의견 조회
 */
export const getRubricFeedbacks = async (token: string): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/teacher/rubric-feedbacks`, {
			method: 'GET',
			headers: getHeaders(token)
		});
		
		if (!response.ok) {
			throw new Error('루브릭 의견 조회에 실패했습니다.');
		}
		
		return await response.json();
	} catch (error) {
		return handleApiError(error);
	}
};

/**
 * 교사용: 루브릭 의견 저장
 */
export const updateRubricFeedbacks = async (token: string, feedbacks: Record<string, any>): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/teacher/rubric-feedbacks`, {
			method: 'PUT',
			headers: getHeaders(token),
			body: JSON.stringify(feedbacks)
		});
		
		if (!response.ok) {
			throw new Error('루브릭 의견 저장에 실패했습니다.');
		}
		
		return await response.json();
	} catch (error) {
		return handleApiError(error);
	}
};

/**
 * 교사용: 항목별 점수로 세션 필터링
 */
export const getSessionsByItemScore = async (
	token: string,
	item: string,
	minScore: number = 1,
	maxScore: number = 5,
	skip: number = 0,
	limit: number = 100
): Promise<any> => {
	try {
		const params = new URLSearchParams({
			item,
			min_score: minScore.toString(),
			max_score: maxScore.toString(),
			skip: skip.toString(),
			limit: limit.toString()
		});
		
		const response = await safeFetch(`${API_BASE_URL}/api/teacher/sessions/by-item-score?${params}`, {
			method: 'GET',
			headers: getHeaders(token)
		});

		if (!response.ok) {
			const error = await response.json().catch(() => ({}));
			console.error('항목별 세션 조회 에러:', error);
			// FastAPI validation error detail이 배열로 올 수 있음
			const errorMsg = Array.isArray(error.detail) 
				? error.detail.map((e: any) => `${e.loc?.join('.')}: ${e.msg}`).join(', ')
				: error.detail || JSON.stringify(error);
			throw new Error(errorMsg || '항목별 세션 조회에 실패했습니다.');
		}

		return await response.json();
	} catch (error) {
		console.error('getSessionsByItemScore 에러:', error);
		return handleApiError(error);
	}
};

// v4.3 체크리스트 타입 정의
export interface ChecklistElement {
	value: 0 | 1;  // 0=미충족, 1=충족
	evidence: string;  // 근거 (10자 내외)
}

export interface ChecklistItem {
	element1: ChecklistElement;
	element2: ChecklistElement;
	element3: ChecklistElement;
	element4: ChecklistElement;
}

export interface ManualEvaluationV43 {
	session_id: number;
	// A 영역: 질문 평가 (15점)
	A1?: ChecklistItem;  // 수학적 전문성
	A2?: ChecklistItem;  // 질문 구조화
	A3?: ChecklistItem;  // 학습 맥락 적용
	// B 영역: 답변 평가 (15점)
	B1?: ChecklistItem;  // 학습자 맞춤도
	B2?: ChecklistItem;  // 설명의 체계성
	B3?: ChecklistItem;  // 학습 내용 확장성
	// C 영역: 맥락 평가 (10점)
	C1?: ChecklistItem;  // 대화 일관성
	C2?: ChecklistItem;  // 학습 과정 지원성
	// 교사 의견 (v4.5)
	item_feedbacks?: Record<string, string>;  // 각 항목별 의견
	rubric_overall_feedback?: string;  // 루브릭 총평
	educational_llm_suggestions?: string;  // LLM 교육적 활용 제안
}

/**
 * 교사용: 수동 평가 생성/업데이트 (v4.3 체크리스트 방식)
 */
export const createOrUpdateManualEvaluation = async (
	token: string,
	evaluation: ManualEvaluationV43
): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/teacher/evaluations/manual`, {
			method: 'POST',
			headers: getHeaders(token),
			body: JSON.stringify(evaluation)
		});
		
		if (!response.ok) {
			const errorData = await response.json().catch(() => ({}));
			throw new Error(errorData.detail || '평가 저장에 실패했습니다.');
		}
		
		return await response.json();
	} catch (error) {
		return handleApiError(error);
	}
};

/**
 * 교사용: 학생 목록 조회
 */
export const getTeacherStudents = async (
	token: string,
	skip: number = 0,
	limit: number = 100
): Promise<any> => {
	try {
		const response = await safeFetch(`${API_BASE_URL}/api/teacher/students?skip=${skip}&limit=${limit}`, {
			method: 'GET',
			headers: getHeaders(token)
		});
		
		if (!response.ok) {
			throw new Error('학생 목록 조회에 실패했습니다.');
		}
		
		return await response.json();
	} catch (error) {
		return handleApiError(error);
	}
};

// ============= 사용자 관리 API (관리자용) =============

export interface UserInfo {
	id: number;
	username: string;
	role: string;
	question_count: number;
	max_questions: number | null;
	remaining_questions: number | null;
	assigned_mode: string | null;
	mode_assigned_at: string | null;
	google_email: string | null;
	google_name: string | null;
	created_at: string;
}

export interface UserPreferences {
	max_questions?: number;
	remaining_questions?: number;
	assigned_mode?: string | null;
}

/**
 * 관리자용: 사용자 목록 조회
 */
export const getUsers = async (
	token: string,
	role?: string,
	skip: number = 0,
	limit: number = 100,
	search?: string
): Promise<UserInfo[]> => {
	const params = new URLSearchParams({
		skip: skip.toString(),
		limit: limit.toString()
	});
	
	if (role) params.append('role', role);
	if (search) params.append('search', search);
	
	const response = await safeFetch(`${API_BASE_URL}/api/users/?${params}`, {
		method: 'GET',
		headers: getHeaders(token)
	});
	
	if (!response.ok) {
		throw new Error('사용자 목록 조회에 실패했습니다.');
	}
	
	return await response.json();
};

/**
 * 관리자용: 특정 사용자 조회
 */
export const getUser = async (
	token: string,
	userId: number
): Promise<UserInfo> => {
	const response = await safeFetch(`${API_BASE_URL}/api/users/${userId}`, {
		method: 'GET',
		headers: getHeaders(token)
	});
	
	if (!response.ok) {
		throw new Error('사용자 조회에 실패했습니다.');
	}
	
	return await response.json();
};

/**
 * 관리자용: 사용자 정보 업데이트
 */
export const updateUser = async (
	token: string,
	userId: number,
	userData: Partial<{
		username?: string;
		role?: string;
		max_questions?: number;
	}>
): Promise<UserInfo> => {
	const response = await safeFetch(`${API_BASE_URL}/api/users/${userId}`, {
		method: 'PUT',
		headers: getHeaders(token),
		body: JSON.stringify(userData)
	});
	
	if (!response.ok) {
		const errorData = await response.json().catch(() => ({}));
		throw new Error(errorData.detail || '사용자 정보 업데이트에 실패했습니다.');
	}
	
	return await response.json();
};

/**
 * 관리자용: 사용자 삭제
 */
export const deleteUser = async (
	token: string,
	userId: number
): Promise<void> => {
	const response = await safeFetch(`${API_BASE_URL}/api/users/${userId}`, {
		method: 'DELETE',
		headers: getHeaders(token)
	});
	
	if (!response.ok) {
		const errorData = await response.json().catch(() => ({}));
		throw new Error(errorData.detail || '사용자 삭제에 실패했습니다.');
	}
	
	await response.json();
};

/**
 * 관리자용: 사용자 설정 업데이트
 */
export const updateUserPreferences = async (
	token: string,
	userId: number,
	preferences: UserPreferences
): Promise<UserInfo> => {
	const response = await safeFetch(`${API_BASE_URL}/api/users/${userId}/preferences`, {
		method: 'PUT',
		headers: getHeaders(token),
		body: JSON.stringify(preferences)
	});
	
	if (!response.ok) {
		const errorData = await response.json().catch(() => ({}));
		throw new Error(errorData.detail || '사용자 설정 업데이트에 실패했습니다.');
	}
	
	return await response.json();
};
