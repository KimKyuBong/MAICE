<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import Button from './Button.svelte';
	import { themeStore } from '$lib/stores/theme';

	let {
		isOpen = false,
		onAccept = () => {},
		onReject = () => {}
	}: {
		isOpen?: boolean;
		onAccept?: () => void;
		onReject?: () => void;
	} = $props();

	const dispatch = createEventDispatcher();

	let currentTheme = 'auto';
	let isDark = false;
	let hasRead = $state(false);

	// 테마 상태 구독
	themeStore.subscribe(state => {
		currentTheme = state.current;
		isDark = state.isDark;
	});

	// 스크롤 감지로 읽음 상태 체크
	let scrollContainer: HTMLDivElement | undefined = $state();
	let isAtBottom = $state(false);

	function handleScroll() {
		if (scrollContainer) {
			const { scrollTop, scrollHeight, clientHeight } = scrollContainer;
			isAtBottom = scrollTop + clientHeight >= scrollHeight - 10;
			hasRead = isAtBottom;
		}
	}

	function handleAccept() {
		// 동의 상태를 localStorage에 저장
		if (typeof window !== 'undefined') {
			localStorage.setItem('maice_research_consent', JSON.stringify({
				consent: true,
				date: new Date().toISOString(),
				version: '1.0'
			}));
		}
		dispatch('accept');
		onAccept();
	}

	function handleReject() {
		dispatch('reject');
		onReject();
	}

	// 키보드 이벤트 처리
	function handleKeyDown(event: KeyboardEvent) {
		if (event.key === 'Escape' && hasRead) {
			// ESC 키로 거부 (읽은 후에만)
			handleReject();
		}
	}

	// 모달 외부 클릭 방지
	function handleBackdropClick(event: MouseEvent) {
		event.stopPropagation();
	}
</script>

{#if isOpen}
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div 
		class="consent-modal-backdrop" 
		role="dialog" 
		aria-modal="true" 
		aria-labelledby="consent-modal-title" 
		tabindex="-1"
	>
		<div 
			class="consent-modal-content" 
			onkeydown={handleKeyDown} 
			tabindex="-1"
			onclick={handleBackdropClick}
		>
			<div class="consent-modal-header">
				<h2 id="consent-modal-title" class="consent-modal-title">
					📋 연구 참여 동의서
				</h2>
			</div>

			<div 
				class="consent-modal-body" 
				bind:this={scrollContainer}
				onscroll={handleScroll}
			>
				<div class="consent-content">
					<div class="consent-section">
						<h3>🎯 연구 목적</h3>
						<p>
							본 연구는 AI 기반 수학 학습 지원 시스템(MAICE)의 효과성과 사용성을 분석하여 
							더 나은 학습 환경을 제공하기 위해 수행됩니다. 학생들의 학습 패턴과 AI 튜터와의 
							상호작용을 통해 교육 기술의 발전 방향을 모색하고자 합니다.
						</p>
					</div>

					<div class="consent-section">
						<h3>📊 수집되는 정보</h3>
						<p>
							연구 목적으로 다음 정보들이 수집될 수 있습니다:
						</p>
						<ul>
							<li><strong>대화 내용:</strong> 학생과 AI 튜터 간의 질문과 답변</li>
							<li><strong>학습 패턴:</strong> 질문 유형, 반복 질문 빈도, 학습 진도</li>
							<li><strong>시스템 사용 정보:</strong> 기능 사용 빈도, 세션 시간, 만족도</li>
						</ul>
					</div>

					<div class="consent-section">
						<h3>🔒 개인정보 보호</h3>
						<p>
							수집된 모든 정보는 익명화 처리되어 개인을 식별할 수 없도록 보호됩니다.
							실제 이름이나 개별 학생을 특정할 수 있는 정보는 연구 자료에서 제외되며,
							학습 효과성 분석과 시스템 개선 목적으로만 사용됩니다.
						</p>
					</div>

					<div class="consent-section">
						<h3>⏰ 데이터 보관 기간</h3>
						<p>
							연구에 사용되는 데이터는 연구 종료 후 3년간 보관되며, 그 이후에는 
							안전하게 파기됩니다. 언제든지 동의를 철회할 수 있으며, 
							동의 철회 시 관련 데이터는 즉시 삭제됩니다.
						</p>
					</div>

					<div class="consent-section">
						<h3>🤝 참여자의 권리</h3>
						<ul>
							<li>연구 참여는 <strong>완전히 자발적</strong>이며, 언제든지 참여를 중단할 수 있습니다</li>
							<li>동의를 철회하고 싶을 때는 언제든지 연락하여 요청할 수 있습니다</li>
							<li>연구 참여 여부가 학습 평가에 전혀 영향을 미치지 않습니다</li>
							<li>연구 결과에 대한 문의가 있을 경우 담당자에게 연락하실 수 있습니다</li>
						</ul>
					</div>

					<div class="consent-section">
						<h3>📞 문의사항</h3>
						<p>
							연구와 관련된 문의나 동의 철회 요청은 다음 연락처로 문의해 주시기 바랍니다:
						</p>
						<div class="contact-info">
							<p><strong>연구책임자:</strong> (기관 담당자)</p>
							<p><strong>연락처:</strong> 000-0000-0000</p>
							<p><strong>이메일:</strong> support@example.com</p>
						</div>
					</div>

					<div class="consent-footer">
						<p class="consent-notice">
							<strong>⚠️ 중요:</strong> 위 내용을 모두 읽고 이해했으며, 
							본 연구에 자발적으로 참여하는 데 동의합니다.
						</p>
					</div>
				</div>

				<!-- 스크롤 완료 알림 -->
				{#if !hasRead}
					<div class="scroll-indicator">
						<p>📖 아래로 스크롤하여 전체 내용을 읽어주세요</p>
						<div class="scroll-arrow">↓</div>
					</div>
				{:else}
					<div class="read-complete">
						<p>✅ 전체 내용을 읽으셨습니다</p>
					</div>
				{/if}
			</div>

			<div class="consent-modal-footer">
				<div class="consent-button-group">
					<Button 
						variant="secondary"     
						size="lg" 
						onclick={handleReject}
						disabled={!hasRead}
						class="consent-reject-btn"
					>
						동의하지 않음
					</Button>
					<Button 
						variant="primary" 
						size="lg" 
						onclick={handleAccept}
						disabled={!hasRead}
						class="consent-accept-btn"
					>
						동의하고 계속하기
					</Button>
				</div>
				<p class="consent-help-text">
					위 내용을 모두 읽은 후에만 선택할 수 있습니다.
				</p>
			</div>
		</div>
	</div>
{/if}

<style>
	.consent-modal-backdrop {
		position: fixed;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		background-color: rgba(0, 0, 0, 0.7);
		backdrop-filter: blur(4px);
		z-index: 9999;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 1rem;
		box-sizing: border-box;
	}

	.consent-modal-content {
		background-color: var(--maice-bg-card);
		border: 2px solid var(--maice-border-primary);
		border-radius: 16px;
		box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
		max-width: 600px;
		width: 100%;
		max-height: 90vh;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.consent-modal-header {
		padding: 2rem 2rem 1rem 2rem;
		border-bottom: 1px solid var(--maice-border-primary);
		background-color: var(--maice-bg-secondary);
	}

	.consent-modal-title {
		margin: 0;
		font-size: 1.5rem;
		font-weight: 600;
		color: var(--maice-text-primary);
		text-align: center;
	}

	.consent-modal-body {
		flex: 1;
		overflow-y: auto;
		padding: 0;
		max-height: 400px;
	}

	.consent-content {
		padding: 2rem;
	}

	.consent-section {
		margin-bottom: 2rem;
	}

	.consent-section h3 {
		margin: 0 0 1rem 0;
		font-size: 1.125rem;
		font-weight: 600;
		color: var(--maice-text-primary);
		border-left: 4px solid var(--maice-primary);
		padding-left: 1rem;
	}

	.consent-section p {
		margin: 0 0 1rem 0;
		line-height: 1.6;
		color: var(--maice-text-secondary);
	}

	.consent-section ul {
		margin: 0.5rem 0 1rem 1.5rem;
		padding: 0;
	}

	.consent-section li {
		margin-bottom: 0.5rem;
		line-height: 1.5;
		color: var(--maice-text-secondary);
	}

	.contact-info {
		background-color: var(--maice-bg-secondary);
		border: 1px solid var(--maice-border-primary);
		border-radius: 8px;
		padding: 1rem;
		margin-top: 1rem;
	}

	.contact-info p {
		margin: 0.25rem 0;
		font-size: 0.9rem;
	}

	.consent-footer {
		background-color: var(--maice-bg-secondary);
		border: 1px solid var(--maice-border-primary);
		border-radius: 8px;
		padding: 1rem;
		margin-top: 2rem;
	}

	.consent-notice {
		margin: 0;
		font-size: 0.9rem;
		color: var(--maice-warning);
		font-weight: 500;
	}

	.scroll-indicator {
		position: sticky;
		bottom: 0;
		background: linear-gradient(transparent, var(--maice-bg-secondary) 20%);
		padding: 1rem 2rem 1rem 2rem;
		text-align: center;
		border-top: 1px solid var(--maice-border-primary);
	}

	.scroll-indicator p {
		margin: 0 0 0.5rem 0;
		font-size: 0.9rem;
		color: var(--maice-text-secondary);
	}

	.scroll-arrow {
		font-size: 1.5rem;
		color: var(--maice-primary);
		animation: bounce 1.5s infinite;
	}

	.read-complete {
		position: sticky;
		bottom: 0;
		background-color: rgba(16, 185, 129, 0.1);
		border: 1px solid var(--maice-success);
		border-radius: 8px;
		margin: 1rem 2rem;
		padding: 1rem;
		text-align: center;
	}

	.read-complete p {
		margin: 0;
		color: var(--maice-success);
		font-weight: 500;
	}

	.consent-modal-footer {
		padding: 1.5rem 2rem 2rem 2rem;
		border-top: 1px solid var(--maice-border-primary);
		background-color: var(--maice-bg-secondary);
	}

	.consent-button-group {
		display: flex;
		gap: 1rem;
		margin-bottom: 1rem;
		justify-content: center;
		max-width: 100%;
	}

	.consent-reject-btn {
		min-width: 140px;
		max-width: 200px;
		flex: 0 1 auto;
	}

	.consent-accept-btn {
		min-width: 140px;
		max-width: 200px;
		flex: 0 1 auto;
	}

	.consent-help-text {
		margin: 0;
		font-size: 0.8rem;
		color: var(--maice-text-secondary);
		text-align: center;
	}

	@keyframes bounce {
		0%, 20%, 50%, 80%, 100% {
			transform: translateY(0);
		}
		40% {
			transform: translateY(-10px);
		}
		60% {
			transform: translateY(-5px);
		}
	}

	/* 모바일 대응 */
	@media (max-width: 640px) {
		.consent-modal-content {
			margin: 0.5rem;
			max-height: 95vh;
		}

		.consent-modal-header,
		.consent-content,
		.consent-modal-footer {
			padding-left: 1rem;
			padding-right: 1rem;
		}

		.consent-button-group {
			flex-direction: column;
			align-items: center;
		}

		.consent-reject-btn,
		.consent-accept-btn {
			width: 100%;
			max-width: 240px;
		}

		.consent-modal-title {
			font-size: 1.25rem;
		}
	}
</style>
