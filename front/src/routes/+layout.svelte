<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { onMount } from 'svelte';
	import { authStore, authActions } from '$lib/stores/auth';
	import { themeStore, themeActions } from '$lib/stores/theme';
	
	onMount(() => {
		// 페이지 새로고침 시 로컬 스토리지에서 인증 상태 복원
		const savedAuth = localStorage.getItem('maice_auth');
		if (savedAuth) {
			try {
				const authData = JSON.parse(savedAuth);
				authActions.login(authData);
			} catch (error) {
				console.error('저장된 인증 정보를 불러올 수 없습니다:', error);
				localStorage.removeItem('maice_auth');
			}
		}
		
		// 테마 초기화
		const savedTheme = localStorage.getItem('maice_theme');
		if (savedTheme) {
			themeActions.setTheme(savedTheme as 'light' | 'dark' | 'auto');
		}
	});

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<div class="min-h-screen bg-maice-bg text-maice-primary transition-colors duration-300">
	{@render children?.()}
</div>
