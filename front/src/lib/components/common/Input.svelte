<script lang="ts">
	interface Props {
		type?: string;
		placeholder?: string;
		value?: string;
		label?: string;
		error?: string;
		disabled?: boolean;
		required?: boolean;
		id?: string;
		className?: string;
	}

	let { 
		type = 'text', 
		placeholder = '', 
		value = $bindable(), 
		label = '', 
		error = '', 
		disabled = false, 
		required = false, 
		id = '', 
		className = '' 
	}: Props = $props();

	// 고유 ID 생성
	const inputId = $derived(id || `input-${Math.random().toString(36).substr(2, 9)}`);
</script>

<div class="space-y-2 {className}">
	{#if label}
		<label for={inputId} class="maice-input-label">
			{label}
			{#if required}
				<span class="maice-required">*</span>
			{/if}
		</label>
	{/if}
	
	<input
		{id}
		{type}
		{placeholder}
		{disabled}
		{required}
		bind:value
		class="maice-input {error ? 'maice-input-error' : ''}"
	/>
	
	{#if error}
		<p class="maice-input-error-text">{error}</p>
	{/if}
</div>

<style>
	.maice-input-label {
		display: block;
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--maice-text-secondary);
		margin-bottom: 0.5rem;
		transition: color 0.2s ease-in-out;
	}

	.maice-required {
		color: var(--maice-error);
		margin-left: 0.25rem;
		font-weight: 700;
	}

	.maice-input {
		width: 100%;
		padding: 0.75rem 1rem;
		border: 2px solid var(--maice-border-primary);
		border-radius: 0.75rem;
		font-size: 1rem;
		font-weight: 500;
		color: var(--maice-text-primary);
		background: var(--maice-bg-card);
		transition: all 0.2s ease-in-out;
		box-shadow: var(--maice-shadow-xs);
	}

	.maice-input::placeholder {
		color: var(--maice-text-muted);
		font-weight: 400;
	}

	.maice-input:hover:not(:disabled) {
		border-color: var(--maice-border-secondary);
		box-shadow: var(--maice-shadow-sm);
	}

	.maice-input:focus {
		outline: none;
		border-color: var(--maice-primary);
		box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1), var(--maice-shadow-sm);
		transform: translateY(-1px);
	}

	.maice-input:disabled {
		background-color: var(--maice-bg-secondary);
		color: var(--maice-text-muted);
		cursor: not-allowed;
		border-color: var(--maice-border-primary);
		opacity: 0.7;
	}

	.maice-input-error {
		border-color: var(--maice-error);
		background-color: #fef2f2;
	}

	.maice-input-error:focus {
		border-color: var(--maice-error);
		box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1), var(--maice-shadow-sm);
	}

	.maice-input-error-text {
		font-size: 0.875rem;
		color: var(--maice-error);
		font-weight: 500;
		margin-top: 0.25rem;
		display: flex;
		align-items: center;
		gap: 0.25rem;
	}

	.maice-input-error-text::before {
		content: '⚠️';
		font-size: 0.75rem;
	}

	/* 반응형 디자인 */
	@media (max-width: 640px) {
		.maice-input {
			padding: 0.625rem 0.875rem;
			font-size: 0.9375rem;
			border-radius: 0.625rem;
		}
		
		.maice-input-label {
			font-size: 0.8125rem;
		}
	}
</style>

