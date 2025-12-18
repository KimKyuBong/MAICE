# 프론트엔드 아키텍처

MAICE 시스템의 SvelteKit 기반 프론트엔드 아키텍처를 상세히 설명합니다.

## 🏗️ 전체 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (SvelteKit)                       │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Pages         │   Components    │      Stores & Utils         │
│   (Routes)      │   (Reusable)     │    (State Management)       │
├─────────────────┼─────────────────┼─────────────────────────────┤
│ • / (Login)     │ • Button        │ • authStore                │
│ • /dashboard    │ • Card          │ • themeStore               │
│ • /maice        │ • MessageList   │ • chunkBufferManager        │
│ • /student/*   │ • InlineMathInput│ • maiceAPIClient           │
│ • /teacher      │ • SessionManager│ • errorHandler             │
│ • /admin        │ • ThemeToggle   │ • localStorage             │
└─────────────────┴─────────────────┴─────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │    External Libraries │
                    ├─────────────────────────┤
                    │ • MathLive (수식 입력)  │
                    │ • Tailwind CSS (스타일) │
                    │ • TypeScript (타입)     │
                    │ • Vite (빌드 도구)      │
                    └─────────────────────────┘
```

## 📄 페이지 구조 (Routes)

### 인증 관련 페이지
- **`/` (루트 페이지)**: 로그인 및 Google OAuth 처리
- **`/login`**: 전용 로그인 페이지
- **`/dashboard`**: 사용자 대시보드 (역할별 라우팅)

### 핵심 기능 페이지
- **`/maice`**: 메인 채팅 인터페이스
- **`/student/{token}`**: 학생 전용 인터페이스
- **`/teacher`**: 교사 대시보드
- **`/admin`**: 관리자 패널

### 유틸리티 페이지
- **`/survey`**: 사용자 피드백 설문조사
- **`/test`**: 개발/테스트용 페이지

## 🧩 컴포넌트 아키텍처

### 공통 컴포넌트 (`$lib/components/common/`)
```typescript
// Button.svelte - 재사용 가능한 버튼 컴포넌트
export let variant: 'primary' | 'secondary' | 'danger' = 'primary';
export let size: 'sm' | 'md' | 'lg' = 'md';
export let disabled: boolean = false;
export let loading: boolean = false;

// Card.svelte - 카드 레이아웃 컴포넌트
export let title: string = '';
export let subtitle: string = '';
export let padding: 'sm' | 'md' | 'lg' = 'md';

// ThemeToggle.svelte - 테마 전환 컴포넌트
export let showLabel: boolean = true;
```

### MAICE 전용 컴포넌트 (`$lib/components/maice/`)
```typescript
// MessageList.svelte - 채팅 메시지 목록
export let messages: ChatMessage[] = [];
export let isLoading: boolean = false;
export let onMessageUpdate: (message: ChatMessage) => void;

// InlineMathInput.svelte - MathLive 수식 입력
export let value: string = '';
export let placeholder: string = '수식을 입력하세요';
export let onInput: (value: string) => void;

// SessionManager.svelte - 대화 세션 관리
export let sessions: Session[] = [];
export let currentSessionId: number | null = null;
export let onSessionSelect: (sessionId: number) => void;
```

## 🗄️ 상태 관리 (Stores)

### 인증 상태 관리 (`authStore`)
```typescript
// $lib/stores/auth.ts
interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
}

class AuthStore {
  private state = writable<AuthState>({
    isAuthenticated: false,
    user: null,
    token: null
  });

  async login(authData: AuthData): Promise<void> {
    // 로그인 로직
  }

  async logout(): Promise<void> {
    // 로그아웃 로직
  }

  subscribe(callback: (state: AuthState) => void): Unsubscriber {
    return this.state.subscribe(callback);
  }
}
```

### 테마 상태 관리 (`themeStore`)
```typescript
// $lib/stores/theme.ts
interface ThemeState {
  current: 'light' | 'dark' | 'auto';
  isDark: boolean;
}

class ThemeStore {
  private state = writable<ThemeState>({
    current: 'auto',
    isDark: false
  });

  setTheme(theme: 'light' | 'dark' | 'auto'): void {
    // 테마 변경 로직
  }

  toggleTheme(): void {
    // 테마 토글 로직
  }
}
```

## 🔌 API 통신

### MAICE API 클라이언트 (`maice-client.ts`)
```typescript
// $lib/api/maice-client.ts
export class MaiceAPIClient {
  private baseURL: string;
  private token: string;

  constructor(baseURL: string, token: string) {
    this.baseURL = baseURL;
    this.token = token;
  }

  async submitQuestionStream(
    question: string,
    sessionId?: number,
    handlers?: ChatEventHandlers
  ): Promise<void> {
    // Server-Sent Events를 통한 실시간 스트리밍
  }

  async getSessionHistory(sessionId: number): Promise<Message[]> {
    // 세션 히스토리 조회
  }

  async createNewSession(): Promise<Session> {
    // 새 세션 생성
  }
}
```

### 청크 버퍼 관리 (`chunk-buffer.ts`)
```typescript
// $lib/utils/chunk-buffer.ts
export class ChunkBufferManager {
  private buffers: Map<string, ChunkBuffer> = new Map();

  addChunk(streamId: string, chunk: SSEMessage): void {
    // 청크 순서 정렬 및 버퍼링
  }

  getCompleteMessage(streamId: string): string | null {
    // 완성된 메시지 반환
  }

  clearBuffer(streamId: string): void {
    // 버퍼 정리
  }
}
```

## 🎨 스타일링 아키텍처

### Tailwind CSS 설정
```javascript
// tailwind.config.js
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      colors: {
        'maice': {
          'primary': 'var(--maice-primary)',
          'secondary': 'var(--maice-secondary)',
          'bg': 'var(--maice-bg)',
          'surface': 'var(--maice-surface)',
          'text': 'var(--maice-text)',
          'muted': 'var(--maice-muted)'
        }
      }
    }
  },
  darkMode: 'class'
}
```

### CSS 변수를 통한 테마 시스템
```css
/* src/app.css */
:root {
  --maice-primary: #2563eb;
  --maice-secondary: #64748b;
  --maice-bg: #ffffff;
  --maice-surface: #f8fafc;
  --maice-text: #1e293b;
  --maice-muted: #64748b;
}

[data-theme="dark"] {
  --maice-primary: #3b82f6;
  --maice-secondary: #94a3b8;
  --maice-bg: #0f172a;
  --maice-surface: #1e293b;
  --maice-text: #f1f5f9;
  --maice-muted: #94a3b8;
}
```

## 📱 반응형 디자인

### 브레이크포인트 전략
```css
/* 모바일 우선 접근법 */
.container {
  @apply px-4 sm:px-6 lg:px-8;
}

.chat-interface {
  @apply flex flex-col h-screen;
  @apply md:flex-row;
}

.sidebar {
  @apply w-full md:w-80 lg:w-96;
  @apply hidden md:block;
}
```

### 컴포넌트별 반응형 처리
```typescript
// MessageList.svelte
let isMobile = $state(false);

$effect(() => {
  const checkMobile = () => {
    isMobile = window.innerWidth < 768;
  };
  
  checkMobile();
  window.addEventListener('resize', checkMobile);
  
  return () => window.removeEventListener('resize', checkMobile);
});
```

## 🔧 개발 도구 및 빌드

### Vite 설정
```typescript
// vite.config.ts
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8000'
    }
  },
  build: {
    sourcemap: true
  }
});
```

### TypeScript 설정
```json
// tsconfig.json
{
  "extends": "./.svelte-kit/tsconfig.json",
  "compilerOptions": {
    "allowJs": true,
    "checkJs": true,
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "skipLibCheck": true,
    "sourceMap": true,
    "strict": true
  }
}
```

## 🧪 테스트 전략

### 컴포넌트 테스트
```typescript
// Button.test.ts
import { render, fireEvent } from '@testing-library/svelte';
import Button from '$lib/components/common/Button.svelte';

test('버튼 클릭 이벤트 처리', async () => {
  const { getByRole } = render(Button, {
    props: { variant: 'primary' }
  });
  
  const button = getByRole('button');
  await fireEvent.click(button);
  
  // 테스트 로직
});
```

### E2E 테스트
```typescript
// chat-flow.test.ts
import { test, expect } from '@playwright/test';

test('채팅 플로우 테스트', async ({ page }) => {
  await page.goto('/maice');
  
  // 로그인
  await page.click('[data-testid="google-login"]');
  
  // 질문 입력
  await page.fill('[data-testid="question-input"]', '이차방정식의 해를 구해주세요');
  await page.click('[data-testid="submit-button"]');
  
  // 응답 확인
  await expect(page.locator('[data-testid="ai-response"]')).toBeVisible();
});
```

## 🚀 성능 최적화

### 코드 분할
```typescript
// 지연 로딩 컴포넌트
const MathInput = lazy(() => import('$lib/components/maice/InlineMathInput.svelte'));

// 조건부 렌더링
{#if showMathInput}
  <MathInput />
{/if}
```

### 이미지 최적화
```typescript
// 이미지 최적화 컴포넌트
<script lang="ts">
  import { onMount } from 'svelte';
  
  export let src: string;
  export let alt: string;
  export let width: number;
  export let height: number;
  
  let loaded = $state(false);
  
  onMount(() => {
    const img = new Image();
    img.onload = () => loaded = true;
    img.src = src;
  });
</script>

{#if loaded}
  <img {src} {alt} {width} {height} />
{:else}
  <div class="skeleton-loader" style="width: {width}px; height: {height}px;"></div>
{/if}
```

## 🔗 관련 문서

- [시스템 개요](./overview.md) - 전체 시스템 구조
- [백엔드 아키텍처](./backend-architecture.md) - FastAPI 기반 백엔드 구조
- [프론트엔드 컴포넌트](../components/frontend-components.md) - 상세 컴포넌트 가이드
- [수학 입력 시스템](../components/math-input.md) - MathLive 통합 가이드
