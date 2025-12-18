<script lang="ts">
	import MarkdownRenderer from './MarkdownRenderer.svelte';
	import { onMount, tick } from 'svelte';

	let {
		messages = [],
		isLoading = false
	}: {
		messages: Array<{
			id: number;
			type: 'user' | 'ai';
			content: string;
			timestamp: string;
			isClarification?: boolean;
		}>;
		isLoading?: boolean;
	} = $props();

	// 초기 메시지 토글 상태
	let isExamplesExpanded = $state(false);

	// 초기 메시지 내용 분리
	function getInitialMessageContent() {
		if (messages.length === 0) return { intro: '', examples: '' };
		const firstMessage = messages[0];
		if (firstMessage.type === 'ai' && firstMessage.id === 1) {
			// "사용 예시:" 부분을 찾아서 분리
			const content = firstMessage.content;
			const examplesIndex = content.indexOf('**사용 예시:**');
			if (examplesIndex !== -1) {
				return {
					intro: content.substring(0, examplesIndex).trim(),
					examples: content.substring(examplesIndex).trim()
				};
			}
		}
		return { intro: firstMessage.content, examples: '' };
	}

	// 토글 버튼 클릭 핸들러
	function toggleExamples() {
		isExamplesExpanded = !isExamplesExpanded;
	}

	// 메시지 목록 컨테이너 참조 (스크롤은 부모에서 처리)
	let messageListContainer: HTMLDivElement;
	
	// 로딩 상태 변화 감지 (디버깅용)
	$effect(() => {
		console.log('🔄 MessageList isLoading 상태:', isLoading);
	});
</script>

<div class="message-list" bind:this={messageListContainer}>
	{#each messages as message, index (message.id)}
		<div class="message {message.type}">
			<div class="message-content">
				<div class="message-avatar">
					{#if message.type === 'ai'}
						<svg class="ai-icon" viewBox="0 0 24 24" fill="currentColor">
							<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
						</svg>
					{:else}
						<svg class="user-icon" viewBox="0 0 24 24" fill="currentColor">
							<path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
						</svg>
					{/if}
				</div>
				<div class="message-text">
					{#if message.type === 'ai' && message.id === 1 && index === 0}
						<!-- 초기 메시지 토글 버전 -->
						{@const messageContent = getInitialMessageContent()}
						<div class="initial-message">
							<div class="message-intro">
								<MarkdownRenderer content={messageContent.intro} />
							</div>
							{#if messageContent.examples}
								<div class="examples-toggle">
									<button 
										class="toggle-button" 
										onclick={toggleExamples}
										aria-expanded={isExamplesExpanded}
									>
										<span class="toggle-text">
											{isExamplesExpanded ? '사용 예시 숨기기' : '사용 예시 보기'}
										</span>
										<span class="toggle-icon" class:expanded={isExamplesExpanded}>
											<svg viewBox="0 0 24 24" fill="currentColor">
												<path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/>
											</svg>
										</span>
									</button>
								</div>
								{#if isExamplesExpanded}
									<div class="examples-content">
										<MarkdownRenderer content={messageContent.examples} />
									</div>
								{/if}
							{/if}
						</div>
					{:else}
						<!-- 일반 메시지 -->
						<MarkdownRenderer content={message.content} />
					{/if}
					<span class="message-time">{message.timestamp}</span>
				</div>
			</div>
		</div>
	{/each}
	
	{#if isLoading}
		<div class="message ai">
			<div class="message-content">
				<div class="message-avatar">
					<svg class="ai-icon" viewBox="0 0 24 24" fill="currentColor">
						<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
					</svg>
				</div>
				<div class="message-text">
					<div class="typing-indicator">
						<span></span>
						<span></span>
						<span></span>
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	.message-list {
		flex: 1; /* 부모 컨테이너의 남은 공간을 모두 차지 */
		overflow: visible; /* 스크롤은 부모 컨테이너에서 처리 */
		padding: 0; /* 패딩 제거 - 부모에서 처리 */
		background: transparent; /* 배경 제거 - 부모에서 처리 */
		border-radius: 0; /* 둥근 모서리 제거 */
		margin-bottom: 0; /* 마진 제거 */
		display: flex;
		flex-direction: column;
		min-height: 0; /* flex item이 축소될 수 있도록 */
	}

	.message {
		margin-bottom: 1rem;
		padding: 0.5rem 0;
		display: flex;
		width: 100%;
	}

	.message.user {
		justify-content: flex-end;
	}

	.message.ai {
		justify-content: flex-start;
	}

	.message-content {
		display: inline-flex;
		align-items: flex-start;
		gap: 0.75rem;
		max-width: 80%;
	}

	.message.user .message-content {
		flex-direction: row-reverse;
	}

	.message-avatar {
		font-size: 1.5rem;
		width: 2.5rem;
		height: 2.5rem;
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--maice-bg-card);
		border-radius: 50%;
		flex-shrink: 0;
		border: 1px solid var(--maice-border-primary);
	}

	.message-avatar .ai-icon,
	.message-avatar .user-icon {
		width: 1.25rem;
		height: 1.25rem;
		color: var(--maice-primary);
	}

	.message.user .message-avatar {
		background: var(--maice-primary);
		border-color: var(--maice-primary);
	}

	.message.user .message-avatar .user-icon {
		color: var(--maice-text-on-primary);
	}

	.message-text {
		background: var(--maice-bg-card);
		padding: 0.75rem 1rem;
		border-radius: 1rem;
		border: 1px solid var(--maice-border-primary);
	}

	.message.user .message-text {
		background: var(--maice-primary);
		color: #ffffff;
		border-color: var(--maice-primary);
	}

	/* 사용자 메시지 내부의 MarkdownRenderer 텍스트를 흰색으로 강제 */
	.message.user .message-text :global(.markdown-content) {
		color: #ffffff !important;
	}

	.message.user .message-text :global(.markdown-content p) {
		color: #ffffff !important;
	}

	.message.user .message-text :global(.markdown-content strong) {
		color: #ffffff !important;
	}

	.message.user .message-text :global(.markdown-content em) {
		color: #ffffff !important;
	}

	/* 사용자 메시지 내부의 마크다운 요소들은 실제로 사용되지 않으므로 제거 */

	/* 다크 모드일 때 사용자 메시지 스타일 - 라이트 모드와 동일하게 유지 */
	:global(.dark) .message.user .message-text {
		background: var(--maice-primary) !important;
		color: var(--maice-text-on-primary) !important;
		border-color: var(--maice-primary) !important;
	}

	:global(.dark) .message.user .message-text :global(.markdown-content) {
		color: var(--maice-text-on-primary) !important;
	}

	:global(.dark) .message.user .message-text :global(.markdown-content p) {
		color: var(--maice-text-on-primary) !important;
	}

	:global(.dark) .message.user .message-text :global(.markdown-content strong) {
		color: var(--maice-text-on-primary) !important;
	}

	:global(.dark) .message.user .message-text :global(.markdown-content em) {
		color: var(--maice-text-on-primary) !important;
	}

	.message-time {
		font-size: 0.75rem;
		color: var(--maice-text-muted);
		opacity: 0.7;
	}

	.message.user .message-time {
		color: rgba(255, 255, 255, 0.8);
	}

	/* 다크 모드에서 사용자 메시지 시간 스타일 */
	:global(.dark) .message.user .message-time {
		color: rgba(255, 255, 255, 0.8) !important;
	}

	/* 타이핑 인디케이터 */
	.typing-indicator {
		display: flex;
		gap: 0.25rem;
		align-items: center;
	}

	.typing-indicator span {
		width: 0.5rem;
		height: 0.5rem;
		background: var(--maice-text-secondary);
		border-radius: 50%;
		animation: typing 1.4s infinite ease-in-out;
	}

	.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
	.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

	@keyframes typing {
		0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
		40% { transform: scale(1); opacity: 1; }
	}

	/* 초기 메시지 토글 스타일 */
	.initial-message {
		width: 100%;
	}

	.message-intro {
		margin-bottom: 0.75rem;
	}

	.examples-toggle {
		margin: 0.75rem 0;
	}

	.toggle-button {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		background: var(--maice-bg-secondary);
		border: 1px solid var(--maice-border-primary);
		border-radius: 0.5rem;
		padding: 0.5rem 0.75rem;
		cursor: pointer;
		transition: all 0.2s ease;
		font-size: 0.875rem;
		color: var(--maice-text-primary);
		width: 100%;
		text-align: left;
	}

	.toggle-button:hover {
		background: var(--maice-bg-hover);
		border-color: var(--maice-primary);
	}

	.toggle-button:focus {
		outline: 2px solid var(--maice-primary);
		outline-offset: 2px;
	}

	.toggle-text {
		flex: 1;
		font-weight: 500;
	}

	.toggle-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		transition: transform 0.2s ease;
	}

	.toggle-icon svg {
		width: 1rem;
		height: 1rem;
		color: var(--maice-text-secondary);
	}

	.toggle-icon.expanded {
		transform: rotate(180deg);
	}

	.examples-content {
		margin-top: 0.75rem;
		padding: 0.75rem;
		background: var(--maice-bg-secondary);
		border: 1px solid var(--maice-border-primary);
		border-radius: 0.5rem;
		animation: slideDown 0.3s ease-out;
	}

	@keyframes slideDown {
		from {
			opacity: 0;
			transform: translateY(-10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	/* 다크 모드 토글 버튼 스타일 */
	:global(.dark) .toggle-button {
		background: var(--maice-bg-secondary-dark, #374151);
		border-color: var(--maice-border-dark, #4b5563);
		color: var(--maice-text-primary-dark, #f9fafb);
	}

	:global(.dark) .toggle-button:hover {
		background: var(--maice-bg-hover-dark, #4b5563);
		border-color: var(--maice-primary-dark, #60a5fa);
	}

	:global(.dark) .examples-content {
		background: var(--maice-bg-secondary-dark, #374151);
		border-color: var(--maice-border-dark, #4b5563);
	}

	/* 반응형 디자인 */
	@media (max-width: 768px) {
		.message-list {
			flex: 1; /* 모바일에서도 전체 높이 차지 */
		}
		
		.message-content {
			max-width: 90%;
		}
		
		.message-avatar {
			width: 2rem;
			height: 2rem;
			font-size: 1.2rem;
		}
		
		.message-avatar .ai-icon,
		.message-avatar .user-icon {
			width: 1rem;
			height: 1rem;
		}
		
		.message-text {
			padding: 0.6rem 0.8rem;
			font-size: 0.875rem; /* 14px - 모바일에서 글자 크기 줄임 */
		}
		
		/* 메시지 내부 마크다운 콘텐츠도 줄임 */
		.message-text :global(.markdown-content) {
			font-size: 0.875rem;
		}
		
		.message-text :global(.markdown-content p) {
			font-size: 0.875rem;
			line-height: 1.5;
		}
		
		.message-text :global(.markdown-content h1),
		.message-text :global(.markdown-content h2),
		.message-text :global(.markdown-content h3) {
			font-size: 1rem;
			margin-top: 0.75rem;
			margin-bottom: 0.5rem;
		}
		
		.message-text :global(.markdown-content code) {
			font-size: 0.8125rem;
		}
		
		.message-text :global(.markdown-content pre code) {
			font-size: 0.75rem;
		}
		
		.message-time {
			font-size: 0.65rem;
			margin-top: 0.25rem;
		}

		.toggle-button {
			padding: 0.6rem;
			font-size: 0.8125rem;
		}
		
		.toggle-text {
			font-size: 0.8125rem;
		}
	}
</style>
