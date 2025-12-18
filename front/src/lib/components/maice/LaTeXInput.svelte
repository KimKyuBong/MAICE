<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import katex from 'katex';
	import 'katex/dist/katex.min.css';
	import { themeStore } from '$lib/stores/theme';

	let {
		placeholder = '텍스트와 수식을 함께 입력하세요... (예: `x^2 + 1 = 0`)',
		className = '',
		value = $bindable(''),
		disabled = false
	}: {
		placeholder?: string;
		className?: string;
		value?: string;
		disabled?: boolean;
	} = $props();

	const dispatch = createEventDispatcher<{
		input: { value: string };
		enter: { value: string };
	}>();

	let textareaElement: HTMLTextAreaElement;
	let renderedPreview = $state('');

	function renderLatex(text: string): string {
		if (!text) return '';
		
		try {
			// Replace block math first
			text = text.replace(/\$\$([^]+?)\$\$/g, (match, content) => {
				try {
					return katex.renderToString(content, { displayMode: true, throwOnError: false });
				} catch (e) {
					console.warn('블록 수식 렌더링 오류:', e);
					return `<span class="error">블록 수식 오류: ${content}</span>`;
				}
			});
			
			// Then replace inline math
			text = text.replace(/\$([^]+?)\$/g, (match, content) => {
				try {
					return katex.renderToString(content, { displayMode: false, throwOnError: false });
				} catch (e) {
					console.warn('인라인 수식 렌더링 오류:', e);
					return `<span class="error">인라인 수식 오류: ${content}</span>`;
				}
			});
			
			return text;
		} catch (error) {
			console.error('LaTeX 렌더링 중 오류 발생:', error);
			return `<span class="error">렌더링 오류가 발생했습니다.</span>`;
		}
	}

	function handleInput(event: Event) {
		const target = event.target as HTMLTextAreaElement;
		const newValue = target.value;
		
		// 값이 실제로 변경되었을 때만 처리
		if (newValue !== value) {
			value = newValue;
			renderedPreview = renderLatex(value);
			
			// 이벤트 디스패치
			dispatch('input', { value: value });
			
			console.log('📝 LaTeX 입력 처리됨:', {
				value: value,
				length: value.length,
				hasLatex: /\$/.test(value)
			});
		}
	}

	function handleKeyPress(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			
			// Enter 키 이벤트 디스패치
			dispatch('enter', { value: value });
			
			console.log('↵ Enter 키 이벤트 발생:', {
				value: value,
				length: value.length
			});
		}
	}
	
	// 외부에서 호출할 수 있는 clear 메서드
	export function clear() {
		value = '';
		renderedPreview = '';
		
		// textarea 요소가 있다면 직접 초기화
		if (textareaElement) {
			textareaElement.value = '';
		}
		
		// 이벤트 디스패치
		dispatch('input', { value: '' });
		
		console.log('🧹 LaTeX 입력 필드 초기화 완료');
	}

	// Expose clear method for external access
	$effect(() => {
		if (typeof window !== 'undefined') {
			(window as any).LaTeXInputComponent = {
				clear
			};
		}
	});

	// Update preview when value changes externally
	$effect(() => {
		renderedPreview = renderLatex(value);
	});
	
	// 컴포넌트 마운트 시 초기화
	onMount(() => {
		console.log('🚀 LaTeXInput 컴포넌트 마운트됨');
		if (textareaElement) {
			textareaElement.focus();
		}
	});
</script>

<div class="latex-input-container {className}" class:disabled>
	<textarea
		bind:this={textareaElement}
		{placeholder}
		{disabled}
		on:input={handleInput}
		on:keypress={handleKeyPress}
		class="latex-textarea"
		bind:value
		rows="3"
	></textarea>
	
	{#if value && value.trim()}
		<div class="latex-preview-container">
			<div class="preview-header">
				📝 미리보기 {#if /\$/.test(value)}<span class="latex-indicator">LaTeX</span>{/if}
			</div>
			<div class="latex-preview">
				{@html renderedPreview}
			</div>
		</div>
	{/if}
</div>

<style>
	.latex-input-container {
		width: 100%;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.latex-textarea {
		width: 100%;
		min-height: 80px;
		padding: 0.75rem 1rem;
		border: 2px solid var(--maice-border-primary);
		border-radius: 0.5rem;
		background: var(--maice-bg-primary);
		color: var(--maice-text-primary);
		font-size: 1rem;
		line-height: 1.5;
		font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
		resize: vertical;
		transition: all 0.2s ease;
	}

	.latex-textarea:focus {
		outline: none;
		border-color: var(--maice-primary);
		box-shadow: 0 0 0 3px var(--maice-primary-border-hover);
		transform: translateY(-1px);
	}

	.latex-textarea:disabled {
		opacity: 0.7;
		cursor: not-allowed;
		background: var(--maice-bg-secondary);
	}

	.latex-preview-container {
		border: 1px solid var(--maice-border-secondary);
		border-radius: 0.5rem;
		background: var(--maice-bg-secondary);
		overflow: hidden;
	}

	.preview-header {
		font-size: 0.75rem;
		font-weight: 500;
		padding: 0.5rem 0.75rem;
		color: var(--maice-text-secondary);
		background: var(--maice-bg-tertiary);
		border-bottom: 1px solid var(--maice-border-secondary);
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.latex-indicator {
		background: var(--maice-primary);
		color: var(--maice-text-on-primary);
		padding: 0.125rem 0.375rem;
		border-radius: 0.25rem;
		font-size: 0.625rem;
		font-weight: 600;
	}

	.latex-preview {
		padding: 0.75rem 1rem;
		min-height: 40px;
		color: var(--maice-text-primary);
		line-height: 1.6;
	}

	.latex-preview :global(.katex) {
		font-size: 1em;
	}
	
	.latex-preview :global(.error) {
		color: #ef4444;
		background-color: #fee2e2;
		padding: 0.25rem 0.5rem;
		border-radius: 0.25rem;
		font-size: 0.875rem;
	}
	
	/* 반응형 디자인 */
	@media (max-width: 768px) {
		.latex-textarea {
			min-height: 60px;
			font-size: 0.875rem;
		}
		
		.latex-preview {
			padding: 0.5rem 0.75rem;
		}
	}
</style>