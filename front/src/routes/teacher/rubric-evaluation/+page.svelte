<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth';
	import Button from '$lib/components/common/Button.svelte';
	import Card from '$lib/components/common/Card.svelte';
	import MarkdownRenderer from '$lib/components/maice/MarkdownRenderer.svelte';
	import { getSessionsByItemScore, getSessionDetail, getRubricFeedbacks, updateRubricFeedbacks } from '$lib/api';
	
	let token = '';
	let isLoading = false;
	let error: string | null = null;
	
	// 필터 상태
	let selectedItem = 'A1';
	let scoreFilter: 'excellent' | 'good' | 'poor' = 'excellent';
	
	// 세션 목록
	let sessions: any[] = [];
	let totalCount = 0;
	
	// 교사 의견
	let elementFeedbacks: Record<string, string> = {};
	let itemOverallFeedback = '';
	
	// 항목 정의
	const itemTitles: Record<string, string> = {
		'A1': 'A1. 수학적 전문성',
		'A2': 'A2. 질문 구조화',
		'A3': 'A3. 학습 맥락 적용',
		'B1': 'B1. 학습자 맞춤도',
		'B2': 'B2. 설명의 체계성',
		'B3': 'B3. 학습 내용 확장성',
		'C1': 'C1. 대화 일관성',
		'C2': 'C2. 학습 과정 지원성'
	};
	
	const itemDescriptions: Record<string, string> = {
		'A1': '수학적 개념/원리의 정확성, 교과과정 내 위계성 파악, 수학적 용어 사용의 적절성, 문제해결 방향의 구체성',
		'A2': '질문 구조의 논리적 연계성, 선행 지식 제시 여부, 학습목표 명시성, 정보의 단계성',
		'A3': '단원/개념 식별의 명확성, 교육과정 맥락 반영도, 학습 상황과의 적합성, 이전 지식과의 연계성',
		'B1': '어려운 개념 쉬운 설명 노력, 학습 수준 반영, 개인 맞춤 응답 여부, 학습자 배경 고려',
		'B2': '개념 정의 → 설명 → 예시 구조, 논리적 흐름, 단계별 이해 확인, 교수 방법론 활용',
		'B3': '확장 활동 제안, 다른 수학 개념 연계, 사고 확장 질문, 응용 사례 제시',
		'C1': '문맥 일관성, 이전 대화 참조, 학습자 이해 상태 추적, 주제 유지',
		'C2': '학습 동기 지원, 긍정적 피드백, 자기주도학습 장려, 학습 과정 안내'
	};
	
	const checklistElements: Record<string, Array<{title: string, description: string, example: string}>> = {
		'A1': [
			{ title: '수학적 개념/원리의 정확성', description: '질문에서 언급된 수학적 개념이나 원리가 정확하게 표현되었는가?', example: '예: "이차함수의 꼭짓점"을 정확히 표현, "미분계수"와 "도함수"의 구분' },
			{ title: '교과과정 내 위계성 파악', description: '질문이 학습자의 현재 수준과 교육과정 단계에 적합한가?', example: '예: 중학교 과정에서 고등학교 개념 요구, 선수 학습 없이 고급 개념 질문' },
			{ title: '수학적 용어 사용의 적절성', description: '수학 용어를 정확하고 적절하게 사용하였는가?', example: '예: "경사"가 아닌 "기울기", "늘어나는"이 아닌 "증가하는"' },
			{ title: '문제해결 방향의 구체성', description: '무엇을 해결하고 싶은지, 어떤 도움이 필요한지 명확한가?', example: '예: "수학 어려워요"보다 "이차방정식 근의 공식 유도 과정을 모르겠어요"' }
		],
		'A2': [
			{ title: '질문 구조의 논리적 연계성', description: '질문의 각 부분이 논리적으로 연결되어 있는가?', example: '예: "삼각함수를 배우는데, 이차함수의 근과 관련이 있나요?" (비논리적)' },
			{ title: '선행 지식 제시 여부', description: '질문에 필요한 선행 지식을 언급하였는가?', example: '예: "일차함수는 알아요. 이차함수의 그래프는 어떻게 그리나요?"' },
			{ title: '학습목표 명시성', description: '무엇을 학습하고자 하는지 명확한가?', example: '예: "이차함수의 그래프를 그릴 수 있게 되고 싶어요"' },
			{ title: '정보의 단계성', description: '정보가 단계적으로 제시되고 있는가?', example: '예: 정의 → 성질 → 응용 순서로 질문' }
		],
		'A3': [
			{ title: '단원/개념 식별의 명확성', description: '어떤 단원이나 개념에 대한 질문인지 명확한가?', example: '예: "수학Ⅰ 삼각함수 단원의 사인 법칙에 대해 질문해요"' },
			{ title: '교육과정 맥락 반영도', description: '현재 교육과정에서의 위치를 인식하고 있는가?', example: '예: "중3 과정에서 배운 인수분해를 이용해서..."' },
			{ title: '학습 상황과의 적합성', description: '현재 학습 상황(시험, 숙제, 예습 등)에 적합한 질문인가?', example: '예: "내일 시험인데 이차함수의 최댓값 구하는 문제가 나온대요"' },
			{ title: '이전 지식과의 연계성', description: '이전에 배운 내용과 연결하여 질문하는가?', example: '예: "일차함수처럼 이차함수도 y절편이 있나요?"' }
		],
		'B1': [
			{ title: '어려운 개념 쉬운 설명 노력', description: 'AI가 복잡한 개념을 학습자 수준에 맞게 쉽게 설명하려 노력하는가?', example: '예: 추상적 개념을 구체적 예시로, 전문 용어를 일상 언어로 풀어서 설명' },
			{ title: '학습 수준 반영', description: '학습자의 현재 이해 수준을 고려한 설명인가?', example: '예: 중학생에게 극한 개념 사용 지양, 기초부터 차근차근 설명' },
			{ title: '개인 맞춤 응답 여부', description: '학습자의 질문 의도와 상황에 맞춤화된 답변인가?', example: '예: 시험 대비 → 핵심 정리, 이해 중심 → 상세 설명' },
			{ title: '학습자 배경 고려', description: '학습자의 이전 대화나 배경 지식을 고려하는가?', example: '예: "아까 배운 일차함수처럼..." 이전 대화 참조' }
		],
		'B2': [
			{ title: '개념 정의 → 설명 → 예시 구조', description: '체계적인 순서로 설명이 구성되어 있는가?', example: '예: 1) 이차함수란? 2) 특징은? 3) 구체적 예시' },
			{ title: '논리적 흐름', description: '설명의 각 단계가 논리적으로 연결되어 있는가?', example: '예: 정의 → 성질 도출 → 응용으로 자연스럽게 전개' },
			{ title: '단계별 이해 확인', description: '각 단계마다 이해를 확인하거나 점검하는가?', example: '예: "여기까지 이해되셨나요?", "더 궁금한 점이 있나요?"' },
			{ title: '교수 방법론 활용', description: '효과적인 교수 방법(비유, 시각화 등)을 활용하는가?', example: '예: 그래프로 시각화, 실생활 비유, 단계별 문제 제시' }
		],
		'B3': [
			{ title: '확장 활동 제안', description: '학습을 확장할 수 있는 활동을 제안하는가?', example: '예: "직접 그래프를 그려보세요", "다른 예제를 풀어보세요"' },
			{ title: '다른 수학 개념 연계', description: '관련된 다른 수학 개념과의 연결을 제시하는가?', example: '예: "이차함수는 나중에 배울 미분과도 연결됩니다"' },
			{ title: '사고 확장 질문', description: '더 깊이 생각하게 하는 질문을 던지는가?', example: '예: "왜 포물선 모양이 나올까요?", "계수가 바뀌면 어떻게 될까요?"' },
			{ title: '응용 사례 제시', description: '실생활이나 다른 분야의 응용 사례를 제시하는가?', example: '예: "포물선 운동", "다리 설계에서의 활용"' }
		],
		'C1': [
			{ title: '문맥 일관성', description: '대화 전체가 일관된 주제와 맥락을 유지하는가?', example: '예: 처음 이차함수 질문 → 끝까지 이차함수 맥락 유지' },
			{ title: '이전 대화 참조', description: '이전 대화 내용을 적절히 참조하고 활용하는가?', example: '예: "아까 설명한 꼭짓점을 이용하면...", "앞에서 배운 개념으로..."' },
			{ title: '학습자 이해 상태 추적', description: '학습자의 이해 정도를 파악하고 그에 맞춰 대화하는가?', example: '예: 학습자가 혼란스러워하면 다시 설명, 이해했으면 다음 단계로' },
			{ title: '주제 유지', description: '대화가 본래 주제에서 벗어나지 않고 유지되는가?', example: '예: 이차함수 질문에 삼각함수로 이탈하지 않음' }
		],
		'C2': [
			{ title: '학습 동기 지원', description: '학습에 대한 동기와 흥미를 유발하는가?', example: '예: "이 개념을 알면 더 어려운 문제도 풀 수 있어요!"' },
			{ title: '긍정적 피드백', description: '학습자의 시도와 진전에 대해 긍정적으로 반응하는가?', example: '예: "좋은 질문이에요!", "잘 이해하셨네요!"' },
			{ title: '자기주도학습 장려', description: '스스로 생각하고 탐구하도록 격려하는가?', example: '예: "직접 해보면 어떨까요?", "왜 그럴지 생각해보세요"' },
			{ title: '학습 과정 안내', description: '다음 학습 단계나 방향을 안내하는가?', example: '예: "다음엔 이차방정식을 배워보세요", "이 부분을 먼저 복습하세요"' }
		]
	};
	
	const scoreFilterOptions = {
		excellent: { label: '우수 (4-5점)', min: 4, max: 5, color: '#10b981' },
		good: { label: '보통 (3점)', min: 3, max: 3, color: '#f59e0b' },
		poor: { label: '미흡 (1-2점)', min: 1, max: 2, color: '#ef4444' }
	};
	
	onMount(() => {
		const unsubscribe = authStore.subscribe(state => {
			if (!state.isAuthenticated || !state.user) {
				goto('/');
				return;
			}
			
			const userRole = state.user.role?.toLowerCase();
			if (userRole !== 'teacher' && userRole !== 'admin') {
				goto('/dashboard');
				return;
			}
			
		token = state.token || '';
		if (token) {
			loadRubricFeedbacks();
			loadSessions();
		}
		});
		
		return unsubscribe;
	});
	
	let allRubricFeedbacks: Record<string, any> = {};
	
	async function loadRubricFeedbacks() {
		if (!token) return;
		
		try {
			const response = await getRubricFeedbacks(token);
			allRubricFeedbacks = response.rubric_feedbacks || {};
			
			// 현재 항목의 의견 불러오기
			if (allRubricFeedbacks[selectedItem]) {
				const savedFeedback = allRubricFeedbacks[selectedItem];
				elementFeedbacks = savedFeedback.elements || {};
				itemOverallFeedback = savedFeedback.overall || '';
			}
		} catch (err) {
			console.error('루브릭 의견 로드 실패:', err);
		}
	}
	
	async function loadSessions() {
		if (!token) return;
		
		try {
			isLoading = true;
			error = null;
			
			const filterConfig = scoreFilterOptions[scoreFilter];
			const response = await getSessionsByItemScore(
				token,
				selectedItem,
				filterConfig.min,
				filterConfig.max,
				0,
				50
			);
			
			sessions = response.sessions || [];
			totalCount = response.total_count || 0;
			
			// 각 세션의 대화 내용 로드
			for (const session of sessions) {
				try {
					const detail = await getSessionDetail(token, session.id);
					session.messages = (detail.messages || []).filter((msg: any) => 
						!['maice_processing', 'system', 'internal'].includes(msg.message_type)
					);
					session.evaluation = detail.current_evaluation;
				} catch (err) {
					console.error(`세션 ${session.id} 로드 실패:`, err);
					session.messages = [];
				}
			}
			
			// 현재 항목의 의견 불러오기 (DB에서 이미 로드됨)
			if (allRubricFeedbacks[selectedItem]) {
				const savedFeedback = allRubricFeedbacks[selectedItem];
				elementFeedbacks = savedFeedback.elements || {};
				itemOverallFeedback = savedFeedback.overall || '';
			} else {
				elementFeedbacks = {};
				itemOverallFeedback = '';
			}
			
		} catch (err: any) {
			console.error('세션 목록 로드 실패:', err);
			error = err.message || '세션 목록을 불러오는데 실패했습니다.';
		} finally {
			isLoading = false;
		}
	}
	
	async function saveFeedback() {
		if (!token) return;
		
		if (!itemOverallFeedback.trim()) {
			alert('총평을 입력해주세요.');
			return;
		}
		
		try {
			isLoading = true;
			error = null;
			
			// DB에 루브릭 의견 저장
			allRubricFeedbacks[selectedItem] = {
				elements: elementFeedbacks,
				overall: itemOverallFeedback,
				lastUpdated: new Date().toISOString()
			};
			
			await updateRubricFeedbacks(token, allRubricFeedbacks);
			
			alert('✅ 의견이 저장되었습니다!');
			goToNextItem();
			
		} catch (err: any) {
			console.error('의견 저장 실패:', err);
			error = err.message || '의견 저장에 실패했습니다.';
		} finally {
			isLoading = false;
		}
	}
	
	function goToNextItem() {
		const items = ['A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'C1', 'C2'];
		const currentIndex = items.indexOf(selectedItem);
		if (currentIndex < items.length - 1) {
			selectedItem = items[currentIndex + 1];
			loadSessions();
		} else {
			alert('모든 항목 평가를 완료했습니다!');
			goto('/dashboard');
		}
	}
	
	function handleItemChange() {
		loadSessions();
	}
	
	function handleScoreFilterChange() {
		loadSessions();
	}
</script>

<svelte:head>
	<title>루브릭 평가 | MAICE</title>
</svelte:head>

<div class="rubric-evaluation">
	<div class="header">
		<div>
			<h1>📊 루브릭 평가</h1>
			<p class="subtitle">항목별로 세션을 검토하고 루브릭의 타당성에 대한 의견을 작성하세요</p>
		</div>
		<Button variant="secondary" onclick={() => goto('/dashboard')}>
			대시보드로
		</Button>
	</div>
	
	<!-- 필터 -->
	<Card>
		<div class="filters">
			<div class="filter-section">
				<h3>평가 항목</h3>
				<select bind:value={selectedItem} onchange={handleItemChange}>
					{#each Object.keys(itemTitles) as item}
						<option value={item}>{itemTitles[item]}</option>
					{/each}
				</select>
				<p class="item-desc">{itemDescriptions[selectedItem]}</p>
			</div>
			
			<div class="filter-section">
				<h3>점수 필터</h3>
				<div class="score-filters">
					{#each Object.entries(scoreFilterOptions) as [key, config]}
						<button
							class="score-filter-btn"
							class:active={scoreFilter === key}
							onclick={() => {
								scoreFilter = key as 'excellent' | 'good' | 'poor';
								handleScoreFilterChange();
							}}
						>
							{config.label}
						</button>
					{/each}
				</div>
			</div>
		</div>
	</Card>
	
	{#if isLoading}
		<Card>
			<div class="loading">로딩 중...</div>
		</Card>
	{:else if error}
		<Card>
			<div class="error">{error}</div>
		</Card>
	{:else}
		<!-- 루브릭 의견 작성 (먼저 표시) -->
		<Card>
			<h3>✍️ {itemTitles[selectedItem]} 루브릭 평가</h3>
			
			<!-- 세부 요소별 의견 -->
			<div class="checklist-section">
				<h4>📋 세부 요소별 의견</h4>
				{#each checklistElements[selectedItem] as element, index}
					<div class="element-item">
						<div class="element-header">
							<span class="element-num">{index + 1}</span>
							<div class="element-info">
								<div class="element-name">{element.title}</div>
								<div class="element-desc">{element.description}</div>
								<div class="element-example">{element.example}</div>
							</div>
						</div>
						<textarea
							bind:value={elementFeedbacks[`element_${index + 1}`]}
							placeholder="이 요소에 대한 의견 (선택사항)"
							rows="3"
						></textarea>
					</div>
				{/each}
			</div>
			
			<!-- 항목 총평 -->
			<div class="overall-section">
				<h4>📝 {itemTitles[selectedItem]} 총평 <span class="required">*</span></h4>
				<p class="guide-text">이 루브릭 항목이 학습 평가에 적절한지, 개선이 필요한 부분은 무엇인지 의견을 작성해주세요.</p>
				<textarea
					bind:value={itemOverallFeedback}
					placeholder="예시:
- 이 루브릭 항목은 수학적 전문성을 잘 평가하고 있음
- '교과과정 위계성' 기준이 모호하여 명확한 지표 필요
- AI가 수학 용어를 정확히 사용하는지 평가하는데 유용함"
					rows="8"
				></textarea>
			</div>
			
			<div class="actions">
				<Button variant="primary" onclick={saveFeedback} disabled={isLoading || !itemOverallFeedback.trim()}>
					💾 저장하고 다음 항목으로
				</Button>
			</div>
		</Card>
		
		<!-- 참고 세션들 (아래 표시) -->
		{#if sessions.length > 0}
			<Card>
				<h3>📚 참고 세션 ({sessions.length}개)</h3>
				<p class="guide-text">위의 의견 작성 시 아래 세션들을 참고하세요.</p>
				
				<div class="sessions-list">
					{#each sessions as session, idx}
						<div class="session-item">
							<div class="session-header">
								<span class="session-badge">세션 {idx + 1}</span>
								<span class="session-title">{session.title || '제목 없음'}</span>
								<span class="session-score" style="color: {scoreFilterOptions[scoreFilter].color}">
									{session.item_score}점
								</span>
							</div>
							
							<div class="messages">
								{#if session.messages && session.messages.length > 0}
									{#each session.messages as message}
										<div class="message {message.sender}">
											<div class="msg-sender">{message.sender === 'user' ? '👤 학생' : '🤖 AI'}</div>
											<div class="msg-content">
												<MarkdownRenderer content={message.content} />
											</div>
										</div>
									{/each}
								{:else}
									<p class="no-messages">메시지를 불러올 수 없습니다.</p>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			</Card>
		{:else}
			<Card>
				<div class="no-sessions-notice">
					<p>💡 해당 조건의 세션이 없습니다.</p>
					<p class="hint">세션 없이도 루브릭에 대한 일반적인 의견을 작성할 수 있습니다.</p>
				</div>
			</Card>
		{/if}
	{/if}
</div>

<style>
	.rubric-evaluation {
		padding: 2rem;
		max-width: 1400px;
		margin: 0 auto;
	}
	
	.header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 2rem;
	}
	
	.header h1 {
		margin: 0 0 0.5rem 0;
		font-size: 2rem;
		font-weight: 600;
		color: var(--maice-text);
	}
	
	.subtitle {
		margin: 0;
		font-size: 0.9375rem;
		color: var(--maice-text-muted);
	}
	
	/* 필터 */
	.filters {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 2rem;
	}
	
	.filter-section h3 {
		margin: 0 0 0.75rem 0;
		font-size: 1rem;
		font-weight: 600;
		color: var(--maice-text);
	}
	
	.filter-section select {
		width: 100%;
		padding: 0.75rem;
		border: 1px solid var(--maice-border);
		border-radius: 6px;
		font-size: 0.9375rem;
		background: var(--maice-bg);
		color: var(--maice-text);
		cursor: pointer;
	}
	
	.item-desc {
		margin: 0.75rem 0 0 0;
		padding: 0.75rem;
		background: var(--maice-bg-hover);
		border-radius: 6px;
		font-size: 0.875rem;
		color: var(--maice-text-muted);
	}
	
	.score-filters {
		display: flex;
		gap: 0.75rem;
	}
	
	.score-filter-btn {
		flex: 1;
		padding: 0.75rem 1rem;
		border: 2px solid var(--maice-border);
		border-radius: 6px;
		background: var(--maice-bg);
		color: var(--maice-text);
		font-size: 0.9375rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.2s;
	}
	
	.score-filter-btn:hover {
		border-color: var(--maice-primary);
	}
	
	.score-filter-btn.active {
		background: var(--maice-primary);
		color: white;
		border-color: var(--maice-primary);
	}
	
	/* 로딩/에러/빈 상태 */
	.loading, .error, .empty {
		padding: 2rem;
		text-align: center;
		color: var(--maice-text-muted);
	}
	
	.error {
		color: var(--maice-error-text-dark, #ef4444);
	}
	
	.empty-hint {
		margin-top: 0.5rem;
		font-size: 0.875rem;
	}
	
	/* 세션 목록 */
	.sessions-list {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1.5rem;
		margin-top: 1.5rem;
		max-height: 800px;
		overflow-y: auto;
		padding-right: 0.5rem;
	}
	
	.session-item {
		padding: 1.5rem;
		border: 2px solid var(--maice-border-primary);
		border-radius: 12px;
		background: var(--maice-card-bg);
		box-shadow: var(--maice-shadow-md);
	}
	
	.session-header {
		display: flex;
		align-items: center;
		gap: 1rem;
		margin-bottom: 1rem;
		padding: 1rem;
		background: var(--maice-bg-secondary);
		border-radius: 8px;
		border-left: 4px solid var(--maice-primary);
	}
	
	.session-badge {
		padding: 0.25rem 0.75rem;
		background: var(--maice-primary);
		color: white;
		border-radius: 6px;
		font-size: 0.875rem;
		font-weight: 600;
	}
	
	.session-title {
		flex: 1;
		font-weight: 600;
		color: var(--maice-text);
	}
	
	.session-score {
		font-size: 1.125rem;
		font-weight: 700;
	}
	
	.messages {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		max-height: 500px;
		overflow-y: auto;
		padding: 0.5rem;
		background: var(--maice-bg-secondary);
		border-radius: 8px;
	}
	
	.message {
		padding: 1rem;
		border-radius: 8px;
		border-left: 3px solid transparent;
	}
	
	.message.user {
		background: var(--maice-bg-hover);
		border-left-color: var(--maice-primary);
	}
	
	.message.maice {
		background: var(--maice-success-bg-light);
		border-left-color: var(--maice-success-border);
	}
	
	.msg-sender {
		font-size: 0.875rem;
		font-weight: 600;
		margin-bottom: 0.5rem;
		color: var(--maice-text);
	}
	
	.msg-content {
		line-height: 1.6;
		color: var(--maice-text);
		white-space: pre-wrap;
	}
	
	.no-messages {
		color: var(--maice-text-muted);
		font-style: italic;
	}
	
	.no-sessions-notice {
		padding: 2rem;
		text-align: center;
	}
	
	.no-sessions-notice p {
		margin: 0 0 0.5rem 0;
		color: var(--maice-text-secondary);
	}
	
	.no-sessions-notice .hint {
		font-size: 0.875rem;
		color: var(--maice-text-muted);
	}
	
	/* 의견 작성 */
	.checklist-section {
		margin-bottom: 2rem;
	}
	
	.checklist-section h4, .overall-section h4 {
		margin: 0 0 1rem 0;
		font-size: 1rem;
		font-weight: 600;
		color: var(--maice-text);
	}
	
	.element-item {
		margin-bottom: 1.5rem;
	}
	
	.element-header {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		margin-bottom: 0.75rem;
	}
	
	.element-num {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 28px;
		height: 28px;
		background: var(--maice-primary);
		color: white;
		border-radius: 50%;
		font-size: 0.875rem;
		font-weight: 600;
		flex-shrink: 0;
		margin-top: 0.25rem;
	}
	
	.element-info {
		flex: 1;
	}
	
	.element-name {
		font-size: 1rem;
		font-weight: 600;
		color: var(--maice-text-primary);
		margin-bottom: 0.5rem;
	}
	
	.element-desc {
		font-size: 0.875rem;
		color: var(--maice-text-secondary);
		margin-bottom: 0.375rem;
		line-height: 1.5;
	}
	
	.element-example {
		font-size: 0.8125rem;
		color: var(--maice-text-muted);
		font-style: italic;
		padding: 0.5rem;
		background: var(--maice-bg-hover);
		border-radius: 4px;
		border-left: 3px solid var(--maice-primary);
	}
	
	.overall-section {
		margin-bottom: 1.5rem;
	}
	
	.required {
		color: var(--maice-error-text-dark, #ef4444);
		font-size: 1.125rem;
	}
	
	.guide-text {
		margin: 0 0 0.75rem 0;
		font-size: 0.875rem;
		color: var(--maice-text-muted);
		line-height: 1.5;
	}
	
	textarea {
		width: 100%;
		padding: 1rem;
		border: 2px solid var(--maice-border-primary);
		border-radius: 8px;
		font-size: 0.9375rem;
		font-family: inherit;
		line-height: 1.6;
		resize: vertical;
		background: var(--maice-bg-secondary);
		color: var(--maice-text-primary);
		transition: all 0.2s;
		box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.1);
	}
	
	textarea::placeholder {
		color: var(--maice-text-muted);
		opacity: 0.7;
	}
	
	textarea:focus {
		outline: none;
		border-color: var(--maice-primary);
		box-shadow: 0 0 0 3px rgba(75, 85, 99, 0.1), inset 0 1px 3px rgba(0, 0, 0, 0.05);
		background: var(--maice-bg-primary);
	}
	
	textarea:hover:not(:focus) {
		border-color: var(--maice-border-secondary);
	}
	
	.actions {
		display: flex;
		gap: 1rem;
		justify-content: flex-end;
	}
	
	/* 반응형 */
	@media (max-width: 1024px) {
		.sessions-list {
			grid-template-columns: 1fr;
		}
	}
	
	@media (max-width: 768px) {
		.filters {
			grid-template-columns: 1fr;
		}
		
		.score-filters {
			flex-direction: column;
		}
	}
</style>
