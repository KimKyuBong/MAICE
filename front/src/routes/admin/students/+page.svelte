<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth';
    import { getStudents, getStudentSessions, getSessionMessages, evaluateSession, getSessionEvaluations, batchEvaluateSessions, batchEvaluateAllSessions as apiBatchEvaluateAllSessions } from '$lib/api';
	import Button from '$lib/components/common/Button.svelte';
	import Card from '$lib/components/common/Card.svelte';
	import MarkdownRenderer from '$lib/components/maice/MarkdownRenderer.svelte';
	
	let token: string = '';
	let students: any[] = [];
	let allStudents: any[] = []; // 전체 학생 목록 (검색용)
	let selectedStudent: any = null;
	let selectedStudentSessions: any[] = [];
	let selectedSession: any = null;
	let selectedSessionMessages: any[] = [];
	let selectedSessionEvaluations: any[] = [];
	let isLoading = false;
	let error: string | null = null;
	let currentView: 'list' | 'sessions' | 'messages' = 'list';
	let loadingStudentId: number | null = null;
	let loadingSessionId: number | null = null;
	let evaluatingSessionId: number | null = null;
	let evaluatingSessionIds: Set<number> = new Set();
	let showEvaluations = false;
	
	// 검색 및 정렬
	let searchTerm = '';
	let sortField: 'username' | 'role' | 'session_count' | 'created_at' | null = null;
	let sortOrder: 'asc' | 'desc' = 'desc';
	
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
				loadStudents();
			}
		});
		
		return unsubscribe;
	});
	
	async function loadStudents() {
		if (!token) return;
		
		try {
			isLoading = true;
			error = null;
			
			const response = await getStudents(token);
			allStudents = response.students || [];
			students = allStudents; // 초기에는 전체 표시
			applyFilters();
			
		} catch (err: any) {
			error = err.message || '학생 목록을 불러올 수 없습니다.';
			console.error('학생 목록 로드 실패:', err);
        } finally {
            isLoading = false;
        }
    }
	
	function applyFilters() {
		let filtered = [...allStudents];
		
		// 검색 필터 적용
		if (searchTerm) {
			filtered = filtered.filter(student => {
				const searchLower = searchTerm.toLowerCase();
				return (
					(student.google_name || student.username || '').toLowerCase().includes(searchLower) ||
					(student.google_email || student.username || '').toLowerCase().includes(searchLower) ||
					(student.username || '').toLowerCase().includes(searchLower)
				);
			});
		}
		
		// 정렬 적용
		if (sortField) {
			filtered.sort((a, b) => {
				let aValue = a[sortField!];
				let bValue = b[sortField!];
				
				// null/undefined 처리
				if (!aValue && !bValue) return 0;
				if (!aValue) return 1;
				if (!bValue) return -1;
				
				// 비교
				if (sortField === 'session_count' || sortField === 'created_at') {
					// 숫자나 날짜 비교
					const comparison = aValue > bValue ? 1 : aValue < bValue ? -1 : 0;
					return sortOrder === 'asc' ? comparison : -comparison;
				} else {
					// 문자열 비교
					const comparison = String(aValue).localeCompare(String(bValue));
					return sortOrder === 'asc' ? comparison : -comparison;
				}
			});
		}
		
		students = filtered;
	}
	
	function handleSearch() {
		applyFilters();
	}
	
	function handleSort(field: 'username' | 'role' | 'session_count' | 'created_at') {
		if (sortField === field) {
			// 같은 필드면 정렬 순서만 토글
			sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
		} else {
			// 다른 필드면 새로 정렬 적용
			sortField = field;
			sortOrder = 'asc';
		}
		applyFilters();
	}
	
	function getSortIcon(field: 'username' | 'role' | 'session_count' | 'created_at'): string {
		if (sortField !== field) return '↕';
		return sortOrder === 'asc' ? '↑' : '↓';
	}
	
    async function viewStudentSessions(student: any) {
		if (!token) return;
		
		try {
			loadingStudentId = student.id;
			error = null;
			
			const response = await getStudentSessions(token, student.id);
			selectedStudent = response.student;
			selectedStudentSessions = response.sessions || [];
			currentView = 'sessions';
			selectedSession = null;
			selectedSessionMessages = [];
			
		} catch (err: any) {
			error = err.message || '세션 목록을 불러올 수 없습니다.';
			console.error('세션 목록 로드 실패:', err);
		} finally {
			loadingStudentId = null;
        }
        }

    async function evaluateAllStudentsAllSessions(onlyUnevaluated: boolean = true) {
        if (!token) return;
        try {
            evaluatingSessionId = 0;
            error = null;
            const response = await apiBatchEvaluateAllSessions(token, onlyUnevaluated);
            
            if (response.status === 'processing') {
                alert(`평가가 백그라운드에서 시작되었습니다.\n총 ${response.total}개 세션이 처리됩니다.\n완료 후 페이지를 새로고침하세요.`);
            } else {
                alert(`평가 완료: 총 ${response.total || 0}개 세션`);
            }
            
            // 목록 갱신
            await loadStudents();
            if (selectedStudent) {
                await viewStudentSessions(selectedStudent);
            }
        } catch (err: any) {
            error = err.message || '전체 평가 실행에 실패했습니다.';
            console.error('전체 평가 실행 실패:', err);
            alert('전체 평가 실행 중 오류가 발생했습니다.');
        } finally {
            evaluatingSessionId = null;
    }
	}
	
	async function viewSessionMessages(session: any) {
		if (!token) return;
		
		try {
			loadingSessionId = session.id;
			error = null;
			
			const response = await getSessionMessages(token, session.id);
			selectedSession = response.session;
			selectedSessionMessages = response.messages || [];
			
			// 평가 결과도 함께 조회
			try {
				const evaluationsResponse = await getSessionEvaluations(token, session.id);
				selectedSessionEvaluations = evaluationsResponse.evaluations || [];
				console.log('평가 결과 조회 성공:', selectedSessionEvaluations.length, '개');
			} catch (evalErr: any) {
				console.error('평가 결과 조회 실패:', evalErr);
				selectedSessionEvaluations = [];
			}
			
			currentView = 'messages';
			
		} catch (err: any) {
			error = err.message || '메시지 목록을 불러올 수 없습니다.';
			console.error('메시지 목록 로드 실패:', err);
		} finally {
			loadingSessionId = null;
		}
	}
	
	async function evaluateCurrentSession() {
		if (!token || !selectedSession) return;
		
		try {
			evaluatingSessionId = selectedSession.id;
			error = null;
			
			const response = await evaluateSession(token, selectedSession.id);
			
			// 평가 결과 조회
			const evaluationsResponse = await getSessionEvaluations(token, selectedSession.id);
			selectedSessionEvaluations = evaluationsResponse.evaluations || [];
			
			alert('평가가 완료되었습니다.');
			
		} catch (err: any) {
			error = err.message || '평가 실행에 실패했습니다.';
			console.error('평가 실행 실패:', err);
			alert('평가 실행 중 오류가 발생했습니다.');
		} finally {
			evaluatingSessionId = null;
		}
	}
	
	async function batchEvaluateAllSessions() {
		if (!token || !selectedStudentSessions.length) return;
		
		try {
			evaluatingSessionId = 0; // 일괄 평가 표시
			// 진행 중인 세션들 버튼 상태 표시
			const sessionIds = selectedStudentSessions.map(s => s.id);
			evaluatingSessionIds = new Set(sessionIds);
			error = null;
			const response = await batchEvaluateSessions(token, sessionIds);
			
			alert(`평가 완료: ${response.successful}개 성공, ${response.failed}개 실패`);
			
			// 세션 목록 새로고침
			await viewStudentSessions(selectedStudent);
			
		} catch (err: any) {
			error = err.message || '일괄 평가 실행에 실패했습니다.';
			console.error('일괄 평가 실행 실패:', err);
			alert('일괄 평가 실행 중 오류가 발생했습니다.');
		} finally {
			evaluatingSessionId = null;
			evaluatingSessionIds = new Set();
		}
	}
	
	function formatDate(dateString: string): string {
		if (!dateString) return '-';
		const date = new Date(dateString);
		return date.toLocaleString('ko-KR', {
			year: 'numeric',
			month: '2-digit',
			day: '2-digit',
			hour: '2-digit',
			minute: '2-digit'
		});
	}
	
	function getSenderLabel(sender: string): string {
		return sender === 'user' ? '학생' : 'MAICE';
	}
	
	function getRoleLabel(role: string): string {
		switch (role) {
			case 'admin': return '관리자';
			case 'teacher': return '교사';
			case 'student': return '학생';
			default: return role;
		}
	}
	
	function backToList() {
		if (currentView === 'messages') {
			currentView = 'sessions';
			selectedSession = null;
			selectedSessionMessages = [];
		} else if (currentView === 'sessions') {
			currentView = 'list';
			selectedStudent = null;
			selectedStudentSessions = [];
		}
}
</script>

<svelte:head>
	<title>학생 관리 - MAICE</title>
</svelte:head>

<div class="min-h-screen bg-maice-bg p-6">
	<div class="max-w-7xl mx-auto">
		<!-- 헤더 -->
		<div class="mb-6 flex items-center justify-between">
			<div>
				{#if currentView !== 'list'}
					<Button variant="secondary" onclick={backToList} class="mb-2">
						← 뒤로
					</Button>
				{/if}
                <h1 class="text-3xl font-bold text-maice-primary">
					사용자 관리
				</h1>
				<p class="text-maice-text-muted mt-2">
					{#if currentView === 'list'}
						모든 사용자를 조회하고 관리할 수 있습니다.
					{:else if currentView === 'sessions'}
						{selectedStudent?.google_name || selectedStudent?.username} 학생의 세션 목록
					{:else if currentView === 'messages'}
						세션 대화 내역
					{/if}
				</p>
			</div>
		</div>

		{#if error}
			<div class="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
				<p class="text-red-800">{error}</p>
			</div>
		{/if}

		{#if isLoading && currentView === 'list' && students.length === 0}
			<div class="text-center py-12">
				<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-maice-primary mx-auto mb-4"></div>
				<p class="text-maice-text-secondary">학생 목록을 불러오는 중...</p>
			</div>
		{:else if currentView === 'list'}
			<!-- 검색 및 정렬 컨트롤 -->
            <Card variant="elevated" class="mb-4">
				<div class="p-4 flex gap-4 items-center">
					<div class="flex-1">
						<label for="search" class="block text-sm font-medium text-maice-text-primary mb-2">
							검색
						</label>
						<input
							id="search"
							type="text"
							placeholder="이름, 이메일로 검색..."
							bind:value={searchTerm}
							oninput={handleSearch}
							class="w-full px-4 py-2 border border-maice-border rounded-lg bg-maice-card text-maice-text-primary focus:outline-none focus:ring-2 focus:ring-maice-primary"
						/>
					</div>
                    <div class="flex items-center gap-2">
                        <div class="text-sm text-maice-text-secondary mr-2">
                            총 {students.length}명
                        </div>
                        <Button variant="secondary" size="sm" onclick={() => evaluateAllStudentsAllSessions(true)} disabled={evaluatingSessionId !== null}>
                            {evaluatingSessionId === 0 ? '전체 평가 중...' : '모든 학생 전체 평가'}
                        </Button>
                        <Button variant="secondary" size="sm" onclick={() => evaluateAllStudentsAllSessions(false)} disabled={evaluatingSessionId !== null}>
                            {evaluatingSessionId === 0 ? '재평가 중...' : '모든 학생 전체 재평가'}
                        </Button>
                    </div>
				</div>
			</Card>
			
			<!-- 학생 목록 -->
			<Card variant="elevated">
				<div class="overflow-x-auto" style="max-height: calc(100vh - 300px);">
					<table class="w-full">
						<thead class="sticky top-0 bg-maice-card z-10">
							<tr class="border-b border-maice-border">
								<th 
									class="text-left py-3 px-4 text-sm font-semibold text-maice-text-primary cursor-pointer hover:bg-maice-hover"
									onclick={() => handleSort('username')}
								>
									이름 {getSortIcon('username')}
								</th>
								<th 
									class="text-left py-3 px-4 text-sm font-semibold text-maice-text-primary cursor-pointer hover:bg-maice-hover"
									onclick={() => handleSort('role')}
								>
									역할 {getSortIcon('role')}
								</th>
								<th class="text-left py-3 px-4 text-sm font-semibold text-maice-text-primary">이메일</th>
								<th 
									class="text-left py-3 px-4 text-sm font-semibold text-maice-text-primary cursor-pointer hover:bg-maice-hover"
									onclick={() => handleSort('session_count')}
								>
									세션 수 {getSortIcon('session_count')}
								</th>
								<th class="text-left py-3 px-4 text-sm font-semibold text-maice-text-primary">최근 활동</th>
								<th 
									class="text-left py-3 px-4 text-sm font-semibold text-maice-text-primary cursor-pointer hover:bg-maice-hover"
									onclick={() => handleSort('created_at')}
								>
									가입일 {getSortIcon('created_at')}
								</th>
								<th class="text-right py-3 px-4 text-sm font-semibold text-maice-text-primary">작업</th>
							</tr>
						</thead>
						<tbody>
							{#each students as student}
								<tr class="border-b border-maice-border hover:bg-maice-hover">
									<td class="py-3 px-4">
										<div class="font-medium text-maice-text-primary">
											{student.google_name || student.username}
										</div>
									</td>
									<td class="py-3 px-4">
										{#if student.role === 'admin'}
											<span class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-red-100 text-red-800">
												관리자
											</span>
										{:else if student.role === 'teacher'}
											<span class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
												교사
											</span>
										{:else if student.role === 'student'}
											<span class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
												학생
											</span>
										{:else}
											<span class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-800">
												{student.role || '알 수 없음'}
											</span>
										{/if}
									</td>
									<td class="py-3 px-4 text-maice-text-secondary">
										{student.google_email || student.username}
									</td>
									<td class="py-3 px-4 text-maice-text-secondary">
										{student.session_count}
									</td>
									<td class="py-3 px-4 text-maice-text-secondary text-sm">
										{formatDate(student.last_session_at)}
									</td>
									<td class="py-3 px-4 text-maice-text-secondary text-sm">
										{formatDate(student.created_at)}
									</td>
									<td class="py-3 px-4">
										<div class="flex justify-end">
											<Button 
												variant="primary" 
												size="sm" 
												onclick={() => viewStudentSessions(student)}
												disabled={loadingStudentId === student.id || isLoading}
											>
												{loadingStudentId === student.id ? '로딩 중...' : '세션 보기'}
											</Button>
										</div>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</Card>
			
		{:else if currentView === 'sessions'}
			<!-- 세션 목록 -->
			<div class="space-y-4">
			{#if selectedStudent}
				<Card variant="default">
					<div class="p-4 flex justify-between items-center">
						<div>
							<h2 class="text-xl font-semibold text-maice-primary mb-2">
								{selectedStudent.google_name || selectedStudent.username}
							</h2>
							<p class="text-maice-text-secondary">
								이메일: {selectedStudent.google_email || selectedStudent.username}
							</p>
						</div>
						<div>
							<Button 
								variant="secondary" 
								size="sm"
								onclick={batchEvaluateAllSessions}
								disabled={evaluatingSessionId !== null}
							>
								{evaluatingSessionId === 0 ? '평가 중...' : '전체 세션 평가'}
							</Button>
						</div>
					</div>
				</Card>
			{/if}
				
				<div class="grid gap-4">
					{#each selectedStudentSessions as session}
						<Card variant="default" class="hover:shadow-md transition-shadow">
							<div class="p-4">
								<div class="flex items-start justify-between">
									<div class="flex-1">
										<div class="flex items-center gap-2 mb-1">
											<h3 class="font-semibold text-maice-text-primary">
												{session.title || '제목 없음'}
											</h3>
											{#if session.evaluation_in_progress}
												<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
													⏳ 평가 진행중
												</span>
											{:else if session.has_evaluation}
												<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
													✓ 평가 완료
												</span>
											{:else}
												<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
													○ 미평가
												</span>
											{/if}
										</div>
										<div class="flex items-center gap-4 text-sm text-maice-text-secondary">
											<span>메시지: {session.message_count}개</span>
											<span class="inline-flex items-center px-2 py-1 rounded bg-blue-100 text-blue-800">
												{session.is_active ? '활성' : '비활성'}
											</span>
											<span>단계: {session.current_stage}</span>
										</div>
										<p class="text-xs text-maice-text-muted mt-2">
											생성: {formatDate(session.created_at)} | 수정: {formatDate(session.updated_at)}
											{#if session.has_evaluation && session.last_evaluation_at}
												| 평가: {formatDate(session.last_evaluation_at)}
											{/if}
										</p>
									</div>
									<div class="ml-4 flex gap-2">
										<Button 
											variant="primary" 
											size="sm"
											onclick={() => viewSessionMessages(session)}
											disabled={loadingSessionId === session.id}
										>
											{loadingSessionId === session.id ? '로딩 중...' : '대화 보기'}
										</Button>
										<Button 
											variant="secondary" 
											size="sm"
											onclick={async () => {
												if (!confirm('이 세션을 평가하시겠습니까?')) return;
												try {
													evaluatingSessionId = session.id;
													await evaluateSession(token, session.id);
													alert('평가가 완료되었습니다.');
													// 세션 목록 새로고침
													await viewStudentSessions(selectedStudent);
												} catch (err: any) {
													alert('평가 실행 중 오류가 발생했습니다.');
												} finally {
													evaluatingSessionId = null;
												}
											}}
											disabled={evaluatingSessionId === session.id || evaluatingSessionIds.has(session.id) || session.evaluation_in_progress}
										>
											{(evaluatingSessionId === session.id || evaluatingSessionIds.has(session.id) || session.evaluation_in_progress)
												? '평가 중...'
												: (session.has_evaluation ? '재평가' : '평가')}
										</Button>
									</div>
								</div>
							</div>
						</Card>
					{/each}
					
					{#if selectedStudentSessions.length === 0}
						<Card variant="default">
							<div class="p-8 text-center text-maice-text-secondary">
								세션이 없습니다.
							</div>
						</Card>
					{/if}
				</div>
			</div>
			
		{:else if currentView === 'messages'}
			<!-- 메시지 목록 -->
			<div class="space-y-4">
				{#if selectedSession}
					<Card variant="default">
						<div class="p-4 flex justify-between items-center">
							<div>
								<h2 class="text-lg font-semibold text-maice-primary mb-2">
									{selectedSession.title || '제목 없음'}
								</h2>
								<div class="flex items-center gap-4 text-sm text-maice-text-secondary">
									<span class="inline-flex items-center px-2 py-1 rounded bg-blue-100 text-blue-800">
										{selectedSession.is_active ? '활성' : '비활성'}
									</span>
									<span>상태: {selectedSession.current_stage}</span>
									<span>생성: {formatDate(selectedSession.created_at)}</span>
								</div>
							</div>
							<div class="flex gap-2">
								<Button 
									variant="primary" 
									size="sm"
									onclick={evaluateCurrentSession}
									disabled={evaluatingSessionId !== null}
								>
									{evaluatingSessionId === selectedSession.id ? '평가 중...' : '평가 실행'}
								</Button>
								<Button 
									variant="secondary" 
									size="sm"
									onclick={() => showEvaluations = !showEvaluations}
								>
									{showEvaluations ? '평가 결과 숨기기' : '평가 결과 보기'}
								</Button>
							</div>
						</div>
					</Card>
				{/if}
				
				{#if showEvaluations && selectedSessionEvaluations.length > 0}
					<!-- 평가 결과 -->
					<div class="space-y-4 mb-6">
						<h3 class="text-lg font-semibold text-maice-primary">평가 결과</h3>
						{#each selectedSessionEvaluations as evaluation}
							<Card variant="elevated">
								<div class="p-6">
									<!-- 평가 헤더 -->
                                    <div class="flex justify-between items-start mb-4">
                                        <div>
											<p class="text-sm text-maice-text-muted">
												평가일: {formatDate(evaluation.created_at)}
											</p>
											{#if evaluation.evaluator}
												<p class="text-sm text-maice-text-muted">
													평가자: {evaluation.evaluator.username}
												</p>
											{/if}
										</div>
                                        <div class="flex gap-4 items-end">
                                            <div class="text-right">
                                                <p class="text-xs text-maice-text-muted mb-1">질문 합계</p>
                                                <div class="text-2xl font-bold text-maice-primary">
                                                    {(evaluation.question_total_score ?? '-')}
                                                </div>
                                            </div>
                                            <div class="text-right">
                                                <p class="text-xs text-maice-text-muted mb-1">답변 합계</p>
                                                <div class="text-2xl font-bold text-maice-primary">
                                                    {(evaluation.answer_total_score ?? evaluation.response_total_score ?? '-')}
                                                </div>
                                            </div>
                                            {#if evaluation.overall_score}
                                                <div class="text-right">
                                                    <p class="text-xs text-maice-text-muted mb-1">총점(0~30)</p>
                                                    <div class="text-2xl font-bold text-maice-secondary">
                                                        {evaluation.overall_score.toFixed(1)}
                                                    </div>
                                                </div>
                                            {/if}
                                        </div>
									</div>
									
                                    <!-- 평가 점수 카드 (질문 3 + 답변 3, 각 5점 만점) -->
                                    <div class="grid grid-cols-2 gap-4 mb-4">
                                        <!-- 질문 평가 -->
                                        <div class="p-4 border border-maice-border rounded-lg bg-maice-card">
                                            <p class="text-xs text-maice-text-muted mb-3 font-semibold">질문 평가 (총 {evaluation.question_total_score ?? '-'} / 15)</p>
                                            <div class="space-y-2 text-sm">
                                                <div class="flex justify-between">
                                                    <span class="text-maice-text-muted">수학적 전문성</span>
                                                    <span class="font-medium text-maice-text-primary">{evaluation.question_professionalism_score ?? '-'}</span>
                                                </div>
                                                <div class="flex justify-between">
                                                    <span class="text-maice-text-muted">질문 구조화</span>
                                                    <span class="font-medium text-maice-text-primary">{evaluation.question_structuring_score ?? '-'}</span>
                                                </div>
                                                <div class="flex justify-between">
                                                    <span class="text-maice-text-muted">학습 맥락 적용</span>
                                                    <span class="font-medium text-maice-text-primary">{evaluation.question_context_application_score ?? '-'}</span>
                                                </div>
                                            </div>
                                            {#if evaluation.question_level_feedback}
                                                <p class="mt-3 text-xs text-maice-text-secondary whitespace-pre-wrap">{evaluation.question_level_feedback}</p>
                                            {/if}
                                            {#if evaluation.question_level_score}
                                                <!-- 구버전 호환 표시 (있을 경우) -->
                                                <p class="mt-2 text-[11px] text-maice-text-muted">(구) 질문 수준: {evaluation.question_level_score?.toFixed(1)}</p>
                                            {/if}
                                        </div>

                                        <!-- 답변 평가 -->
                                        <div class="p-4 border border-maice-border rounded-lg bg-maice-card">
                                            <p class="text-xs text-maice-text-muted mb-3 font-semibold">답변 평가 (총 {evaluation.answer_total_score ?? evaluation.response_total_score ?? '-'} / 15)</p>
                                            <div class="space-y-2 text-sm">
                                                <div class="flex justify-between">
                                                    <span class="text-maice-text-muted">학습자 맞춤도</span>
                                                    <span class="font-medium text-maice-text-primary">{evaluation.answer_customization_score ?? '-'}</span>
                                                </div>
                                                <div class="flex justify-between">
                                                    <span class="text-maice-text-muted">설명의 체계성</span>
                                                    <span class="font-medium text-maice-text-primary">{evaluation.answer_systematicity_score ?? '-'}</span>
                                                </div>
                                                <div class="flex justify-between">
                                                    <span class="text-maice-text-muted">학습 내용 확장성</span>
                                                    <span class="font-medium text-maice-text-primary">{evaluation.answer_expandability_score ?? '-'}</span>
                                                </div>
                                            </div>
                                            {#if evaluation.response_appropriateness_feedback}
                                                <p class="mt-3 text-xs text-maice-text-secondary whitespace-pre-wrap">{evaluation.response_appropriateness_feedback}</p>
                                            {/if}
                                            {#if evaluation.response_appropriateness_score}
                                                <!-- 구버전 호환 표시 (있을 경우) -->
                                                <p class="mt-2 text-[11px] text-maice-text-muted">(구) 응답 적합성: {evaluation.response_appropriateness_score?.toFixed(1)}</p>
                                            {/if}
                                        </div>
                                    </div>
									
									<!-- 종합 평가 -->
									{#if evaluation.overall_assessment}
										<div class="p-4 border border-maice-border rounded-lg bg-maice-card">
											<p class="text-xs text-maice-text-muted mb-2 font-semibold uppercase">종합 평가</p>
											<p class="text-sm text-maice-text-primary whitespace-pre-wrap leading-relaxed">
												{evaluation.overall_assessment}
											</p>
										</div>
									{/if}
								</div>
							</Card>
						{/each}
					</div>
				{:else if showEvaluations}
					<Card variant="default">
						<div class="p-4 text-center text-maice-text-secondary">
							평가 결과가 없습니다.
						</div>
					</Card>
				{/if}
				
				<div class="space-y-3">
					{#each selectedSessionMessages as message}
						<Card variant="default" class="hover:shadow-sm transition-shadow">
							<div class="p-4">
								<div class="flex items-start gap-3">
									<div class="flex-shrink-0">
										<div class="w-8 h-8 rounded-full flex items-center justify-center
											{message.sender === 'user' ? 'bg-maice-primary' : 'bg-maice-secondary'}">
											<span class="text-white text-xs font-medium">
												{getSenderLabel(message.sender).charAt(0)}
											</span>
										</div>
									</div>
									<div class="flex-1">
										<div class="flex items-center gap-2 mb-1">
											<span class="font-medium text-maice-text-primary">
												{getSenderLabel(message.sender)}
											</span>
											<span class="text-xs text-maice-text-muted">
												{formatDate(message.created_at)}
											</span>
											<span class="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-700">
												{message.message_type}
											</span>
										</div>
										<div class="text-maice-text-secondary markdown-content">
											<MarkdownRenderer content={message.content} />
										</div>
									</div>
								</div>
							</div>
						</Card>
					{/each}
					
					{#if selectedSessionMessages.length === 0}
						<Card variant="default">
							<div class="p-8 text-center text-maice-text-secondary">
								메시지가 없습니다.
							</div>
						</Card>
					{/if}
				</div>
			</div>
		{/if}
	</div>
</div>

