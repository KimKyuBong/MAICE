<script lang="ts">
	import Button from '$lib/components/common/Button.svelte';
	import Card from '$lib/components/common/Card.svelte';
	import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
	import { themeStore } from '$lib/stores/theme';
	import { authStore } from '$lib/stores/auth';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { googleLogin } from '$lib/api';
	
	let currentTheme = 'auto';
	let isDark = false;
	let isLoading = false;
	let errorMessage = '';
	
	// 테마 상태 구독
	themeStore.subscribe(state => {
		currentTheme = state.current;
		isDark = state.isDark;
	});
	
	onMount(() => {
		console.log('로그인 페이지 마운트됨');
		// 이미 로그인된 경우 대시보드로 리다이렉트
		authStore.subscribe(state => {
			if (state.isAuthenticated) {
				goto('/dashboard');
			}
		});
		
		// Google OAuth 콜백 처리
		const urlParams = new URLSearchParams(window.location.search);
		const token = urlParams.get('token');
		
		if (token) {
			// Google OAuth 콜백에서 토큰을 받은 경우
			handleGoogleCallback(token);
		}
	});
	
	async function handleGoogleCallback(token: string) {
		try {
			isLoading = true;
			errorMessage = '';
			
			// JWT 토큰으로 사용자 정보 조회
			import('$lib/stores/auth').then(({ authActions }) => {
				authActions.loginWithToken(token).then(() => {
					// URL에서 토큰 파라미터 제거
					const url = new URL(window.location.href);
					url.searchParams.delete('token');
					window.history.replaceState({}, '', url.toString());
					
					// 역할에 따라 적절한 페이지로 리다이렉트
					authStore.subscribe((state) => {
						if (state.user) {
							switch (state.user.role) {
								case 'admin':
									goto('/dashboard');  // 관리자도 대시보드로
									break;
								case 'teacher':
									goto('/dashboard');  // 교사도 대시보드로
									break;
								case 'student':
									goto('/maice');  // 학생은 MAICE로
									break;
								default:
									goto('/maice');
							}
						}
					});
				}).catch((error) => {
					console.error('Google OAuth 콜백 처리 오류:', error);
					errorMessage = 'Google 로그인 처리 중 오류가 발생했습니다.';
				}).finally(() => {
					isLoading = false;
				});
			});
		} catch (error) {
			console.error('Google OAuth 콜백 오류:', error);
			errorMessage = 'Google 로그인 처리 중 오류가 발생했습니다.';
			isLoading = false;
		}
	}
	
	async function handleGoogleLogin() {
		try {
			console.log('Google 로그인 버튼 클릭됨');
			isLoading = true;
			errorMessage = '';
			console.log('googleLogin 함수 호출 중...');
			await googleLogin();
			console.log('googleLogin 함수 호출 완료');
		} catch (error) {
			console.error('Google 로그인 오류:', error);
			errorMessage = 'Google 로그인 중 오류가 발생했습니다.';
			isLoading = false;
		}
	}
</script>

<svelte:head>
	<title>MAICE 시스템 - 로그인</title>
</svelte:head>

<div class="login-page">
	<div class="login-container">
		<!-- 로고 및 제목 영역 -->
		<div class="login-header">
			<div class="logo-container">
				<h1 class="logo-title">MAICE</h1>
			</div>
			<p class="login-subtitle">AI 기반 학습 도우미 시스템</p>
		</div>
		
		<!-- 로그인 폼 -->
		<Card variant="elevated" className="maice-card">
			<div class="form-header">
				<h2 class="form-title">로그인</h2>
				<p class="form-description">Google 계정으로 MAICE 시스템에 로그인하세요</p>
			</div>
			
			{#if errorMessage}
				<div class="error-message">
					{errorMessage}
				</div>
			{/if}
			
			<!-- Google 로그인 버튼 -->
			<div class="google-login-section">
				<Button
					variant="primary"
					size="lg"
					fullWidth={true}
					onclick={handleGoogleLogin}
					disabled={isLoading}
				>
					{#if isLoading}
						<div class="loading-spinner"></div>
						<span>로그인 중...</span>
					{:else}
						<svg class="google-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
							<path fill="#ffffff" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
							<path fill="#ffffff" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
							<path fill="#ffffff" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
							<path fill="#ffffff" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
						</svg>
						Google로 로그인
					{/if}
				</Button>
			</div>
			
			<!-- 로그인 안내 -->
			<div class="login-info">
				<h3 class="login-info-title">로그인 안내</h3>
				<div class="info-list">
					<div class="info-item">
						<span class="info-role">관리자</span>
						<span class="info-desc">시스템 관리 및 사용자 관리</span>
					</div>
					<div class="info-item">
						<span class="info-role">교사</span>
						<span class="info-desc">질문 평가 및 피드백</span>
					</div>
					<div class="info-item">
						<span class="info-role">학생</span>
						<span class="info-desc">질문 작성 및 설문 응답</span>
					</div>
				</div>
			</div>
		</Card>
		
		<!-- 테마 토글 -->
		<div class="theme-toggle-container">
			<ThemeToggle />
		</div>
	</div>
</div>

<style>
	.login-page {
		min-height: 100vh;
		background: var(--maice-bg-primary);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2rem 1rem;
	}
	
	.login-container {
		width: 100%;
		max-width: 420px;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2rem;
	}
	
	/* 헤더 영역 */
	.login-header {
		text-align: center;
		margin-bottom: 1rem;
		position: relative;
		padding: 2rem 0;
	}
	
	/* 배경 아이콘 - 점점 밝아지는 효과 */
	.login-header::before {
		content: '';
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		width: 200px;
		height: 200px;
		background-image: url('/icon.png');
		background-size: contain;
		background-repeat: no-repeat;
		background-position: center;
		opacity: 0;
		z-index: 0;
		pointer-events: none;
		animation: fadeInIcon 1.5s ease-out forwards;
	}
	
	/* 점점 밝아지는 애니메이션 */
	@keyframes fadeInIcon {
		0% {
			opacity: 0;
			transform: translate(-50%, -50%) scale(0.95);
		}
		100% {
			opacity: 0.18;
			transform: translate(-50%, -50%) scale(1);
		}
	}
	
	/* 다크모드에서 배경 아이콘 더 진하게 */
	:global(.dark) .login-header::before {
		animation: fadeInIconDark 1.5s ease-out forwards;
	}
	
	@keyframes fadeInIconDark {
		0% {
			opacity: 0;
			transform: translate(-50%, -50%) scale(0.95);
		}
		100% {
			opacity: 0.25;
			transform: translate(-50%, -50%) scale(1);
		}
	}
	
	.logo-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		margin-bottom: 1rem;
		position: relative;
		z-index: 1;
	}
	
	.logo-title {
		font-size: 2.5rem;
		font-weight: 800;
		color: var(--maice-text-primary);
		margin: 0;
		letter-spacing: -0.025em;
	}
	
	.login-subtitle {
		font-size: 1rem;
		color: var(--maice-text-secondary);
		margin: 0;
		font-weight: 400;
		position: relative;
		z-index: 1;
	}
	
	/* 로그인 폼 카드 */
	
	.form-header {
		text-align: center;
		margin-bottom: 2rem;
	}
	
	.form-title {
		font-size: 1.75rem;
		font-weight: 700;
		color: var(--maice-text-primary);
		margin: 0 0 0.5rem 0;
	}
	
	.form-description {
		font-size: 0.875rem;
		color: var(--maice-text-secondary);
		margin: 0;
		line-height: 1.5;
	}
	
	/* Google 로그인 섹션 */
	.google-login-section {
		margin-bottom: 1.5rem;
		margin-top: 0.5rem;
	}
	
	/* Google 로그인 버튼 스타일 */
	.google-login-section :global(.maice-btn) {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
	}
	
	.google-icon {
		width: 20px;
		height: 20px;
	}
	
	/* 다크 모드에서도 흰색 아이콘 유지 */
	:global(.dark) .google-icon path {
		fill: #ffffff;
	}
	
	.loading-spinner {
		width: 1rem;
		height: 1rem;
		border: 2px solid transparent;
		border-top: 2px solid currentColor;
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}
	
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
	
	.error-message {
		background: #fef2f2;
		border: 1px solid #fecaca;
		color: #dc2626;
		padding: 0.75rem;
		border-radius: 0.5rem;
		font-size: 0.875rem;
		text-align: center;
		margin-bottom: 1.5rem;
	}
	
	/* 로그인 안내 */
	.login-info {
		margin-top: 2rem;
		padding-top: 1.5rem;
		border-top: 1px solid var(--maice-border-primary);
	}
	
	.login-info-title {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--maice-text-secondary);
		margin: 0 0 1rem 0;
		text-align: center;
	}
	
	.info-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}
	
	.info-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem;
		background: var(--maice-bg-secondary);
		border-radius: 0.5rem;
		border: 1px solid var(--maice-border-secondary);
	}
	
	.info-role {
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--maice-text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	
	.info-desc {
		font-size: 0.75rem;
		color: var(--maice-text-primary);
		text-align: right;
	}
	
	/* 테마 토글 */
	.theme-toggle-container {
		display: flex;
		justify-content: center;
	}
	
	/* 반응형 디자인 */
	@media (max-width: 480px) {
		.login-container {
			padding: 1rem;
		}
		
		.logo-title {
			font-size: 2rem;
		}
	}
</style>

