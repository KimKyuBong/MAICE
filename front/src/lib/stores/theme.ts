import { writable } from 'svelte/store';

export type Theme = 'light' | 'dark' | 'auto';

interface ThemeState {
	current: Theme;
	isDark: boolean;
}

// 시스템 테마 감지
function getSystemTheme(): boolean {
	if (typeof window === 'undefined') return false;
	return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

// 로컬 스토리지에서 테마 복원
function getInitialTheme(): Theme {
	if (typeof window === 'undefined') return 'auto';
	return (localStorage.getItem('maice_theme') as Theme) || 'auto';
}

// 초기 상태 설정
function getInitialState(): ThemeState {
	const theme = getInitialTheme();
	const isDark = theme === 'auto' ? getSystemTheme() : theme === 'dark';
	
	return {
		current: theme,
		isDark
	};
}

export const themeStore = writable<ThemeState>(getInitialState());

// 테마 액션들
export const themeActions = {
	setTheme: (theme: Theme) => {
		const isDark = theme === 'auto' ? getSystemTheme() : theme === 'dark';
		
		// 로컬 스토리지에 저장
		if (typeof window !== 'undefined') {
			localStorage.setItem('maice_theme', theme);
		}
		
		// HTML 클래스 업데이트
		updateHtmlClass(isDark);
		
		// 스토어 업데이트
		themeStore.update(state => ({
			...state,
			current: theme,
			isDark
		}));
	},
	
	toggleTheme: () => {
		themeStore.update(state => {
			// 현재 테마에 따라 다음 테마 결정
			let newTheme: Theme;
			if (state.current === 'auto') {
				// auto 모드에서는 현재 다크/라이트 상태를 기반으로 토글
				newTheme = state.isDark ? 'light' : 'dark';
			} else {
				// light/dark 모드에서는 서로 토글
				newTheme = state.current === 'light' ? 'dark' : 'light';
			}
			
			const isDark = newTheme === 'dark';
			
			// 로컬 스토리지에 저장
			if (typeof window !== 'undefined') {
				localStorage.setItem('maice_theme', newTheme);
			}
			
			// HTML 클래스 업데이트
			updateHtmlClass(isDark);
			
			return {
				current: newTheme,
				isDark
			};
		});
	},
	
	updateSystemTheme: () => {
		themeStore.update(state => {
			if (state.current === 'auto') {
				const isDark = getSystemTheme();
				updateHtmlClass(isDark);
				return { ...state, isDark };
			}
			return state;
		});
	}
};

// HTML 클래스 업데이트 - CSS 변수를 사용하므로 모든 요소가 자동으로 동시에 반응
function updateHtmlClass(isDark: boolean) {
	if (typeof document === 'undefined') return;
	
	const html = document.documentElement;
	
	// CSS 변수가 :root.dark 클래스에 의해 바뀌므로 모든 요소가 동시에 transition 시작
	if (isDark) {
		html.classList.remove('light');
		html.classList.add('dark');
	} else {
		html.classList.remove('dark');
		html.classList.add('light');
	}
}

// 시스템 테마 변경 감지
if (typeof window !== 'undefined') {
	const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
	mediaQuery.addEventListener('change', () => {
		themeActions.updateSystemTheme();
	});
}

// 초기 HTML 클래스 설정 (DOM이 준비된 후)
if (typeof document !== 'undefined') {
	// DOMContentLoaded 이벤트를 기다려서 초기화
	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', () => {
			const initialState = getInitialState();
			updateHtmlClass(initialState.isDark);
		});
	} else {
		// DOM이 이미 준비된 경우 즉시 실행
		const initialState = getInitialState();
		updateHtmlClass(initialState.isDark);
	}
}
