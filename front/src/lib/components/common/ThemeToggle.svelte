<script lang="ts">
	import { themeStore, themeActions, type Theme } from '$lib/stores/theme';
	import Button from './Button.svelte';
	
	let currentTheme: Theme = $state('auto');
	let isDark = $state(false);
	
	// 테마 상태 구독
	$effect(() => {
		const unsubscribe = themeStore.subscribe((state: any) => {
			currentTheme = state.current;
			isDark = state.isDark;
		});
		
		return unsubscribe;
	});
	
	function handleThemeToggle() {
		themeActions.toggleTheme();
	}
</script>

<div class="maice-theme-toggle">
	<!-- 테마 토글 버튼 -->
	<Button 
		variant="ghost" 
		size="sm" 
		className="maice-theme-toggle-btn"
		onclick={handleThemeToggle}
	>
		{#if isDark}
			<!-- 현재 다크 모드일 때 - 라이트 모드로 전환 -->
			<svg class="maice-theme-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"></path>
			</svg>
			<span class="maice-theme-text">라이트로 전환</span>
		{:else}
			<!-- 현재 라이트 모드일 때 - 다크 모드로 전환 -->
			<svg class="maice-theme-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"></path>
			</svg>
			<span class="maice-theme-text">다크로 전환</span>
		{/if}
	</Button>
</div>

<style>
	.maice-theme-toggle {
		display: flex;
		align-items: center;
	}

	.maice-theme-icon {
		width: 1.25rem;
		height: 1.25rem;
	}

	.maice-theme-text {
		font-size: 0.875rem;
		font-weight: 500;
	}
</style>
