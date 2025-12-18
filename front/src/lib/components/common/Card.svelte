<script lang="ts">
	interface Props {
		variant?: 'default' | 'elevated';
		padding?: 'sm' | 'md' | 'lg' | 'xl';
		animation?: 'none' | 'fade-in' | 'slide-up' | 'scale-in';
		className?: string;
		class?: string;
	}

	let { variant = 'default', padding = 'md', animation = 'none', className = '', class: classProp = '' }: Props = $props();

	// CSS 클래스 생성
	const cardClasses = $derived([
		'maice-card',
		`maice-card-${variant}`,
		`maice-card-${padding}`,
		animation !== 'none' ? `maice-animation-${animation}` : '',
		className,
		classProp
	].filter(Boolean).join(' '));
</script>

<div class={cardClasses}>
	<slot />
</div>

<style>
	.maice-card {
		background: var(--maice-bg-card);
		border-radius: 1rem;
		border: 1px solid var(--maice-border-primary);
		box-shadow: var(--maice-shadow-sm);
		transition: all 0.3s ease-in-out;
		position: relative;
		overflow: hidden;
	}

	.maice-card::before {
		content: '';
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		height: 4px;
		background: var(--maice-primary);
		opacity: 0;
		transition: opacity 0.3s ease-in-out;
	}

	.maice-card:hover {
		transform: translateY(-2px);
		box-shadow: var(--maice-shadow-lg);
		border-color: var(--maice-border-secondary);
	}

	.maice-card:hover::before {
		opacity: 1;
	}

	.maice-card-elevated {
		box-shadow: var(--maice-shadow-xl);
		border-color: var(--maice-border-secondary);
	}

	.maice-card-elevated:hover {
		box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
		transform: translateY(-4px);
	}

	.maice-card-sm {
		padding: 0.75rem;
	}

	.maice-card-md {
		padding: 1rem;
	}

	.maice-card-lg {
		padding: 1.5rem;
	}

	.maice-card-xl {
		padding: 2rem;
	}

	/* 애니메이션 */
	.maice-animation-fade-in {
		animation: fadeIn 0.5s ease-out;
	}

	.maice-animation-slide-up {
		animation: slideUp 0.5s ease-out;
	}

	.maice-animation-scale-in {
		animation: scaleIn 0.4s ease-out;
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

	@keyframes slideUp {
		from { 
			opacity: 0; 
			transform: translateY(20px);
		}
		to { 
			opacity: 1; 
			transform: translateY(0);
		}
	}

	@keyframes scaleIn {
		from { 
			opacity: 0; 
			transform: scale(0.95);
		}
		to { 
			opacity: 1; 
			transform: scale(1);
		}
	}

	/* 반응형 디자인 */
	@media (max-width: 640px) {
		.maice-card {
			border-radius: 0.75rem;
		}
		
		.maice-card-lg {
			padding: 1.25rem;
		}
		
		.maice-card-xl {
			padding: 1.5rem;
		}
	}
</style>

