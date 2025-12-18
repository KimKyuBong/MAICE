<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth';
	
	onMount(() => {
		console.log('루트 페이지 마운트됨 - 역할별 리다이렉트');
		
		// 이미 로그인된 경우 역할별 페이지로, 아니면 로그인 페이지로
		authStore.subscribe(state => {
			if (state.isAuthenticated && state.user) {
				console.log('이미 로그인됨 - 역할별 페이지로 이동');
				
				// 역할별 리다이렉트
				switch (state.user.role) {
					case 'admin':
					case 'teacher':
						goto('/dashboard');  // 관리자/교사는 대시보드
						break;
					case 'student':
						goto('/maice');  // 학생은 MAICE
						break;
					default:
						goto('/maice');
				}
			} else {
				console.log('로그인 필요 - 로그인 페이지로 이동');
				goto('/login');
			}
		});
	});
</script>

<svelte:head>
	<title>MAICE 시스템</title>
</svelte:head>

<!-- 루트 페이지는 자동으로 리다이렉트됩니다 -->
<div style="min-height: 100vh; display: flex; align-items: center; justify-content: center; background: var(--maice-bg-primary);">
	<p style="color: var(--maice-text-secondary);">리다이렉트 중...</p>
</div>

