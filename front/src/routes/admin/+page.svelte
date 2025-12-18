<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	
	onMount(() => {
		// admin 페이지 접속 시 dashboard로 리다이렉트
		goto('/dashboard');
	});
</script>

<div class="loading-container">
	<div class="loading-spinner"></div>
	<p>대시보드로 이동 중...</p>
</div>

<style>
	.loading-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 100vh;
		background: var(--maice-bg);
	}
	
	.loading-container p {
		color: var(--maice-text-secondary);
		margin-top: 1rem;
	}
	
	.loading-spinner {
		width: 3rem;
		height: 3rem;
		border: 3px solid var(--maice-border);
		border-top-color: var(--maice-primary);
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}
	
	@keyframes spin {
		to { transform: rotate(360deg); }
	}
</style>

