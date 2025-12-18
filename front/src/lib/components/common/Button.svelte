<script lang="ts">
	interface Props {
		variant?: 'primary' | 'secondary' | 'ghost';
		size?: 'sm' | 'md' | 'lg';
		disabled?: boolean;
		loading?: boolean;
		fullWidth?: boolean;
		type?: 'button' | 'submit' | 'reset';
		className?: string;
		class?: string;
		children?: import('svelte').Snippet;
		onclick?: (event: MouseEvent) => void;
		onsubmit?: (event: SubmitEvent) => void;
		onreset?: (event: Event) => void;
	}

	let { 
		variant = 'primary', 
		size = 'md', 
		disabled = false, 
		loading = false, 
		fullWidth = false, 
		type = 'button',
		className = '',
		class: classProp = '',
		children,
		onclick,
		onsubmit,
		onreset
	}: Props = $props();

	// CSS 클래스 생성
	const buttonClasses = $derived([
		'maice-btn',
		`maice-btn-${variant}`,
		`maice-btn-${size}`,
		fullWidth ? 'maice-btn-full' : '',
		className,
		classProp
	].filter(Boolean).join(' '));
</script>

<button
	{type}
	{disabled}
	class={buttonClasses}
	{onclick}
	{onsubmit}
	{onreset}
>
	{#if loading}
		<div class="maice-btn-loading">
			<div class="maice-spinner"></div>
			<span>로딩 중...</span>
		</div>
	{:else}
		{@render children?.()}
	{/if}
</button>

<style>
	.maice-btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		border-radius: 0.5rem;
		font-weight: 600;
		font-size: 0.875rem;
		transition: all 0.2s ease-in-out;
		cursor: pointer;
		border: none;
		outline: none;
		text-decoration: none;
		position: relative;
		overflow: hidden;
		box-shadow: var(--maice-shadow-sm);
	}

	.maice-btn:hover {
		transform: translateY(-1px);
		box-shadow: var(--maice-shadow-md);
	}

	.maice-btn:active {
		transform: translateY(0);
	}

	.maice-btn:focus {
		outline: none;
		box-shadow: 0 0 0 2px var(--maice-primary), 0 0 0 4px white;
	}

	/* Primary 버튼 */
	.maice-btn-primary {
		background: var(--maice-primary);
		color: var(--maice-text-on-primary);
		border: 1px solid var(--maice-primary);
	}

	.maice-btn-primary:hover:not(:disabled) {
		background: var(--maice-primary-hover);
		border-color: var(--maice-primary-hover);
	}

	.maice-btn-primary:focus {
		box-shadow: 0 0 0 2px var(--maice-primary), 0 0 0 4px white;
	}

	/* Secondary 버튼 */
	.maice-btn-secondary {
		background: var(--maice-bg-secondary);
		color: var(--maice-text-secondary);
		border: 2px solid var(--maice-border-secondary);
		box-shadow: var(--maice-shadow-xs);
	}

	.maice-btn-secondary:hover:not(:disabled) {
		background: var(--maice-bg-secondary-hover);
		border-color: var(--maice-border-secondary-hover);
		color: var(--maice-text-secondary-hover);
	}

	.maice-btn-secondary:focus {
		box-shadow: 0 0 0 2px var(--maice-border-secondary), 0 0 0 4px white;
	}

	/* Ghost 버튼 */
	.maice-btn-ghost {
		background: transparent;
		color: var(--maice-text-ghost);
		border: 1px solid transparent;
		box-shadow: none;
	}

	.maice-btn-ghost:hover:not(:disabled) {
		background: var(--maice-bg-ghost-hover);
		color: var(--maice-text-ghost-hover);
		border-color: var(--maice-border-ghost-hover);
	}

	.maice-btn-ghost:focus {
		box-shadow: 0 0 0 2px var(--maice-border-primary), 0 0 0 4px white;
	}

	/* 크기별 스타일 */
	.maice-btn-sm {
		padding: 0.5rem 1rem;
		font-size: 0.75rem;
		min-height: 2rem;
	}

	.maice-btn-md {
		padding: 0.75rem 1.5rem;
		font-size: 0.875rem;
		min-height: 2.5rem;
	}

	.maice-btn-lg {
		padding: 1rem 2rem;
		font-size: 1rem;
		min-height: 3rem;
	}

	.maice-btn-full {
		width: 100%;
	}

	/* 비활성화 상태 */
	.maice-btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
		transform: none !important;
		box-shadow: var(--maice-shadow-xs) !important;
	}

	/* 로딩 상태 */
	.maice-btn-loading {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		pointer-events: none;
	}

	.maice-spinner {
		width: 1rem;
		height: 1rem;
		border: 2px solid transparent;
		border-top-color: currentColor;
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* 반응형 디자인 - 모바일에서 터치하기 좋은 크기로 조정 */
	@media (max-width: 640px) {
		.maice-btn-sm {
			padding: 0.75rem 1.25rem;
			font-size: 0.875rem;
			min-height: 2.75rem; /* 터치하기 좋은 높이 */
		}
		
		.maice-btn-md {
			padding: 1rem 1.5rem;
			font-size: 0.9375rem;
			min-height: 3rem;
		}
		
		.maice-btn-lg {
			padding: 1.25rem 2rem;
			font-size: 1.0625rem;
			min-height: 3.5rem;
		}
	}
</style>

