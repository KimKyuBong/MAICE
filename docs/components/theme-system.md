# MAICE 테마 시스템 가이드

## 📋 개요

MAICE 테마 시스템은 라이트/다크 테마를 지원하며, 사용자 선호도와 시스템 설정에 따라 자동으로 전환됩니다. Tailwind CSS를 기반으로 한 일관된 디자인 시스템을 제공합니다.

## 🎨 테마 구조

### 1. 테마 타입 정의
```typescript
// lib/types/theme.ts
export type Theme = 'light' | 'dark' | 'auto';

export interface ThemeState {
  current: Theme;
  isDark: boolean;
  systemPrefersDark: boolean;
}
```

### 2. 테마 스토어
```typescript
// lib/stores/theme.ts
import { writable } from 'svelte/store';
import { browser } from '$app/environment';

export const themeStore = writable<ThemeState>({
  current: 'auto',
  isDark: false,
  systemPrefersDark: false
});

export const themeActions = {
  setTheme: (theme: Theme) => {
    themeStore.update(state => ({
      ...state,
      current: theme,
      isDark: theme === 'dark' || (theme === 'auto' && state.systemPrefersDark)
    }));
    
    if (browser) {
      localStorage.setItem('theme', theme);
      updateDocumentClass(theme);
    }
  },
  
  toggleTheme: () => {
    themeStore.update(state => {
      const newTheme = state.isDark ? 'light' : 'dark';
      return {
        ...state,
        current: newTheme,
        isDark: newTheme === 'dark'
      };
    });
  },
  
  initializeTheme: () => {
    if (!browser) return;
    
    const savedTheme = localStorage.getItem('theme') as Theme;
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    const theme = savedTheme || 'auto';
    const isDark = theme === 'dark' || (theme === 'auto' && systemPrefersDark);
    
    themeStore.set({
      current: theme,
      isDark,
      systemPrefersDark
    });
    
    updateDocumentClass(theme);
    
    // 시스템 테마 변경 감지
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
      themeStore.update(state => ({
        ...state,
        systemPrefersDark: e.matches,
        isDark: state.current === 'dark' || (state.current === 'auto' && e.matches)
      }));
    });
  }
};

function updateDocumentClass(theme: Theme) {
  const root = document.documentElement;
  root.classList.remove('light', 'dark');
  
  if (theme === 'auto') {
    root.classList.add(window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  } else {
    root.classList.add(theme);
  }
}
```

## 🎨 디자인 토큰

### 1. 색상 팔레트
```css
/* tailwind.config.js */
module.exports = {
  theme: {
    extend: {
      colors: {
        // 라이트 테마 색상
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        
        // 다크 테마 색상
        dark: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
        }
      }
    }
  }
}
```

### 2. 타이포그래피
```css
/* 폰트 크기 */
.text-xs { font-size: 0.75rem; line-height: 1rem; }
.text-sm { font-size: 0.875rem; line-height: 1.25rem; }
.text-base { font-size: 1rem; line-height: 1.5rem; }
.text-lg { font-size: 1.125rem; line-height: 1.75rem; }
.text-xl { font-size: 1.25rem; line-height: 1.75rem; }
.text-2xl { font-size: 1.5rem; line-height: 2rem; }
.text-3xl { font-size: 1.875rem; line-height: 2.25rem; }
.text-4xl { font-size: 2.25rem; line-height: 2.5rem; }

/* 폰트 두께 */
.font-thin { font-weight: 100; }
.font-light { font-weight: 300; }
.font-normal { font-weight: 400; }
.font-medium { font-weight: 500; }
.font-semibold { font-weight: 600; }
.font-bold { font-weight: 700; }
.font-extrabold { font-weight: 800; }
.font-black { font-weight: 900; }
```

### 3. 간격 시스템
```css
/* 패딩 및 마진 */
.p-0 { padding: 0; }
.p-1 { padding: 0.25rem; }
.p-2 { padding: 0.5rem; }
.p-3 { padding: 0.75rem; }
.p-4 { padding: 1rem; }
.p-5 { padding: 1.25rem; }
.p-6 { padding: 1.5rem; }
.p-8 { padding: 2rem; }
.p-10 { padding: 2.5rem; }
.p-12 { padding: 3rem; }

/* 마진도 동일한 패턴 */
.m-0 { margin: 0; }
.m-1 { margin: 0.25rem; }
/* ... */
```

## 🧩 컴포넌트 테마 적용

### 1. 기본 컴포넌트 스타일
```svelte
<!-- Button.svelte -->
<script>
  export let variant = 'primary';
  export let size = 'md';
  export let disabled = false;
</script>

<button 
  class="
    inline-flex items-center justify-center
    font-medium rounded-lg
    transition-colors duration-200
    focus:outline-none focus:ring-2 focus:ring-offset-2
    disabled:opacity-50 disabled:cursor-not-allowed
    
    {variant === 'primary' ? 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500 dark:bg-blue-500 dark:hover:bg-blue-600' : ''}
    {variant === 'secondary' ? 'bg-gray-200 text-gray-900 hover:bg-gray-300 focus:ring-gray-500 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600' : ''}
    {variant === 'danger' ? 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500 dark:bg-red-500 dark:hover:bg-red-600' : ''}
    
    {size === 'sm' ? 'px-3 py-1.5 text-sm' : ''}
    {size === 'md' ? 'px-4 py-2 text-base' : ''}
    {size === 'lg' ? 'px-6 py-3 text-lg' : ''}
  "
  {disabled}
  on:click
>
  <slot />
</button>
```

### 2. 카드 컴포넌트
```svelte
<!-- Card.svelte -->
<script>
  export let title = '';
  export let subtitle = '';
</script>

<div class="
  bg-white dark:bg-gray-800
  border border-gray-200 dark:border-gray-700
  rounded-lg shadow-sm
  p-6
">
  {#if title}
    <h3 class="
      text-lg font-semibold
      text-gray-900 dark:text-white
      mb-2
    ">
      {title}
    </h3>
  {/if}
  
  {#if subtitle}
    <p class="
      text-sm text-gray-600 dark:text-gray-400
      mb-4
    ">
      {subtitle}
    </p>
  {/if}
  
  <div class="text-gray-700 dark:text-gray-300">
    <slot />
  </div>
</div>
```

### 3. 입력 필드 컴포넌트
```svelte
<!-- Input.svelte -->
<script>
  export let type = 'text';
  export let placeholder = '';
  export let value = '';
  export let error = '';
  export let disabled = false;
</script>

<div class="space-y-1">
  <input
    {type}
    {placeholder}
    {value}
    {disabled}
    class="
      w-full px-3 py-2
      border border-gray-300 dark:border-gray-600
      rounded-md shadow-sm
      bg-white dark:bg-gray-700
      text-gray-900 dark:text-white
      placeholder-gray-500 dark:placeholder-gray-400
      focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
      disabled:opacity-50 disabled:cursor-not-allowed
      {error ? 'border-red-500 focus:ring-red-500 focus:border-red-500' : ''}
    "
    on:input
  />
  
  {#if error}
    <p class="text-sm text-red-600 dark:text-red-400">
      {error}
    </p>
  {/if}
</div>
```

## 🌙 다크 모드 구현

### 1. CSS 변수 활용
```css
/* globals.css */
:root {
  --color-bg-primary: #ffffff;
  --color-bg-secondary: #f8fafc;
  --color-text-primary: #1f2937;
  --color-text-secondary: #6b7280;
  --color-border: #e5e7eb;
}

.dark {
  --color-bg-primary: #0f172a;
  --color-bg-secondary: #1e293b;
  --color-text-primary: #f8fafc;
  --color-text-secondary: #94a3b8;
  --color-border: #374151;
}

.bg-primary {
  background-color: var(--color-bg-primary);
}

.text-primary {
  color: var(--color-text-primary);
}
```

### 2. Tailwind 다크 모드 설정
```javascript
// tailwind.config.js
module.exports = {
  darkMode: 'class', // 'media' 또는 'class'
  theme: {
    extend: {
      colors: {
        // 테마별 색상 정의
      }
    }
  }
}
```

### 3. 테마 전환 애니메이션
```css
/* 부드러운 테마 전환 */
* {
  transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease;
}

/* 다크 모드 전환 시 깜빡임 방지 */
html {
  color-scheme: light dark;
}
```

## 🎛️ 테마 토글 컴포넌트

### 1. 기본 테마 토글
```svelte
<!-- ThemeToggle.svelte -->
<script>
  import { themeStore, themeActions } from '$lib/stores/theme';
  
  let currentTheme = 'auto';
  
  themeStore.subscribe(state => {
    currentTheme = state.current;
  });
  
  function handleThemeChange(event) {
    const theme = event.target.value;
    themeActions.setTheme(theme);
  }
</script>

<div class="flex items-center space-x-2">
  <label for="theme-select" class="text-sm font-medium text-gray-700 dark:text-gray-300">
    테마:
  </label>
  
  <select
    id="theme-select"
    value={currentTheme}
    on:change={handleThemeChange}
    class="
      px-3 py-1
      border border-gray-300 dark:border-gray-600
      rounded-md
      bg-white dark:bg-gray-700
      text-gray-900 dark:text-white
      focus:outline-none focus:ring-2 focus:ring-blue-500
    "
  >
    <option value="light">라이트</option>
    <option value="dark">다크</option>
    <option value="auto">자동</option>
  </select>
</div>
```

### 2. 아이콘 기반 토글
```svelte
<!-- ThemeToggleIcon.svelte -->
<script>
  import { themeStore, themeActions } from '$lib/stores/theme';
  
  let isDark = false;
  
  themeStore.subscribe(state => {
    isDark = state.isDark;
  });
  
  function toggleTheme() {
    themeActions.toggleTheme();
  }
</script>

<button
  on:click={toggleTheme}
  class="
    p-2 rounded-lg
    bg-gray-100 dark:bg-gray-800
    text-gray-600 dark:text-gray-400
    hover:bg-gray-200 dark:hover:bg-gray-700
    focus:outline-none focus:ring-2 focus:ring-blue-500
    transition-colors duration-200
  "
  aria-label={isDark ? '라이트 모드로 전환' : '다크 모드로 전환'}
>
  {#if isDark}
    <!-- 태양 아이콘 -->
    <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
      <path fill-rule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clip-rule="evenodd" />
    </svg>
  {:else}
    <!-- 달 아이콘 -->
    <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
      <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
    </svg>
  {/if}
</button>
```

## 📱 반응형 테마

### 1. 모바일 최적화
```svelte
<!-- 모바일에서 테마 토글 -->
<div class="
  fixed bottom-4 right-4
  md:hidden
  z-50
">
  <ThemeToggleIcon />
</div>

<!-- 데스크톱에서 테마 토글 -->
<div class="
  hidden md:block
  absolute top-4 right-4
">
  <ThemeToggle />
</div>
```

### 2. 접근성 고려사항
```svelte
<!-- 키보드 접근성 -->
<button
  on:click={toggleTheme}
  on:keydown={(e) => e.key === 'Enter' && toggleTheme()}
  tabindex="0"
  role="button"
  aria-label="테마 전환"
>
  테마 토글
</button>
```

## 🔧 테마 개발 가이드

### 1. 새로운 컴포넌트 테마 적용
```svelte
<!-- 새 컴포넌트 개발 시 -->
<div class="
  bg-white dark:bg-gray-800
  text-gray-900 dark:text-white
  border border-gray-200 dark:border-gray-700
  hover:bg-gray-50 dark:hover:bg-gray-700
  focus:ring-blue-500 dark:focus:ring-blue-400
">
  <!-- 컴포넌트 내용 -->
</div>
```

### 2. 테마 테스트
```typescript
// 테마 테스트 예시
import { render } from '@testing-library/svelte';
import { themeStore } from '$lib/stores/theme';
import Component from './Component.svelte';

test('renders correctly in light theme', () => {
  themeStore.set({ current: 'light', isDark: false, systemPrefersDark: false });
  const { container } = render(Component);
  expect(container.firstChild).toHaveClass('bg-white');
});

test('renders correctly in dark theme', () => {
  themeStore.set({ current: 'dark', isDark: true, systemPrefersDark: false });
  const { container } = render(Component);
  expect(container.firstChild).toHaveClass('dark:bg-gray-800');
});
```

### 3. 성능 최적화
```typescript
// 테마 변경 시 성능 최적화
const themeStore = writable<ThemeState>(initialState, () => {
  return () => {
    // 정리 함수
  };
});

// 디바운싱을 통한 테마 변경 최적화
let themeChangeTimeout: NodeJS.Timeout;
export const debouncedSetTheme = (theme: Theme) => {
  clearTimeout(themeChangeTimeout);
  themeChangeTimeout = setTimeout(() => {
    themeActions.setTheme(theme);
  }, 100);
};
```
