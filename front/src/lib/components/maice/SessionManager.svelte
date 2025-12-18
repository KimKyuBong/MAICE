<script lang="ts">
	import { onMount } from 'svelte';
	import { getMaiceSessions, deleteMaiceSession } from '$lib/api';
	import Button from '$lib/components/common/Button.svelte';
	import Card from '$lib/components/common/Card.svelte';

	interface Props {
		authToken: string;
		currentSessionId: number | null;
		onSessionSelect: (sessionId: number) => Promise<void>;
		onNewSession: () => void;
		refreshTrigger?: number;
	}

	const { authToken, currentSessionId, onSessionSelect, onNewSession, refreshTrigger = 0 }: Props = $props();

	let sessions = $state<any[]>([]);
	let isLoading = $state(false);
	let error = $state<string | null>(null);

	// 세션 목록 로드 (외부에서 호출 가능하도록 export)
	export async function loadSessions() {
		// 테스트 모드 확인
		const isTestMode = import.meta.env.DEV && window.location.search.includes('test=true');
		
		if (!authToken && !isTestMode) return;
		
		isLoading = true;
		error = null;
		
		try {
			console.log('🚀 세션 로드 시작:', { authToken: !!authToken, isTestMode });
			sessions = await getMaiceSessions(authToken || '');
			console.log('✅ 세션 로드 완료:', { count: sessions.length, sessions: sessions.slice(0, 3) });
		} catch (err) {
			error = '세션을 불러오는데 실패했습니다.';
			console.error('❌ 세션 로드 오류:', err);
		} finally {
			isLoading = false;
		}
	}

	// 새 세션 생성 (새 질문을 통해 자동 생성됨)
	async function handleCreateNewSession() {
		console.log('🆕 새 세션 버튼 클릭됨');
		console.log('📋 현재 상태:', {
			isLoading,
			authToken: !!authToken,
			currentSessionId,
			onNewSession: typeof onNewSession
		});
		onNewSession();
		console.log('✅ onNewSession 호출 완료');
	}

	// 세션 삭제
	async function handleDeleteSession(sessionId: number, event: Event) {
		event.stopPropagation();
		
		// 테스트 모드 확인
		const isTestMode = import.meta.env.DEV && window.location.search.includes('test=true');
		
		if (!authToken && !isTestMode || !confirm('이 세션을 삭제하시겠습니까?')) return;
		
		try {
			await deleteMaiceSession(sessionId, authToken || '');
			await loadSessions(); // 세션 목록 새로고침
		} catch (err) {
			error = '세션 삭제에 실패했습니다.';
			console.error('세션 삭제 오류:', err);
		}
	}

	// 세션 선택
	function handleSessionSelect(sessionId: number) {
		onSessionSelect(sessionId);
	}

	onMount(() => {
		loadSessions();
	});

	// authToken이 변경될 때마다 세션 목록 새로고침
	$effect(() => {
		if (authToken) {
			loadSessions();
		}
	});

	// refreshTrigger가 변경될 때마다 세션 목록 새로고침
	$effect(() => {
		if (refreshTrigger > 0) {
			console.log('🔄 세션 목록 새로고침 트리거 감지:', refreshTrigger);
			loadSessions();
		}
	});
</script>

<div class="session-manager">
	<div class="session-header">
		<h3>💬 세션 관리</h3>
		<Button 
			variant="secondary" 
			size="sm" 
			onclick={handleCreateNewSession}
			disabled={isLoading}
		>
			➕ 새 세션
		</Button>
	</div>

	{#if error}
		<div class="session-error">
			⚠️ {error}
		</div>
	{/if}

	{#if isLoading}
		<div class="session-loading">
			⏳ 세션을 불러오는 중...
		</div>
	{:else if sessions.length === 0}
		<div class="session-empty">
			📝 세션이 없습니다.
		</div>
	{:else}
		<div class="session-list">
			{#each sessions as session}
				<div 
					class="session-item {currentSessionId === session.id ? 'active' : ''}" 
					role="button"
					tabindex="0"
					onclick={() => handleSessionSelect(session.id)}
					onkeydown={(e) => e.key === 'Enter' && handleSessionSelect(session.id)}
				>
					<div class="session-info">
						<div class="session-header">
							<div class="session-title">
								{session.title || `세션 ${session.id}`}
							</div>
							<div class="session-id">#{session.id}</div>
						</div>
						<div class="session-meta">
							{#if session.created_at}
								<span class="session-date">
									{new Date(session.created_at).toLocaleDateString('ko-KR', { 
										month: 'short', 
										day: 'numeric',
										hour: '2-digit',
										minute: '2-digit'
									})}
								</span>
							{/if}
							<span class="message-count">{session.message_count || 0}개 메시지</span>
						</div>
					</div>
					<Button 
						variant="ghost" 
						size="sm" 
						onclick={(e: Event) => handleDeleteSession(session.id, e)}
					>
						🗑️
					</Button>
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.session-manager {
		width: 100%;
		height: 100%;
		display: flex;
		flex-direction: column;
	}

	.session-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem;
		border-bottom: 1px solid var(--maice-border-secondary);
	}

	.session-header h3 {
		margin: 0;
		font-size: 1.125rem;
		font-weight: 600;
		color: var(--maice-text-primary);
	}

	.session-error {
		padding: 1rem;
		color: #ef4444;
		background: #fef2f2;
		border: 1px solid #fecaca;
		border-radius: 0.5rem;
		margin: 1rem;
		font-size: 0.875rem;
	}

	.session-loading,
	.session-empty {
		padding: 2rem 1rem;
		text-align: center;
		color: var(--maice-text-secondary);
		font-size: 0.875rem;
	}

	.session-list {
		flex: 1;
		overflow-y: auto;
		padding: 0.5rem;
	}

	.session-item {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.75rem;
		margin-bottom: 0.5rem;
		background: var(--maice-bg-secondary);
		border: 1px solid var(--maice-border-secondary);
		border-radius: 0.5rem;
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.session-item:hover {
		background: var(--maice-bg-hover);
		border-color: var(--maice-border-hover);
	}

	.session-item.active {
		background: var(--maice-bg-primary);
		border-color: var(--maice-accent-primary);
		box-shadow: 0 0 0 1px var(--maice-accent-primary);
	}

	.session-info {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.session-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 0.75rem;
	}

	.session-title {
		font-weight: 600;
		color: var(--maice-text-primary);
		font-size: 0.9rem;
		line-height: 1.3;
		flex: 1;
		min-width: 0;
		/* 여러 줄 표시 허용 */
		white-space: normal;
		overflow: hidden;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
	}

	.session-id {
		font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
		font-size: 0.7rem;
		color: var(--maice-accent-primary);
		background: var(--maice-bg-tertiary);
		padding: 2px 6px;
		border-radius: 4px;
		font-weight: 600;
		flex-shrink: 0;
	}

	.session-meta {
		display: flex;
		justify-content: space-between;
		align-items: center;
		font-size: 0.7rem;
		color: var(--maice-text-secondary);
		gap: 0.5rem;
	}

	.session-date {
		font-size: 0.7rem;
		font-weight: 500;
	}

	.message-count {
		font-size: 0.7rem;
		color: var(--maice-text-tertiary);
		background: var(--maice-bg-tertiary);
		padding: 2px 6px;
		border-radius: 4px;
	}

</style>
