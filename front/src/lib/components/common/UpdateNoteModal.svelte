<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import Button from './Button.svelte';
	import { themeStore } from '$lib/stores/theme';
	import { CURRENT_UPDATE_NOTE_VERSION } from '$lib/utils/update-note';

	let {
		isOpen = false,
		onClose = () => {}
	}: {
		isOpen?: boolean;
		onClose?: () => void;
	} = $props();

	const dispatch = createEventDispatcher();

	let currentTheme = 'auto';
	let isDark = false;
	let hasRead = $state(false);
	let doNotShowAgain = $state(false);

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

	function handleClose() {
		// 업데이트 노트를 읽었다는 표시를 localStorage에 저장
		if (typeof window !== 'undefined') {
			try {
				// 인증 정보에서 사용자 ID 가져오기
				const savedAuth = localStorage.getItem('maice_auth');
				if (savedAuth) {
					const authData = JSON.parse(savedAuth);
					const userId = authData.id;
					
					if (userId) {
						localStorage.setItem(`maice_update_note_read_${userId}`, JSON.stringify({
							read: true,
							date: new Date().toISOString(),
							version: CURRENT_UPDATE_NOTE_VERSION,
							doNotShowAgain: doNotShowAgain
						}));
						console.log('💾 업데이트 노트 상태 저장:', {
							userId,
							version: CURRENT_UPDATE_NOTE_VERSION,
							doNotShowAgain,
							timestamp: new Date().toISOString()
						});
					}
				}
			} catch (error) {
				console.error('❌ 업데이트 노트 저장 실패:', error);
			}
		}
		dispatch('close');
		onClose();
	}

	// 키보드 이벤트 처리
	function handleKeyDown(event: KeyboardEvent) {
		if (event.key === 'Escape' && hasRead) {
			// ESC 키로 닫기 (읽은 후에만)
			handleClose();
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
		class="update-modal-backdrop" 
		role="dialog" 
		aria-modal="true" 
		aria-labelledby="update-modal-title" 
		tabindex="-1"
	>
		<div 
			class="update-modal-content" 
			onkeydown={handleKeyDown} 
			tabindex="-1"
			onclick={handleBackdropClick}
		>
			<div class="update-modal-header">
				<h2 id="update-modal-title" class="update-modal-title">
					🎉 MAICE 시스템 업데이트 - 사진 인식 기능 추가!
				</h2>
			</div>

			<div 
				class="update-modal-body" 
				bind:this={scrollContainer}
				onscroll={handleScroll}
			>
				<div class="update-content">
					<div class="update-section">
						<h3>✨ 새로운 기능</h3>
						<div class="feature-highlight">
							<div class="highlight-icon">📸</div>
							<div class="highlight-content">
								<h4>사진 인식 수식 입력</h4>
								<p>카메라로 수학 문제를 촬영하면 자동으로 수식으로 변환하여 입력됩니다. 복잡한 수식을 직접 타이핑할 필요 없이 간편하게 입력하세요!</p>
							</div>
						</div>
						<ul>
							<li><strong>수학 수식 입력 개선:</strong> MathLive를 활용한 더 직관적인 수식 입력</li>
							<li><strong>실시간 스트리밍:</strong> AI 응답의 실시간 표시로 더 빠른 학습 경험</li>
							<li><strong>세션 관리:</strong> 대화 기록을 체계적으로 관리하고 이어서 학습</li>
							<li><strong>다크 모드:</strong> 눈의 피로를 줄이는 다크 테마 지원</li>
						</ul>
					</div>

					<div class="update-section">
						<h3>🔧 개선사항</h3>
						<ul>
							<li><strong>성능 최적화:</strong> 더 빠른 응답 속도와 안정성 향상</li>
							<li><strong>사용자 경험:</strong> 직관적인 인터페이스와 접근성 개선</li>
							<li><strong>오류 처리:</strong> 더 나은 오류 메시지와 복구 기능</li>
							<li><strong>모바일 지원:</strong> 모바일 기기에서의 사용성 향상</li>
						</ul>
					</div>

					<div class="update-section">
						<h3>📚 사용 팁</h3>
						<ul>
							<li><strong>📸 사진 인식 활용:</strong> 수학 문제나 수식을 카메라로 촬영하면 자동으로 텍스트로 변환됩니다</li>
							<li><strong>수식 입력:</strong> 수식 입력창에서 LaTeX 문법을 사용하거나 MathLive 에디터를 활용하세요</li>
							<li><strong>세션 활용:</strong> 이전 대화를 참고하여 연속적인 학습을 진행하세요</li>
							<li><strong>테마 변경:</strong> 우측 상단의 테마 토글을 통해 라이트/다크 모드를 전환하세요</li>
							<li><strong>질문 유형:</strong> 구체적이고 명확한 질문을 하면 더 정확한 답변을 받을 수 있습니다</li>
						</ul>
					</div>

					<div class="update-section">
						<h3>🎯 앞으로의 계획</h3>
						<p>
							MAICE 시스템은 지속적으로 개선되고 있습니다. 사용자 피드백을 바탕으로 
							더 나은 학습 경험을 제공하기 위해 노력하고 있습니다. 
							궁금한 점이나 개선 제안이 있으시면 언제든지 말씀해 주세요!
						</p>
					</div>
				</div>
			</div>

		<div class="update-modal-footer">
			<div class="read-indicator" class:read={hasRead}>
				{#if hasRead}
					✅ 모든 내용을 읽었습니다
				{:else}
					📖 아래로 스크롤하여 모든 내용을 읽어주세요
				{/if}
			</div>
			<div class="checkbox-container">
				<label class="checkbox-label">
					<input 
						type="checkbox" 
						bind:checked={doNotShowAgain}
						disabled={!hasRead}
						class="checkbox-input"
					/>
					<span class="checkbox-text">다음에 보지 않기</span>
				</label>
			</div>
			<Button 
				onclick={handleClose} 
				disabled={!hasRead}
				variant="primary"
				size="lg"
			>
				{hasRead ? '확인' : '내용을 모두 읽어주세요'}
			</Button>
		</div>
		</div>
	</div>
{/if}

<style>
	.update-modal-backdrop {
		position: fixed;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		background: var(--maice-bg-overlay);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
		backdrop-filter: blur(4px);
	}

	.update-modal-content {
		background: var(--maice-bg-primary);
		border: 1px solid var(--maice-border-primary);
		border-radius: 0.75rem;
		box-shadow: var(--maice-shadow-xl);
		width: 90%;
		max-width: 600px;
		max-height: 80vh;
		overflow: hidden;
		animation: modalSlideIn 0.3s ease-out;
		position: relative;
		z-index: 1001;
		display: flex;
		flex-direction: column;
	}

	@keyframes modalSlideIn {
		from {
			opacity: 0;
			transform: translateY(-20px) scale(0.95);
		}
		to {
			opacity: 1;
			transform: translateY(0) scale(1);
		}
	}

	.update-modal-header {
		padding: 1.5rem 1.5rem 1rem 1.5rem;
		border-bottom: 1px solid var(--maice-border-primary);
		background: var(--maice-bg-primary);
	}

	.update-modal-title {
		margin: 0;
		font-size: 1.5rem;
		font-weight: 700;
		color: var(--maice-text-primary);
		text-align: center;
	}

	.update-modal-body {
		flex: 1;
		overflow-y: auto;
		padding: 1.5rem;
		background: var(--maice-bg-primary);
		color: var(--maice-text-primary);
	}

	.update-content {
		max-width: none;
	}

	.update-section {
		margin-bottom: 2rem;
	}

	.update-section:last-child {
		margin-bottom: 0;
	}

	.update-section h3 {
		margin: 0 0 1rem 0;
		font-size: 1.125rem;
		font-weight: 600;
		color: var(--maice-text-primary);
		border-bottom: 2px solid var(--maice-accent-primary);
		padding-bottom: 0.5rem;
	}

	.update-section ul {
		margin: 0;
		padding-left: 1.5rem;
	}

	.update-section li {
		margin-bottom: 0.75rem;
		line-height: 1.6;
		color: var(--maice-text-secondary);
	}

	.update-section li:last-child {
		margin-bottom: 0;
	}

	.update-section p {
		margin: 0;
		line-height: 1.6;
		color: var(--maice-text-secondary);
	}

	.update-section strong {
		color: var(--maice-text-primary);
		font-weight: 600;
	}

	/* 하이라이트 기능 스타일 */
	.feature-highlight {
		background: linear-gradient(135deg, var(--maice-accent-primary), var(--maice-accent-secondary));
		border-radius: 0.75rem;
		padding: 1.5rem;
		margin-bottom: 1.5rem;
		display: flex;
		align-items: flex-start;
		gap: 1rem;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
		border: 2px solid var(--maice-accent-primary);
	}

	.highlight-icon {
		font-size: 2rem;
		flex-shrink: 0;
		background: rgba(255, 255, 255, 0.2);
		border-radius: 50%;
		width: 3rem;
		height: 3rem;
		display: flex;
		align-items: center;
		justify-content: center;
		backdrop-filter: blur(10px);
	}

	.highlight-content h4 {
		margin: 0 0 0.5rem 0;
		font-size: 1.125rem;
		font-weight: 700;
		color: white;
		text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
	}

	.highlight-content p {
		margin: 0;
		color: rgba(255, 255, 255, 0.95);
		line-height: 1.5;
		font-size: 0.95rem;
		text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
	}

	.update-modal-footer {
		padding: 1rem 1.5rem 1.5rem 1.5rem;
		border-top: 1px solid var(--maice-border-primary);
		background: var(--maice-bg-primary);
		display: flex;
		flex-direction: column;
		gap: 1rem;
		align-items: center;
	}

	.read-indicator {
		font-size: 0.875rem;
		color: var(--maice-text-muted);
		text-align: center;
		transition: color 0.2s;
	}

	.read-indicator.read {
		color: var(--maice-success);
		font-weight: 500;
	}

	.checkbox-container {
		display: flex;
		justify-content: center;
		align-items: center;
		padding: 0.5rem 0;
	}

	.checkbox-label {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		cursor: pointer;
		user-select: none;
		font-size: 0.875rem;
		color: var(--maice-text-secondary);
		transition: color 0.2s;
	}

	.checkbox-label:hover {
		color: var(--maice-text-primary);
	}

	.checkbox-input {
		width: 1.125rem;
		height: 1.125rem;
		cursor: pointer;
		accent-color: var(--maice-accent-primary);
	}

	.checkbox-input:disabled {
		cursor: not-allowed;
		opacity: 0.5;
	}

	.checkbox-text {
		font-weight: 500;
	}

	/* 다크 테마 지원 */
	:global(.dark) .update-modal-content {
		background: var(--maice-bg-primary);
		border-color: var(--maice-border-primary);
	}

	:global(.dark) .update-modal-header,
	:global(.dark) .update-modal-body,
	:global(.dark) .update-modal-footer {
		background: var(--maice-bg-primary);
	}

	:global(.dark) .update-modal-title {
		color: var(--maice-text-primary);
	}

	:global(.dark) .update-section h3 {
		color: var(--maice-text-primary);
		border-bottom-color: var(--maice-accent-primary);
	}

	:global(.dark) .update-section li,
	:global(.dark) .update-section p {
		color: var(--maice-text-secondary);
	}

	:global(.dark) .update-section strong {
		color: var(--maice-text-primary);
	}

	:global(.dark) .read-indicator {
		color: var(--maice-text-muted);
	}

	:global(.dark) .read-indicator.read {
		color: var(--maice-success);
	}

	:global(.dark) .checkbox-text {
		color: var(--maice-text-secondary);
	}

	:global(.dark) .checkbox-label:hover {
		color: var(--maice-text-primary);
	}

	/* 다크 테마 하이라이트 스타일 */
	:global(.dark) .feature-highlight {
		background: linear-gradient(135deg, var(--maice-accent-primary), var(--maice-accent-secondary));
		border-color: var(--maice-accent-primary);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
	}

	:global(.dark) .highlight-icon {
		background: rgba(255, 255, 255, 0.15);
	}

	:global(.dark) .highlight-content h4 {
		color: white;
		text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
	}

	:global(.dark) .highlight-content p {
		color: rgba(255, 255, 255, 0.9);
		text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
	}

	/* 모바일 반응형 */
	@media (max-width: 640px) {
		.update-modal-content {
			width: 95%;
			max-height: 85vh;
		}

		.update-modal-header,
		.update-modal-body,
		.update-modal-footer {
			padding: 1rem;
		}

		.update-modal-title {
			font-size: 1.25rem;
		}

		.update-section h3 {
			font-size: 1rem;
		}

		.feature-highlight {
			flex-direction: column;
			text-align: center;
			padding: 1rem;
		}

		.highlight-icon {
			width: 2.5rem;
			height: 2.5rem;
			font-size: 1.5rem;
			margin: 0 auto 0.75rem auto;
		}

		.highlight-content h4 {
			font-size: 1rem;
		}

		.highlight-content p {
			font-size: 0.875rem;
		}

		.checkbox-text {
			font-size: 0.8125rem;
		}
	}
</style>
