<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { browser } from '$app/environment';
	import Button from '$lib/components/common/Button.svelte';
	import Card from '$lib/components/common/Card.svelte';
	import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
	import MessageList from '$lib/components/maice/MessageList.svelte';
	import InlineMathInput from '$lib/components/maice/InlineMathInput.svelte';
	import SessionManager from '$lib/components/maice/SessionManager.svelte';
	import HamburgerMenu from '$lib/components/common/HamburgerMenu.svelte';
	import { themeStore } from '$lib/stores/theme';
	import { authStore, authActions } from '$lib/stores/auth';
	import { consentStore, consentActions } from '$lib/stores/consent';
	import ConsentModal from '$lib/components/common/ConsentModal.svelte';
	import UpdateNoteModal from '$lib/components/common/UpdateNoteModal.svelte';
	import CameraModal from '$lib/components/maice/CameraModal.svelte';
	import ImageCropModal from '$lib/components/maice/ImageCropModal.svelte';
	import { goto } from '$app/navigation';
	import { hasUserReadUpdateNote, getCurrentUserId } from '$lib/utils/update-note';
	import { submitQuestionStream, getMaiceSessionHistory } from '$lib/api';
	import { createMaiceAPIClient, getMaiceAPIClient } from '$lib/api/maice-client';
	import type { ChatRequest, ChatEventHandlers, SSEMessage } from '$lib/types/api';
	import { 
		createDefaultMessage, 
		createUserMessage, 
		createAIMessage, 
		createErrorMessage,
		classifyError,
		handleSSEMessage,
		type ChatMessage,
		type ChatState,
		type SSEHandler,
		type ErrorInfo
	} from './chat-logic';
	import { chunkBufferManager } from '$lib/utils/chunk-buffer';
	import './maice.css';
	
	let currentTheme = 'auto';
	let isDark = false;
	let authToken = $state('');
	let isAuthenticated = $state(false);
	let user = $state<any>(null);
	
	// 연구 동의 관련 상태
	let hasResearchConsent = $state(false);
	let showConsentModal = $state(false);
	
	// 업데이트 노트 관련 상태
	let showUpdateNoteModal = $state(false);
	
	// 이미지 관련 모달 상태
	let showCameraModal = $state(false);
	let showImageCropModal = $state(false);
	let selectedImageUrl = $state('');
	
	// 테마 상태 구독
	$effect(() => {
		const unsubscribe = themeStore.subscribe(state => {
			currentTheme = state.current;
			isDark = state.isDark;
		});
		
		return unsubscribe;
	});
	
	// 인증 상태 구독 (클라이언트 사이드에서만)
	if (browser) {
		authStore.subscribe(state => {
			authToken = state.user?.access_token || '';
			isAuthenticated = state.isAuthenticated;
			user = state.user;
		});
		
		// 연구 동의 상태 구독
		consentStore.subscribe(state => {
			hasResearchConsent = state.hasConsented;
		});
	}
	
	// 페이지 로드 시 실행
	$effect(() => {
		if (isAuthenticated) {
			console.log('✅ 인증된 사용자:', user?.username, '역할:', user?.role);
			console.log('🔑 인증 토큰:', authToken);
			
			// 새로운 API 클라이언트 초기화
			maiceClient = createMaiceAPIClient(authToken);
			console.log('🚀 MAICE API 클라이언트 초기화 완료 [v2024.12.26]');
			
			// 사용자 인증 후 연구 동의 상태 확인 (모든 사용자 대상)
			if (user) {
				// 백엔드에서 동의 상태 동기화
				setTimeout(async () => {
					try {
						await consentActions.syncConsentFromBackend(authToken);
						// 동기화 후 다시 체크
						checkResearchConsent();
					} catch (error) {
						console.error('❌ 연구 동의 상태 동기화 실패:', error);
						// 동기화 실패 시에도 로컬 상태로 체크
						checkResearchConsent();
					}
				}, 500);
			}
		}
	});
	

	
	// 채팅 관련 상태
	let messages: ChatMessage[] = $state([createDefaultMessage()]);

	// 답변 중복 방지를 위한 상태
	let isAnswerCompleted = $state(false);
	
	// 메시지 ID 생성기
	let nextMessageId = $state(2); // 기본 메시지가 ID 1을 사용하므로 2부터 시작
	
	function getNextMessageId(): number {
		return nextMessageId++;
	}
	
	// 요약 진행 상태 추적
	let isSummarizing = $state(false);

	// 새로운 API 클라이언트 인스턴스
	let maiceClient: any = null;
	
	// 현재 활성 SSE 연결 추적
	let activeSSEController: AbortController | null = null;

	// 스크롤 상태 추적
	let isUserScrolling = $state(false);
	let lastScrollTop = $state(0);
	let scrollTimeout: any = null;
	
	// 에러 상태 관리
	let lastError: ErrorInfo | null = $state(null);
	let isOnline = $state(true);

	// 메시지 배열 변경 감지 및 자동 스크롤 (조건부) - 개선된 로직
	let lastMessageCount = 0;
	$effect(() => {
		// 실제로 메시지 수가 변경된 경우에만 로그 출력
		if (messages.length !== lastMessageCount) {
			console.log('🔄 메시지 배열 변경됨:', messages.length, '개');
			lastMessageCount = messages.length;
			
			if (messages.length > 0) {
				// $state.snapshot을 사용하여 프록시 경고 방지
				console.log('📝 최신 메시지:', $state.snapshot(messages[messages.length - 1]));
				
				// 사용자가 스크롤하지 않고, 새 메시지가 추가된 경우에만 자동 스크롤
				// 단, 사용자가 입력 중이거나 포커스 이동 중에는 스크롤하지 않음
				if (!isUserScrolling && !document.activeElement?.closest('.input-area')) {
					// 스크롤이 이미 하단 근처에 있는 경우에만 자동 스크롤
					if (messagesAreaRef) {
						const { scrollTop, scrollHeight, clientHeight } = messagesAreaRef;
						const isNearBottom = scrollTop + clientHeight >= scrollHeight - 150;
						
						if (isNearBottom) {
							setTimeout(() => {
								scrollToBottom();
							}, 100);
						}
					}
				}
			}
		}
	});

	// 스크롤을 맨 아래로 이동하는 함수
	function scrollToBottom() {
		if (messagesAreaRef) {
			// requestAnimationFrame을 사용하여 DOM 업데이트 후 스크롤
			requestAnimationFrame(() => {
				messagesAreaRef.scrollTop = messagesAreaRef.scrollHeight;
			});
		}
	}

	// 스크롤 위치를 유지하는 함수 (개선됨)
	function maintainScrollPosition() {
		if (messagesAreaRef) {
			const currentScrollTop = messagesAreaRef.scrollTop;
			const isNearBottom = currentScrollTop + messagesAreaRef.clientHeight >= messagesAreaRef.scrollHeight - 100;
			
			// 사용자가 스크롤했는지 감지
			if (Math.abs(currentScrollTop - lastScrollTop) > 5) {
				isUserScrolling = true;
				
				// 스크롤 타임아웃 클리어
				if (scrollTimeout) {
					clearTimeout(scrollTimeout);
				}
				
				// 2초 후 자동 스크롤 재활성화
				scrollTimeout = setTimeout(() => {
					isUserScrolling = false;
				}, 2000);
			}
			
			lastScrollTop = currentScrollTop;
			
			// 맨 아래 근처에 있으면 자동 스크롤 유지
			if (isNearBottom && !isUserScrolling) {
				scrollToBottom();
			}
		}
	}

	// 강제로 스크롤을 맨 아래로 이동하는 함수
	function forceScrollToBottom() {
		if (messagesAreaRef) {
			messagesAreaRef.scrollTop = messagesAreaRef.scrollHeight;
		}
	}

	// 마우스 휠 스크롤 감지
	function handleWheelScroll(event: WheelEvent) {
		// 사용자가 휠로 스크롤했음을 표시
		isUserScrolling = true;
		
		// 스크롤 타임아웃 클리어
		if (scrollTimeout) {
			clearTimeout(scrollTimeout);
		}
		
		// 3초 후 자동 스크롤 재활성화
		scrollTimeout = setTimeout(() => {
			isUserScrolling = false;
		}, 3000);
	}

	let isLoading = $state(false);
	let sessionId = $state<number | null>(null);
	let requestId = $state<string | undefined>(undefined);
	let messageInputRef: any = null;
	let messagesAreaRef: HTMLDivElement;
	
	// 로딩 상태 변경 시 스크롤 (조건부)
	$effect(() => {
		if (isLoading) {
			// 로딩 시작 시에만 자동 스크롤 (새 질문 시작 시)
			if (!isUserScrolling) {
				setTimeout(() => {
					scrollToBottom();
				}, 50);
			}
		}
	});
	
	// 명료화 관련 상태 추가 (백엔드에서만 동작, 프론트엔드에서는 숨김)
	let isClarificationMode = $state(false);
	let currentClarificationRequest: any = null;
	
	// 에이전트 모드 상태 (백엔드에서 자동 할당되므로 UI에서 제거)
	// let useAgents = $state(true);  // 백엔드에서 사용자별 랜덤 할당으로 변경됨
	
	// 세션 관리 사이드바 상태
	let isSessionSidebarOpen = $state(false);
	// 햄버거 메뉴 상태
	let isHamburgerMenuOpen = $state(false);
	
	// 햄버거 메뉴 외부 클릭으로 닫기
	function handleOutsideClick(event: MouseEvent) {
		const target = event.target as HTMLElement;
		if (isHamburgerMenuOpen && !target.closest('.hamburger-wrapper')) {
			isHamburgerMenuOpen = false;
		}
	}
	
	// isLoading 상태 변경 감지
	$effect(() => {
		console.log('🔄 isLoading 상태 변경됨:', isLoading);
		console.log('🔄 isSummarizing 상태:', isSummarizing);
	});

	// 입력 필드 포커스 관리 - 수식 필드 포커스 간섭 방지
	$effect(() => {
		// 로딩 중이 아니고, 사용자가 직접 다른 곳에 포커스하지 않은 경우에만 포커스
		if (!isLoading && messageInputRef && !isUserScrolling) {
			// 현재 포커스가 입력 영역이 아닌 경우에만 포커스 이동
			const activeElement = document.activeElement;
			const isInputAreaFocused = activeElement?.closest('.input-area') || 
									   activeElement?.closest('.inline-math-input-container') ||
									   activeElement?.tagName === 'MATH-FIELD' ||
									   activeElement?.closest('math-field');
			
			// 수식 필드나 입력 영역에 포커스가 있으면 포커스 이동하지 않음
			if (!isInputAreaFocused) {
				setTimeout(() => {
					// 한 번 더 확인: 포커스 이동 시도 직전에 수식 필드에 포커스가 있는지 재확인
					const currentActiveElement = document.activeElement;
					const isStillInMathField = currentActiveElement?.tagName === 'MATH-FIELD' ||
											  currentActiveElement?.closest('math-field') ||
											  currentActiveElement?.closest('.inline-math-container');
					
					if (!isStillInMathField && messageInputRef && typeof messageInputRef.focus === 'function') {
						// 부드러운 포커스 이동 (스크롤 방지)
						messageInputRef.focus({ preventScroll: true });
					}
				}, 150); // 약간 더 긴 지연으로 다른 작업과 충돌 방지
			}
		}
	});
	
	
	// 네트워크 상태 감지
	function setupNetworkStatusListener() {
		if (typeof window !== 'undefined') {
			window.addEventListener('online', () => {
				isOnline = true;
				console.log('🌐 네트워크 연결됨');
			});
			
			window.addEventListener('offline', () => {
				isOnline = false;
				console.log('🌐 네트워크 연결 끊어짐');
			});
		}
	}
	
	// 세션 목록 새로고침을 위한 상태
	let sessionRefreshTrigger = $state(0);
	
	// 세션 목록 새로고침 함수
	async function refreshSessionList() {
		try {
			// 세션 새로고침 트리거 증가
			sessionRefreshTrigger++;
			console.log('✅ 세션 목록 새로고침 트리거:', sessionRefreshTrigger);
		} catch (error) {
			console.error('❌ 세션 목록 새로고침 실패:', error);
		}
	}

	// 세션 관련 함수들
	async function handleSessionSelect(selectedSessionId: number) {
		// 기존 세션 정리
		console.log('🔄 세션 전환 시작:', sessionId, '→', selectedSessionId);
		
		// 기존 SSE 연결 중단
		if (activeSSEController) {
			activeSSEController.abort();
			activeSSEController = null;
			console.log('🔌 기존 SSE 연결 중단됨');
		}
		
		// 진행 중인 모든 작업 즉시 중단
		isLoading = false;
		isSummarizing = false;
		
		// 기존 요청 ID 초기화 (새 세션에서는 새 요청 ID 사용)
		requestId = undefined;
		
		// 세션 ID 업데이트
		const oldSessionId = sessionId;
		sessionId = selectedSessionId;
		isSessionSidebarOpen = false; // 사이드바 닫기
		
		console.log('🔗 세션 전환 완료:', oldSessionId, '→', selectedSessionId);
		console.log('🔄 상태 초기화: isLoading=false, isSummarizing=false, requestId=undefined');
		
		// 세션 히스토리 로드
		const isTestMode = import.meta.env.DEV && window.location.search.includes('test=true');
		
		if (authToken || isTestMode) {
			try {
				const history = await getMaiceSessionHistory(selectedSessionId, authToken || '');
				console.log('📚 세션 히스토리 응답:', history);
				
				if (history && history.data && history.data.history && history.data.history.length > 0) {
					// 히스토리를 메시지 배열로 변환 (기본 메시지 제거하고 히스토리만 로드)
					messages = history.data.history.map((msg: any, index: number) => ({
						id: msg.id || index + 1,
						content: msg.content,
						type: msg.sender === 'user' ? 'user' : 'ai', // 'user' 또는 'assistant'를 'user' 또는 'ai'로 변환
						timestamp: msg.timestamp || new Date().toISOString(),
						isStreaming: false
					}));
					console.log('📚 세션 히스토리 로드됨:', messages.length, '개 메시지');
				} else {
					console.log('📝 세션 히스토리가 없습니다. 새 대화를 시작합니다.');
					messages = [createDefaultMessage()];
				}
			} catch (error) {
				console.error('❌ 세션 히스토리 로드 실패:', error);
				messages = [createDefaultMessage()];
			}
		}
	}
	
	function handleNewSession() {
		console.log('🎯 부모 컴포넌트 handleNewSession 호출됨');
		console.log('📋 현재 상태:', {
			sessionId,
			messagesCount: messages.length,
			isLoading,
			isSummarizing,
			hasActiveSSE: !!activeSSEController
		});
		
		// 기존 SSE 연결 중단
		if (activeSSEController) {
			activeSSEController.abort();
			activeSSEController = null;
			console.log('🔌 새 세션 생성으로 SSE 연결 중단됨');
		}
		
		sessionId = null;
		messages = [createDefaultMessage()];
		isLoading = false;
		isSummarizing = false;
		isSessionSidebarOpen = false; // 사이드바 닫기 추가
		console.log('🆕 새 세션 생성됨 - 사이드바 닫힘');
	}
	
	// 메시지 전송 이벤트 핸들러
	async function handleMessageSend(event: CustomEvent) {
		console.log('🚀 부모 컴포넌트: send 이벤트 수신됨');
		console.log('📋 이벤트 상세:', event.detail);
		console.log('📋 이벤트 타입:', event.type);
		console.log('📋 이벤트 타겟:', event.target);
		
		const message = event.detail.message;
		console.log('🚀 메시지 전송 시작:', message);
		
		if (!message.trim()) {
			console.warn('⚠️ 빈 메시지 전송 시도');
			return;
		}
		
		// 새 질문 시작 시 사용자 스크롤 상태 초기화
		isUserScrolling = false;
		
		// 사용자 메시지 추가
		const userMessage = createUserMessage(message, getNextMessageId());
		
		console.log('👤 사용자 메시지 생성:', userMessage);
		
		// 배열 업데이트 - 반응성 보장
		messages = [...messages, userMessage];
		console.log('📝 메시지 배열 업데이트됨, 총 개수:', messages.length);
		console.log('📋 현재 메시지 배열:', messages);
		
		// 새 메시지 추가 시 조건부 자동 스크롤
		if (messagesAreaRef) {
			const { scrollTop, scrollHeight, clientHeight } = messagesAreaRef;
			const isNearBottom = scrollTop + clientHeight >= scrollHeight - 100;
			
			// 하단 근처에 있을 때만 자동 스크롤
			if (isNearBottom) {
				setTimeout(() => {
					scrollToBottom();
				}, 100);
			}
		}
		
		// 새 질문 시작 - 이전 버퍼 정리
		if (sessionId) {
			chunkBufferManager.removeBuffer(sessionId);
			console.log('🗑️ 이전 버퍼 정리 완료 - 새 질문 시작');
		}
		
		// 즉시 로딩 상태 활성화하여 입력 필드 비활성화
		isLoading = true;
		console.log('🔒 입력 필드 비활성화됨 (isLoading = true)');
		
		try {
			console.log('🚀 SSE 스트리밍 시작...');
			console.log('🔑 인증 토큰:', authToken ? '있음' : '없음');
			console.log('📝 질문:', message);
			console.log('🆔 세션 ID:', sessionId);
			
			// SSE 스트리밍을 사용하여 질문 처리
			// 현재 세션 ID와 요청 ID 사용
			const currentSessionId = sessionId; // null이어도 백엔드로 전달
			const currentRequestId = requestId;
			
			console.log('🚀 질문 처리 시작:', {
				sessionId: currentSessionId,
				sessionIdType: typeof currentSessionId,
				requestId: currentRequestId,
				message: message
			});
			
			// 새로운 API 클라이언트 사용
			if (!maiceClient) {
				console.error('❌ MAICE API 클라이언트가 초기화되지 않았습니다.');
				return;
			}

		// 채팅 요청 생성 - 프론트엔드는 단순히 사용자 메시지만 전달
		const chatRequest: ChatRequest = {
			message: message,
			session_id: currentSessionId || undefined,
			request_id: currentRequestId || undefined,
			// message_type과 use_agents는 백엔드에서 판단하므로 제거됨
		};
		
		console.log('📤 백엔드로 전송할 채팅 요청:', {
			message: message,
			session_id: chatRequest.session_id,
			session_id_type: typeof chatRequest.session_id,
			request_id: chatRequest.request_id
		});

			// 이벤트 핸들러 정의
			const eventHandlers: ChatEventHandlers = {
				onConnected: (data) => {
					console.log('🔗 연결됨:', data);
					
					// session_id와 request_id 저장
					if (data.session_id !== undefined && data.session_id !== null) {
						sessionId = data.session_id;
						console.log('✅ 세션 ID 저장:', sessionId);
					}
					if (data.request_id) {
						requestId = data.request_id;
						console.log('✅ 요청 ID 저장:', requestId);
					}
				},
				
				onProcessing: (data) => {
					console.log('⏳ 처리 중:', data.message);
				},
				
				onClarification: (data) => {
					console.log('🔍 명료화 질문 수신:', data);
					
					// 명료화 질문의 request_id와 session_id 저장
					if (data.request_id) {
						requestId = data.request_id;
						console.log('🔗 명료화 질문 request_id 저장:', requestId);
					}
					if (data.session_id !== undefined && data.session_id !== null) {
						sessionId = data.session_id;
						console.log('🔗 명료화 질문 session_id 저장:', sessionId);
					}
					
					// 명료화 질문을 그냥 일반 AI 메시지로 표시 (프론트엔드는 명료화 과정을 모름)
					const questionContent = data.message || '추가 정보가 필요합니다.';
					const uniqueTimestamp = `${new Date().toLocaleTimeString()}.${Date.now() % 1000}`;
					const clarificationMessage = {
						id: getNextMessageId(),
						type: 'ai' as const,
						content: questionContent,
						timestamp: uniqueTimestamp,
						isClarification: false, // 명료화 과정을 모르므로 그냥 일반 메시지로 처리
						requestId: requestId || undefined // 현재 진행 중인 request_id 사용
					};
					
					messages = [...messages, clarificationMessage];
					console.log('📝 명료화 질문을 일반 AI 메시지로 추가:', clarificationMessage);
					
					// 로딩 상태 해제
					isLoading = false;
				},
				
				onAnswer: (data) => {
					console.log('📝 스트리밍 청크 수신:', { 
						request_id: data.request_id?.substring(0, 8),
						chunk_index: data.chunk_index,
						is_final: data.is_final,
						content_preview: data.content?.substring(0, 30) + '...'
					});
					
					// 빈 청크 처리 방지
					if (!data.content && data.content !== '') {
						console.log('⚠️ null/undefined 청크 무시');
						return;
					}
					
					const dataRequestId = data.request_id || requestId;
					const hasRequestId = !!(data.request_id || requestId);
					
					// 완료된 답변으로 갈아치우기 (is_final이 true인 경우 - answer_result 메시지)
					// 백엔드에서 answer_result는 chunk_index=0으로 전송됨
					if (data.is_final === true && data.chunk_index === 0) {
						console.log('🔄 완성된 전체 답변으로 기존 스트리밍 결과 갈아치우기 (answer_result)');
						
						const sessionId = data.session_id || currentSessionId;
						
						// request_id로 해당 메시지 찾기 (request_id가 없으면 가장 최근 스트리밍 메시지)
						const messageIndex = hasRequestId 
							? messages.findLastIndex(m => 
								m.type === 'ai' && 
								(m as any).isStreaming === true &&
								(m as any).requestId === dataRequestId
							  )
							: messages.findLastIndex(m => 
								m.type === 'ai' && 
								(m as any).isStreaming === true
							  );
						
						if (messageIndex !== -1) {
							// 기존 스트리밍 메시지를 완전한 답변으로 교체
							messages[messageIndex] = {
								...messages[messageIndex],
								content: data.content,
								isStreaming: false
							};
							// Svelte 반응성을 위한 배열 재할당
							messages = [...messages];
							console.log('✅ 스트리밍 메시지를 완전한 답변으로 갈아치움:', {
								requestId: dataRequestId?.substring(0, 8),
								messageIndex
							});
						} else {
							// 스트리밍 메시지가 없으면 새로 생성
							const newMessage = {
								id: getNextMessageId(),
								type: 'ai' as const,
								content: data.content,
								timestamp: new Date().toLocaleTimeString(),
								isClarification: false,
								isStreaming: false,
								requestId: dataRequestId
							};
							messages = [...messages, newMessage];
							console.log('🆕 새 답변 메시지 생성:', {
								requestId: dataRequestId?.substring(0, 8)
							});
						}
						
						// 버퍼 정리 (answer_result 후 추가 청크 무시를 위해)
						chunkBufferManager.removeBuffer(sessionId);
						console.log('🗑️ 버퍼 정리 완료 - answer_result 처리됨');
						
						return;
					}
					
					// 청크 인덱스 확인 (0도 유효한 값이므로 ?? 사용)
				const chunkIndex = data.chunk_index ?? 1;
				const sessionId = data.session_id || currentSessionId;
				
				// request_id로 해당 메시지 찾기 (request_id가 없으면 가장 최근 스트리밍 메시지)
				let messageIndex = hasRequestId
					? messages.findLastIndex(m => 
						m.type === 'ai' && 
						(m as any).isStreaming === true &&
						(m as any).requestId === dataRequestId
					  )
					: messages.findLastIndex(m => 
						m.type === 'ai' && 
						(m as any).isStreaming === true
					  );
					
				// answer_result로 이미 완료되었거나 다른 request의 청크인 경우
				if (messageIndex === -1) {
					// 첫 번째 청크인 경우에만 새 메시지 생성 (chunk_index 0부터 시작)
					if (chunkIndex === 0) {
						const newMessage = {
							id: getNextMessageId(),
							type: 'ai' as const,
							content: data.content,
							timestamp: new Date().toLocaleTimeString(),
							isClarification: false,
							isStreaming: true,
							requestId: dataRequestId
						};
						messages = [...messages, newMessage];
						console.log('🆕 새 스트리밍 메시지 생성:', {
							requestId: dataRequestId?.substring(0, 8),
							chunkIndex
						});
						messageIndex = messages.length - 1;  // 생성된 메시지의 인덱스 저장
					} else {
						console.log('⚠️ 스트리밍 중인 메시지 없음 - 청크 무시:', {
							requestId: dataRequestId?.substring(0, 8),
							chunkIndex,
							reason: `첫 청크(0)가 아직 도착하지 않음, 현재 청크: ${chunkIndex}`
						});
						return;
					}
				}
					
					// 청크 버퍼에 추가하고 정렬된 텍스트 받기
					const buffer = chunkBufferManager.getBuffer(sessionId);
					const orderedText = buffer.addChunk(
						chunkIndex,
						data.content || '',
						data.is_final || false,
						data.timestamp || new Date().toISOString()
					);
					
					// 기존 스트리밍 메시지를 정렬된 전체 텍스트로 업데이트
					if ((messages[messageIndex] as any).content !== orderedText) {
						// 컨텐츠가 실제로 변경된 경우에만 업데이트
						(messages[messageIndex] as any).content = orderedText;
						// Svelte 반응성을 위해 최소한의 배열 재할당
						messages = [...messages];
						console.log('🔄 스트리밍 메시지 업데이트:', {
							requestId: dataRequestId?.substring(0, 8),
							chunkIndex,
							totalLength: orderedText.length
						});
					} else {
						console.log('⚡ 동일한 컨텐츠 - 배열 재할당 스킵');
					}
					
					// 최종 청크인 경우 스트리밍 완료 처리
					if (data.is_final) {
						console.log('🏁 답변 스트리밍 완료 (is_final=true)');
						
						// 버퍼 정리만 수행 (상태 해제는 onAnswerComplete에서 처리)
						chunkBufferManager.removeBuffer(sessionId);
					}
				},
				
				onAnswerComplete: (data: any) => {
					console.log('✅ 답변 완료:', data);
					
					// full_response가 있으면 안전장치로 갈아치우기 (청크 순서/누락 대비)
					if (data.full_response) {
						console.log('🔄 full_response로 최종 답변 갈아치우기 (안전장치)');
						
						const messageIndex = messages.findLastIndex(m => m.type === 'ai' && (m as any).isStreaming === true);
						
						if (messageIndex !== -1) {
							messages[messageIndex] = {
								...messages[messageIndex],
								content: data.full_response,  // 완전한 답변으로 교체
								isStreaming: false
							} as any;
							messages = [...messages];
							console.log('✅ full_response로 갈아치움 (안전장치 작동)');
						}
					} else {
						// full_response가 없으면 스트리밍 상태만 해제
						const messageIndex = messages.findLastIndex(m => m.type === 'ai' && (m as any).isStreaming === true);
						
						if (messageIndex !== -1) {
							messages[messageIndex] = {
								...messages[messageIndex],
								isStreaming: false
							} as any;
							messages = [...messages];
							console.log('✅ 스트리밍 상태 해제');
						}
					}
					
					// 버퍼 정리
					const sessionId = data.session_id || currentSessionId;
					chunkBufferManager.removeBuffer(sessionId);
					
					// 답변 완료 후 요약 대기 상태로 전환
					isSummarizing = true;
					isLoading = true;
					console.log('📝 답변 완료 - 요약 대기 중');
					
					// 요약 타임아웃 설정 (30초 후 자동 해제)
					setTimeout(() => {
						if (isSummarizing) {
							console.log('⏰ 요약 타임아웃 - 입력 필드 재활성화');
							isSummarizing = false;
							isLoading = false;
						}
					}, 30000);
				},
				
				onMessage: (data) => {
					console.log('📨 일반 메시지 수신:', data);
					
					// 백엔드에서 보내는 메시지 타입에 따라 처리
					switch (data.type) {
						case 'session_status':
							// 세션 상태 정보 처리
							console.log('🔍 세션 상태 정보 수신:', data);
							
							if (data.session_id !== undefined && data.session_id !== null) {
								sessionId = data.session_id;
								console.log('✅ 세션 ID 업데이트 (session_status):', sessionId);
							}
							if (data.request_id) {
								requestId = data.request_id;
								console.log('✅ 요청 ID 업데이트 (session_status):', requestId);
							}
							break;
							
						case 'clarification_question':
							// 명료화 질문은 onClarification 핸들러에서 처리됨
							console.log('🔍 명료화 질문은 onClarification 핸들러에서 이미 처리됨 - 무시');
							break;
							
						case 'streaming_chunk':
							// 스트리밍 청크 처리 - onAnswer 핸들러에서 이미 처리됨
							console.log('📝 streaming_chunk 메시지 무시 - onAnswer 핸들러에서 이미 처리됨');
							return; // 처리하지 않고 바로 종료
							
						case 'summary_complete':
							// 요약 완료 처리
							console.log('📝 요약 완료:', data);
							
							// 요약 완료 시 입력창 활성화
							isSummarizing = false;
							isLoading = false;
							console.log('🔓 요약 완료 - 입력 필드 재활성화됨');
							break;
							
						case 'answer_complete':
							// answer_complete는 onAnswerComplete 핸들러에서 처리됨
							console.log('✅ answer_complete는 onAnswerComplete 핸들러에서 이미 처리됨 - 무시');
							break;
							
						default:
							console.log('⚠️ 처리되지 않은 메시지 타입:', data.type);
							break;
					}
				},
				
				onComplete: () => {
					console.log('✅ 완료됨');
					
					// ⚠️ 중복 방지: onAnswerComplete에서 이미 처리했으므로 여기서는 로그만 출력
					console.log('✅ onComplete 처리 완료 (중복 방지됨)');
					
					// 세션 목록 새로고침
					refreshSessionList();
				},
				
				onError: (error) => {
					console.error('❌ 오류 발생:', error);
					
					const errorMessage = createErrorMessage(error, getNextMessageId());
					messages = [...messages, errorMessage];
					
					// 로딩 및 요약 상태 해제
					isLoading = false;
					isSummarizing = false;
				}
			};

			// 새로운 SSE 연결을 위한 AbortController 생성
			activeSSEController = new AbortController();
			console.log('🔌 새로운 SSE 연결 시작');

			// 새로운 API 클라이언트로 채팅 스트림 시작
			try {
				const result = await maiceClient.chatStream(chatRequest, eventHandlers, activeSSEController);
				console.log('✅ 채팅 스트림 완료:', result);
				
				// 결과에서 세션 정보 업데이트
				if (result && result.sessionId) {
					sessionId = result.sessionId;
					console.log('✅ 완료 후 세션 ID 업데이트:', sessionId);
				}
				if (result && result.requestId) {
					requestId = result.requestId;
					console.log('✅ 완료 후 요청 ID 업데이트:', requestId);
				}
			} catch (error) {
				console.error('❌ 채팅 스트림 오류:', error);
				// 에러 메시지는 onError 핸들러에서 이미 처리됨
				isLoading = false;
			}
			
			console.log('✅ SSE 스트리밍 호출 완료');
			
		} catch (error) {
			console.error('💥 질문 처리 중 오류:', error);
			
			// 에러 분류 및 상태 저장
			const errorInfo = classifyError(error);
			lastError = errorInfo;
			
			// 네트워크 상태 확인
			if (!isOnline) {
				const networkErrorMessage = createAIMessage(
					'🌐 네트워크 연결이 끊어졌습니다. 인터넷 연결을 확인하고 다시 시도해주세요.',
					getNextMessageId()
				);
				messages = [...messages, networkErrorMessage];
			} else {
				// 일반 에러 메시지
				const errorMessage = createErrorMessage(error, getNextMessageId());
				messages = [...messages, errorMessage];
			}
			
			// 에러 발생 시 로딩 및 요약 상태 해제하여 입력 필드 재활성화
			isLoading = false;
			isSummarizing = false;
			console.log('🔓 catch 블록에서 입력 필드 재활성화됨 (isLoading = false)');
		}
	}
	
	function handleBackToDashboard() {
		goto('/dashboard');
	}
	
	function handleClearChat() {
		console.log('🔄 새 대화 시작');
		
		// 기존 SSE 연결 중단
		if (activeSSEController) {
			activeSSEController.abort();
			activeSSEController = null;
			console.log('🔌 새 대화 시작으로 SSE 연결 중단됨');
		}
		
		// 세션 ID와 요청 ID 초기화
		sessionId = null;
		requestId = undefined;
		
		// 스크롤 상태 초기화
		isUserScrolling = false;
		if (scrollTimeout) {
			clearTimeout(scrollTimeout);
			scrollTimeout = null;
		}
		
		// 입력 필드 초기화
		if (messageInputRef && typeof messageInputRef.clear === 'function') {
			messageInputRef.clear();
		}
		
		// 메시지 배열 초기화
		messages = [createDefaultMessage()];
		
		// 로딩 및 요약 상태 초기화
		isLoading = false;
		isSummarizing = false;
		
		console.log('✅ 새 대화 시작 완료 - sessionId 초기화됨');
	}
	
	// 토큰 검증 및 인증 체크
	async function verifyAuthentication() {
		// 테스트 모드: 인증 체크 우회 (개발 환경에서만 허용)
		const isTestMode = import.meta.env.DEV && window.location.search.includes('test=true');
		console.log('🔍 테스트 모드 체크:', {
			hasTestParam: window.location.search.includes('test=true'),
			isDev: import.meta.env.DEV,
			viteEnv: import.meta.env.VITE_ENVIRONMENT,
			isTestMode: isTestMode
		});
		
		if (!isTestMode) {
			// 인증 상태 확인
			if (!isAuthenticated || !authToken) {
				console.warn('⚠️ 인증되지 않은 사용자 - 로그인 페이지로 이동');
				// 약간의 지연을 주고 리다이렉트
				setTimeout(() => {
					goto('/login');
				}, 100);
				return false;
			}
			console.log('✅ 인증된 사용자 확인됨');
			
			// 토큰 유효성 검증 (에러가 발생하면 무시)
			try {
				console.log('🔍 토큰 유효성 검증 시작...');
				const isValid = await authActions.checkTokenValidity();
				
				if (!isValid) {
					console.warn('⚠️ 토큰이 만료되었습니다. 로그아웃 처리합니다.');
					await authActions.logout();
					setTimeout(() => {
						goto('/login');
					}, 100);
					return false;
				}
				
				console.log('✅ 토큰이 유효합니다');
			} catch (error) {
				console.error('❌ 토큰 검증 중 에러 발생:', error);
				// 에러가 발생해도 일단 페이지는 로드 (백엔드가 응답하지 않는 경우 대비)
				console.warn('⚠️ 토큰 검증에 실패했지만 계속 진행합니다.');
			}
		} else {
			console.log('🧪 테스트 모드로 실행 중');
			// 테스트용 가짜 사용자 데이터 설정
			user = {
				id: 1,
				username: 'test_user',
				role: 'STUDENT',
				email: 'dev@example.com',
				access_token: ''
			};
			isAuthenticated = true;
			authToken = '';
		}
		
		return true;
	}

	// 외부 클릭 및 네트워크 리스너 초기화
	let isListenersSetup = $state(false);
	
	function setupAllListeners() {
		if (!isListenersSetup) {
			console.log('📡 이벤트 리스너 설정 중...');
			document.addEventListener('click', handleOutsideClick);
			setupNetworkStatusListener();
			isListenersSetup = true;
		}
	}

	// 컴포넌트 마운트 시 실행
	onMount(() => {
		console.log('🚀 MAICE 채팅 페이지 마운트됨');
		
		// 새로고침 시 요청 ID만 초기화 (세션 ID는 유지)
		requestId = undefined;
		messages = [createDefaultMessage()];
		isLoading = false;
		isSummarizing = false;
		isClarificationMode = false;
		currentClarificationRequest = null;
		
		// 스크롤 상태 초기화
		isUserScrolling = false;
		if (scrollTimeout) {
			clearTimeout(scrollTimeout);
			scrollTimeout = null;
		}
		
		console.log('🔄 새로고침으로 인한 세션 초기화 완료');
		
		// 외부 클릭 이벤트 리스너와 네트워크 리스너는 무조건 추가
		setupAllListeners();
		
		// 토큰 검증 및 인증 체크 (비동기로 실행)
		verifyAuthentication().then((isAuthValid) => {
			if (!isAuthValid) {
				console.warn('⚠️ 인증 실패, 페이지 종료');
				return;
			}
			
			// 인증 성공 후 실행될 로직들
			// 연구 동의 상태 확인 (모든 사용자 대상)
			setTimeout(() => {
				checkResearchConsent();
			}, 500);
			
			// 입력 필드에 포커스 (스크롤 방지)
			setTimeout(() => {
				if (messageInputRef && typeof messageInputRef.focus === 'function') {
					messageInputRef.focus({ preventScroll: true });
				}
			}, 200);
		});
		
		// 컴포넌트 언마운트 시 이벤트 리스너 제거
		return () => {
			console.log('🧹 컴포넌트 언마운트, 리스너 제거');
			document.removeEventListener('click', handleOutsideClick);
		};
	});

	// 로그인 함수
	function handleLogin() {
		goto('/login');
	}
	
	// 로그아웃 함수
	async function handleLogout() {
		console.log('MAICE 페이지에서 로그아웃 시작');
		await authActions.logout();
		console.log('MAICE 페이지 로그아웃 완료');
		goto('/');
	}
	
	// 연구 동의 관련 함수들
	async function handleConsentAccept() {
		try {
			await consentActions.acceptConsent(authToken);
			showConsentModal = false;
			console.log('✅ 연구 참여 동의 완료');
			// 연구 동의 완료 후 업데이트 노트 확인
			setTimeout(() => {
				checkUpdateNote();
			}, 300);
		} catch (error) {
			console.error('❌ 연구 동의 처리 실패:', error);
			// 동의 실패 시에도 모달은 닫기
			showConsentModal = false;
		}
	}
	
	async function handleConsentReject() {
		try {
			// 동의 철회 처리 (선택사항)
			// await consentActions.withdrawConsent(authToken);
		} catch (error) {
			console.error('❌ 연구 동의 철회 실패:', error);
		}
		
		showConsentModal = false;
		// 동의하지 않으면 대시보드로 리다이렉트
		goto('/dashboard');
		console.log('❌ 연구 참여 동의 거부');
	}
	
	function checkResearchConsent() {
		// 모든 사용자에게 동의 확인 (학생, 교사, 관리자 모두)
		// 백엔드 상태와 로컬 상태 모두 확인
		const hasBackendConsent = user?.research_consent && !user?.research_consent_withdrawn_at;
		const shouldShowModal = user && 
			!hasResearchConsent && 
			!hasBackendConsent;
			
		if (shouldShowModal) {
			showConsentModal = true;
		} else {
			// 연구 동의가 완료되었거나 이미 동의한 경우 업데이트 노트 확인
			checkUpdateNote();
		}
	}
	
	function checkUpdateNote() {
		// 업데이트 노트를 읽었는지 확인
		const userId = getCurrentUserId();
		
		if (!userId) {
			console.log('⚠️ 사용자 ID 없음, 업데이트 노트 건너뜀');
			return;
		}
		
		// 로컬 스토리지에서 체크 여부 확인
		const hasRead = hasUserReadUpdateNote(userId);
		
		if (!hasRead) {
			console.log('📢 업데이트 노트 표시:', userId);
			showUpdateNoteModal = true;
		} else {
			console.log('✅ 업데이트 노트 이미 읽음 또는 보지 않기로 설정됨:', userId);
		}
	}
	
	function handleUpdateNoteClose() {
		showUpdateNoteModal = false;
		console.log('✅ 업데이트 노트 닫기');
		
		// 로컬 스토리지에서 다시 확인
		const userId = getCurrentUserId();
		if (userId) {
			const hasRead = hasUserReadUpdateNote(userId);
			console.log('📋 업데이트 노트 상태:', hasRead ? '읽음/보지않기 설정됨' : '읽지 않음');
		}
	}
</script>

<svelte:head>
	<title>MAICE AI 학습 도우미 - MAICE</title>
</svelte:head>

<div class="chat-app">
	<!-- 상단 헤더 -->
	<header class="chat-header">
		<div class="header-content desktop-header">
			<!-- 왼쪽: 앱 타이틀과 핵심 기능들 -->
			<div class="header-main">
				<h1 class="app-title">MAICE AI</h1>
				
				<!-- 현재 세션 ID 표시 -->
				{#if sessionId}
					<div class="session-info">
						<span class="session-label">세션</span>
						<span class="session-id">#{sessionId}</span>
					</div>
				{/if}
				
				<!-- AI 모드 토글 버튼 제거됨 (백엔드에서 자동 할당) -->
				
				<Button 
					variant="secondary" 
					size="sm" 
					onclick={handleClearChat}
					class="new-chat-button"
				>
					<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
						<path d="M3 3v5h5"/>
					</svg>
					새 대화
				</Button>
				
				<Button 
					variant="ghost" 
					size="sm" 
					onclick={() => isSessionSidebarOpen = !isSessionSidebarOpen}
					class="session-button"
				>
					<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
					</svg>
					세션
				</Button>
			</div>
			
			<!-- 오른쪽: 사용자 정보와 추가 기능들 -->
			<div class="header-right">
				<!-- 테마 토글 버튼 -->
				<div class="theme-toggle-container">
					<ThemeToggle />
				</div>
				
				{#if user}
					<div class="user-info">
						<div class="user-avatar">
							{#if user.google_picture}
								<img src={user.google_picture} alt="프로필" />
							{:else}
								<span class="avatar-text">
									{user.name ? user.name.charAt(0).toUpperCase() : user.username.charAt(0).toUpperCase()}
								</span>
							{/if}
						</div>
						<div class="user-details">
							<span class="user-name">{user.name || user.username}</span>
							<span class="user-role">
								{user.role === 'student' ? '학생' : user.role === 'teacher' ? '교사' : '관리자'}
							</span>
						</div>
					</div>
					
					<Button variant="ghost" size="sm" onclick={() => { handleLogout(); isHamburgerMenuOpen = false; }} class="logout-button">
						<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>
						</svg>
						로그아웃
					</Button>
				{:else}
					<Button variant="primary" size="sm" onclick={() => { handleLogin(); isHamburgerMenuOpen = false; }} class="login-button">
						로그인
					</Button>
				{/if}
			</div>
		</div>
		
		<!-- 모바일 헤더 -->
		<div class="header-content mobile-header">
			<!-- 상단 행: 앱 타이틀과 햄버거 버튼 -->
			<div class="mobile-header-top">
				<div class="mobile-title-section">
					<h1 class="mobile-app-title">MAICE AI</h1>
					<!-- 현재 세션 ID 표시 (모바일) -->
					{#if sessionId}
						<div class="session-info mobile">
							<span class="session-label">세션</span>
							<span class="session-id">#{sessionId}</span>
						</div>
					{/if}
				</div>
				
				<!-- 햄버거 버튼과 메뉴를 감싸는 wrapper -->
				<div class="hamburger-wrapper">
					<Button 
						variant="ghost" 
						size="lg" 
						onclick={() => isHamburgerMenuOpen = !isHamburgerMenuOpen}
						class="hamburger-button"
					>
						<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
							<line x1="3" y1="6" x2="21" y2="6"/>
							<line x1="3" y1="12" x2="21" y2="12"/>
							<line x1="3" y1="18" x2="21" y2="18"/>
						</svg>
					</Button>
					
					<!-- 햄버거 메뉴 컴포넌트 -->
					<HamburgerMenu
						bind:isOpen={isHamburgerMenuOpen}
						bind:user={user}
						onBackToDashboard={handleBackToDashboard}
						onClearChat={handleClearChat}
						onToggleSession={() => isSessionSidebarOpen = !isSessionSidebarOpen}
						onLogin={handleLogin}
						onLogout={handleLogout}
					/>
				</div>
			</div>
		</div>
	</header>

	<!-- 메인 채팅 영역 -->
	<main class="chat-main">
		<!-- 세션 사이드바 -->
		<aside class="session-sidebar" class:open={isSessionSidebarOpen}>
			<div class="sidebar-content">
				<SessionManager
					{authToken}
					currentSessionId={sessionId}
					onSessionSelect={handleSessionSelect}
					onNewSession={handleNewSession}
					refreshTrigger={sessionRefreshTrigger}
				/>
			</div>
		</aside>
		
		<!-- 채팅 컨테이너 -->
		<div class="chat-container">
			<!-- 채팅 콘텐츠 래퍼 -->
			<div class="chat-content-wrapper">
				<!-- 메시지 영역 -->
				<div class="messages-area" bind:this={messagesAreaRef} onscroll={maintainScrollPosition} onwheel={handleWheelScroll}>
					<MessageList {messages} {isLoading} />
				</div>
				
				<!-- 입력 영역 -->
				<div class="input-area">
					<InlineMathInput
						placeholder={
							isSummarizing ? "대화를 요약하고 있습니다... 잠시만 기다려주세요 📝" :
								"수학 질문을 입력하세요..."
						}
						disabled={isLoading || isSummarizing}
						{isLoading}
						on:send={handleMessageSend}
						on:openCamera={() => showCameraModal = true}
						on:openImageCrop={(e) => { selectedImageUrl = e.detail.imageUrl; showImageCropModal = true; }}
						bind:this={messageInputRef}
					/>
				</div>
			</div>
		</div>
	</main>
</div>

<!-- 연구 참여 동의 모달 -->
<ConsentModal 
	isOpen={showConsentModal}
	onAccept={handleConsentAccept}
	onReject={handleConsentReject}
/>

<!-- 업데이트 노트 모달 -->
<UpdateNoteModal 
	isOpen={showUpdateNoteModal}
	onClose={handleUpdateNoteClose}
/>

<!-- 카메라 모달 (페이지 레벨) -->
<CameraModal 
	bind:show={showCameraModal}
	on:capture={(e) => { selectedImageUrl = e.detail.imageUrl; showImageCropModal = true; }}
/>

<!-- 이미지 크롭 모달 (페이지 레벨) -->
<ImageCropModal 
	bind:show={showImageCropModal}
	imageUrl={selectedImageUrl}
	on:confirm={(e) => {
		if (messageInputRef) {
			messageInputRef.handleImageCropConfirm(e);
		}
	}}
/>

<!-- CSS는 maice.css 파일로 분리됨 -->
