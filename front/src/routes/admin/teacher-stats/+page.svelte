<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth';
	import Button from '$lib/components/common/Button.svelte';
	import Card from '$lib/components/common/Card.svelte';
	import { getTeacherEvaluationStats } from '$lib/api';
	
	$: authUser = $authStore.user;
	
	let token = '';
	let isLoading = false;
	let error: string | null = null;
	let stats: any = null;
	let targetGoal = 100;
	
	onMount(() => {
		const unsubscribe = authStore.subscribe(state => {
			if (!state.isAuthenticated || !state.user) {
				goto('/');
				return;
			}
			
			const userRole = state.user.role?.toLowerCase();
			if (userRole !== 'admin') {
				goto('/dashboard');
				return;
			}
			
			token = state.token || '';
			
			if (token) {
				loadStats();
			}
		});
		
		return unsubscribe;
	});
	
	async function loadStats() {
		if (!token) return;
		
		try {
			isLoading = true;
			error = null;
			stats = await getTeacherEvaluationStats(token);
		} catch (err: any) {
			console.error('통계 로드 실패:', err);
			error = err.message || '통계를 불러오는데 실패했습니다.';
		} finally {
			isLoading = false;
		}
	}
</script>

<svelte:head>
	<title>교사 채점 현황 | MAICE Admin</title>
</svelte:head>

<div class="teacher-stats-page">
	<div class="page-header">
		<div class="header-left">
			<h1>👩‍🏫 교사 채점 현황</h1>
			<p class="subtitle">각 교사의 세션 평가 진행 상황을 확인하세요</p>
		</div>
		<Button variant="secondary" onclick={() => goto('/dashboard')}>
			대시보드로
		</Button>
	</div>
	
	{#if isLoading}
		<div class="loading">로딩 중...</div>
	{:else if error}
		<Card className="error-card">
			<p>{error}</p>
			<Button onclick={loadStats}>다시 시도</Button>
		</Card>
	{:else if stats}
		<!-- 전체 요약 -->
		<Card className="summary-card">
			<div class="summary-header">
				<h2>📊 전체 진행 현황</h2>
			</div>
			<div class="summary-grid">
				<div class="summary-item">
					<span class="label">전체 세션</span>
					<span class="value total">{stats.total_sessions}</span>
				</div>
				<div class="summary-item">
					<span class="label">평가 완료</span>
					<span class="value completed">{stats.evaluated_sessions}</span>
				</div>
				<div class="summary-item">
					<span class="label">목표 (100개)</span>
					<span class="value target">{Math.min(stats.evaluated_sessions, targetGoal)} / {targetGoal}</span>
				</div>
			<div class="summary-item">
				<span class="label">달성률</span>
				<span class="value percent">{stats.achievement_rate || 0}%</span>
			</div>
			</div>
			
			<!-- 전체 진행 바 -->
			<div class="progress-section">
				<div class="progress-label">
					<span>연구 목표 진행률</span>
					<span class="progress-value">{Math.min(stats.evaluated_sessions, targetGoal)} / {targetGoal}개</span>
				</div>
			<div class="progress-bar-container">
				<div 
					class="progress-bar-fill" 
					style="width: {stats.achievement_rate || 0}%"
				></div>
			</div>
			</div>
		</Card>
		
		<!-- 교사별 통계 -->
		<div class="teachers-section">
			<h2>👨‍🏫 교사별 평가 현황</h2>
			
			{#if stats.teacher_stats && stats.teacher_stats.length > 0}
				<div class="teachers-grid">
					{#each stats.teacher_stats as teacher}
						<Card className="teacher-card">
							<div class="teacher-header">
								<div class="teacher-info">
									<div class="teacher-name">{teacher.teacher_username}</div>
									<div class="teacher-count">{teacher.evaluated_count}개 평가</div>
								</div>
								<div 
									class="teacher-badge"
									class:high={teacher.evaluated_count >= 50}
									class:medium={teacher.evaluated_count >= 20 && teacher.evaluated_count < 50}
									class:low={teacher.evaluated_count < 20}
								>
									{#if teacher.evaluated_count >= 50}
										🏆 우수
									{:else if teacher.evaluated_count >= 20}
										✨ 양호
									{:else}
										📝 진행중
									{/if}
								</div>
							</div>
							
							<div class="teacher-progress">
								<div class="progress-label-sm">
									<span>목표 대비 진행률</span>
									<span class="progress-percent">{teacher.progress_percent}%</span>
								</div>
								<div class="progress-bar-sm">
									<div 
										class="progress-fill-sm" 
										style="width: {Math.min(teacher.progress_percent, 100)}%"
										class:high={teacher.evaluated_count >= 50}
										class:medium={teacher.evaluated_count >= 20 && teacher.evaluated_count < 50}
										class:low={teacher.evaluated_count < 20}
									></div>
								</div>
							</div>
							
							<div class="teacher-stats-detail">
								<div class="stat-item-sm">
									<span class="icon">📝</span>
									<span>{teacher.evaluated_count}개 평가 완료</span>
								</div>
								<div class="stat-item-sm">
									<span class="icon">🎯</span>
									<span>남은 목표: {Math.max(100 - teacher.evaluated_count, 0)}개</span>
								</div>
							</div>
						</Card>
					{/each}
				</div>
			{:else}
				<Card className="empty-card">
					<p>아직 평가를 진행한 교사가 없습니다.</p>
				</Card>
			{/if}
		</div>
	{/if}
</div>

<style>
	.teacher-stats-page {
		padding: 2rem;
		max-width: 1400px;
		margin: 0 auto;
	}
	
	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 2rem;
	}
	
	.header-left h1 {
		margin: 0 0 0.5rem 0;
		font-size: 2rem;
		font-weight: 600;
		color: var(--maice-text);
	}
	
	.subtitle {
		margin: 0;
		color: var(--maice-text-muted);
		font-size: 0.9375rem;
	}
	
	/* 전체 요약 */
	.summary-card {
		margin-bottom: 2rem;
	}
	
	.summary-header h2 {
		margin: 0 0 1.5rem 0;
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--maice-text);
	}
	
	.summary-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 1.5rem;
		margin-bottom: 2rem;
	}
	
	.summary-item {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
		padding: 1.5rem;
		background: var(--maice-bg-secondary, #f9fafb);
		border-radius: 8px;
	}
	
	.summary-item .label {
		font-size: 0.875rem;
		color: var(--maice-text-muted);
	}
	
	.summary-item .value {
		font-size: 2rem;
		font-weight: 700;
	}
	
	.value.total {
		color: var(--maice-text);
	}
	
	.value.completed {
		color: var(--maice-success-text, #10b981);
	}
	
	.value.target {
		color: var(--maice-primary, #3b82f6);
	}
	
	.value.percent {
		color: var(--maice-secondary, #8b5cf6);
	}
	
	/* 진행 바 */
	.progress-section {
		padding-top: 1.5rem;
		border-top: 1px solid var(--maice-border);
	}
	
	.progress-label {
		display: flex;
		justify-content: space-between;
		margin-bottom: 0.75rem;
		font-weight: 600;
		color: var(--maice-text);
	}
	
	.progress-value {
		color: var(--maice-primary);
	}
	
	.progress-bar-container {
		width: 100%;
		height: 32px;
		background: var(--maice-bg-secondary, #f3f4f6);
		border-radius: 16px;
		overflow: hidden;
	}
	
	.progress-bar-fill {
		height: 100%;
		background: linear-gradient(90deg, 
			var(--maice-primary, #3b82f6), 
			var(--maice-secondary, #8b5cf6));
		transition: width 0.5s ease;
		box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
	}
	
	/* 교사 섹션 */
	.teachers-section {
		margin-top: 2rem;
	}
	
	.teachers-section h2 {
		margin: 0 0 1.5rem 0;
		font-size: 1.5rem;
		font-weight: 600;
		color: var(--maice-text);
	}
	
	.teachers-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
		gap: 1.5rem;
	}
	
	.teacher-card {
		transition: transform 0.2s;
	}
	
	.teacher-card:hover {
		transform: translateY(-2px);
	}
	
	.teacher-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.5rem;
		padding-bottom: 1rem;
		border-bottom: 1px solid var(--maice-border);
	}
	
	.teacher-name {
		font-size: 1.125rem;
		font-weight: 600;
		color: var(--maice-text);
	}
	
	.teacher-count {
		font-size: 0.875rem;
		color: var(--maice-text-muted);
	}
	
	.teacher-badge {
		padding: 0.375rem 0.75rem;
		border-radius: 12px;
		font-size: 0.875rem;
		font-weight: 600;
	}
	
	.teacher-badge.high {
		background: linear-gradient(135deg, #fef3c7, #fde68a);
		color: #92400e;
	}
	
	.teacher-badge.medium {
		background: var(--maice-success-bg, #ecfdf5);
		color: var(--maice-success-text, #059669);
	}
	
	.teacher-badge.low {
		background: var(--maice-bg-secondary, #f9fafb);
		color: var(--maice-text-muted);
	}
	
	.teacher-progress {
		margin-bottom: 1rem;
	}
	
	.progress-label-sm {
		display: flex;
		justify-content: space-between;
		margin-bottom: 0.5rem;
		font-size: 0.875rem;
		color: var(--maice-text-muted);
	}
	
	.progress-percent {
		font-weight: 600;
		color: var(--maice-primary);
	}
	
	.progress-bar-sm {
		width: 100%;
		height: 8px;
		background: var(--maice-bg-secondary, #f3f4f6);
		border-radius: 4px;
		overflow: hidden;
	}
	
	.progress-fill-sm {
		height: 100%;
		transition: width 0.5s ease;
	}
	
	.progress-fill-sm.high {
		background: linear-gradient(90deg, #f59e0b, #d97706);
	}
	
	.progress-fill-sm.medium {
		background: linear-gradient(90deg, #10b981, #059669);
	}
	
	.progress-fill-sm.low {
		background: linear-gradient(90deg, #6b7280, #4b5563);
	}
	
	.teacher-stats-detail {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
	
	.stat-item-sm {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.875rem;
		color: var(--maice-text);
	}
	
	.stat-item-sm .icon {
		font-size: 1.125rem;
	}
	
	.loading {
		padding: 3rem;
		text-align: center;
		color: var(--maice-text-muted);
	}
	
	.error-card,
	.empty-card {
		padding: 3rem 2rem;
		text-align: center;
	}
	
	.error-card p,
	.empty-card p {
		margin: 0 0 1rem 0;
		color: var(--maice-text-muted);
	}
	
	/* 반응형 */
	@media (max-width: 1200px) {
		.summary-grid {
			grid-template-columns: repeat(2, 1fr);
		}
	}
	
	@media (max-width: 768px) {
		.teacher-stats-page {
			padding: 1rem;
		}
		
		.summary-grid {
			grid-template-columns: 1fr;
		}
		
		.teachers-grid {
			grid-template-columns: 1fr;
		}
	}
</style>

