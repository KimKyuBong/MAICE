<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth';
	import { 
		getUsers,
		updateUser,
		updateUserPreferences,
		deleteUser,
		getStudentSessions,
		getSessionMessages,
		type UserInfo,
		type UserPreferences
	} from '$lib/api';
	import Button from '$lib/components/common/Button.svelte';
	import Card from '$lib/components/common/Card.svelte';
	import MarkdownRenderer from '$lib/components/maice/MarkdownRenderer.svelte';
	
	// authStore를 reactive로 사용
	$: authUser = $authStore.user;
	
	let token: string = '';
	let users: UserInfo[] = [];
	let isLoading = false;
	let error: string | null = null;
	
	// 필터링 및 검색
	let roleFilter: string = 'all';
	let searchQuery: string = '';
	
	// 뷰 상태
	let currentView: 'list' | 'sessions' | 'messages' = 'list';
	
	// 세션 관련
	let selectedUser: UserInfo | null = null;
	let selectedUserSessions: any[] = [];
	let selectedSession: any = null;
	let selectedSessionMessages: any[] = [];
	let loadingUserId: number | null = null;
	let loadingSessionId: number | null = null;
	
	// 편집 모달
	let showEditModal = false;
	let editingPreferences: {
		role: string;
		max_questions: number | null;
		remaining_questions: number | null;
		assigned_mode: string;
	} = {
		role: '',
		max_questions: null,
		remaining_questions: null,
		assigned_mode: ''
	};
	
	onMount(() => {
		const unsubscribe = authStore.subscribe(state => {
			if (!state.isAuthenticated || !state.user) {
				goto('/');
				return;
			}
			
			const userRole = state.user.role?.toLowerCase();
			// 관리자만 접근 가능
			if (userRole !== 'admin') {
				goto('/dashboard');
				return;
			}
			
			token = state.token || '';
			
			if (token) {
				loadUsers();
			}
		});
		
		return unsubscribe;
	});
	
	async function loadUsers() {
		if (!token) return;
		
		try {
			isLoading = true;
			error = null;
			
			const roleParam = roleFilter === 'all' ? undefined : roleFilter.toUpperCase();
			users = await getUsers(token, roleParam, 0, 1000);
			
		} catch (err: any) {
			console.error('사용자 목록 로드 실패:', err);
			error = err.message || '사용자 목록을 불러오는데 실패했습니다.';
		} finally {
			isLoading = false;
		}
	}
	
	function openEditModal(user: UserInfo) {
		selectedUser = user;
		editingPreferences = {
			role: user.role ? user.role.toUpperCase() : 'STUDENT',
			max_questions: user.max_questions,
			remaining_questions: user.remaining_questions,
			assigned_mode: user.assigned_mode || ''
		};
		showEditModal = true;
		console.log('✏️ 편집 모달 열림:', { role: editingPreferences.role, user: user.username });
	}
	
	function closeEditModal() {
		showEditModal = false;
		selectedUser = null;
		editingPreferences = {
			role: '',
			max_questions: null,
			remaining_questions: null,
			assigned_mode: ''
		};
	}
	
	async function saveUserPreferences() {
		if (!token || !selectedUser) return;
		
		try {
			isLoading = true;
			
			// 역할이 변경된 경우 사용자 정보 업데이트
			if (editingPreferences.role && editingPreferences.role !== selectedUser.role) {
				await updateUser(token, selectedUser.id, {
					role: editingPreferences.role.toUpperCase()
				});
			}
			
			// 사용자 설정(질문 수, 모드) 업데이트
			const preferences: UserPreferences = {
				max_questions: editingPreferences.max_questions || undefined,
				remaining_questions: editingPreferences.remaining_questions || undefined,
				assigned_mode: editingPreferences.assigned_mode === '' ? null : editingPreferences.assigned_mode
			};
			
			await updateUserPreferences(token, selectedUser.id, preferences);
			
			alert('✅ 사용자 설정이 업데이트되었습니다.');
			closeEditModal();
			await loadUsers();
			
		} catch (err: any) {
			console.error('사용자 설정 업데이트 실패:', err);
			alert('❌ ' + (err.message || '사용자 설정 업데이트에 실패했습니다.'));
		} finally {
			isLoading = false;
		}
	}
	
	async function handleDeleteUser(user: UserInfo) {
		if (!token) return;
		
		// 확인 메시지
		const confirmMessage = `정말로 "${user.username}" 사용자를 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없으며, 해당 사용자의 모든 데이터가 삭제됩니다.`;
		
		if (!confirm(confirmMessage)) {
			return;
		}
		
		try {
			isLoading = true;
			
			await deleteUser(token, user.id);
			
			alert('✅ 사용자가 삭제되었습니다.');
			await loadUsers();
			
		} catch (err: any) {
			console.error('사용자 삭제 실패:', err);
			alert('❌ ' + (err.message || '사용자 삭제에 실패했습니다.'));
		} finally {
			isLoading = false;
		}
	}
	
	async function viewUserSessions(user: UserInfo) {
		if (!token) return;
		
		try {
			loadingUserId = user.id;
			error = null;
			
			const response = await getStudentSessions(token, user.id);
			selectedUser = response.student;
			selectedUserSessions = response.sessions || [];
			currentView = 'sessions';
			selectedSession = null;
			selectedSessionMessages = [];
			
		} catch (err: any) {
			error = err.message || '세션 목록을 불러올 수 없습니다.';
			console.error('세션 목록 로드 실패:', err);
		} finally {
			loadingUserId = null;
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
			currentView = 'messages';
			
		} catch (err: any) {
			error = err.message || '메시지 목록을 불러올 수 없습니다.';
			console.error('메시지 목록 로드 실패:', err);
		} finally {
			loadingSessionId = null;
		}
	}
	
	function backToList() {
		if (currentView === 'messages') {
			currentView = 'sessions';
			selectedSession = null;
			selectedSessionMessages = [];
		} else if (currentView === 'sessions') {
			currentView = 'list';
			selectedUser = null;
			selectedUserSessions = [];
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
		return sender === 'user' ? '사용자' : 'MAICE';
	}
	
	function getRoleLabel(role: string): string {
		const roleUpper = role.toUpperCase();
		if (roleUpper === 'STUDENT') return '학생';
		if (roleUpper === 'TEACHER') return '교사';
		if (roleUpper === 'ADMIN') return '관리자';
		return role;
	}
	
	function getStageLabel(stage: string): string {
		switch (stage) {
			case 'initial': return '초기';
			case 'clarification': return '명료화';
			case 'answering': return '답변 중';
			case 'completed': return '완료';
			default: return stage;
		}
	}
	
	function getModeLabel(mode: string | null): string {
		if (!mode) return '미배정';
		if (mode === 'agent') return '🤖 에이전트';
		if (mode === 'freepass') return '🎯 프리패스';
		return mode;
	}
	
	function getModeBadgeClass(mode: string | null): string {
		if (!mode) return 'badge-neutral';
		if (mode === 'agent') return 'badge-agent';
		if (mode === 'freepass') return 'badge-freepass';
		return 'badge-neutral';
	}
	
	// 필터링된 사용자 목록
	$: filteredUsers = users.filter(user => {
		// 검색어 필터
		if (searchQuery) {
			const query = searchQuery.toLowerCase();
			const matchesSearch = 
				user.username.toLowerCase().includes(query) ||
				(user.google_name || '').toLowerCase().includes(query) ||
				(user.google_email || '').toLowerCase().includes(query);
			if (!matchesSearch) return false;
		}
		return true;
	});
	
	// 통계 계산
	$: stats = {
		total: users.length,
		students: users.filter(u => u.role.toUpperCase() === 'STUDENT').length,
		teachers: users.filter(u => u.role.toUpperCase() === 'TEACHER').length,
		admins: users.filter(u => u.role.toUpperCase() === 'ADMIN').length,
		agentMode: users.filter(u => u.assigned_mode === 'agent').length,
		freepassMode: users.filter(u => u.assigned_mode === 'freepass').length,
		unassigned: users.filter(u => !u.assigned_mode).length
	};
</script>

<div class="admin-page">
	<div class="admin-header">
		<div class="header-content">
			{#if currentView !== 'list'}
				<Button variant="secondary" onclick={backToList} class="mb-2">
					← 뒤로
				</Button>
			{/if}
			<h1>👥 사용자 관리</h1>
			<p class="subtitle">
				{#if currentView === 'list'}
					시스템의 모든 사용자를 관리하고 설정을 변경할 수 있습니다
				{:else if currentView === 'sessions'}
					{selectedUser?.google_name || selectedUser?.username} 사용자의 세션 목록
				{:else if currentView === 'messages'}
					세션 대화 내역
				{/if}
			</p>
		</div>
		<div class="header-actions">
			<Button variant="secondary" onclick={() => goto('/dashboard')}>
				← 대시보드로
			</Button>
		</div>
	</div>
	
	{#if currentView === 'list'}
	<!-- 통계 카드 -->
	<div class="stats-grid">
		<Card className="stat-card">
			<div class="stat-icon">👤</div>
			<div class="stat-content">
				<div class="stat-label">전체 사용자</div>
				<div class="stat-value">{stats.total}</div>
			</div>
		</Card>
		
		<Card className="stat-card">
			<div class="stat-icon">🎓</div>
			<div class="stat-content">
				<div class="stat-label">학생</div>
				<div class="stat-value">{stats.students}</div>
			</div>
		</Card>
		
		<Card className="stat-card">
			<div class="stat-icon">👨‍🏫</div>
			<div class="stat-content">
				<div class="stat-label">교사</div>
				<div class="stat-value">{stats.teachers}</div>
			</div>
		</Card>
		
		<Card className="stat-card">
			<div class="stat-icon">🤖</div>
			<div class="stat-content">
				<div class="stat-label">에이전트 모드</div>
				<div class="stat-value">{stats.agentMode}</div>
			</div>
		</Card>
		
		<Card className="stat-card">
			<div class="stat-icon">🎯</div>
			<div class="stat-content">
				<div class="stat-label">프리패스 모드</div>
				<div class="stat-value">{stats.freepassMode}</div>
			</div>
		</Card>
		
		<Card className="stat-card">
			<div class="stat-icon">⚪</div>
			<div class="stat-content">
				<div class="stat-label">미배정</div>
				<div class="stat-value">{stats.unassigned}</div>
			</div>
		</Card>
	</div>
	
	<!-- 필터 및 검색 -->
	<Card>
		<div class="filter-section">
			<div class="filter-group">
				<label for="role-filter">역할 필터:</label>
				<select 
					id="role-filter"
					bind:value={roleFilter} 
					onchange={() => loadUsers()}
					class="filter-select"
				>
					<option value="all">전체</option>
					<option value="student">학생</option>
					<option value="teacher">교사</option>
					<option value="admin">관리자</option>
				</select>
			</div>
			
			<div class="search-group">
				<input 
					type="text" 
					placeholder="🔍 사용자명, 이메일, 이름으로 검색..." 
					bind:value={searchQuery}
					class="search-input"
				/>
			</div>
		</div>
	</Card>
	
	<!-- 사용자 목록 -->
	<Card>
		{#if isLoading}
			<div class="loading-container">
				<div class="loading-spinner"></div>
				<p>사용자 목록을 불러오는 중...</p>
			</div>
		{:else if error}
			<div class="error-container">
				<p class="error-message">❌ {error}</p>
				<Button onclick={loadUsers}>다시 시도</Button>
			</div>
		{:else if filteredUsers.length === 0}
			<div class="empty-container">
				<p>📭 사용자가 없습니다.</p>
			</div>
		{:else}
			<div class="users-table-container">
				<table class="users-table">
					<thead>
						<tr>
							<th>ID</th>
							<th>사용자명</th>
							<th>역할</th>
							<th>이메일</th>
							<th>질문 수</th>
							<th>세션 수</th>
							<th>최대 질문</th>
							<th>잔여 질문</th>
							<th>배정 모드</th>
							<th>가입일</th>
							<th>작업</th>
						</tr>
					</thead>
					<tbody>
						{#each filteredUsers as user}
							<tr>
								<td>{user.id}</td>
								<td class="username-cell">
									<div class="username">{user.username}</div>
									{#if user.google_name}
										<div class="google-name">{user.google_name}</div>
									{/if}
								</td>
								<td>
									<span class="role-badge role-{user.role.toLowerCase()}">
										{getRoleLabel(user.role)}
									</span>
								</td>
								<td class="email-cell">{user.google_email || '-'}</td>
								<td class="number-cell">{user.question_count}</td>
								<td class="number-cell">{(user as any).session_count ?? 0}</td>
								<td class="number-cell">{user.max_questions ?? '-'}</td>
								<td class="number-cell">{user.remaining_questions ?? '-'}</td>
								<td>
									<span class="mode-badge {getModeBadgeClass(user.assigned_mode)}">
										{getModeLabel(user.assigned_mode)}
									</span>
								</td>
								<td class="date-cell">{new Date(user.created_at).toLocaleDateString('ko-KR')}</td>
								<td class="action-cell">
									<div class="action-buttons">
										<Button 
											variant="primary" 
											size="sm"
											onclick={() => viewUserSessions(user)}
											disabled={loadingUserId === user.id}
										>
											{loadingUserId === user.id ? '로딩...' : '📋 세션'}
										</Button>
										<Button 
											variant="secondary" 
											size="sm"
											onclick={() => openEditModal(user)}
										>
											⚙️ 설정
										</Button>
										<button
											class="delete-button"
											onclick={() => handleDeleteUser(user)}
											disabled={isLoading}
										>
											🗑️ 삭제
										</button>
									</div>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</Card>
	
	{:else if currentView === 'sessions'}
	<!-- 세션 목록 -->
	{#if selectedUser}
		<Card>
			<div class="user-session-header">
				<h2>
					{selectedUser.google_name || selectedUser.username}
				</h2>
				<p>
					이메일: {selectedUser.google_email || selectedUser.username}
				</p>
			</div>
		</Card>
	{/if}
	
	<div class="sessions-grid">
		{#each selectedUserSessions as session}
			<Card>
				<div class="session-card">
					<div class="session-content">
						<div class="session-header">
							<h3>
								{session.title || '제목 없음'}
							</h3>
							<div class="session-info">
								<span>메시지: {session.message_count}개</span>
								<span class="badge-{session.is_active ? 'active' : 'inactive'}">
									{session.is_active ? '활성' : '비활성'}
								</span>
								<span>단계: {getStageLabel(session.current_stage)}</span>
							</div>
							<p class="session-date">
								생성: {formatDate(session.created_at)} | 수정: {formatDate(session.updated_at)}
							</p>
						</div>
						<div class="session-action">
							<Button 
								variant="primary" 
								size="sm"
								onclick={() => viewSessionMessages(session)}
								disabled={loadingSessionId === session.id}
							>
								{loadingSessionId === session.id ? '로딩...' : '대화 보기'}
							</Button>
						</div>
					</div>
				</div>
			</Card>
		{/each}
		
		{#if selectedUserSessions.length === 0}
			<Card>
				<div class="empty-container">
					<p>세션이 없습니다.</p>
				</div>
			</Card>
		{/if}
	</div>
	
	{:else if currentView === 'messages'}
	<!-- 메시지 목록 -->
	{#if selectedSession}
		<Card>
			<div class="session-message-header">
				<h2>
					{selectedSession.title || '제목 없음'}
				</h2>
				<div class="session-info">
					<span class="badge-{selectedSession.is_active ? 'active' : 'inactive'}">
						{selectedSession.is_active ? '활성' : '비활성'}
					</span>
					<span>단계: {getStageLabel(selectedSession.current_stage)}</span>
					<span>생성: {formatDate(selectedSession.created_at)}</span>
				</div>
			</div>
		</Card>
	{/if}
	
	<div class="messages-list">
		{#each selectedSessionMessages as message}
			<Card>
				<div class="message-card">
					<div class="message-wrapper">
						<div class="message-avatar {message.sender === 'user' ? 'avatar-user' : 'avatar-maice'}">
							<span>
								{getSenderLabel(message.sender).charAt(0)}
							</span>
						</div>
						<div class="message-content-wrapper">
							<div class="message-header">
								<span class="message-sender">
									{getSenderLabel(message.sender)}
								</span>
								<span class="message-time">
									{formatDate(message.created_at)}
								</span>
								<span class="message-type-badge">
									{message.message_type}
								</span>
							</div>
							<div class="markdown-content">
								<MarkdownRenderer content={message.content} />
							</div>
						</div>
					</div>
				</div>
			</Card>
		{/each}
		
		{#if selectedSessionMessages.length === 0}
			<Card>
				<div class="empty-container">
					<p>메시지가 없습니다.</p>
				</div>
			</Card>
		{/if}
	</div>
	
	{/if}
</div>

<!-- 편집 모달 -->
{#if showEditModal && selectedUser}
	<div class="modal-overlay" onclick={closeEditModal} role="button" tabindex="-1" onkeydown={(e) => e.key === 'Escape' && closeEditModal()}>
		<div class="modal-content" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.stopPropagation()} role="dialog" tabindex="0">
			<div class="modal-header">
				<h2>⚙️ 사용자 설정 편집</h2>
				<button class="modal-close" onclick={closeEditModal}>×</button>
			</div>
			
			<div class="modal-body">
				<div class="user-info">
					<p><strong>사용자:</strong> {selectedUser.username}</p>
					{#if selectedUser.google_name}
						<p><strong>이름:</strong> {selectedUser.google_name}</p>
					{/if}
					{#if selectedUser.google_email}
						<p><strong>이메일:</strong> {selectedUser.google_email}</p>
					{/if}
				</div>
				
				<div class="form-group">
					<label for="role">사용자 역할:</label>
					<select 
						id="role"
						bind:value={editingPreferences.role}
						class="form-select"
					>
						<option value="STUDENT">🎓 학생</option>
						<option value="TEACHER">👨‍🏫 교사</option>
						<option value="ADMIN">⚙️ 관리자</option>
					</select>
					<p class="form-hint">
						* 관리자: 모든 시스템 설정 및 사용자 관리<br>
						* 교사: 학생 평가 및 통계 조회<br>
						* 학생: 질문 및 답변 이용
					</p>
				</div>
				
				<div class="form-group">
					<label for="max-questions">최대 질문 수:</label>
					<input 
						type="number" 
						id="max-questions"
						bind:value={editingPreferences.max_questions}
						min="0"
						class="form-input"
						placeholder="학생의 최대 질문 횟수"
					/>
					<p class="form-hint">
						* 학생이 질문할 수 있는 최대 횟수를 설정합니다
					</p>
				</div>
				
				<div class="form-group">
					<label for="remaining-questions">잔여 질문 수:</label>
					<input 
						type="number" 
						id="remaining-questions"
						bind:value={editingPreferences.remaining_questions}
						min="0"
						class="form-input"
						placeholder="남은 질문 횟수"
					/>
					<p class="form-hint">
						* 현재 남은 질문 횟수를 직접 설정합니다
					</p>
				</div>
				
				<div class="form-group">
					<label for="assigned-mode">배정 모드:</label>
					<select 
						id="assigned-mode"
						bind:value={editingPreferences.assigned_mode}
						class="form-select"
					>
						<option value="">⚪ 미배정</option>
						<option value="agent">🤖 에이전트</option>
						<option value="freepass">🎯 프리패스</option>
					</select>
					<p class="form-hint">
						* 에이전트: 질문 분석 및 명료화 질문 진행<br>
						* 프리패스: 질문을 그대로 전달하여 즉시 답변<br>
						* 미배정: 첫 질문 시 자동으로 균등 배정
					</p>
				</div>
			</div>
			
			<div class="modal-footer">
				<Button variant="secondary" onclick={closeEditModal}>
					취소
				</Button>
				<Button variant="primary" onclick={saveUserPreferences} disabled={isLoading}>
					💾 저장
				</Button>
			</div>
		</div>
	</div>
{/if}

<style>
	.admin-page {
		max-width: 1400px;
		margin: 0 auto;
		padding: 2rem;
	}
	
	.admin-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 2rem;
	}
	
	.header-content h1 {
		font-size: 2rem;
		font-weight: 700;
		color: var(--maice-text);
		margin: 0 0 0.5rem 0;
	}
	
	.subtitle {
		color: var(--maice-text-secondary);
		margin: 0;
	}
	
	/* 통계 카드 그리드 */
	.stats-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
		gap: 1rem;
		margin-bottom: 2rem;
	}
	
	.stat-card {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 1.5rem !important;
	}
	
	.stat-icon {
		font-size: 2.5rem;
	}
	
	.stat-content {
		flex: 1;
	}
	
	.stat-label {
		font-size: 0.875rem;
		color: var(--maice-text-secondary);
		margin-bottom: 0.25rem;
	}
	
	.stat-value {
		font-size: 1.75rem;
		font-weight: 700;
		color: var(--maice-text);
	}
	
	/* 필터 섹션 */
	.filter-section {
		display: flex;
		gap: 1rem;
		align-items: center;
		flex-wrap: wrap;
	}
	
	.filter-group {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
	
	.filter-group label {
		font-weight: 600;
		color: var(--maice-text);
	}
	
	.filter-select {
		padding: 0.5rem 1rem;
		border: 1px solid var(--maice-border);
		border-radius: 0.375rem;
		background: var(--maice-card-bg) !important;
		color: var(--maice-text) !important;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		/* 브라우저 기본 스타일 오버라이드 */
		-webkit-appearance: none;
		-moz-appearance: none;
		appearance: none;
		/* 커스텀 화살표 */
		background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23666' d='M6 9L1 4h10z'/%3E%3C/svg%3E");
		background-repeat: no-repeat;
		background-position: right 0.5rem center;
		background-size: 10px;
		padding-right: 2rem;
	}
	
	/* 다크 테마에서 화살표 색상 */
	@media (prefers-color-scheme: dark) {
		.filter-select {
			background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23ccc' d='M6 9L1 4h10z'/%3E%3C/svg%3E");
		}
	}
	
	/* Filter select option 스타일 */
	.filter-select option {
		background: var(--maice-card-bg) !important;
		color: var(--maice-text) !important;
		font-weight: 500;
	}
	
	.filter-select:hover {
		border-color: var(--maice-text-muted);
	}
	
	.filter-select:focus {
		outline: none;
		border-color: var(--maice-primary);
		box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
	}
	
	.search-group {
		flex: 1;
		min-width: 300px;
	}
	
	.search-input {
		width: 100%;
		padding: 0.5rem 1rem;
		border: 1px solid var(--maice-border);
		border-radius: 0.375rem;
		background: var(--maice-card-bg);
		color: var(--maice-text);
		font-size: 0.875rem;
	}
	
	/* Search input placeholder */
	.search-input::placeholder {
		color: var(--maice-text-muted);
		opacity: 0.6;
	}
	
	.search-input:hover {
		border-color: var(--maice-text-muted);
	}
	
	.search-input:focus {
		outline: none;
		border-color: var(--maice-primary);
		box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
	}
	
	/* 테이블 */
	.users-table-container {
		overflow-x: auto;
	}
	
	.users-table {
		width: 100%;
		border-collapse: collapse;
	}
	
	.users-table th,
	.users-table td {
		padding: 1rem;
		text-align: left;
		border-bottom: 1px solid var(--maice-border);
	}
	
	.users-table th {
		font-weight: 600;
		color: var(--maice-text);
		background: var(--maice-bg-secondary);
		white-space: nowrap;
	}
	
	.users-table td {
		color: var(--maice-text-secondary);
	}
	
	.username-cell {
		min-width: 150px;
	}
	
	.username {
		font-weight: 600;
		color: var(--maice-text);
	}
	
	.google-name {
		font-size: 0.75rem;
		color: var(--maice-text-muted);
		margin-top: 0.25rem;
	}
	
	.email-cell {
		min-width: 200px;
		font-size: 0.875rem;
	}
	
	.number-cell {
		text-align: center;
	}
	
	.date-cell {
		white-space: nowrap;
		font-size: 0.875rem;
	}
	
	.action-cell {
		text-align: center;
	}
	
	.action-buttons {
		display: flex;
		gap: 0.5rem;
		justify-content: center;
		align-items: center;
	}
	
	.delete-button {
		padding: 0.5rem 0.75rem;
		border: 1px solid #fca5a5;
		border-radius: 0.375rem;
		background: #fef2f2;
		color: #991b1b;
		font-size: 0.875rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.2s;
	}
	
	.delete-button:hover:not(:disabled) {
		background: #fee2e2;
		border-color: #f87171;
	}
	
	.delete-button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
	
	/* 다크 모드 */
	@media (prefers-color-scheme: dark) {
		.delete-button {
			background: #450a0a;
			color: #fca5a5;
			border-color: #991b1b;
		}
		
		.delete-button:hover:not(:disabled) {
			background: #7f1d1d;
			border-color: #dc2626;
		}
	}
	
	/* 뱃지 */
	.role-badge {
		display: inline-block;
		padding: 0.25rem 0.75rem;
		border-radius: 1rem;
		font-size: 0.75rem;
		font-weight: 600;
	}
	
	.role-student {
		background: #dbeafe;
		color: #1e40af;
	}
	
	.role-teacher {
		background: #fef3c7;
		color: #92400e;
	}
	
	.role-admin {
		background: #fee2e2;
		color: #991b1b;
	}
	
	.mode-badge {
		display: inline-block;
		padding: 0.25rem 0.75rem;
		border-radius: 1rem;
		font-size: 0.75rem;
		font-weight: 600;
	}
	
	.badge-agent {
		background: #dcfce7;
		color: #166534;
	}
	
	.badge-freepass {
		background: #e0e7ff;
		color: #3730a3;
	}
	
	.badge-neutral {
		background: var(--maice-bg-secondary);
		color: var(--maice-text-muted);
	}
	
	/* 로딩, 에러, 빈 상태 */
	.loading-container,
	.error-container,
	.empty-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 3rem;
		text-align: center;
	}
	
	.loading-spinner {
		width: 3rem;
		height: 3rem;
		border: 3px solid var(--maice-border);
		border-top-color: var(--maice-primary);
		border-radius: 50%;
		animation: spin 1s linear infinite;
		margin-bottom: 1rem;
	}
	
	@keyframes spin {
		to { transform: rotate(360deg); }
	}
	
	.error-message {
		color: var(--maice-error);
		margin-bottom: 1rem;
	}
	
	/* 세션 및 메시지 뷰 */
	.user-session-header {
		padding: 1.5rem;
	}
	
	.user-session-header h2 {
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--maice-text);
		margin-bottom: 0.5rem;
	}
	
	.user-session-header p {
		color: var(--maice-text-secondary);
		margin: 0;
	}
	
	.sessions-grid {
		display: grid;
		gap: 1rem;
		margin-top: 1rem;
	}
	
	.session-card {
		padding: 1.5rem;
	}
	
	.session-content {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 1rem;
	}
	
	.session-header {
		flex: 1;
	}
	
	.session-header h3 {
		font-size: 1rem;
		font-weight: 600;
		color: var(--maice-text);
		margin-bottom: 0.5rem;
	}
	
	.session-info {
		display: flex;
		gap: 1rem;
		align-items: center;
		flex-wrap: wrap;
		font-size: 0.875rem;
		color: var(--maice-text-secondary);
		margin: 0.5rem 0;
	}
	
	.session-date {
		font-size: 0.75rem;
		color: var(--maice-text-muted);
		margin-top: 0.5rem;
	}
	
	.session-action {
		flex-shrink: 0;
	}
	
	.session-message-header {
		padding: 1.5rem;
	}
	
	.session-message-header h2 {
		font-size: 1.125rem;
		font-weight: 600;
		color: var(--maice-text);
		margin-bottom: 0.5rem;
	}
	
	.badge-active {
		display: inline-block;
		padding: 0.25rem 0.5rem;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		background: #dcfce7;
		color: #166534;
		font-weight: 600;
	}
	
	.badge-inactive {
		display: inline-block;
		padding: 0.25rem 0.5rem;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		background: var(--maice-bg-secondary);
		color: var(--maice-text-muted);
		font-weight: 600;
	}
	
	.messages-list {
		display: grid;
		gap: 0.75rem;
		margin-top: 1rem;
	}
	
	.message-card {
		padding: 1rem;
	}
	
	.message-wrapper {
		display: flex;
		gap: 0.75rem;
		align-items: flex-start;
	}
	
	.message-avatar {
		width: 2rem;
		height: 2rem;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}
	
	.message-avatar span {
		color: white;
		font-size: 0.75rem;
		font-weight: 500;
	}
	
	.avatar-user {
		background: var(--maice-primary);
	}
	
	.avatar-maice {
		background: var(--maice-secondary);
	}
	
	.message-content-wrapper {
		flex: 1;
	}
	
	.message-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.5rem;
		flex-wrap: wrap;
	}
	
	.message-sender {
		font-weight: 500;
		color: var(--maice-text);
	}
	
	.message-time {
		font-size: 0.75rem;
		color: var(--maice-text-muted);
	}
	
	.message-type-badge {
		display: inline-block;
		padding: 0.125rem 0.5rem;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		background: var(--maice-bg-secondary);
		color: var(--maice-text-muted);
	}
	
	.markdown-content {
		line-height: 1.6;
		color: var(--maice-text-secondary);
	}
	
	/* 모달 */
	.modal-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
		padding: 1rem;
	}
	
	.modal-content {
		background: var(--maice-card-bg);
		border-radius: 0.75rem;
		width: 100%;
		max-width: 600px;
		max-height: 90vh;
		overflow-y: auto;
		box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
	}
	
	.modal-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1.5rem;
		border-bottom: 1px solid var(--maice-border);
	}
	
	.modal-header h2 {
		margin: 0;
		font-size: 1.5rem;
		font-weight: 700;
		color: var(--maice-text);
	}
	
	.modal-close {
		background: none;
		border: none;
		font-size: 2rem;
		color: var(--maice-text-secondary);
		cursor: pointer;
		padding: 0;
		width: 2rem;
		height: 2rem;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 0.375rem;
		transition: background 0.2s;
	}
	
	.modal-close:hover {
		background: var(--maice-bg-hover);
	}
	
	.modal-body {
		padding: 1.5rem;
	}
	
	.user-info {
		padding: 1rem;
		background: var(--maice-bg-secondary);
		border-radius: 0.5rem;
		margin-bottom: 1.5rem;
	}
	
	.user-info p {
		margin: 0.5rem 0;
		color: var(--maice-text);
	}
	
	.form-group {
		margin-bottom: 1.5rem;
	}
	
	.form-group label {
		display: block;
		font-weight: 600;
		color: var(--maice-text);
		margin-bottom: 0.5rem;
	}
	
	.form-input,
	.form-select {
		width: 100%;
		padding: 0.75rem;
		border: 1px solid var(--maice-border);
		border-radius: 0.375rem;
		background: var(--maice-card-bg) !important;
		color: var(--maice-text) !important;
		font-size: 1rem;
		font-weight: 500;
		/* 브라우저 기본 스타일 오버라이드 */
		-webkit-appearance: none;
		-moz-appearance: none;
		appearance: none;
	}
	
	/* Select 드롭다운 화살표 커스텀 */
	.form-select {
		background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23666' d='M6 9L1 4h10z'/%3E%3C/svg%3E");
		background-repeat: no-repeat;
		background-position: right 0.75rem center;
		background-size: 12px;
		padding-right: 2.5rem;
	}
	
	/* 다크 테마에서 화살표 색상 */
	@media (prefers-color-scheme: dark) {
		.form-select {
			background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23ccc' d='M6 9L1 4h10z'/%3E%3C/svg%3E");
		}
	}
	
	/* Placeholder 텍스트 색상 (다크/라이트 테마 모두 보이도록) */
	.form-input::placeholder {
		color: var(--maice-text-muted) !important;
		opacity: 0.6;
	}
	
	/* Select option 스타일 (다크 테마에서 보이도록) */
	.form-select option {
		background: var(--maice-card-bg) !important;
		color: var(--maice-text) !important;
		padding: 0.5rem;
		font-weight: 500;
	}
	
	/* Number input 스피너 버튼 색상 */
	.form-input[type="number"]::-webkit-inner-spin-button,
	.form-input[type="number"]::-webkit-outer-spin-button {
		opacity: 0.7;
	}
	
	.form-input:focus,
	.form-select:focus {
		outline: none;
		border-color: var(--maice-primary);
		box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
	}
	
	/* 입력 필드 hover 효과 */
	.form-input:hover,
	.form-select:hover {
		border-color: var(--maice-text-muted);
	}
	
	/* Disabled 상태 */
	.form-input:disabled,
	.form-select:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
	
	.form-hint {
		margin-top: 0.5rem;
		font-size: 0.875rem;
		color: var(--maice-text-muted);
		line-height: 1.6;
	}
	
	.modal-footer {
		display: flex;
		justify-content: flex-end;
		gap: 0.75rem;
		padding: 1.5rem;
		border-top: 1px solid var(--maice-border);
	}
	
	/* 반응형 */
	@media (max-width: 768px) {
		.admin-page {
			padding: 1rem;
		}
		
		.admin-header {
			flex-direction: column;
			align-items: flex-start;
			gap: 1rem;
		}
		
		.stats-grid {
			grid-template-columns: repeat(2, 1fr);
		}
		
		.filter-section {
			flex-direction: column;
			align-items: stretch;
		}
		
		.search-group {
			min-width: 100%;
		}
		
		.users-table {
			font-size: 0.875rem;
		}
		
		.users-table th,
		.users-table td {
			padding: 0.75rem 0.5rem;
		}
	}
</style>
