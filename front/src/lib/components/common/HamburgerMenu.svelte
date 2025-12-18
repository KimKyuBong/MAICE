<script lang="ts">
	import { slide } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';
	import Button from './Button.svelte';
	import ThemeToggle from './ThemeToggle.svelte';

	// Props
	let { 
		isOpen = $bindable(false),
		user = $bindable(null),
		onBackToDashboard = () => {},
		onClearChat = () => {},
		onToggleSession = () => {},
		onLogin = () => {},
		onLogout = () => {}
	}: {
		isOpen?: boolean;
		user?: any;
		onBackToDashboard?: () => void;
		onClearChat?: () => void;
		onToggleSession?: () => void;
		onLogin?: () => void;
		onLogout?: () => void;
	} = $props();

	// 메뉴 항목 클릭 핸들러
	function handleMenuClick(action: () => void) {
		action();
		isOpen = false;
	}
</script>

{#if isOpen}
	<div 
		class="hamburger-menu" 
		transition:slide={{ duration: 200, easing: quintOut }}
		onclick={(e) => e.stopPropagation()} 
		onkeydown={(e) => e.key === 'Escape' && (isOpen = false)} 
		role="menu" 
		tabindex="-1"
	>
		<div class="hamburger-menu-content">
			<!-- 기본 메뉴 항목들 -->
			<Button 
				variant="ghost" 
				size="sm" 
				onclick={() => handleMenuClick(onBackToDashboard)} 
				class="menu-item"
			>
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M19 12H5M12 19l-7-7 7-7"/>
				</svg>
				대시보드
			</Button>
			
			<Button 
				variant="secondary" 
				size="sm" 
				onclick={() => handleMenuClick(onClearChat)}
				class="menu-item"
			>
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
					<path d="M3 3v5h5"/>
				</svg>
				새 대화
			</Button>
			
			<Button 
				variant="ghost" 
				size="sm" 
				onclick={() => handleMenuClick(onToggleSession)}
				class="menu-item"
			>
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
				</svg>
				세션
			</Button>
			
			<!-- 사용자 정보 및 인증 관련 -->
			{#if user}
				<div class="menu-user-info">
					<div class="user-avatar">
						{#if user.google_picture}
							<img src={user.google_picture} alt="프로필" />
						{:else}
							<span class="avatar-text">
								{user.name ? user.name.charAt(0).toUpperCase() : user.username.charAt(0).toUpperCase()}
							</span>
						{/if}
					</div>
					<div class="user-details">
						<span class="user-name">{user.name || user.username}</span>
						<span class="user-role">
							{user.role === 'student' ? '학생' : user.role === 'teacher' ? '교사' : '관리자'}
						</span>
					</div>
				</div>
				
				<Button 
					variant="ghost" 
					size="sm" 
					onclick={() => handleMenuClick(onLogout)} 
					class="menu-item"
				>
					<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>
					</svg>
					로그아웃
				</Button>
			{:else}
				<Button 
					variant="primary" 
					size="sm" 
					onclick={() => handleMenuClick(onLogin)} 
					class="menu-item"
				>
					<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>
					</svg>
					로그인
				</Button>
			{/if}
			
			<!-- 테마 설정 -->
			<div class="menu-theme">
				<ThemeToggle />
			</div>
		</div>
	</div>
{/if}

<style>
	/* 햄버거 메뉴 스타일 */
	.hamburger-menu {
		position: absolute;
		top: calc(100% + 8px);
		right: 0;
		background: var(--maice-bg-primary);
		border: 1px solid var(--maice-border-primary);
		border-radius: var(--maice-spacing-sm);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
		z-index: 1000;
		min-width: 200px;
		width: max-content;
		overflow: hidden;
	}

	/* 햄버거 메뉴 콘텐츠 */
	.hamburger-menu-content {
		padding: 8px;
		display: flex;
		flex-direction: column;
		gap: 0;
		width: 100%;
	}

	/* 메뉴 아이템 공통 스타일 */
	:global(.hamburger-menu .menu-item) {
		display: flex !important;
		align-items: center;
		justify-content: flex-start;
		gap: 8px;
		width: 100%;
		padding: 8px 12px;
		min-height: 36px;
		height: auto;
		font-size: 0.8125rem;
		font-weight: 500;
		text-align: left;
		border-radius: 4px;
		margin-bottom: 2px;
		transition: background-color 0.2s ease;
	}

	:global(.hamburger-menu .menu-item:hover) {
		background-color: var(--maice-bg-secondary);
	}

	:global(.hamburger-menu .menu-item svg) {
		flex-shrink: 0;
		width: 14px;
		height: 14px;
	}

	/* 사용자 정보 섹션 */
	.menu-user-info {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 8px 12px;
		border-bottom: 1px solid var(--maice-border-primary);
		margin-bottom: 4px;
		border-radius: 4px;
		background: var(--maice-bg-secondary);
	}

	.user-avatar {
		width: 28px;
		height: 28px;
		border-radius: 50%;
		background: var(--maice-primary);
		display: flex;
		align-items: center;
		justify-content: center;
		color: white;
		font-weight: 600;
		font-size: 0.75rem;
		overflow: hidden;
		flex-shrink: 0;
	}

	.user-avatar img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.avatar-text {
		font-size: 0.875rem;
		font-weight: 600;
	}

	.user-details {
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
		flex: 1;
	}

	.user-name {
		font-size: 0.8125rem;
		font-weight: 600;
		color: var(--maice-text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.user-role {
		font-size: 0.6875rem;
		color: var(--maice-text-secondary);
		white-space: nowrap;
	}

	/* 테마 토글 섹션 */
	.menu-theme {
		padding: 8px 12px;
		border-top: 1px solid var(--maice-border-primary);
		margin-top: 4px;
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.menu-theme::before {
		content: "테마";
		font-size: 0.8125rem;
		font-weight: 500;
		color: var(--maice-text-secondary);
	}

	/* 모바일 대응 */
	@media (max-width: 768px) {
		.hamburger-menu {
			position: fixed;
			top: 68px;
			right: 8px;
			min-width: 240px;
			max-width: 85vw;
		}

		:global(.hamburger-menu .menu-item) {
			padding: 10px 12px !important;
			min-height: 40px !important;
			font-size: 0.8125rem !important;
			margin-bottom: 2px !important;
		}

		.menu-user-info {
			padding: 10px 12px !important;
			margin-bottom: 4px !important;
		}

		.user-avatar {
			width: 30px !important;
			height: 30px !important;
		}

		.menu-theme {
			padding: 10px 12px !important;
			margin-top: 4px !important;
		}
	}

	@media (max-width: 480px) {
		.hamburger-menu {
			top: 60px;
		}
	}
</style>

