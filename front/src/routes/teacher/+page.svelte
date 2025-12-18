<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth';
	import { themeStore, themeActions } from '$lib/stores/theme';
	import { 
		getRandomUnevaluatedSession,
		createOrUpdateManualEvaluation,
		getEvaluationStats,
		getResearchConsentStatus,
		getTeacherSessions,
		getSessionDetail,
		type ChecklistItem,
		type ChecklistElement,
		type ManualEvaluationV43
	} from '$lib/api';
	import Button from '$lib/components/common/Button.svelte';
	import Card from '$lib/components/common/Card.svelte';
	import MessageList from '$lib/components/maice/MessageList.svelte';
	import TeacherGuideModal from '$lib/components/teacher/TeacherGuideModal.svelte';
	import ResearchConsentModal from '$lib/components/teacher/ResearchConsentModal.svelte';
	import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
	
	// authStore를 reactive로 사용
	$: authUser = $authStore.user;
	
	let token: string = '';
	let selectedSession: any = null;
	let sessionMessages: any[] = [];
	let isLoading = false;
	let error: string | null = null;
	let currentSection: 'A' | 'B' | 'C' = 'A';  // 현재 보여지는 섹션
	let evaluatedCount = 0;  // 평가 완료한 세션 수
	
	// 평가 통계
	let evaluationStats: any = null;
	let targetGoal = 100;
	
	// 모달 상태
	let showGuideModal = false;
	let showConsentModal = false;
	
	// 탭 상태
	let currentTab: 'evaluation' | 'history' = 'evaluation';
	let evaluatedSessions: any[] = [];
	let isLoadingHistory = false;
	
	// v4.5 체크리스트 평가 폼 상태 (교사 의견 포함)
	interface EvaluationForm {
		A1: ChecklistItem;
		A2: ChecklistItem;
		A3: ChecklistItem;
		B1: ChecklistItem;
		B2: ChecklistItem;
		B3: ChecklistItem;
		C1: ChecklistItem;
		C2: ChecklistItem;
		// 교사 의견
		item_feedbacks: Record<string, string>;
		rubric_overall_feedback: string;
		educational_llm_suggestions: string;
		// 인덱스 시그니처 추가
		[key: string]: ChecklistItem | string | Record<string, string>;
	}
	
	// 체크리스트 요소 초기값
	const createEmptyElement = (): ChecklistElement => ({ value: 0, evidence: '' });
	const createEmptyItem = (): ChecklistItem => ({
		element1: createEmptyElement(),
		element2: createEmptyElement(),
		element3: createEmptyElement(),
		element4: createEmptyElement()
	});
	
	let evaluationForm: EvaluationForm = {
		A1: createEmptyItem(),
		A2: createEmptyItem(),
		A3: createEmptyItem(),
		B1: createEmptyItem(),
		B2: createEmptyItem(),
		B3: createEmptyItem(),
		C1: createEmptyItem(),
		C2: createEmptyItem(),
		item_feedbacks: {},
		rubric_overall_feedback: '',
		educational_llm_suggestions: ''
	};
	
	
	// 체크리스트 요소 이름 정의 (루브릭에서 정의된 대로)
	const elementLabels: Record<string, string[]> = {
		A1: ['수학적 개념/원리의 정확성', '교과과정 내 위계성 파악', '수학적 용어 사용의 적절성', '문제해결 방향의 구체성'],
		A2: ['핵심 질문의 단일성', '조건 제시의 완결성', '문장 구조의 논리성', '질문 의도의 명시성'],
		A3: ['현재 학습 단계 설명', '선수학습 내용 언급', '구체적 어려움 명시', '학습 목표 제시'],
		B1: ['학습자 수준별 접근', '선수지식 연계성', '학습 난이도 조절', '개인화된 피드백'],
		B2: ['개념 설명의 위계화', '단계별 논리 전개', '핵심 요소 강조', '예시 활용의 적절성'],
		B3: ['심화학습 방향 제시', '응용문제 연계성', '오개념 교정 전략', '자기주도 학습 유도'],
		C1: ['학습 목표 중심 일관성', '누적 맥락 참조 (전체 대화 이력)', '주제 연속성', '직전 턴 연결성 (턴바이턴 흐름)'],
		C2: ['사고 과정 유도', '이해도 확인', '메타인지 촉진', '깊이 있는 사고 유도']
	};
	
	// 각 요소별 상세 설명 및 예시
	const elementTooltips: Record<string, {description: string, example: string}[]> = {
		A1: [
			{
				description: '수학 용어를 정확하게 사용했는가?',
				example: '✓ "n^2 < 2^n 귀납법 증명"\n✗ "파이 1억 자리"'
			},
			{
				description: '학년 수준에 맞는 개념인가?',
				example: '✓ "고2 수학적 귀납법"\n✗ 학년/수준 미언급'
			},
			{
				description: '전문 용어를 적절히 사용했는가?',
				example: '✓ "귀납 가정", "귀납 단계"\n✗ 일반 용어만 사용'
			},
			{
				description: '해결하려는 문제가 구체적인가?',
				example: '✓ "귀납 단계 증명 방법"\n✗ "귀납법 어려워"'
			}
		],
		A2: [
			{
				description: '한 번에 하나의 명확한 질문을 하는가?',
				example: '✓ "귀납 단계 어떻게 증명?"\n✗ "귀납법이랑 수열이랑 미분이랑..."'
			},
			{
				description: '필요한 조건/정보를 모두 제시했는가?',
				example: '✓ "1+2+...+n = n(n+1)/2 증명"\n✗ "이거 어떻게 풀어?"'
			},
			{
				description: '문장이 논리적으로 구성되었는가?',
				example: '✓ 주어+서술어 명확\n✗ "ㅁㅝ야", 의미불명'
			},
			{
				description: '무엇을 알고 싶은지 명확한가?',
				example: '✓ "귀납 단계 증명법 알려줘"\n✗ "귀납법?"'
			}
		],
		A3: [
			{
				description: '학년/단원/진도를 언급했는가?',
				example: '✓ "고2, 귀납법 처음 배움"\n✗ 학습 단계 미언급'
			},
			{
				description: '이전에 배운 내용을 언급했는가?',
				example: '✓ "수열의 합 배웠어요"\n✗ 선수학습 미언급'
			},
			{
				description: '어디서 막혔는지 구체적으로 말했는가?',
				example: '✓ "귀납 단계가 어려워요"\n✗ "어려워요"'
			},
			{
				description: '무엇을 배우고 싶은지 목표를 제시했는가?',
				example: '✓ "귀납법 증명 배우고 싶어요"\n✗ 목표 미제시'
			}
		],
		B1: [
			{
				description: '학생 수준에 맞게 설명했는가?',
				example: '✓ 고2 수준 용어 사용\n✗ 대학 수준 설명'
			},
			{
				description: '이미 배운 내용과 연결했는가?',
				example: '✓ "배운 수열 개념 활용"\n✗ 선수지식 무시'
			},
			{
				description: '너무 어렵거나 쉽지 않은가?',
				example: '✓ 적절한 난이도 유지\n✗ 너무 어렵거나 쉬움'
			},
			{
				description: '학생 상황을 고려한 피드백인가?',
				example: '✓ "귀납 단계 어려워하니 단계별 설명"\n✗ 일반적 설명'
			}
		],
		B2: [
			{
				description: '쉬운 것부터 어려운 것으로 단계적 설명?',
				example: '✓ 기저→귀납 가정→귀납 단계\n✗ 무작위 순서'
			},
			{
				description: '각 단계가 논리적으로 연결되는가?',
				example: '✓ 단계 간 연결 명확\n✗ 단절된 설명'
			},
			{
				description: '중요한 내용을 명확히 강조했는가?',
				example: '✓ "핵심은 귀납 가정 활용"\n✗ 강조 없음'
			},
			{
				description: '이해를 돕는 적절한 예시 제공?',
				example: '✓ "1+2+3+...+n 예시"\n✗ 예시 없음'
			}
		],
		B3: [
			{
				description: '더 깊이 공부할 방향을 제시했는가?',
				example: '✓ "강한 귀납법 공부해보세요"\n✗ 심화 방향 없음'
			},
			{
				description: '관련된 응용 문제를 연결했는가?',
				example: '✓ "피보나치 수열 증명"\n✗ 응용 연계 없음'
			},
			{
				description: '잘못된 이해를 바로잡았는가?',
				example: '✓ "n=1만 확인하면 안 돼요"\n✗ 오개념 방치'
			},
			{
				description: '스스로 탐구하도록 유도했는가?',
				example: '✓ "직접 증명해볼까요?"\n✗ 답만 제공'
			}
		],
		C1: [
			{
				description: '학습 목표를 벗어나지 않고 진행?',
				example: '✓ 귀납법 주제 일관 유지\n✗ 주제 이탈'
			},
			{
				description: '전체 대화 이력을 기억하고 참조하는가? (멀리 떨어진 이전 대화도 기억)',
				example: '✓ "처음에 질문하신...", "아까 말한..."\n✗ 세션 메모리 없이 답변\n\n💡 C1-4와 차이: 멀리 떨어진 대화 참조'
			},
			{
				description: '주제가 자연스럽게 연결되는가?',
				example: '✓ 기저→귀납 자연스러운 전개\n✗ 갑작스런 주제 변경'
			},
			{
				description: '바로 직전 턴과 유기적으로 연결되는가? (턴바이턴 흐름)',
				example: '✓ 직전 학생 발화의 구체적 내용 언급\n✗ 직전 턴 내용 무시하고 답변\n\n💡 C1-2와 차이: 바로 직전 턴만 평가'
			}
		],
		C2: [
			{
				description: '학생의 사고 과정을 유도하는가?',
				example: '✓ "왜 그렇게 생각했나요?"\n✗ 답만 제공'
			},
			{
				description: '학생의 이해도를 확인하는가?',
				example: '✓ "이해했나요? 설명해볼래요?"\n✗ 확인 없음'
			},
			{
				description: '자신의 학습 과정을 돌아보게 하는가?',
				example: '✓ "무엇을 배웠나요?"\n✗ 성찰 유도 없음'
			},
			{
				description: '단순 암기를 넘어 깊은 사고 유도?',
				example: '✓ "왜 그럴까요? 추론해보세요"\n✗ 암기만 요구'
			}
		]
	};
	
	// Tooltip 상태 관리
	let activeTooltip: string | null = null;
	
	function showTooltip(key: string) {
		activeTooltip = key;
	}
	
	function hideTooltip() {
		activeTooltip = null;
	}
	
	const itemTitles: Record<string, string> = {
		A1: 'A1. 수학적 전문성',
		A2: 'A2. 질문 구조화',
		A3: 'A3. 학습 맥락 적용',
		B1: 'B1. 학습자 맞춤도',
		B2: 'B2. 설명의 체계성',
		B3: 'B3. 학습 내용 확장성',
		C1: 'C1. 대화 일관성',
		C2: 'C2. 학습 과정 지원성'
	};
	
	onMount(() => {
		const unsubscribe = authStore.subscribe(state => {
			if (!state.isAuthenticated || !state.user) {
				goto('/');
				return;
			}
			
			const userRole = state.user.role?.toLowerCase();
			// 교사와 관리자 모두 접근 가능
			if (userRole !== 'teacher' && userRole !== 'admin') {
				goto('/dashboard');
				return;
			}
			
			token = state.token || '';
			
			if (token) {
				// DB에서 연구 동의 상태 확인
				checkResearchConsent();
			}
		});
		
		return unsubscribe;
	});
	
	async function checkResearchConsent() {
		try {
			// DB에서 연구 동의 상태 확인
			const data = await getResearchConsentStatus(token);
			
			if (!data.research_consent) {
				// DB에 동의 기록이 없거나 거부한 경우
				showConsentModal = true;
			} else {
				// 동의했으면 안내 모달 확인
				checkGuideModal();
			}
		} catch (error) {
			console.error('연구 동의 상태 확인 실패:', error);
			// 에러 시 모달 표시 (안전하게)
			showConsentModal = true;
		}
	}
	
	function checkGuideModal() {
		// 안내를 읽었는지 확인
		const guideRead = typeof window !== 'undefined' 
			? localStorage.getItem('teacher_guide_read') 
			: null;
		
		if (!guideRead) {
			showGuideModal = true;
		} else {
			// 안내도 읽었으면 바로 시작
			startEvaluation();
		}
	}
	
	function startEvaluation() {
		loadEvaluationStats();
		loadRandomSession();
	}
	
	function handleConsentAccept() {
		showConsentModal = false;
		checkGuideModal();
	}
	
	function handleConsentReject() {
		showConsentModal = false;
		alert('연구 참여에 동의하지 않으셨습니다. 대시보드로 이동합니다.');
		goto('/dashboard');
	}
	
	function handleGuideClose() {
		showGuideModal = false;
		startEvaluation();
	}
	
	async function loadEvaluationStats() {
		if (!token) return;
		
		try {
			evaluationStats = await getEvaluationStats(token);
		} catch (err: any) {
			console.error('통계 로드 실패:', err);
		}
	}
	
	async function loadRandomSession() {
		if (!token) return;
		
		try {
			isLoading = true;
			error = null;
			
			const response = await getRandomUnevaluatedSession(token);
			selectedSession = response;
			
			// 메시지 변환 (MessageList 컴포넌트 형식에 맞게)
			// 시스템 메시지(maice_processing 등)는 제외하고, 학생에게 보이는 메시지만 표시
			sessionMessages = response.messages
				.filter((msg: any) => {
					// 시스템 메시지 타입 필터링 (학생에게 보이지 않는 메시지)
					const systemMessageTypes = ['maice_processing', 'system', 'internal'];
					return !systemMessageTypes.includes(msg.message_type);
				})
				.map((msg: any) => ({
					id: msg.id,
					type: msg.sender === 'user' ? 'user' : 'ai',
					content: msg.content,
					timestamp: msg.created_at,
					isClarification: msg.message_type === 'maice_clarification_question'
				}));
			
			// 새로운 세션이므로 평가 폼 초기화
			resetEvaluationForm();
			currentSection = 'A';  // 항상 A 섹션부터 시작
			
		} catch (err: any) {
			error = err.message || '세션을 불러올 수 없습니다.';
			console.error('랜덤 세션 로드 실패:', err);
			
			// 더 이상 평가할 세션이 없는 경우
			if (err.message?.includes('모든 세션을 평가했습니다')) {
				alert('🎉 축하합니다!\n모든 세션 평가를 완료했습니다.');
				goto('/dashboard');
			}
		} finally {
			isLoading = false;
		}
	}
	
	function loadChecklistData(checklistData: any) {
		// 체크리스트 데이터를 폼에 로드
		const items = ['A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'C1', 'C2'];
		items.forEach(itemKey => {
			if (checklistData[itemKey]) {
				const data = checklistData[itemKey];
				const elementNames = Object.keys(data);
				
				// element1, element2, element3, element4로 매핑
				for (let i = 0; i < 4 && i < elementNames.length; i++) {
					const elementKey = `element${i + 1}` as keyof ChecklistItem;
					const elementData = data[elementNames[i]];
					(evaluationForm[itemKey as keyof EvaluationForm] as ChecklistItem)[elementKey] = {
						value: elementData.value,
						evidence: elementData.evidence || ''
					};
				}
			}
		});
	}
	
	function resetEvaluationForm() {
		evaluationForm = {
			A1: createEmptyItem(),
			A2: createEmptyItem(),
			A3: createEmptyItem(),
			B1: createEmptyItem(),
			B2: createEmptyItem(),
			B3: createEmptyItem(),
		C1: createEmptyItem(),
		C2: createEmptyItem(),
		item_feedbacks: {},
		rubric_overall_feedback: '',
		educational_llm_suggestions: ''
	};
}
	
	function calculateItemScore(item: ChecklistItem): number {
		const checkedCount = item.element1.value + item.element2.value + item.element3.value + item.element4.value;
		return checkedCount + 1;  // 0개=1점, 1개=2점, ..., 4개=5점
	}
	
	function calculateQuestionTotal(): number {
		return calculateItemScore(evaluationForm.A1) + 
		       calculateItemScore(evaluationForm.A2) + 
		       calculateItemScore(evaluationForm.A3);
	}
	
	function calculateAnswerTotal(): number {
		return calculateItemScore(evaluationForm.B1) + 
		       calculateItemScore(evaluationForm.B2) + 
		       calculateItemScore(evaluationForm.B3);
	}
	
	function calculateContextTotal(): number {
		return calculateItemScore(evaluationForm.C1) + 
		       calculateItemScore(evaluationForm.C2);
	}
	
	function calculateOverallTotal(): number {
		return calculateQuestionTotal() + calculateAnswerTotal() + calculateContextTotal();
	}
	
	function isItemComplete(itemKey: keyof EvaluationForm): boolean {
		return calculateItemScore(evaluationForm[itemKey] as ChecklistItem) === 5;
	}
	
	function isSectionComplete(section: 'A' | 'B' | 'C'): boolean {
		if (section === 'A') {
			return ['A1', 'A2', 'A3'].every(key => isItemComplete(key as keyof EvaluationForm));
		} else if (section === 'B') {
			return ['B1', 'B2', 'B3'].every(key => isItemComplete(key as keyof EvaluationForm));
		} else {
			return ['C1', 'C2'].every(key => isItemComplete(key as keyof EvaluationForm));
		}
	}
	
	function getOverallProgress(): number {
		const totalItems = 8;  // A1-A3, B1-B3, C1-C2
		const completedItems = ['A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'C1', 'C2'].filter(key => 
			isItemComplete(key as keyof EvaluationForm)
		).length;
		return Math.round((completedItems / totalItems) * 100);
	}
	
	async function saveEvaluation() {
		if (!token || !selectedSession) return;
		
		try {
			isLoading = true;
			error = null;
			
			const request: ManualEvaluationV43 = {
				session_id: selectedSession.id,
				A1: evaluationForm.A1,
				A2: evaluationForm.A2,
				A3: evaluationForm.A3,
				B1: evaluationForm.B1,
				B2: evaluationForm.B2,
				B3: evaluationForm.B3,
				C1: evaluationForm.C1,
				C2: evaluationForm.C2,
				item_feedbacks: evaluationForm.item_feedbacks,
				rubric_overall_feedback: evaluationForm.rubric_overall_feedback,
				educational_llm_suggestions: evaluationForm.educational_llm_suggestions
			};
			
			await createOrUpdateManualEvaluation(token, request);
			
			evaluatedCount++;
			await loadEvaluationStats();  // 통계 갱신
			alert(`✅ 평가가 저장되었습니다! (${evaluatedCount}개 완료)\n다음 세션을 불러옵니다.`);
			
			// 다음 랜덤 세션 자동 로드
			await loadRandomSession();
			
		} catch (err: any) {
			error = err.message || '평가 저장에 실패했습니다.';
			console.error('평가 저장 실패:', err);
			alert(error);
		} finally {
			isLoading = false;
		}
	}
	
	// 평가된 세션 목록 로드
	async function loadEvaluatedSessions() {
		if (!token) return;
		
		try {
			isLoadingHistory = true;
			const data = await getTeacherSessions(token, 0, 100, undefined, true);
			evaluatedSessions = data.sessions || [];
		} catch (err: any) {
			console.error('평가 목록 로드 실패:', err);
			error = '평가 목록을 불러오는데 실패했습니다.';
		} finally {
			isLoadingHistory = false;
		}
	}
	
	// checklist_data를 프론트엔드 형식으로 변환
	function convertChecklistDataToForm(checklistData: any): ChecklistItem {
		if (!checklistData) return createEmptyItem();
		
		// 백엔드 저장 형식에서 프론트엔드 형식으로 변환
		const keys = Object.keys(checklistData);
		if (keys.length === 0) return createEmptyItem();
		
		return {
			element1: checklistData[keys[0]] || createEmptyElement(),
			element2: checklistData[keys[1]] || createEmptyElement(),
			element3: checklistData[keys[2]] || createEmptyElement(),
			element4: checklistData[keys[3]] || createEmptyElement()
		};
	}
	
	// 특정 세션 다시 로드 (재평가)
	async function loadSessionForReview(sessionId: number) {
		if (!token) return;
		
		try {
			isLoading = true;
			error = null;
			
			const data = await getSessionDetail(token, sessionId);
			selectedSession = data;
			
			// 메시지를 MessageList 컴포넌트 형식으로 변환
			sessionMessages = (data.messages || [])
				.filter((msg: any) => {
					// 시스템 메시지 타입 필터링 (학생에게 보이지 않는 메시지)
					const systemMessageTypes = ['maice_processing', 'system', 'internal'];
					return !systemMessageTypes.includes(msg.message_type);
				})
				.map((msg: any) => ({
					id: msg.id,
					type: msg.sender === 'user' ? 'user' : 'ai',  // sender를 type으로 변환
					content: msg.content,
					timestamp: msg.created_at,
					isClarification: msg.message_type === 'maice_clarification_question'
				}));
			
			// 기존 평가 데이터 로드
			if (data.current_evaluation && data.current_evaluation.checklist_data) {
				const checklist = data.current_evaluation.checklist_data;
				const eval_data = data.current_evaluation;
				
				evaluationForm = {
					A1: convertChecklistDataToForm(checklist.A1),
					A2: convertChecklistDataToForm(checklist.A2),
					A3: convertChecklistDataToForm(checklist.A3),
					B1: convertChecklistDataToForm(checklist.B1),
					B2: convertChecklistDataToForm(checklist.B2),
					B3: convertChecklistDataToForm(checklist.B3),
					C1: convertChecklistDataToForm(checklist.C1),
					C2: convertChecklistDataToForm(checklist.C2),
					item_feedbacks: eval_data.item_feedbacks || {},
					rubric_overall_feedback: eval_data.rubric_overall_feedback || '',
					educational_llm_suggestions: eval_data.educational_llm_suggestions || ''
				};
			} else {
				// 평가 데이터가 없으면 초기화
				evaluationForm = {
					A1: createEmptyItem(),
					A2: createEmptyItem(),
					A3: createEmptyItem(),
					B1: createEmptyItem(),
					B2: createEmptyItem(),
					B3: createEmptyItem(),
					C1: createEmptyItem(),
					C2: createEmptyItem(),
					item_feedbacks: {},
					rubric_overall_feedback: '',
					educational_llm_suggestions: ''
				};
			}
			
			// 평가 탭으로 전환
			currentTab = 'evaluation';
			currentSection = 'A';
			
		} catch (err: any) {
			error = err.message || '세션 로드에 실패했습니다.';
			console.error('세션 로드 실패:', err);
		} finally {
			isLoading = false;
		}
	}
	
	
	function goToSection(section: 'A' | 'B' | 'C') {
		currentSection = section;
		// 스크롤을 상단으로
		const panel = document.querySelector('.evaluation-panel');
		if (panel) {
			panel.scrollTop = 0;
		}
	}
	
	function toggleCheckbox(itemKey: keyof EvaluationForm, elementKey: keyof ChecklistItem) {
		const current = (evaluationForm[itemKey] as ChecklistItem)[elementKey] as ChecklistElement;
		current.value = current.value === 1 ? 0 : 1;
		evaluationForm = evaluationForm;  // Svelte reactivity trigger
	}
</script>

<!-- 모달들 -->
<TeacherGuideModal isOpen={showGuideModal} onClose={handleGuideClose} />
<ResearchConsentModal 
	isOpen={showConsentModal}
	token={token}
	onAccept={handleConsentAccept} 
	onReject={handleConsentReject} 
/>

<div class="teacher-dashboard">
	{#if isLoading && !selectedSession}
		<div class="loading-screen">
			<div class="loading-spinner"></div>
			<p>평가할 세션을 불러오는 중...</p>
		</div>
	{:else if error && !selectedSession}
		<div class="error-screen">
			<p>{error}</p>
			<Button onclick={() => goto('/dashboard')}>대시보드로 돌아가기</Button>
		</div>
	{:else if selectedSession}
		<!-- 세션 평가 뷰 -->
		<div class="dashboard-header">
			<div class="header-info">
				<h1>세션 채점 (v4.3 루브릭)</h1>
				{#if evaluationStats}
					<div class="stats-summary">
						<span class="stat-item">
							<strong>{evaluationStats.evaluated_sessions}</strong> / {targetGoal}개 완료
						</span>
						<span class="stat-separator">•</span>
						<span class="stat-item">
							진행률: <strong>{Math.min(Math.round(evaluationStats.evaluated_sessions / targetGoal * 100), 100)}%</strong>
						</span>
					</div>
				{:else}
					<div class="session-count">평가 완료: {evaluatedCount}개</div>
				{/if}
			</div>
			<div class="header-actions">
				<ThemeToggle />
				<Button variant="ghost" onclick={() => showGuideModal = true}>
					❓ 안내
				</Button>
				<Button variant="secondary" onclick={() => goto('/teacher/rubric-evaluation')}>
					📊 루브릭 평가
				</Button>
				<Button variant="secondary" onclick={() => goto('/dashboard')}>
					대시보드로
				</Button>
			</div>
		</div>
		
		<!-- 탭 네비게이션 -->
		<div class="tabs-container">
			<button 
				class="tab-button {currentTab === 'evaluation' ? 'active' : ''}"
				onclick={() => currentTab = 'evaluation'}
			>
				✍️ 새 평가
			</button>
			<button 
				class="tab-button {currentTab === 'history' ? 'active' : ''}"
				onclick={() => {
					currentTab = 'history';
					loadEvaluatedSessions();
				}}
			>
				📝 평가 목록
			</button>
		</div>
		
		<!-- 진행 상태 바 -->
		{#if evaluationStats}
			<Card className="progress-card">
				<div class="progress-header">
					<div class="progress-title">
						<span class="icon">🎯</span>
						<strong>연구 목표 진행 현황</strong>
					</div>
					<div class="progress-text">
						{evaluationStats.evaluated_sessions} / {targetGoal}개 세션 평가 완료
					</div>
				</div>
				<div class="progress-bar-container">
					<div 
						class="progress-bar-fill" 
						style="width: {Math.min(evaluationStats.evaluated_sessions / targetGoal * 100, 100)}%"
					></div>
				</div>
				<div class="progress-stats">
					<div class="stat-group">
						<span class="stat-label">평가 완료</span>
						<span class="stat-value completed">{evaluationStats.evaluated_sessions}</span>
					</div>
					<div class="stat-group">
						<span class="stat-label">미평가</span>
						<span class="stat-value pending">{evaluationStats.unevaluated_sessions}</span>
					</div>
					<div class="stat-group">
						<span class="stat-label">남은 세션</span>
						<span class="stat-value remaining">{Math.max(targetGoal - evaluationStats.evaluated_sessions, 0)}</span>
					</div>
				</div>
			</Card>
		{/if}
		
		{#if currentTab === 'evaluation'}
		<!-- 새 평가 탭 -->
		<div class="detail-container">
			<!-- 왼쪽: 대화 내용 -->
			<div class="conversation-panel">
				<Card className="conversation-card">
					<div class="session-info">
						<h2>{selectedSession.title || '제목 없음'}</h2>
						<p>학생: {selectedSession.student_username}</p>
						<p>생성일: {new Date(selectedSession.created_at).toLocaleString('ko-KR')}</p>
					</div>
					
					<div class="messages-container">
						<MessageList messages={sessionMessages} />
					</div>
				</Card>
			</div>
			
			<!-- 오른쪽: 평가 패널 -->
			<div class="evaluation-panel">
				<Card className="evaluation-card">
					<!-- 헤더: 항상 표시 -->
					<div class="evaluation-header">
						<h2>v4.3 루브릭 채점 (40점 만점)</h2>
						
						<!-- 단계 표시기 -->
						<div class="step-indicator">
							<div class="step" class:active={currentSection === 'A'} class:completed={isSectionComplete('A')}>
								<div class="step-number">1</div>
								<div class="step-label">질문 영역</div>
							</div>
							<div class="step-divider"></div>
							<div class="step" class:active={currentSection === 'B'} class:completed={isSectionComplete('B')}>
								<div class="step-number">2</div>
								<div class="step-label">답변 영역</div>
							</div>
							<div class="step-divider"></div>
							<div class="step" class:active={currentSection === 'C'} class:completed={isSectionComplete('C')}>
								<div class="step-number">3</div>
								<div class="step-label">맥락 영역</div>
							</div>
						</div>
						
						<!-- 진행률 표시 -->
						<div class="progress-container">
							<div class="progress-bar">
								<div class="progress-fill" style="width: {getOverallProgress()}%"></div>
							</div>
							<div class="progress-text">
								진행률: {getOverallProgress()}% ({['A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'C1', 'C2'].filter(k => isItemComplete(k as keyof EvaluationForm)).length}/8 항목 완료)
							</div>
						</div>
					</div>
					
					<!-- 섹션별 콘텐츠 -->
					<div class="section-content">
					
					{#if currentSection === 'A'}
					<!-- A 영역: 질문 평가 (15점) -->
					<section class="evaluation-section section-a">
						<h3>
							{#if isSectionComplete('A')}
								<span class="complete-check">✓</span>
							{/if}
							A. 질문 영역 (15점) - 총 {calculateQuestionTotal()}점
						</h3>
						
						{#each ['A1', 'A2', 'A3'] as itemKey}
							<div class="checklist-item">
								<div class="item-header">
									<h4>{itemTitles[itemKey]} ({calculateItemScore(evaluationForm[itemKey] as ChecklistItem)}점)</h4>
								</div>
								<div class="checklist-elements">
									{#each ['element1', 'element2', 'element3', 'element4'] as elemKey, idx}
										<div class="element-wrapper">
											<label 
												class="checkbox-label-simple"
												onmouseenter={() => showTooltip(`${itemKey}-${idx}`)}
												onmouseleave={hideTooltip}
											>
												<input 
													type="checkbox" 
											checked={(evaluationForm[itemKey] as ChecklistItem)[elemKey as keyof ChecklistItem].value === 1}
											onchange={() => toggleCheckbox(itemKey, elemKey as keyof ChecklistItem)}
												/>
												<span>{elementLabels[itemKey][idx]}</span>
											</label>
											{#if activeTooltip === `${itemKey}-${idx}`}
												<div class="tooltip">
													<div class="tooltip-title">📋 평가 기준</div>
													<div class="tooltip-description">{elementTooltips[itemKey][idx].description}</div>
													<div class="tooltip-example">{elementTooltips[itemKey][idx].example}</div>
												</div>
											{/if}
										</div>
									{/each}
								</div>
							</div>
					{/each}
					
					<div class="section-nav">
							<Button variant="primary" onclick={() => goToSection('B')}>
								다음: B 영역 (답변 평가) →
							</Button>
						</div>
					</section>
					
					{:else if currentSection === 'B'}
					<!-- B 영역: 답변 평가 (15점) -->
					<section class="evaluation-section section-b">
						<h3>
							{#if isSectionComplete('B')}
								<span class="complete-check">✓</span>
							{/if}
							B. 답변 영역 (15점) - 총 {calculateAnswerTotal()}점
						</h3>
						
						{#each ['B1', 'B2', 'B3'] as itemKey}
							<div class="checklist-item">
								<div class="item-header">
									<h4>{itemTitles[itemKey]} ({calculateItemScore(evaluationForm[itemKey] as ChecklistItem)}점)</h4>
								</div>
								<div class="checklist-elements">
									{#each ['element1', 'element2', 'element3', 'element4'] as elemKey, idx}
										<div class="element-wrapper">
											<label 
												class="checkbox-label-simple"
												onmouseenter={() => showTooltip(`${itemKey}-${idx}`)}
												onmouseleave={hideTooltip}
											>
												<input 
													type="checkbox" 
											checked={(evaluationForm[itemKey] as ChecklistItem)[elemKey as keyof ChecklistItem].value === 1}
											onchange={() => toggleCheckbox(itemKey, elemKey as keyof ChecklistItem)}
												/>
												<span>{elementLabels[itemKey][idx]}</span>
											</label>
											{#if activeTooltip === `${itemKey}-${idx}`}
												<div class="tooltip">
													<div class="tooltip-title">📋 평가 기준</div>
													<div class="tooltip-description">{elementTooltips[itemKey][idx].description}</div>
													<div class="tooltip-example">{elementTooltips[itemKey][idx].example}</div>
												</div>
											{/if}
										</div>
									{/each}
								</div>
							</div>
					{/each}
					
					<div class="section-nav">
							<Button variant="secondary" onclick={() => goToSection('A')}>
								← 이전: A 영역
							</Button>
							<Button variant="primary" onclick={() => goToSection('C')}>
								다음: C 영역 (맥락 평가) →
							</Button>
						</div>
					</section>
					
					{:else if currentSection === 'C'}
					<!-- C 영역: 맥락 평가 (10점) -->
					<section class="evaluation-section section-c">
						<h3>
							{#if isSectionComplete('C')}
								<span class="complete-check">✓</span>
							{/if}
							C. 맥락 영역 (10점) - 총 {calculateContextTotal()}점
						</h3>
						
						{#each ['C1', 'C2'] as itemKey}
							<div class="checklist-item">
								<div class="item-header">
									<h4>{itemTitles[itemKey]} ({calculateItemScore(evaluationForm[itemKey] as ChecklistItem)}점)</h4>
								</div>
								<div class="checklist-elements">
									{#each ['element1', 'element2', 'element3', 'element4'] as elemKey, idx}
										<div class="element-wrapper">
											<label 
												class="checkbox-label-simple"
												onmouseenter={() => showTooltip(`${itemKey}-${idx}`)}
												onmouseleave={hideTooltip}
											>
												<input 
													type="checkbox" 
											checked={(evaluationForm[itemKey] as ChecklistItem)[elemKey as keyof ChecklistItem].value === 1}
											onchange={() => toggleCheckbox(itemKey, elemKey as keyof ChecklistItem)}
												/>
												<span>{elementLabels[itemKey][idx]}</span>
											</label>
											{#if activeTooltip === `${itemKey}-${idx}`}
												<div class="tooltip">
													<div class="tooltip-title">📋 평가 기준</div>
													<div class="tooltip-description">{elementTooltips[itemKey][idx].description}</div>
													<div class="tooltip-example">{elementTooltips[itemKey][idx].example}</div>
												</div>
											{/if}
										</div>
									{/each}
								</div>
							</div>
					{/each}
					
					<!-- 점수 요약 -->
						<div class="score-summary">
							<div class="summary-item">
								<span>A영역 (질문)</span>
								<strong>{calculateQuestionTotal()}점 / 15점</strong>
							</div>
							<div class="summary-item">
								<span>B영역 (답변)</span>
								<strong>{calculateAnswerTotal()}점 / 15점</strong>
							</div>
							<div class="summary-item">
								<span>C영역 (맥락)</span>
								<strong>{calculateContextTotal()}점 / 10점</strong>
							</div>
							<div class="summary-total">
								<span>전체 총점</span>
								<strong>{calculateOverallTotal()}점 / 40점</strong>
							</div>
					</div>
					
					<div class="section-nav">
							<Button variant="secondary" onclick={() => goToSection('B')}>
								← 이전: B 영역
							</Button>
							<Button variant="primary" onclick={saveEvaluation} disabled={isLoading}>
								💾 평가 저장하기
							</Button>
						</div>
					</section>
					
					{/if}
					
					</div><!-- section-content 끝 -->
				</Card>
			</div>
		</div>
		
		<div class="action-buttons">
			<Button variant="ghost" onclick={loadRandomSession} disabled={isLoading}>
				⏭️ 이 세션 건너뛰기
			</Button>
		</div>
		
		{:else if currentTab === 'history'}
		<!-- 평가 목록 탭 -->
		<Card>
			<div class="history-header">
				<h2>📝 내가 평가한 세션 목록</h2>
				<p class="history-desc">이전에 평가한 세션을 다시 선택하여 수정할 수 있습니다.</p>
			</div>
			
			{#if isLoadingHistory}
				<div class="loading-indicator">
					<div class="loading-spinner"></div>
					<p>평가 목록을 불러오는 중...</p>
				</div>
			{:else if evaluatedSessions.length === 0}
				<div class="empty-history">
					<p>📭 아직 평가한 세션이 없습니다.</p>
					<Button variant="primary" onclick={() => currentTab = 'evaluation'}>
						새 평가 시작하기
					</Button>
				</div>
			{:else}
				<div class="history-list">
					{#each evaluatedSessions as session}
						<div class="history-item">
							<div class="history-info">
								<h3>{session.title || '제목 없음'}</h3>
								<div class="history-meta">
									<span>학생: {session.student_username}</span>
									<span>•</span>
									<span>메시지: {session.message_count}개</span>
									<span>•</span>
									<span>평가일: {session.last_evaluation_at ? new Date(session.last_evaluation_at).toLocaleString('ko-KR') : '알 수 없음'}</span>
								</div>
							</div>
							<Button 
								variant="secondary" 
								onclick={() => loadSessionForReview(session.id)}
							>
								✏️ 재평가
							</Button>
						</div>
					{/each}
				</div>
			{/if}
		</Card>
		{/if}
	{/if}
</div>

<style>
	.teacher-dashboard {
		padding: 2rem;
		max-width: 1800px;
		margin: 0 auto;
	}
	
	.dashboard-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 2rem;
	}
	
	.header-info {
		display: flex;
		align-items: center;
		gap: 2rem;
	}
	
	.header-actions {
		display: flex;
		gap: 1rem;
		align-items: center;
	}
	
	.dashboard-header h1 {
		font-size: 2rem;
		font-weight: 600;
		margin: 0;
	}
	
	.session-count {
		font-size: 1rem;
		padding: 0.5rem 1rem;
		background: var(--maice-success-bg, #ecfdf5);
		color: var(--maice-success-text, #059669);
		border-radius: 0.5rem;
		font-weight: 600;
	}
	
	.stats-summary {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-size: 0.9375rem;
		color: var(--maice-text-muted);
		background: var(--maice-bg-secondary, #f9fafb);
		padding: 0.5rem 1rem;
		border-radius: 20px;
	}
	
	.stat-item strong {
		color: var(--maice-primary);
		font-weight: 600;
	}
	
	.stat-separator {
		color: var(--maice-border);
	}
	
	/* 진행 상태 카드 */
	
	.progress-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
	}
	
	.progress-title {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 1.125rem;
		color: var(--maice-text);
	}
	
	.progress-title .icon {
		font-size: 1.5rem;
	}
	
	.progress-text {
		font-size: 0.9375rem;
		color: var(--maice-text-muted);
	}
	
	.progress-bar-container {
		width: 100%;
		height: 24px;
		background: var(--maice-bg-secondary, #f3f4f6);
		border-radius: 12px;
		overflow: hidden;
		position: relative;
		margin-bottom: 1rem;
	}
	
	.progress-bar-fill {
		height: 100%;
		background: linear-gradient(90deg, 
			var(--maice-primary, #3b82f6), 
			var(--maice-secondary, #8b5cf6));
		transition: width 0.5s ease;
		box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
	}
	
	.progress-stats {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 1rem;
	}
	
	.stat-group {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.25rem;
	}
	
	.stat-label {
		font-size: 0.8125rem;
		color: var(--maice-text-muted);
	}
	
	.stat-value {
		font-size: 1.5rem;
		font-weight: 700;
	}
	
	.stat-value.completed {
		color: var(--maice-success-text, #10b981);
	}
	
	.stat-value.pending {
		color: var(--maice-warning-text, #f59e0b);
	}
	
	.stat-value.remaining {
		color: var(--maice-primary, #3b82f6);
	}
	
	/* 로딩 화면 */
	.loading-screen,
	.error-screen {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 80vh;
		text-align: center;
	}
	
	.loading-spinner {
		width: 4rem;
		height: 4rem;
		border: 4px solid var(--maice-border-primary, #e5e7eb);
		border-top-color: var(--maice-primary, #3b82f6);
		border-radius: 50%;
		animation: spin 1s linear infinite;
		margin-bottom: 1.5rem;
	}
	
	@keyframes spin {
		to { transform: rotate(360deg); }
	}
	
	.loading-screen p,
	.error-screen p {
		font-size: 1.125rem;
		color: var(--maice-text-secondary, #6b7280);
		margin-bottom: 1.5rem;
	}
	
	.error-screen p {
		color: var(--maice-error, #dc2626);
	}
	
	.detail-container {
		display: grid;
		grid-template-columns: 2fr 1fr;
		gap: 2rem;
		min-height: 90vh;
		align-items: start;
	}
	
	.conversation-panel,
	.evaluation-panel {
		display: flex;
		flex-direction: column;
		height: 100%;
	}
	
	
	.session-info {
		padding: 1rem;
		border-bottom: 1px solid var(--maice-border-primary, #e5e7eb);
		margin-bottom: 1rem;
	}
	
	.session-info h2 {
		margin: 0 0 0.5rem 0;
		font-size: 1.5rem;
	}
	
	.session-info p {
		margin: 0.25rem 0;
		font-size: 0.875rem;
		color: var(--maice-text-secondary, #6b7280);
	}
	
	.messages-container {
		flex: 1;
		overflow-y: auto;
		padding: 1rem;
		max-height: calc(100vh - 100px);
		min-height: 1000px;
	}
	
	.evaluation-header {
		position: sticky;
		top: 0;
		background: var(--maice-card-bg, white);
		z-index: 10;
		padding-bottom: 1.5rem;
		margin-bottom: 1.5rem;
		border-bottom: 2px solid var(--maice-border-primary, #e5e7eb);
	}
	
	.evaluation-header h2 {
		margin: 0 0 1.5rem 0;
		font-size: 1.5rem;
		font-weight: 700;
	}
	
	/* 단계 표시기 */
	.step-indicator {
		display: flex;
		align-items: center;
		justify-content: center;
		margin-bottom: 1.5rem;
		gap: 0.5rem;
	}
	
	.step {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.375rem;
		transition: all 0.3s ease;
	}
	
	.step-number {
		width: 2.5rem;
		height: 2.5rem;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-weight: 700;
		font-size: 1rem;
		background: var(--maice-bg-secondary, #f9fafb);
		color: var(--maice-text-muted, #9ca3af);
		border: 2px solid var(--maice-border-primary, #e5e7eb);
		transition: all 0.3s ease;
	}
	
	.step.active .step-number {
		background: var(--maice-primary, #3b82f6);
		color: var(--maice-text-on-primary, white);
		border-color: var(--maice-primary, #3b82f6);
		transform: scale(1.1);
	}
	
	.step.completed .step-number {
		background: var(--maice-success-border, #10b981);
		color: white;
		border-color: var(--maice-success-border, #10b981);
	}
	
	.step-label {
		font-size: 0.75rem;
		font-weight: 500;
		color: var(--maice-text-muted, #9ca3af);
		transition: all 0.3s ease;
	}
	
	.step.active .step-label {
		color: var(--maice-primary, #3b82f6);
		font-weight: 700;
	}
	
	.step.completed .step-label {
		color: var(--maice-success-text, #059669);
	}
	
	.step-divider {
		width: 2rem;
		height: 2px;
		background: var(--maice-border-primary, #e5e7eb);
		transition: all 0.3s ease;
	}
	
	.step.completed + .step-divider {
		background: var(--maice-success-border, #10b981);
	}
	
	/* 섹션 콘텐츠 */
	.section-content {
		min-height: 800px;
		animation: fadeIn 0.3s ease;
		overflow-y: auto;
		flex: 1;
	}
	
	@keyframes fadeIn {
		from {
			opacity: 0;
			transform: translateY(10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}
	
	.progress-container {
		margin-bottom: 2rem;
		padding: 1rem;
		background: var(--maice-bg-secondary, #f9fafb);
		border-radius: 0.5rem;
		border: 1px solid var(--maice-border-primary, #e5e7eb);
	}
	
	.progress-bar {
		width: 100%;
		height: 1.5rem;
		background: var(--maice-bg-tertiary, #e5e7eb);
		border-radius: 0.75rem;
		overflow: hidden;
		margin-bottom: 0.5rem;
	}
	
	.progress-fill {
		height: 100%;
		background: var(--maice-primary, #3b82f6);
		transition: width 0.5s ease;
		border-radius: 0.75rem;
		display: flex;
		align-items: center;
		justify-content: flex-end;
		padding-right: 0.5rem;
		color: var(--maice-text-on-primary, white);
		font-size: 0.875rem;
		font-weight: 600;
	}
	
	.progress-text {
		text-align: center;
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--maice-text-secondary, #6b7280);
	}
	
	.evaluation-section {
		margin-bottom: 2rem;
		padding-bottom: 2rem;
		border-bottom: 1px solid var(--maice-border-primary, #e5e7eb);
	}
	
	.evaluation-section:last-of-type {
		border-bottom: none;
	}
	
	.evaluation-section h3 {
		margin-top: 0;
		margin-bottom: 1rem;
		font-size: 1.25rem;
		color: var(--maice-primary, #3b82f6);
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}
	
	.complete-check {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 2rem;
		height: 2rem;
		background: var(--maice-success-border, #10b981);
		color: var(--maice-text-on-primary, white);
		border-radius: 50%;
		font-size: 1.25rem;
		font-weight: bold;
		animation: checkBounce 0.5s ease;
	}
	
	@keyframes checkBounce {
		0%, 100% { transform: scale(1); }
		50% { transform: scale(1.2); }
	}
	
	.checklist-item {
		margin-bottom: 1.5rem;
		padding: 1rem;
		background: var(--maice-bg-secondary, #f9fafb);
		border-radius: 0.5rem;
		border: 1px solid var(--maice-border-primary, #e5e7eb);
		transition: all 0.3s ease;
	}
	
	/* 항목 완료 시 스타일 */
	.checklist-item:has(.checkbox-label-simple input:nth-of-type(1):checked):has(.checkbox-label-simple input:nth-of-type(2):checked):has(.checkbox-label-simple input:nth-of-type(3):checked):has(.checkbox-label-simple input:nth-of-type(4):checked) {
		background: var(--maice-success-bg, #ecfdf5);
		border-color: var(--maice-success-border, #10b981);
		box-shadow: 0 0 0 3px var(--maice-success-shadow, rgba(16, 185, 129, 0.1));
	}
	
	.checklist-item:has(.checkbox-label-simple input:nth-of-type(1):checked):has(.checkbox-label-simple input:nth-of-type(2):checked):has(.checkbox-label-simple input:nth-of-type(3):checked):has(.checkbox-label-simple input:nth-of-type(4):checked) .item-header h4 {
		color: var(--maice-success-text, #059669);
		font-weight: 700;
	}
	
	.item-header h4 {
		margin: 0 0 1rem 0;
		font-size: 1rem;
		color: var(--maice-text-primary, #111827);
	}
	
	.checklist-elements {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}
	
	.element-wrapper {
		position: relative;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
	
	.checkbox-label-simple {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem;
		cursor: pointer;
		font-size: 0.9375rem;
		border-radius: 0.375rem;
		transition: all 0.2s ease;
		background: var(--maice-card-bg, white);
		border: 1px solid transparent;
		flex: 1;
	}
	
	.checkbox-label-simple:hover {
		background: var(--maice-bg-hover, #f3f4f6);
		border-color: var(--maice-primary, #3b82f6);
		box-shadow: 0 0 0 2px var(--maice-primary-light, rgba(59, 130, 246, 0.1));
	}
	
	.checkbox-label-simple input[type="checkbox"] {
		width: 1.5rem;
		height: 1.5rem;
		cursor: pointer;
		accent-color: var(--maice-primary, #3b82f6);
		transition: transform 0.15s ease;
	}
	
	.checkbox-label-simple input[type="checkbox"]:checked {
		transform: scale(1.1);
	}
	
	.checkbox-label-simple span {
		flex: 1;
		line-height: 1.5;
	}
	
	/* Tooltip */
	.tooltip {
		position: absolute;
		left: 0;
		top: 100%;
		margin-top: 0.5rem;
		z-index: 1000;
		width: 340px;
		padding: 1rem;
		background: var(--maice-card-bg, white);
		border: 2px solid var(--maice-primary, #3b82f6);
		border-radius: 0.5rem;
		box-shadow: var(--maice-shadow-xl);
		animation: tooltipFadeIn 0.2s ease;
		pointer-events: none;
	}
	
	.tooltip-title {
		font-weight: 700;
		font-size: 0.875rem;
		color: var(--maice-primary, #3b82f6);
		margin-bottom: 0.5rem;
		padding-bottom: 0.5rem;
		border-bottom: 1px solid var(--maice-border-primary, #e5e7eb);
	}
	
	.tooltip-description {
		font-size: 0.875rem;
		color: var(--maice-text-primary, #111827);
		margin-bottom: 0.75rem;
		line-height: 1.5;
	}
	
	.tooltip-example {
		font-size: 0.8125rem;
		color: var(--maice-text-secondary, #6b7280);
		background: var(--maice-bg-secondary, #f9fafb);
		padding: 0.625rem;
		border-radius: 0.375rem;
		white-space: pre-line;
		line-height: 1.6;
		font-family: 'Courier New', monospace;
	}
	
	@keyframes tooltipFadeIn {
		from {
			opacity: 0;
			transform: translateY(-8px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}
	
	/* 섹션 완료 애니메이션 */
	.evaluation-section {
		scroll-margin-top: 2rem;
		transition: all 0.3s ease;
	}
	
	.section-a:has(.checklist-item:nth-child(2) .checkbox-label-simple input:checked):has(.checklist-item:nth-child(3) .checkbox-label-simple input:checked):has(.checklist-item:nth-child(4) .checkbox-label-simple input:checked) {
		border-left: 4px solid var(--maice-success-border, #10b981);
	}
	
	.section-b:has(.checklist-item:nth-child(2) .checkbox-label-simple input:checked):has(.checklist-item:nth-child(3) .checkbox-label-simple input:checked):has(.checklist-item:nth-child(4) .checkbox-label-simple input:checked) {
		border-left: 4px solid var(--maice-success-border, #10b981);
	}
	
	.section-c:has(.checklist-item:nth-child(2) .checkbox-label-simple input:checked):has(.checklist-item:nth-child(3) .checkbox-label-simple input:checked) {
		border-left: 4px solid var(--maice-success-border, #10b981);
	}
	
	
	
	
	/* 섹션 네비게이션 */
	.section-nav {
		display: flex;
		justify-content: space-between;
		gap: 1rem;
		margin-top: 1.5rem;
		padding-top: 1.5rem;
		border-top: 2px dashed var(--maice-border-primary, #e5e7eb);
	}
	
	
	
	
	/* 점수 요약 */
	.score-summary {
		margin-top: 2rem;
		padding: 1.5rem;
		background: var(--maice-bg-secondary, #f9fafb);
		border-radius: 0.75rem;
		border: 2px solid var(--maice-border-primary, #e5e7eb);
	}
	
	.summary-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem;
		margin-bottom: 0.5rem;
		background: var(--maice-card-bg, white);
		border-radius: 0.5rem;
		font-size: 0.9375rem;
	}
	
	.summary-item span {
		color: var(--maice-text-secondary, #6b7280);
	}
	
	.summary-item strong {
		color: var(--maice-text-primary, #111827);
		font-size: 1.125rem;
	}
	
	.summary-total {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem;
		margin-top: 0.75rem;
		background: var(--maice-primary, #3b82f6);
		color: var(--maice-text-on-primary, white);
		border-radius: 0.5rem;
		font-size: 1.125rem;
		font-weight: 700;
	}
	
	.summary-total strong {
		font-size: 1.5rem;
	}
	
	/* 교사 의견 섹션 */
	
	/* 탭 네비게이션 */
	.tabs-container {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 1.5rem;
		border-bottom: 2px solid var(--maice-border-primary, #e5e7eb);
	}
	
	.tab-button {
		padding: 0.75rem 1.5rem;
		background: transparent;
		border: none;
		border-bottom: 3px solid transparent;
		color: var(--maice-text-secondary, #6b7280);
		font-size: 1rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.2s ease;
		margin-bottom: -2px;
	}
	
	.tab-button:hover {
		color: var(--maice-text-primary, #111827);
		background: var(--maice-bg-hover, #f9fafb);
	}
	
	.tab-button.active {
		color: var(--maice-primary, #3b82f6);
		border-bottom-color: var(--maice-primary, #3b82f6);
	}
	
	/* 액션 버튼 */
	.action-buttons {
		display: flex;
		justify-content: center;
		gap: 1rem;
		margin-top: 2rem;
		padding: 1.5rem;
		background: var(--maice-bg-secondary, #f9fafb);
		border-radius: 0.5rem;
	}
	
	/* 평가 목록 */
	.history-header {
		margin-bottom: 1.5rem;
	}
	
	.history-header h2 {
		font-size: 1.5rem;
		color: var(--maice-text-primary, #111827);
		margin-bottom: 0.5rem;
	}
	
	.history-desc {
		color: var(--maice-text-secondary, #6b7280);
		font-size: 0.9375rem;
	}
	
	.history-list {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}
	
	.history-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem;
		background: var(--maice-bg-secondary, #f9fafb);
		border: 1px solid var(--maice-border-primary, #e5e7eb);
		border-radius: 0.5rem;
		transition: all 0.2s ease;
	}
	
	.history-item:hover {
		border-color: var(--maice-primary, #3b82f6);
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	}
	
	.history-info {
		flex: 1;
	}
	
	.history-info h3 {
		font-size: 1.125rem;
		color: var(--maice-text-primary, #111827);
		margin-bottom: 0.5rem;
	}
	
	.history-meta {
		display: flex;
		gap: 0.5rem;
		align-items: center;
		font-size: 0.875rem;
		color: var(--maice-text-secondary, #6b7280);
	}
	
	.empty-history {
		text-align: center;
		padding: 3rem;
	}
	
	.empty-history p {
		font-size: 1.125rem;
		color: var(--maice-text-secondary, #6b7280);
		margin-bottom: 1.5rem;
	}
	
	.loading-indicator {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 3rem;
	}
	
	.loading-indicator p {
		margin-top: 1rem;
		color: var(--maice-text-secondary, #6b7280);
	}
	
	/* 반응형 */
	@media (max-width: 1400px) {
		.detail-container {
			grid-template-columns: 1fr;
		}
		
		.messages-container {
			max-height: 700px;
			min-height: 700px;
		}
		
		.section-content {
			min-height: 600px;
		}
	}
	
	@media (max-width: 768px) {
		.teacher-dashboard {
			padding: 1rem;
		}
		
		.header-info {
			flex-direction: column;
			align-items: flex-start;
			gap: 0.5rem;
		}
		
		.checkbox-label-simple {
			font-size: 0.875rem;
			padding: 0.625rem;
		}
		
		.tooltip {
			width: 280px;
			left: 0;
			right: auto;
		}
		
		.element-wrapper {
			flex-wrap: wrap;
		}
		
		.section-nav {
			flex-direction: column;
		}
		
		
		.step-indicator {
			gap: 0.25rem;
		}
		
		.step-number {
			width: 2rem;
			height: 2rem;
			font-size: 0.875rem;
		}
		
		.step-label {
			font-size: 0.625rem;
		}
		
		.step-divider {
			width: 1rem;
		}
	}
</style>
