<script lang="ts">
	import { createEventDispatcher, onMount, tick } from 'svelte';
	import katex from 'katex';
	import 'katex/dist/katex.min.css';
	import Button from '../common/Button.svelte';

	let {
		isOpen = false,
		onClose = () => {},
		onInsert = (latex: string, type: 'inline' | 'block') => {}
	}: {
		isOpen?: boolean;
		onClose?: () => void;
		onInsert?: (latex: string, type: 'inline' | 'block') => void;
	} = $props();

	let latexInput = $state('');
	let latexType = $state<'inline' | 'block'>('inline');
	let previewHtml = $state('');
	let hasError = $state(false);

	// LaTeX 미리보기 업데이트
	function updatePreview() {
		if (!latexInput.trim()) {
			previewHtml = '';
			hasError = false;
			return;
		}

		try {
			previewHtml = katex.renderToString(latexInput, { 
				displayMode: latexType === 'block', 
				throwOnError: false 
			});
			hasError = false;
		} catch (error) {
			previewHtml = `<span class="error">수식 오류: ${latexInput}</span>`;
			hasError = true;
		}
	}

	// 수식 삽입
	function handleInsert() {
		if (latexInput.trim()) {
			const latex = latexType === 'inline' ? `$${latexInput.trim()}$` : `$$${latexInput.trim()}$$`;
			onInsert(latex, latexType);
			handleClose();
		}
	}

	// 모달 닫기
	function handleClose() {
		latexInput = '';
		latexType = 'inline';
		previewHtml = '';
		hasError = false;
		onClose();
	}

	// 키보드 이벤트 처리
	function handleKeyDown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			handleClose();
		} else if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
			handleInsert();
		}
	}

	// LaTeX 입력 변경 시 미리보기 업데이트
	$effect(() => {
		updatePreview();
	});

	// 모달이 열릴 때 포커스 설정
	$effect(() => {
		if (isOpen) {
			tick().then(() => {
				const input = document.querySelector('.latex-modal-input') as HTMLInputElement;
				if (input) {
					input.focus();
				}
			});
		}
	});

	// 모달 외부 클릭 시 닫기
	function handleBackdropClick(event: MouseEvent) {
		if (event.target === event.currentTarget) {
			handleClose();
		}
	}
</script>

{#if isOpen}
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="modal-backdrop" onclick={handleBackdropClick} role="dialog" aria-modal="true" aria-labelledby="modal-title" tabindex="-1">
		<div class="modal-content" onkeydown={handleKeyDown} tabindex="-1">
			<div class="modal-header">
				<h3 id="modal-title">🔢 LaTeX 수식 입력</h3>
				<button class="close-btn" onclick={handleClose} title="닫기" aria-label="모달 닫기">×</button>
			</div>

			<div class="modal-body">
				<!-- 수식 타입 선택 -->
				<div class="type-selector">
					<label class="type-option">
						<input 
							type="radio" 
							bind:group={latexType} 
							value="inline"
						/>
						<span class="type-label">인라인 수식 ($...$)</span>
					</label>
					<label class="type-option">
						<input 
							type="radio" 
							bind:group={latexType} 
							value="block"
						/>
						<span class="type-label">블록 수식 ($$...$$)</span>
					</label>
				</div>

				<!-- LaTeX 입력 -->
				<div class="input-group">
					<label for="latex-input">LaTeX 코드:</label>
					<input
						id="latex-input"
						type="text"
						class="latex-modal-input"
						bind:value={latexInput}
						placeholder="예: x^2 + 2x + 1 = 0"
						aria-describedby="latex-preview"
					/>
				</div>

				<!-- 미리보기 -->
				{#if previewHtml}
					<div class="preview-section">
						<label for="latex-preview">미리보기:</label>
						<div id="latex-preview" class="latex-preview {hasError ? 'error' : ''}" aria-live="polite">
							{@html previewHtml}
						</div>
					</div>
				{/if}

				<!-- 자주 사용하는 수식 예시 -->
				<div class="examples-section">
					<h4>💡 자주 사용하는 수식:</h4>
					<div class="examples-grid">
						<!-- 기본 수학 기호 -->
						<button 
							class="example-btn"
							onclick={() => {
								latexInput = 'x^2 + 2x + 1 = 0';
								latexType = 'inline';
							}}
						>
							이차방정식
						</button>
						<button 
							class="example-btn"
							onclick={() => {
								latexInput = '\\frac{a}{b}';
								latexType = 'inline';
							}}
						>
							분수
						</button>
						<button 
							class="example-btn"
							onclick={() => {
								latexInput = '\\sqrt{x^2 + y^2}';
								latexType = 'inline';
							}}
						>
							제곱근
						</button>
						<button 
							class="example-btn"
							onclick={() => {
								latexInput = '\\pm \\sqrt{b^2 - 4ac}';
								latexType = 'inline';
							}}
						>
							근의공식
						</button>
						
						<!-- 삼각함수 -->
						<button 
							class="example-btn"
							onclick={() => {
								latexInput = '\\sin^2 x + \\cos^2 x = 1';
								latexType = 'inline';
							}}
						>
							삼각함수
						</button>
						<button 
							class="example-btn"
							onclick={() => {
								latexInput = '\\tan x = \\frac{\\sin x}{\\cos x}';
								latexType = 'inline';
							}}
						>
							탄젠트
						</button>
						
						<!-- 미적분 -->
						<button 
							class="example-btn"
							onclick={() => {
								latexInput = '\\frac{d}{dx}[x^n] = nx^{n-1}';
								latexType = 'block';
							}}
						>
							미분
						</button>
						<button 
							class="example-btn"
							onclick={() => {
								latexInput = '\\int_0^1 x^2 dx';
								latexType = 'block';
							}}
						>
							적분
						</button>
						<button 
							class="example-btn"
							onclick={() => {
								latexInput = '\\lim_{x \\to 0} \\frac{\\sin x}{x} = 1';
								latexType = 'block';
							}}
						>
							극한
						</button>
						
						<!-- 급수와 합계 -->
						<button 
							class="example-btn"
							onclick={() => {
								latexInput = '\\sum_{i=1}^{n} i^2';
								latexType = 'block';
							}}
						>
							합계
						</button>
						<button 
							class="example-btn"
							onclick={() => {
								latexInput = '\\sum_{n=1}^{\\infty} \\frac{1}{n^2} = \\frac{\\pi^2}{6}';
								latexType = 'block';
							}}
						>
							무한급수
						</button>
						
						<!-- 행렬과 벡터 -->
						<button 
							class="example-btn"
							onclick={() => {
								latexInput = '\\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix}';
								latexType = 'block';
							}}
						>
							행렬
						</button>
						<button 
							class="example-btn"
							onclick={() => {
								latexInput = '\\vec{v} = \\langle x, y, z \\rangle';
								latexType = 'inline';
							}}
						>
							벡터
						</button>
						
						<!-- 로그와 지수 -->
						<button 
							class="example-btn"
							onclick={() => {
								latexInput = '\\log_a b = \\frac{\\log b}{\\log a}';
								latexType = 'inline';
							}}
						>
							로그
						</button>
						<button 
							class="example-btn"
							onclick={() => {
								latexInput = 'e^{i\\pi} + 1 = 0';
								latexType = 'block';
							}}
						>
							오일러공식
						</button>
						
						<!-- 확률과 통계 -->
						<button 
							class="example-btn"
							onclick={() => {
								latexInput = 'P(A \\cap B) = P(A) \\cdot P(B)';
								latexType = 'inline';
							}}
						>
							확률
						</button>
						<button 
							class="example-btn"
							onclick={() => {
								latexInput = '\\bar{x} = \\frac{1}{n} \\sum_{i=1}^{n} x_i';
								latexType = 'block';
							}}
						>
							평균
						</button>
						
						<!-- 기하학 -->
						<button 
							class="example-btn"
							onclick={() => {
								latexInput = 'a^2 + b^2 = c^2';
								latexType = 'inline';
							}}
						>
							피타고라스
						</button>
						<button 
							class="example-btn"
							onclick={() => {
								latexInput = 'A = \\pi r^2';
								latexType = 'inline';
							}}
						>
							원의넓이
						</button>
						
						<!-- 복소수 -->
						<button 
							class="example-btn"
							onclick={() => {
								latexInput = 'z = a + bi = r(\\cos\\theta + i\\sin\\theta)';
								latexType = 'inline';
							}}
						>
							복소수
						</button>
						
						<!-- 부등식 -->
						<button 
							class="example-btn"
							onclick={() => {
								latexInput = '|a + b| \\leq |a| + |b|';
								latexType = 'inline';
							}}
						>
							삼각부등식
						</button>
					</div>
				</div>
			</div>

			<div class="modal-footer">
				<Button variant="secondary" onclick={handleClose}>
					취소
				</Button>
				<Button 
					onclick={handleInsert}
					disabled={!latexInput.trim() || hasError}
				>
					수식 삽입
				</Button>
			</div>
		</div>
	</div>
{/if}

<style>
	.modal-backdrop {
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

	.modal-content {
		background: var(--maice-bg-primary);
		border: 1px solid var(--maice-border-primary);
		border-radius: 0.75rem;
		box-shadow: var(--maice-shadow-xl);
		width: 90%;
		max-width: 600px;
		max-height: 90vh;
		overflow-y: auto;
		animation: modalSlideIn 0.3s ease-out;
		position: relative;
		z-index: 1001;
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

	.modal-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1.5rem 1.5rem 1rem 1.5rem;
		border-bottom: 1px solid var(--maice-border-primary);
	}

	.modal-header h3 {
		margin: 0;
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--maice-text-primary);
	}

	.close-btn {
		background: none;
		border: none;
		font-size: 1.5rem;
		color: var(--maice-text-muted);
		cursor: pointer;
		padding: 0.25rem;
		border-radius: 0.25rem;
		transition: all 0.2s;
	}

	.close-btn:hover {
		background: var(--maice-bg-secondary-hover);
		color: var(--maice-text-primary);
	}

	.modal-body {
		padding: 1.5rem;
		background: var(--maice-bg-primary);
		color: var(--maice-text-primary);
	}

	/* 수식 타입 선택 */
	.type-selector {
		display: flex;
		gap: 1rem;
		margin-bottom: 1.5rem;
	}

	.type-option {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		cursor: pointer;
		padding: 0.5rem;
		border-radius: 0.5rem;
		transition: background-color 0.2s;
	}

	.type-option:hover {
		background: var(--maice-bg-secondary-hover);
	}

	.type-option input[type="radio"] {
		margin: 0;
	}

	.type-label {
		font-size: 0.875rem;
		color: var(--maice-text-primary);
	}

	/* 입력 그룹 */
	.input-group {
		margin-bottom: 1.5rem;
	}

	.input-group label {
		display: block;
		margin-bottom: 0.5rem;
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--maice-text-primary);
	}

	.latex-modal-input {
		width: 100%;
		padding: 0.75rem;
		border: 2px solid var(--maice-border-primary);
		border-radius: 0.5rem;
		font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
		font-size: 0.875rem;
		background: var(--maice-bg-primary);
		color: var(--maice-text-primary);
		transition: border-color 0.2s;
	}

	.latex-modal-input:focus {
		outline: none;
		border-color: var(--maice-primary);
		box-shadow: 0 0 0 3px var(--maice-primary-border-hover);
	}

	/* 미리보기 */
	.preview-section {
		margin-bottom: 1.5rem;
	}

	.preview-section label {
		display: block;
		margin-bottom: 0.5rem;
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--maice-text-primary);
	}

	.latex-preview {
		padding: 1rem;
		background: var(--maice-bg-secondary);
		border: 1px solid var(--maice-border-secondary);
		border-radius: 0.5rem;
		min-height: 60px;
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--maice-text-primary);
	}

	.latex-preview.error {
		border-color: var(--maice-error);
		background: var(--maice-bg-secondary);
		color: var(--maice-error);
	}

	.latex-preview :global(.katex) {
		font-size: 1.2em;
	}

	/* 예시 섹션 */
	.examples-section {
		margin-bottom: 1.5rem;
	}

	.examples-section h4 {
		margin: 0 0 1rem 0;
		font-size: 1rem;
		font-weight: 600;
		color: var(--maice-text-primary);
	}

	.examples-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
		gap: 0.5rem;
	}

	.example-btn {
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--maice-border-primary);
		border-radius: 0.375rem;
		background: var(--maice-bg-primary);
		color: var(--maice-text-primary);
		font-size: 0.75rem;
		cursor: pointer;
		transition: all 0.2s;
	}

	.example-btn:hover {
		background: var(--maice-bg-secondary-hover);
		border-color: var(--maice-primary);
	}

	/* 모달 푸터 */
	.modal-footer {
		display: flex;
		justify-content: flex-end;
		gap: 0.75rem;
		padding: 1rem 1.5rem 1.5rem 1.5rem;
		border-top: 1px solid var(--maice-border-primary);
		background: var(--maice-bg-primary);
	}

	/* 반응형 디자인 */
	@media (max-width: 768px) {
		.modal-content {
			width: 95%;
			margin: 1rem;
		}

		.type-selector {
			flex-direction: column;
			gap: 0.5rem;
		}

		.examples-grid {
			grid-template-columns: repeat(2, 1fr);
		}
	}
</style>
