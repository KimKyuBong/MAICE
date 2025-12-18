<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { authStore, authActions } from '$lib/stores/auth';
	import { getMaiceSessions, getAdminDashboardStats, getSystemStatus, healthCheck } from '$lib/api';
	import Button from '$lib/components/common/Button.svelte';
	import Card from '$lib/components/common/Card.svelte';
	import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
	
	let user: any = null;
	let token: string = '';
	let isLoading = true;
	
	// 학생용 데이터
	let sessions: any[] = [];
	let totalQuestions = 0;
	let totalSessions = 0;
	let recentSessions: any[] = [];
	
	// 관리자용 데이터
	let adminStats: any = null;
	let systemStatus: any = null;
	let healthStatus: any = null;
	let error: string | null = null;
	let refreshInterval: ReturnType<typeof setInterval> | undefined = undefined;
	
	onMount(() => {
		// 인증 상태 확인
		const unsubscribe = authStore.subscribe(state => {
			console.log('🔍 대시보드 - authStore 상태:', {
				isAuthenticated: state.isAuthenticated,
				hasUser: !!state.user,
				hasToken: !!state.token,
				userRole: state.user?.role
			});
			
			if (!state.isAuthenticated || !state.user) {
				console.log('❌ 대시보드 - 인증되지 않음, 로그인 페이지로 이동');
				goto('/');
				return;
			}
			
			user = state.user;
			token = state.token || '';
			
			console.log('✅ 대시보드 - 사용자 정보 설정 완료, 데이터 로드 시작');
			// 역할별 데이터 로드 (비동기이지만 별도 실행)
			loadDashboardData();
		});
		
		return unsubscribe;
	});
	
	async function loadDashboardData() {
		console.log('📊 loadDashboardData 시작:', { 
			hasToken: !!token, 
			hasUser: !!user,
			userRole: user?.role 
		});
		
		if (!token || !user) {
			console.log('❌ 토큰 또는 사용자 정보 없음');
			isLoading = false;
			return;
		}
		
		try {
			isLoading = true;
			console.log('⏳ 데이터 로딩 시작...');
			
			if (user.role?.toLowerCase() === 'admin') {
				console.log('👨‍💼 관리자 시스템 상태 로드 중...');
				// 관리자 시스템 상태 및 통계 로드
				const [statusResult, healthResult, statsResult] = await Promise.all([
					getSystemStatus(),  // 토큰 자동 조회
					healthCheck(),
					getAdminDashboardStats(token)  // 이 함수는 명시적으로 필요
				]);
				
				systemStatus = statusResult;
				healthStatus = healthResult;
				adminStats = statsResult;
				
				console.log('✅ 관리자 데이터 로드 완료:', { systemStatus, healthStatus, adminStats });
				
				// 자동 새로고침 설정 (30초마다)
				refreshInterval = setInterval(async () => {
					try {
						const [statusResult, healthResult] = await Promise.all([
							getSystemStatus(),  // 토큰 자동 조회
							healthCheck()
						]);
						systemStatus = statusResult;
						healthStatus = healthResult;
					} catch (err) {
						console.error('자동 새로고침 실패:', err);
					}
				}, 30000);
			} else if (user.role?.toLowerCase() === 'student') {
				console.log('👨‍🎓 학생 세션 로드 중...');
				// 학생 세션 로드
				const sessionsData = await getMaiceSessions(token);
				console.log('📝 세션 데이터:', sessionsData);
				
				sessions = sessionsData || [];
				totalSessions = sessions.length;
				
				// 총 질문 수 계산
				totalQuestions = sessions.reduce((sum: number, session: any) => {
					return sum + (session.messages?.length || 0);
				}, 0);
				
				// 최근 3개 세션
				recentSessions = sessions
					.sort((a: any, b: any) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
					.slice(0, 3);
				
				console.log('✅ 학생 데이터 로드 완료:', {
					totalSessions,
					totalQuestions,
					recentSessionsCount: recentSessions.length
				});
			} else {
				console.log('👨‍🏫 교사 역할 - 데이터 로드 없음');
			}
		} catch (error: any) {
			console.error('❌ 대시보드 데이터 로드 실패:', error);
			console.error('에러 상세:', {
				message: error.message,
				stack: error.stack,
				response: error.response
			});
		} finally {
			isLoading = false;
			console.log('✅ 로딩 완료, isLoading =', isLoading);
		}
	}
	
	async function handleLogout() {
		await authActions.logout();
		goto('/');
	}
	
	function navigateToMAICE() {
		if (!user) return;
		goto('/maice');
	}
	
	async function refreshStatus() {
		if (user?.role?.toLowerCase() === 'admin') {
			try {
				isLoading = true;
				error = null;
				
				const [statusResult, healthResult] = await Promise.all([
					getSystemStatus(),  // 토큰 자동 조회
					healthCheck()
				]);
				
				systemStatus = statusResult;
				healthStatus = healthResult;
			} catch (err: any) {
				error = err.message || '시스템 상태를 불러올 수 없습니다.';
			} finally {
				isLoading = false;
			}
		}
	}
	
	onDestroy(() => {
		if (refreshInterval) {
			clearInterval(refreshInterval);
		}
	});
	
	function formatDate(dateString: string) {
		return new Date(dateString).toLocaleDateString('ko-KR', {
			year: 'numeric',
			month: 'long',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}
	
	function getRoleText(role: string) {
		switch (role) {
			case 'admin': return '관리자';
			case 'teacher': return '교사';
			case 'student': return '학생';
			default: return role;
		}
	}
</script>

<svelte:head>
	<title>대시보드 - MAICE</title>
</svelte:head>

<div class="min-h-screen bg-maice-bg text-maice-primary transition-colors duration-300">
	<!-- 헤더 -->
	<header class="bg-maice-card shadow-maice-sm border-b border-maice-border-primary">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
			<div class="flex justify-between items-center h-16">
			<div class="flex items-center gap-4">
				<h1 class="text-2xl font-bold text-maice-primary">MAICE 대시보드</h1>
				{#if user?.role?.toLowerCase() === 'admin'}
					<Button variant="primary" size="sm" onclick={() => goto('/admin/users')}>
						사용자 관리
					</Button>
				<Button variant="secondary" size="sm" onclick={() => goto('/teacher')}>
					교사 채점
				</Button>
				<Button variant="secondary" size="sm" onclick={() => goto('/teacher/rubric-evaluation')}>
					루브릭 평가
				</Button>
				<Button variant="secondary" size="sm" onclick={() => goto('/admin/teacher-stats')}>
					교사 채점 현황
				</Button>
		{:else if user?.role?.toLowerCase() === 'teacher'}
				<Button variant="primary" size="sm" onclick={() => goto('/teacher')}>
					교사 채점
				</Button>
				<Button variant="secondary" size="sm" onclick={() => goto('/teacher/rubric-evaluation')}>
					루브릭 평가
				</Button>
			{/if}
			</div>
				<div class="flex items-center space-x-4">
					<ThemeToggle />
					<span class="text-sm text-maice-text-secondary">
						안녕하세요, <span class="font-medium text-maice-primary">{user?.username}</span>님
					</span>
					<Button variant="ghost" onclick={handleLogout}>
						로그아웃
					</Button>
				</div>
			</div>
		</div>
	</header>

	<!-- 메인 콘텐츠 -->
	<main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
		<div class="px-4 py-6 sm:px-0">
			<!-- 환영 메시지 -->
			<div class="mb-8">
				<h2 class="text-3xl font-bold text-maice-primary mb-2">
					{getRoleText(user?.role)}님, 환영합니다!
				</h2>
				<p class="text-lg text-maice-text-secondary">
					MAICE 시스템을 통해 학습을 시작하거나 시스템을 관리할 수 있습니다.
				</p>
			</div>

			<!-- 사용자 정보 카드 -->
			<Card className="mb-8">
				<div class="p-6">
					<h3 class="text-lg font-medium text-maice-primary mb-4">사용자 정보</h3>
					<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
						<div>
							<p class="text-sm font-medium text-maice-text-muted">아이디</p>
							<p class="text-lg text-maice-primary">{user?.username}</p>
						</div>
						<div>
							<p class="text-sm font-medium text-maice-text-muted">역할</p>
							<p class="text-lg text-maice-primary">
								{getRoleText(user?.role)}
							</p>
						</div>
						<div>
							<p class="text-sm font-medium text-maice-text-muted">사용자 ID</p>
							<p class="text-lg text-maice-primary">{user?.id}</p>
						</div>
					</div>
				</div>
			</Card>

			{#if isLoading}
				<!-- 로딩 상태 -->
				<div class="flex justify-center items-center py-12">
					<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
				</div>
			{:else if user?.role?.toLowerCase() === 'admin'}
				<!-- 관리자 시스템 모니터링 대시보드 -->
				<div class="space-y-6">
					<!-- 페이지 제목과 새로고침 버튼 -->
					<div class="flex justify-between items-center">
						<h2 class="text-2xl font-bold text-maice-primary">시스템 모니터링</h2>
						<Button variant="primary" onclick={refreshStatus} disabled={isLoading}>
							{isLoading ? '새로고침 중...' : '새로고침'}
						</Button>
					</div>

					{#if error}
						<div class="p-4 bg-red-50 border border-red-200 rounded-lg">
							<p class="text-red-800">{error}</p>
						</div>
					{/if}

					<!-- 시스템 상태 카드들 -->
					<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
						<!-- 전체 사용자 수 -->
						<Card variant="elevated">
							<div class="p-6">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class="w-12 h-12 bg-blue-500 rounded-lg flex items-center justify-center">
											<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z"></path>
											</svg>
										</div>
									</div>
									<div class="ml-4">
										<p class="text-sm font-medium text-maice-text-muted">전체 사용자</p>
										<p class="text-2xl font-semibold text-maice-primary">
											{systemStatus?.total_users || 0}
										</p>
									</div>
								</div>
							</div>
						</Card>

						<!-- 활성 세션 수 -->
						<Card variant="elevated">
							<div class="p-6">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class="w-12 h-12 bg-green-500 rounded-lg flex items-center justify-center">
											<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
											</svg>
										</div>
									</div>
									<div class="ml-4">
										<p class="text-sm font-medium text-maice-text-muted">활성 세션</p>
										<p class="text-2xl font-semibold text-maice-primary">
											{systemStatus?.active_sessions || 0}
										</p>
									</div>
								</div>
							</div>
						</Card>

						<!-- 오늘 질문 수 -->
						<Card variant="elevated">
							<div class="p-6">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class="w-12 h-12 bg-purple-500 rounded-lg flex items-center justify-center">
											<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
											</svg>
										</div>
									</div>
									<div class="ml-4">
										<p class="text-sm font-medium text-maice-text-muted">오늘 질문</p>
										<p class="text-2xl font-semibold text-maice-primary">
											{systemStatus?.questions_today || 0}
										</p>
									</div>
								</div>
							</div>
						</Card>
					</div>

					<!-- 시스템 상태 상세 정보 -->
					<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
						<!-- 백엔드 상태 -->
						<Card variant="elevated">
							<div class="p-6">
								<h3 class="text-lg font-medium text-maice-primary mb-4">백엔드 상태</h3>
								<div class="space-y-3">
									<div class="flex justify-between items-center">
										<span class="text-sm text-maice-text-secondary">API 서버</span>
										<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {healthStatus?.api_status === 'healthy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
											{healthStatus?.api_status === 'healthy' ? '정상' : '오류'}
										</span>
									</div>
									<div class="flex justify-between items-center">
										<span class="text-sm text-maice-text-secondary">데이터베이스</span>
										<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {healthStatus?.database_status === 'healthy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
											{healthStatus?.database_status === 'healthy' ? '정상' : '오류'}
										</span>
									</div>
									<div class="flex justify-between items-center">
										<span class="text-sm text-maice-text-secondary">Redis</span>
										<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {healthStatus?.redis_status === 'healthy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
											{healthStatus?.redis_status === 'healthy' ? '정상' : '오류'}
										</span>
									</div>
								</div>
							</div>
						</Card>

						<!-- MAICE 에이전트 상태 -->
						<Card variant="elevated">
							<div class="p-6">
								<h3 class="text-lg font-medium text-maice-primary mb-4">MAICE 에이전트 상태</h3>
								<div class="space-y-3">
									<div class="flex justify-between items-center">
										<span class="text-sm text-maice-text-secondary">에이전트 시스템</span>
										<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {systemStatus?.agent_status === 'running' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
											{systemStatus?.agent_status === 'running' ? '실행 중' : '중지됨'}
										</span>
									</div>
									<div class="flex justify-between items-center">
										<span class="text-sm text-maice-text-secondary">응답 시간</span>
										<span class="text-sm text-maice-primary">
											{systemStatus?.avg_response_time || 0}ms
										</span>
									</div>
									<div class="flex justify-between items-center">
										<span class="text-sm text-maice-text-secondary">성공률</span>
										<span class="text-sm text-maice-primary">
											{systemStatus?.success_rate || 0}%
										</span>
									</div>
									
									{#if systemStatus?.agents && systemStatus.agents.length > 0}
										<div class="mt-4 pt-3 border-t border-maice-border-primary">
											<h4 class="text-xs font-semibold text-maice-text-muted uppercase mb-2">에이전트별 처리량</h4>
											<div class="space-y-2">
												{#each systemStatus.agents as agent}
													<div class="flex justify-between items-center text-xs">
														<span class="text-maice-text-secondary">{agent.name.replace('Agent', '')}</span>
														<div class="flex items-center gap-2">
															<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {agent.status === 'running' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'}">
																{agent.status === 'running' ? '실행중' : '대기중'}
															</span>
															<span class="text-maice-text-muted">처리: {agent.processed_messages || 0}</span>
														</div>
													</div>
												{/each}
											</div>
										</div>
									{/if}
								</div>
							</div>
						</Card>
					</div>

					<!-- 최근 활동 로그 -->
					<Card variant="elevated">
						<div class="p-6">
							<h3 class="text-lg font-medium text-maice-primary mb-4">최근 활동</h3>
							<div class="overflow-hidden">
								<table class="min-w-full divide-y divide-maice-border-primary">
									<thead class="bg-maice-bg-secondary">
										<tr>
											<th class="px-6 py-3 text-left text-xs font-medium text-maice-text-muted uppercase tracking-wider">시간</th>
											<th class="px-6 py-3 text-left text-xs font-medium text-maice-text-muted uppercase tracking-wider">사용자</th>
											<th class="px-6 py-3 text-left text-xs font-medium text-maice-text-muted uppercase tracking-wider">활동</th>
											<th class="px-6 py-3 text-left text-xs font-medium text-maice-text-muted uppercase tracking-wider">상태</th>
										</tr>
									</thead>
									<tbody class="bg-maice-card divide-y divide-maice-border-primary">
										{#if systemStatus?.recent_activities && systemStatus.recent_activities.length > 0}
											{#each systemStatus.recent_activities as activity}
												<tr>
													<td class="px-6 py-4 whitespace-nowrap text-sm text-maice-primary">
														{activity.time}
													</td>
													<td class="px-6 py-4 whitespace-nowrap text-sm text-maice-primary">
														{activity.user}
													</td>
													<td class="px-6 py-4 whitespace-nowrap text-sm text-maice-text-secondary">
														{activity.action}
													</td>
													<td class="px-6 py-4 whitespace-nowrap">
														<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
															{activity.status}
														</span>
													</td>
												</tr>
											{/each}
										{:else}
											<tr>
												<td colspan="4" class="px-6 py-8 text-center text-sm text-maice-text-muted">
													최근 활동이 없습니다
												</td>
											</tr>
										{/if}
									</tbody>
								</table>
							</div>
						</div>
					</Card>

					<!-- 관리 메뉴 -->
					<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
						<div 
							role="button" 
							tabindex="0" 
							class="cursor-pointer" 
							onclick={() => goto('/admin/monitoring')}
							onkeydown={(e) => e.key === 'Enter' && goto('/admin/monitoring')}
						>
							<Card variant="elevated" className="p-6 hover:shadow-maice-md transition-shadow">
								<h3 class="text-lg font-medium text-maice-primary mb-2">상세 모니터링</h3>
								<p class="text-sm text-maice-text-secondary">에이전트 성능 및 메트릭 상세 분석</p>
							</Card>
						</div>
						
						<div 
							role="button" 
							tabindex="0" 
							class="cursor-pointer" 
							onclick={() => goto('/maice')}
							onkeydown={(e) => e.key === 'Enter' && goto('/maice')}
						>
							<Card variant="elevated" className="p-6 hover:shadow-maice-md transition-shadow">
								<h3 class="text-lg font-medium text-maice-primary mb-2">MAICE 테스트</h3>
								<p class="text-sm text-maice-text-secondary">AI 학습 도우미 기능 테스트</p>
							</Card>
						</div>
					</div>
				</div>
			{:else if user?.role?.toLowerCase() === 'teacher'}
				<!-- 교사 대시보드 -->
				<div class="space-y-8">
					<div class="text-center py-12">
						<h3 class="text-xl font-semibold text-maice-primary mb-4">교사 대시보드</h3>
						<p class="text-maice-text-secondary mb-6">학생 질문 평가 및 피드백 기능이 곧 제공될 예정입니다.</p>
						<Button variant="primary" onclick={navigateToMAICE}>
							MAICE 시작하기
						</Button>
					</div>
				</div>
			{:else if user?.role?.toLowerCase() === 'student'}
				<!-- 학생 대시보드 -->
				<div class="space-y-8">
					<!-- 통계 카드 -->
					<div>
						<h3 class="text-xl font-semibold text-maice-primary mb-4">나의 학습 현황</h3>
						<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
							<Card className="p-6">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class="w-12 h-12 bg-blue-500 rounded-lg flex items-center justify-center">
											<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
											</svg>
										</div>
									</div>
									<div class="ml-4">
										<p class="text-sm font-medium text-maice-text-muted">총 질문</p>
										<p class="text-2xl font-semibold text-maice-primary">
											{totalQuestions}
										</p>
									</div>
								</div>
							</Card>

							<Card className="p-6">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class="w-12 h-12 bg-purple-500 rounded-lg flex items-center justify-center">
											<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"></path>
											</svg>
										</div>
									</div>
									<div class="ml-4">
										<p class="text-sm font-medium text-maice-text-muted">총 세션</p>
										<p class="text-2xl font-semibold text-maice-primary">
											{totalSessions}
										</p>
									</div>
								</div>
							</Card>
						</div>
					</div>

					<!-- 빠른 액션 -->
					<div>
						<h3 class="text-xl font-semibold text-maice-primary mb-4">빠른 액션</h3>
						<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
							<div role="button" tabindex="0" onclick={navigateToMAICE} onkeydown={(e) => e.key === 'Enter' && navigateToMAICE()}>
								<Card className="p-6 hover:shadow-maice-lg transition-all duration-300 cursor-pointer">
									<div class="flex items-center">
										<div class="flex-shrink-0">
											<div class="w-12 h-12 bg-green-500 rounded-lg flex items-center justify-center">
												<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
												</svg>
											</div>
										</div>
										<div class="ml-4">
											<h4 class="text-lg font-medium text-maice-primary">MAICE 시작하기</h4>
											<p class="text-sm text-maice-text-secondary">AI 학습 도우미</p>
										</div>
									</div>
								</Card>
							</div>
							
							<div role="button" tabindex="0" onclick={() => goto('/survey')} onkeydown={(e) => e.key === 'Enter' && goto('/survey')}>
								<Card className="p-6 hover:shadow-maice-lg transition-all duration-300 cursor-pointer">
									<div class="flex items-center">
										<div class="flex-shrink-0">
											<div class="w-12 h-12 bg-blue-500 rounded-lg flex items-center justify-center">
												<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"></path>
												</svg>
											</div>
										</div>
										<div class="ml-4">
											<h4 class="text-lg font-medium text-maice-primary">설문 응답</h4>
											<p class="text-sm text-maice-text-secondary">학습 경험 평가</p>
										</div>
									</div>
								</Card>
							</div>
						</div>
					</div>
				</div>

			{:else if user?.role?.toLowerCase() === 'student'}
				<!-- 학생 대시보드 -->
				<div class="space-y-8">
					<!-- 학습 통계 -->
					<div>
						<h3 class="text-xl font-semibold text-maice-primary mb-4">학습 현황</h3>
						<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
							<Card className="p-6">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class="w-12 h-12 bg-blue-500 rounded-lg flex items-center justify-center">
											<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"></path>
											</svg>
										</div>
									</div>
									<div class="ml-4">
										<p class="text-sm font-medium text-maice-text-muted">총 질문 수</p>
										<p class="text-2xl font-semibold text-maice-primary">{totalQuestions}</p>
									</div>
								</div>
							</Card>

							<Card className="p-6">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class="w-12 h-12 bg-green-500 rounded-lg flex items-center justify-center">
											<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path>
											</svg>
										</div>
									</div>
									<div class="ml-4">
										<p class="text-sm font-medium text-maice-text-muted">학습 세션</p>
										<p class="text-2xl font-semibold text-maice-primary">{totalSessions}</p>
									</div>
								</div>
							</Card>

							<Card className="p-6">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class="w-12 h-12 bg-purple-500 rounded-lg flex items-center justify-center">
											<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
											</svg>
										</div>
									</div>
									<div class="ml-4">
										<p class="text-sm font-medium text-maice-text-muted">사용자 모드</p>
										<p class="text-lg font-semibold text-maice-primary">
											{user?.assigned_mode === 'agent' ? 'Agent 모드' : user?.assigned_mode === 'freepass' ? 'FreePass 모드' : '미할당'}
										</p>
									</div>
								</div>
							</Card>
						</div>
					</div>

					<!-- 최근 세션 -->
					{#if recentSessions.length > 0}
						<div>
							<h3 class="text-xl font-semibold text-maice-primary mb-4">최근 학습 세션</h3>
							<div class="space-y-4">
								{#each recentSessions as session}
									<div role="button" tabindex="0" onclick={() => goto(`/maice?session=${session.id}`)} onkeydown={(e) => e.key === 'Enter' && goto(`/maice?session=${session.id}`)}>
										<Card className="p-6 hover:shadow-maice-lg transition-all duration-300 cursor-pointer">
											<div class="flex items-center justify-between">
												<div class="flex-1">
													<h4 class="text-lg font-medium text-maice-primary mb-2">
														세션 #{session.id}
													</h4>
													<div class="flex items-center space-x-4 text-sm text-maice-text-secondary">
														<span>📝 {session.messages?.length || 0}개 메시지</span>
														<span>🕐 {formatDate(session.updated_at)}</span>
														<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {session.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}">
															{session.is_active ? '진행 중' : '완료'}
														</span>
													</div>
												</div>
												<svg class="w-5 h-5 text-maice-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
												</svg>
											</div>
										</Card>
									</div>
								{/each}
							</div>
						</div>
					{/if}

					<!-- 학습 시작 버튼 -->
					<div role="button" tabindex="0" onclick={navigateToMAICE} onkeydown={(e) => e.key === 'Enter' && navigateToMAICE()}>
						<Card className="p-8 hover:shadow-maice-lg transition-all duration-300 cursor-pointer">
							<div class="text-center">
								<div class="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-4">
									<svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
									</svg>
								</div>
								<h3 class="text-2xl font-bold text-maice-primary mb-2">MAICE 학습 시작하기</h3>
								<p class="text-maice-text-secondary">AI 학습 도우미와 함께 수학 문제를 풀어보세요</p>
							</div>
						</Card>
					</div>
				</div>

			{:else if user?.role?.toLowerCase() === 'teacher'}
				<!-- 교사 대시보드 -->
				<div class="space-y-8">
					<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
						<div role="button" tabindex="0" onclick={() => goto('/teacher')} onkeydown={(e) => e.key === 'Enter' && goto('/teacher')}>
							<Card className="p-6 hover:shadow-maice-lg transition-all duration-300 cursor-pointer">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class="w-12 h-12 bg-purple-500 rounded-lg flex items-center justify-center">
											<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path>
											</svg>
										</div>
									</div>
									<div class="ml-4">
										<h4 class="text-lg font-medium text-maice-primary">교사 대시보드</h4>
										<p class="text-sm text-maice-text-secondary">사용자 관리 및 평가</p>
									</div>
								</div>
							</Card>
						</div>

						<div role="button" tabindex="0" onclick={navigateToMAICE} onkeydown={(e) => e.key === 'Enter' && navigateToMAICE()}>
							<Card className="p-6 hover:shadow-maice-lg transition-all duration-300 cursor-pointer">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class="w-12 h-12 bg-green-500 rounded-lg flex items-center justify-center">
											<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
											</svg>
										</div>
									</div>
									<div class="ml-4">
										<h4 class="text-lg font-medium text-maice-primary">MAICE 시스템</h4>
										<p class="text-sm text-maice-text-secondary">AI 학습 도우미</p>
									</div>
								</div>
							</Card>
						</div>
					</div>
				</div>
			{/if}
		</div>
	</main>
</div>
