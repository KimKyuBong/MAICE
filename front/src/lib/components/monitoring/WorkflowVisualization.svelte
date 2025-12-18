<script lang="ts">
	/**
	 * MAICE 워크플로우 시각화 컴포넌트
	 * 
	 * 에이전트 모드와 프리패스 모드를 구분하여 표시
	 */
	
	export let agentMetrics: any = null;
	
	// 모드 선택 상태
	let selectedMode: 'agent' | 'freepass' = 'agent';
	
	const agentModeAgents = [
		{
			name: 'QuestionClassifierAgent',
			label: '질문 분류',
			color: 'bg-blue-500',
			icon: '🔍'
		},
		{
			name: 'QuestionImprovementAgent',
			label: '질문 개선',
			color: 'bg-yellow-500',
			icon: '✨'
		},
		{
			name: 'AnswerGeneratorAgent',
			label: '답변 생성',
			color: 'bg-green-500',
			icon: '💬'
		},
		{
			name: 'ObserverAgent',
			label: '학습 관찰',
			color: 'bg-purple-500',
			icon: '👁️'
		}
	];
	
	const freepassAgents = [
		{
			name: 'FreeTalkerAgent',
			label: '프리패스 모드',
			color: 'bg-pink-500',
			icon: '🗨️'
		}
	];
	
	function getAgentRequests(agentName: string): number {
		if (!agentMetrics?.agents) return 0;
		const agent = agentMetrics.agents.find((a: any) => a.name === agentName);
		return agent?.requests || 0;
	}
	
	function getAgentStatus(agentName: string): 'active' | 'idle' | 'error' {
		if (!agentMetrics?.agents) return 'idle';
		const agent = agentMetrics.agents.find((a: any) => a.name === agentName);
		if (!agent) return 'idle';
		if (agent.errors > 0 && agent.error_rate > 10) return 'error';
		if (agent.requests > 0) return 'active';
		return 'idle';
	}
	
	function getStatusColor(status: string): string {
		switch (status) {
			case 'active':
				return 'border-green-500 shadow-green-500/50';
			case 'error':
				return 'border-red-500 shadow-red-500/50';
			default:
				return 'border-gray-300 shadow-gray-300/50';
		}
	}
</script>

<div class="p-6 bg-white dark:bg-gray-800 rounded-lg">
	<div class="flex items-center justify-between mb-6">
		<h3 class="text-lg font-semibold text-gray-900 dark:text-white">워크플로우 시각화</h3>
		
		<!-- 모드 선택 버튼 -->
		<div class="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
			<button 
				class="px-4 py-2 text-sm font-medium rounded-md transition-all duration-200 {selectedMode === 'agent' ? 'bg-white dark:bg-gray-600 text-blue-600 shadow-sm' : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'}"
				onclick={() => selectedMode = 'agent'}
			>
				🤖 에이전트 모드
			</button>
			<button 
				class="px-4 py-2 text-sm font-medium rounded-md transition-all duration-200 {selectedMode === 'freepass' ? 'bg-white dark:bg-gray-600 text-pink-600 shadow-sm' : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'}"
				onclick={() => selectedMode = 'freepass'}
			>
				⚡ 프리패스 모드
			</button>
		</div>
	</div>
	
	<!-- 워크플로우 다이어그램 -->
	<div class="relative">
		<!-- 시작점: 사용자 질문 -->
		<div class="flex items-center justify-center mb-8">
			<div class="flex flex-col items-center">
				<div class="w-16 h-16 bg-gray-200 dark:bg-gray-700 rounded-full flex items-center justify-center text-2xl mb-2">
					👤
				</div>
				<p class="text-sm font-medium text-gray-900 dark:text-white">사용자</p>
				<p class="text-xs text-gray-500 dark:text-gray-400">질문 입력</p>
			</div>
		</div>
		
		<!-- 화살표 -->
		<div class="flex justify-center mb-8">
			<svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"/>
			</svg>
		</div>
		
		<!-- 에이전트 모드 워크플로우 -->
		{#if selectedMode === 'agent'}
			<!-- 1단계: 질문 분류 -->
			<div class="flex justify-center mb-8">
				<div class="w-full max-w-sm">
					<div class="border-2 {getStatusColor(getAgentStatus('QuestionClassifierAgent'))} rounded-lg p-4 bg-white dark:bg-gray-800 shadow-lg transition-all duration-300">
						<div class="flex items-center justify-between mb-2">
							<div class="flex items-center space-x-2">
								<span class="text-2xl">{agentModeAgents[0].icon}</span>
								<div>
									<p class="font-semibold text-gray-900 dark:text-white">{agentModeAgents[0].label}</p>
									<p class="text-xs text-gray-500 dark:text-gray-400">1단계</p>
								</div>
							</div>
							<div class="text-right">
								<p class="text-lg font-bold text-gray-900 dark:text-white">{getAgentRequests('QuestionClassifierAgent')}</p>
								<p class="text-xs text-gray-500 dark:text-gray-400">요청</p>
							</div>
						</div>
					</div>
				</div>
			</div>
			
			<!-- 화살표 -->
			<div class="flex justify-center mb-6">
				<svg class="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"/>
				</svg>
			</div>
			
			<!-- 2단계: 분기 처리 -->
			<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
				<!-- 질문 개선 -->
				<div class="flex flex-col items-center">
					<div class="w-full border-2 {getStatusColor(getAgentStatus('QuestionImprovementAgent'))} rounded-lg p-4 bg-white dark:bg-gray-800 shadow-lg">
						<div class="flex items-center justify-between mb-2">
							<div class="flex items-center space-x-2">
								<span class="text-2xl">{agentModeAgents[1].icon}</span>
								<div>
									<p class="font-semibold text-gray-900 dark:text-white">{agentModeAgents[1].label}</p>
									<p class="text-xs text-gray-500 dark:text-gray-400">명료화 필요</p>
								</div>
							</div>
						</div>
						<div class="mt-2">
							<p class="text-lg font-bold text-gray-900 dark:text-white">{getAgentRequests('QuestionImprovementAgent')}</p>
							<p class="text-xs text-gray-500 dark:text-gray-400">요청</p>
						</div>
					</div>
				</div>
				
				<!-- 답변 생성 -->
				<div class="flex flex-col items-center">
					<div class="w-full border-2 {getStatusColor(getAgentStatus('AnswerGeneratorAgent'))} rounded-lg p-4 bg-white dark:bg-gray-800 shadow-lg">
						<div class="flex items-center justify-between mb-2">
							<div class="flex items-center space-x-2">
								<span class="text-2xl">{agentModeAgents[2].icon}</span>
								<div>
									<p class="font-semibold text-gray-900 dark:text-white">{agentModeAgents[2].label}</p>
									<p class="text-xs text-gray-500 dark:text-gray-400">답변 가능</p>
								</div>
							</div>
						</div>
						<div class="mt-2">
							<p class="text-lg font-bold text-gray-900 dark:text-white">{getAgentRequests('AnswerGeneratorAgent')}</p>
							<p class="text-xs text-gray-500 dark:text-gray-400">요청</p>
						</div>
					</div>
				</div>
			</div>
			
			<!-- 화살표 -->
			<div class="flex justify-center mb-6">
				<svg class="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"/>
				</svg>
			</div>
			
			<!-- 3단계: 학습 관찰 -->
			<div class="flex justify-center mb-8">
				<div class="w-full max-w-sm">
					<div class="border-2 {getStatusColor(getAgentStatus('ObserverAgent'))} rounded-lg p-4 bg-white dark:bg-gray-800 shadow-lg">
						<div class="flex items-center justify-between mb-2">
							<div class="flex items-center space-x-2">
								<span class="text-2xl">{agentModeAgents[3].icon}</span>
								<div>
									<p class="font-semibold text-gray-900 dark:text-white">{agentModeAgents[3].label}</p>
									<p class="text-xs text-gray-500 dark:text-gray-400">3단계</p>
								</div>
							</div>
							<div class="text-right">
								<p class="text-lg font-bold text-gray-900 dark:text-white">{getAgentRequests('ObserverAgent')}</p>
								<p class="text-xs text-gray-500 dark:text-gray-400">요청</p>
							</div>
						</div>
					</div>
				</div>
			</div>
		{/if}
		
		<!-- 프리패스 모드 워크플로우 -->
		{#if selectedMode === 'freepass'}
			<div class="flex justify-center mb-8">
				<div class="w-full max-w-sm">
					<div class="border-2 {getStatusColor(getAgentStatus('FreeTalkerAgent'))} rounded-lg p-6 bg-white dark:bg-gray-800 shadow-lg transition-all duration-300">
						<div class="flex flex-col items-center text-center">
							<div class="text-4xl mb-3">{freepassAgents[0].icon}</div>
							<p class="text-lg font-semibold text-gray-900 dark:text-white mb-2">{freepassAgents[0].label}</p>
							<p class="text-sm text-gray-500 dark:text-gray-400 mb-4">직접 LLM 응답 처리</p>
							<div class="text-center">
								<p class="text-2xl font-bold text-gray-900 dark:text-white">{getAgentRequests('FreeTalkerAgent')}</p>
								<p class="text-xs text-gray-500 dark:text-gray-400">요청</p>
							</div>
						</div>
					</div>
				</div>
			</div>
		{/if}
		
		<!-- 화살표 -->
		<div class="flex justify-center mb-8">
			<svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"/>
			</svg>
		</div>
		
		<!-- 종료점: 사용자에게 응답 -->
		<div class="flex items-center justify-center">
			<div class="flex flex-col items-center">
				<div class="w-16 h-16 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center text-2xl mb-2">
					✅
				</div>
				<p class="text-sm font-medium text-gray-900 dark:text-white">완료</p>
				<p class="text-xs text-gray-500 dark:text-gray-400">
					{selectedMode === 'agent' ? '다단계 분석 완료' : '직접 응답 완료'}
				</p>
			</div>
		</div>
	</div>
	
	<!-- 모드 설명 -->
	<div class="mt-6 p-4 rounded-lg {selectedMode === 'agent' ? 'bg-blue-50 dark:bg-blue-900/20' : 'bg-pink-50 dark:bg-pink-900/20'}">
		{#if selectedMode === 'agent'}
			<h4 class="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-2">🤖 에이전트 모드</h4>
			<p class="text-xs text-blue-700 dark:text-blue-300">
				질문을 분류하고 필요시 명료화하여 전문적인 답변을 생성합니다. 학습 관찰 에이전트가 사용자의 학습 패턴을 분석합니다.
			</p>
		{:else}
			<h4 class="text-sm font-semibold text-pink-900 dark:text-pink-100 mb-2">⚡ 프리패스 모드</h4>
			<p class="text-xs text-pink-700 dark:text-pink-300">
				복잡한 에이전트 체인 없이 직접적으로 LLM과 대화합니다. 빠른 응답이 필요한 경우 사용됩니다.
			</p>
		{/if}
	</div>
	
	<!-- 범례 -->
	<div class="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
		<p class="text-sm font-medium text-gray-900 dark:text-white mb-3">상태 표시:</p>
		<div class="flex flex-wrap gap-4">
			<div class="flex items-center space-x-2">
				<div class="w-4 h-4 border-2 border-green-500 rounded shadow-green-500/50"></div>
				<p class="text-sm text-gray-600 dark:text-gray-400">활성 (요청 처리 중)</p>
			</div>
			<div class="flex items-center space-x-2">
				<div class="w-4 h-4 border-2 border-gray-300 rounded shadow-gray-300/50"></div>
				<p class="text-sm text-gray-600 dark:text-gray-400">대기 중</p>
			</div>
			<div class="flex items-center space-x-2">
				<div class="w-4 h-4 border-2 border-red-500 rounded shadow-red-500/50"></div>
				<p class="text-sm text-gray-600 dark:text-gray-400">오류 발생</p>
			</div>
		</div>
	</div>
</div>

