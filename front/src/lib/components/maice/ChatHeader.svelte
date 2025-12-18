<script lang="ts">
	import Button from '../common/Button.svelte';

	let {
		sessionId = null,
		requestId = null,
		onClearChat = () => {}
	}: {
		sessionId?: number | null;
		requestId?: string | null;
		onClearChat?: () => void;
	} = $props();
</script>

<div class="chat-header">
	<h2>💬 AI와 대화하기</h2>
	<p>학습에 관한 질문이나 궁금한 점을 자유롭게 물어보세요!</p>
	<div class="chat-info">
		{#if sessionId}
			<span class="session-info">
				📋 세션 ID: {sessionId}
			</span>
		{/if}
		{#if requestId}
			<span class="request-info">
				🆔 요청 ID: {requestId.slice(0, 8)}...
			</span>
		{/if}
	</div>
	<div class="chat-actions">
		<Button variant="secondary" size="sm" on:click={onClearChat}>
			🔄 새 대화 시작
		</Button>
	</div>
</div>

<style>
	.chat-header {
		text-align: center;
		margin-bottom: 1rem;
		padding-bottom: 0.5rem;
		border-bottom: 1px solid var(--maice-border-primary);
	}

	.chat-header h2 {
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--maice-text-primary);
		margin: 0 0 0.25rem 0;
	}

	.chat-header p {
		font-size: 0.875rem;
		color: var(--maice-text-secondary);
		margin: 0;
	}

	.chat-info {
		margin-bottom: 0.75rem;
		display: flex;
		justify-content: center;
		gap: 0.5rem;
		font-size: 0.75rem;
		color: var(--maice-text-muted);
	}

	.session-info,
	.request-info {
		background: var(--maice-bg-card);
		padding: 0.25rem 0.5rem;
		border-radius: 0.25rem;
		border: 1px solid var(--maice-border-primary);
	}

	.chat-actions {
		margin-top: 0.5rem;
	}

	/* 반응형 디자인 */
	@media (max-width: 768px) {
		.chat-header h2 {
			font-size: 1.125rem;
		}
		
		.chat-header p {
			font-size: 0.75rem;
		}
		
		.chat-info {
			flex-direction: column;
			align-items: center;
		}
	}
</style>
