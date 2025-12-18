<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth';
	import { 
		getAgentsStatus, 
		getMetricsSummary, 
		getDetailedHealth
	} from '$lib/api';
	import Button from '$lib/components/common/Button.svelte';
	import Card from '$lib/components/common/Card.svelte';
	import WorkflowVisualization from '$lib/components/monitoring/WorkflowVisualization.svelte';
	
	let agentsStatus: any = null;
	let metricsSummary: any = null;
	let healthStatus: any = null;
	let isLoading = true;
	let error: string | null = null;
	let token: string = '';
	
	// 자동 새로고침 인터벌
	let refreshInterval: number;
	const REFRESH_INTERVAL = 10000; // 10초
	
	onMount(() => {
		// 인증 확인
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
			
			// 초기 데이터 로드 (비동기)
			if (token) {
				loadAllData();
			}
		});
		
		// 자동 새로고침 시작
		refreshInterval = setInterval(loadAllData, REFRESH_INTERVAL);
		
		return () => {
			unsubscribe();
			if (refreshInterval) {
				clearInterval(refreshInterval);
			}
		};
	});
	
	async function loadAllData() {
		if (!token) return;
		
		try {
			isLoading = true;
			error = null;
			
			// 병렬로 모든 데이터 로드
			const [agentsRes, summaryRes, healthRes] = await Promise.all([
				getAgentsStatus(token),
				getMetricsSummary(token),
				getDetailedHealth(token)
			]);
			
			agentsStatus = agentsRes;
			metricsSummary = summaryRes;
			healthStatus = healthRes;
			
		} catch (err: any) {
			error = err.message || '데이터를 불러올 수 없습니다.';
			console.error('모니터링 데이터 로드 실패:', err);
		} finally {
			isLoading = false;
		}
	}
	
	function formatTimestamp(timestamp: number): string {
		return new Date(timestamp * 1000).toLocaleString('ko-KR');
	}
	
	function formatDuration(seconds: number): string {
		if (seconds < 1) {
			return `${(seconds * 1000).toFixed(0)}ms`;
		}
		return `${seconds.toFixed(2)}s`;
	}
	
	function getStatusColor(status: string): string {
		switch (status) {
			case 'healthy':
				return 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30';
			case 'degraded':
				return 'text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900/30';
			case 'unhealthy':
				return 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30';
			default:
				return 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-900/30';
		}
	}
</script>

<svelte:head>
	<title>실시간 모니터링 - MAICE</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 dark:bg-gray-900">
	<!-- 헤더 -->
	<header class="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
			<div class="flex justify-between items-center h-16">
				<div class="flex items-center space-x-4">
					<Button variant="ghost" onclick={() => goto('/dashboard')}>
						← 대시보드
					</Button>
					<h1 class="text-2xl font-bold text-gray-900 dark:text-white">실시간 모니터링</h1>
					{#if !isLoading}
						<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
							● Live
						</span>
					{/if}
				</div>
				<div class="flex items-center space-x-4">
					<span class="text-sm text-gray-500 dark:text-gray-400">
						{#if metricsSummary}
							마지막 업데이트: {new Date(metricsSummary.timestamp).toLocaleTimeString('ko-KR')}
						{/if}
					</span>
					<Button variant="primary" onclick={loadAllData} disabled={isLoading}>
						{isLoading ? '새로고침 중...' : '새로고침'}
					</Button>
				</div>
			</div>
		</div>
	</header>

	<!-- 메인 콘텐츠 -->
	<main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
		{#if error}
			<div class="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
				<p class="text-red-800 dark:text-red-200">{error}</p>
			</div>
		{/if}

		<!-- 전체 상태 요약 -->
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
			<!-- 전체 요청 수 -->
			<Card variant="elevated">
				<div class="p-6">
					<div class="flex items-center">
						<div class="flex-shrink-0">
							<div class="w-12 h-12 bg-blue-500 rounded-lg flex items-center justify-center">
								<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
								</svg>
							</div>
						</div>
						<div class="ml-4">
							<p class="text-sm font-medium text-gray-500 dark:text-gray-400">전체 요청</p>
							<p class="text-2xl font-semibold text-gray-900 dark:text-white">
								{metricsSummary?.system?.total_requests || 0}
							</p>
						</div>
					</div>
				</div>
			</Card>

			<!-- 평균 응답 시간 -->
			<Card variant="elevated">
				<div class="p-6">
					<div class="flex items-center">
						<div class="flex-shrink-0">
							<div class="w-12 h-12 bg-green-500 rounded-lg flex items-center justify-center">
								<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
								</svg>
							</div>
						</div>
						<div class="ml-4">
							<p class="text-sm font-medium text-gray-500 dark:text-gray-400">평균 응답 시간</p>
							<p class="text-2xl font-semibold text-gray-900 dark:text-white">
								{formatDuration(metricsSummary?.system?.avg_response_time || 0)}
							</p>
						</div>
					</div>
				</div>
			</Card>

			<!-- 에러율 -->
			<Card variant="elevated">
				<div class="p-6">
					<div class="flex items-center">
						<div class="flex-shrink-0">
							<div class="w-12 h-12 {metricsSummary?.system?.error_rate > 5 ? 'bg-red-500' : 'bg-yellow-500'} rounded-lg flex items-center justify-center">
								<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
								</svg>
							</div>
						</div>
						<div class="ml-4">
							<p class="text-sm font-medium text-gray-500 dark:text-gray-400">에러율</p>
							<p class="text-2xl font-semibold text-gray-900 dark:text-white">
								{(metricsSummary?.system?.error_rate || 0).toFixed(2)}%
							</p>
						</div>
					</div>
				</div>
			</Card>

			<!-- 활성 에이전트 -->
			<Card variant="elevated">
				<div class="p-6">
					<div class="flex items-center">
						<div class="flex-shrink-0">
							<div class="w-12 h-12 bg-purple-500 rounded-lg flex items-center justify-center">
								<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"/>
								</svg>
							</div>
						</div>
						<div class="ml-4">
							<p class="text-sm font-medium text-gray-500 dark:text-gray-400">활성 에이전트</p>
							<p class="text-2xl font-semibold text-gray-900 dark:text-white">
								{agentsStatus?.active_agents || 0}/{agentsStatus?.total_agents || 0}
							</p>
						</div>
					</div>
				</div>
			</Card>
		</div>

		<!-- 워크플로우 시각화 -->
		<div class="mb-8">
			<WorkflowVisualization agentMetrics={metricsSummary} />
		</div>

		<!-- 에이전트 상태 -->
		<Card variant="elevated" className="mb-8">
			<div class="p-6">
				<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">에이전트 상태</h3>
				<div class="space-y-4">
					{#if agentsStatus?.agents}
						{#each agentsStatus.agents as agent}
							<div class="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
								<div class="flex items-center space-x-4">
									<div class="flex-shrink-0">
										<div class="w-3 h-3 rounded-full {agent.is_alive ? 'bg-green-500' : 'bg-red-500'}"></div>
									</div>
									<div>
										<p class="font-medium text-gray-900 dark:text-white">{agent.agent_name}</p>
										<p class="text-sm text-gray-500 dark:text-gray-400">
											마지막 업데이트: {formatTimestamp(agent.last_update)}
										</p>
									</div>
								</div>
								<div class="flex items-center space-x-4">
									<span class="text-sm text-gray-500 dark:text-gray-400">
										메트릭: {agent.metrics_count}개
									</span>
									<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {agent.is_alive ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'}">
										{agent.is_alive ? '정상' : '중지됨'}
									</span>
								</div>
							</div>
						{/each}
					{:else}
						<p class="text-center text-gray-500 dark:text-gray-400">에이전트 정보를 불러오는 중...</p>
					{/if}
				</div>
			</div>
		</Card>

		<!-- 에이전트별 성능 메트릭 -->
		<Card variant="elevated" className="mb-8">
			<div class="p-6">
				<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">에이전트별 성능</h3>
				<div class="overflow-x-auto">
					<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
						<thead class="bg-gray-50 dark:bg-gray-800">
							<tr>
								<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">에이전트</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">요청 수</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">에러 수</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">에러율</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">평균 응답 시간</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">활성 세션</th>
							</tr>
						</thead>
						<tbody class="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
							{#if metricsSummary?.agents}
								{#each metricsSummary.agents as agent}
									<tr>
										<td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">{agent.name}</td>
										<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">{agent.requests}</td>
										<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">{agent.errors}</td>
										<td class="px-6 py-4 whitespace-nowrap">
											<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {agent.error_rate > 5 ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400' : 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'}">
												{agent.error_rate.toFixed(2)}%
											</span>
										</td>
										<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
											{formatDuration(agent.avg_response_time)}
										</td>
										<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">{agent.active_sessions}</td>
									</tr>
								{/each}
							{:else}
								<tr>
									<td colspan="6" class="px-6 py-4 text-center text-sm text-gray-500 dark:text-gray-400">
										메트릭 정보를 불러오는 중...
									</td>
								</tr>
							{/if}
						</tbody>
					</table>
				</div>
			</div>
		</Card>

		<!-- 시스템 헬스 -->
		<Card variant="elevated">
			<div class="p-6">
				<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">시스템 헬스</h3>
				<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
					<!-- API 서버 -->
					<div class="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
						<div class="flex items-center justify-between mb-2">
							<p class="font-medium text-gray-900 dark:text-white">API 서버</p>
							<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {getStatusColor(healthStatus?.components?.api?.status || 'unknown')}">
								{healthStatus?.components?.api?.status || 'unknown'}
							</span>
						</div>
					</div>

					<!-- 데이터베이스 -->
					<div class="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
						<div class="flex items-center justify-between mb-2">
							<p class="font-medium text-gray-900 dark:text-white">데이터베이스</p>
							<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {getStatusColor(healthStatus?.components?.database?.status || 'unknown')}">
								{healthStatus?.components?.database?.status || 'unknown'}
							</span>
						</div>
					</div>

					<!-- Redis -->
					<div class="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
						<div class="flex items-center justify-between mb-2">
							<p class="font-medium text-gray-900 dark:text-white">Redis</p>
							<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {getStatusColor(healthStatus?.components?.redis?.status || 'unknown')}">
								{healthStatus?.components?.redis?.status || 'unknown'}
							</span>
						</div>
						{#if healthStatus?.components?.redis?.memory_used}
							<p class="text-sm text-gray-500 dark:text-gray-400">
								메모리: {healthStatus.components.redis.memory_used}
							</p>
						{/if}
					</div>
				</div>
			</div>
		</Card>
	</main>
</div>

