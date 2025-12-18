<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth';
	import { getCurrentUser } from '$lib/api';

	let isLoading = true;
	let errorMessage = '';

	onMount(async () => {
		try {
			// URL에서 authorization code 추출
			const urlParams = new URLSearchParams(window.location.search);
			const code = urlParams.get('code');
			const error = urlParams.get('error');

			if (error) {
				throw new Error('Google OAuth 오류: ' + error);
			}

			if (!code) {
				throw new Error('Authorization code가 없습니다.');
			}

			const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '';
			
			// 백엔드에 authorization code 전송하여 JWT 토큰 받기
			const apiUrl = `${apiBaseUrl}/api/auth/google/callback`;
			console.log('API URL:', apiUrl);
			console.log('API Base URL:', apiBaseUrl);
			console.log('Authorization code:', code);
			
			const response = await fetch(apiUrl, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ code })
			});

			if (!response.ok) {
				// 응답이 JSON인지 확인
				const contentType = response.headers.get('content-type');
				console.log('Response Content-Type:', contentType);
				
				if (contentType && contentType.includes('application/json')) {
					const errorData = await response.json();
					throw new Error(errorData.detail || 'Google OAuth 처리 중 오류가 발생했습니다.');
				} else {
					// HTML 응답인 경우
					const htmlText = await response.text();
					console.error('HTML Response:', htmlText.substring(0, 200));
					throw new Error(`서버에서 HTML 응답을 반환했습니다. API URL을 확인하세요: ${apiUrl}`);
				}
			}

			// 응답이 JSON인지 확인
			const contentType = response.headers.get('content-type');
			if (!contentType || !contentType.includes('application/json')) {
				const htmlText = await response.text();
				console.error('Expected JSON but got HTML:', htmlText.substring(0, 200));
				throw new Error(`서버에서 JSON이 아닌 응답을 반환했습니다. API URL을 확인하세요: ${apiUrl}`);
			}

			const data = await response.json();
			const { access_token, user } = data;

			// 사용자 정보를 스토어에 저장
			authStore.update(state => ({
				...state,
				isAuthenticated: true,
				user: {
					id: user.id,
					username: user.username,
					role: user.role,
					access_token: access_token,
					email: user.email,
					name: user.name,
					google_id: user.google_id,
					google_email: user.google_email,
					google_name: user.google_name,
					google_picture: user.google_picture,
					google_verified_email: user.google_verified_email
				},
				token: access_token,  // 토큰 필드 추가!
				loading: false
			}));

			// 로컬 스토리지에 저장
			if (typeof window !== 'undefined') {
				localStorage.setItem('maice_auth', JSON.stringify({
					id: user.id,
					username: user.username,
					role: user.role,
					access_token: access_token,
					email: user.email,
					name: user.name,
					google_id: user.google_id,
					google_email: user.google_email,
					google_name: user.google_name,
					google_picture: user.google_picture,
					google_verified_email: user.google_verified_email
				}));
			}

			// 권한별 리다이렉트
			switch (user.role) {
				case 'admin':
					goto('/admin');
					break;
				case 'teacher':
					goto('/teacher');
					break;
				case 'student':
				default:
					goto('/maice');
					break;
			}

		} catch (error) {
			console.error('Google OAuth 콜백 처리 오류:', error);
			errorMessage = error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다.';
			isLoading = false;
		}
	});
</script>

<div class="auth-callback-container">
	{#if isLoading}
		<div class="loading-spinner">
			<div class="spinner"></div>
			<p>Google 로그인 처리 중...</p>
		</div>
	{:else if errorMessage}
		<div class="error-message">
			<h2>로그인 오류</h2>
			<p>{errorMessage}</p>
			<button on:click={() => goto('/')} class="retry-button">
				다시 시도
			</button>
		</div>
	{/if}
</div>

<style>
	.auth-callback-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 100vh;
		padding: 2rem;
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
	}

	.loading-spinner {
		text-align: center;
		color: white;
	}

	.spinner {
		width: 40px;
		height: 40px;
		border: 4px solid rgba(255, 255, 255, 0.3);
		border-top: 4px solid white;
		border-radius: 50%;
		animation: spin 1s linear infinite;
		margin: 0 auto 1rem;
	}

	@keyframes spin {
		0% { transform: rotate(0deg); }
		100% { transform: rotate(360deg); }
	}

	.error-message {
		background: white;
		padding: 2rem;
		border-radius: 8px;
		box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
		text-align: center;
		max-width: 400px;
	}

	.error-message h2 {
		color: #e53e3e;
		margin-bottom: 1rem;
	}

	.error-message p {
		color: #666;
		margin-bottom: 1.5rem;
	}

	.retry-button {
		background: #667eea;
		color: white;
		border: none;
		padding: 0.75rem 1.5rem;
		border-radius: 4px;
		cursor: pointer;
		font-size: 1rem;
		transition: background-color 0.2s;
	}

	.retry-button:hover {
		background: #5a67d8;
	}
</style>


