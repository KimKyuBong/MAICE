# MAICE 프론트엔드 컴포넌트 가이드

## 📋 개요

MAICE 프론트엔드는 Svelte 5 기반의 모던 웹 애플리케이션으로, 재사용 가능한 컴포넌트들을 통해 일관된 사용자 경험을 제공합니다.

## 🧩 공통 컴포넌트

### 1. Button.svelte
재사용 가능한 버튼 컴포넌트입니다.

#### 사용법
```svelte
<Button variant="primary" size="lg" disabled={false} onclick={handleClick}>
  클릭하세요
</Button>
```

#### Props
- `variant`: "primary" | "secondary" | "danger" | "ghost"
- `size`: "sm" | "md" | "lg"
- `disabled`: boolean
- `onclick`: function

#### 테마 지원
```svelte
<!-- 라이트 테마 -->
<Button variant="primary" class="bg-blue-600 text-white hover:bg-blue-700">
  Primary Button
</Button>

<!-- 다크 테마 -->
<Button variant="primary" class="bg-blue-500 text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700">
  Primary Button
</Button>
```

### 2. Card.svelte
카드 레이아웃 컴포넌트입니다.

#### 사용법
```svelte
<Card title="제목" subtitle="부제목" class="max-w-md">
  <p>카드 내용입니다.</p>
</Card>
```

#### Props
- `title`: string (선택사항)
- `subtitle`: string (선택사항)
- `class`: string (추가 CSS 클래스)

### 3. Input.svelte
입력 필드 컴포넌트입니다.

#### 사용법
```svelte
<Input 
  type="text" 
  placeholder="입력하세요" 
  value={inputValue} 
  on:input={handleInput}
  error={errorMessage}
/>
```

#### Props
- `type`: "text" | "email" | "password" | "number"
- `placeholder`: string
- `value`: string
- `error`: string (에러 메시지)
- `disabled`: boolean

### 4. ThemeToggle.svelte
다크/라이트 테마 전환 컴포넌트입니다.

#### 사용법
```svelte
<ThemeToggle />
```

#### 기능
- 라이트/다크/자동 테마 전환
- 시스템 테마 감지
- 테마 상태 저장

## 🎨 MAICE 전용 컴포넌트

### 1. MessageList.svelte
채팅 메시지 목록을 표시하는 컴포넌트입니다.

#### 사용법
```svelte
<MessageList 
  messages={chatMessages} 
  isLoading={isLoading}
  on:message-action={handleMessageAction}
/>
```

#### Props
- `messages`: ChatMessage[] - 채팅 메시지 배열
- `isLoading`: boolean - 로딩 상태
- `on:message-action`: 메시지 액션 이벤트

#### 메시지 타입
```typescript
interface ChatMessage {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  metadata?: {
    knowledge_code?: string;
    quality?: string;
    latex_expressions?: string[];
  };
}
```

### 2. UnifiedInput.svelte
수식 입력을 지원하는 통합 입력 컴포넌트입니다.

#### 사용법
```svelte
<UnifiedInput 
  placeholder="수학 질문을 입력하세요..."
  value={question}
  on:submit={handleSubmit}
  on:input={handleInput}
  mathMode={true}
/>
```

#### Props
- `placeholder`: string
- `value`: string
- `mathMode`: boolean - 수식 입력 모드 활성화
- `on:submit`: 제출 이벤트
- `on:input`: 입력 이벤트

#### MathLive 통합
```svelte
<script>
  import { MathField } from 'mathlive';
  
  let mathField;
  
  function initializeMathField(element) {
    mathField = new MathField(element, {
      virtualKeyboardMode: 'manual',
      virtualKeyboards: 'all',
      smartFence: true,
      smartSuperscript: true
    });
  }
</script>

<div bind:this={mathFieldElement} use:initializeMathField></div>
```

### 3. SessionManager.svelte
세션 관리를 위한 컴포넌트입니다.

#### 사용법
```svelte
<SessionManager 
  sessions={userSessions}
  currentSession={currentSession}
  on:session-create={handleSessionCreate}
  on:session-select={handleSessionSelect}
  on:session-delete={handleSessionDelete}
/>
```

#### Props
- `sessions`: Session[] - 사용자 세션 목록
- `currentSession`: Session | null - 현재 선택된 세션
- `on:session-create`: 새 세션 생성 이벤트
- `on:session-select`: 세션 선택 이벤트
- `on:session-delete`: 세션 삭제 이벤트

### 4. ChatHeader.svelte
채팅 헤더 컴포넌트입니다.

#### 사용법
```svelte
<ChatHeader 
  title="MAICE 채팅"
  sessionTitle={currentSession?.title}
  user={currentUser}
  on:logout={handleLogout}
  on:settings={handleSettings}
/>
```

#### Props
- `title`: string - 헤더 제목
- `sessionTitle`: string - 현재 세션 제목
- `user`: User - 현재 사용자 정보
- `on:logout`: 로그아웃 이벤트
- `on:settings`: 설정 이벤트

### 5. MarkdownRenderer.svelte
마크다운 렌더링 컴포넌트입니다.

#### 사용법
```svelte
<MarkdownRenderer 
  content={markdownContent}
  enableLatex={true}
  enableCodeHighlight={true}
/>
```

#### Props
- `content`: string - 마크다운 내용
- `enableLatex`: boolean - LaTeX 수식 렌더링 활성화
- `enableCodeHighlight`: boolean - 코드 하이라이팅 활성화

#### LaTeX 수식 지원
```svelte
<script>
  import { renderMath } from 'mathlive';
  
  function renderLatex(content) {
    return renderMath(content, { displayMode: false });
  }
</script>

<div class="markdown-content">
  {@html renderLatex(content)}
</div>
```

### 6. LatexModal.svelte
LaTeX 수식 편집을 위한 모달 컴포넌트입니다.

#### 사용법
```svelte
<LatexModal 
  isOpen={showLatexModal}
  initialValue={latexExpression}
  on:save={handleLatexSave}
  on:close={handleLatexClose}
/>
```

#### Props
- `isOpen`: boolean - 모달 열림 상태
- `initialValue`: string - 초기 LaTeX 수식
- `on:save`: 수식 저장 이벤트
- `on:close`: 모달 닫기 이벤트

## 🎨 테마 시스템

### 1. 테마 컨텍스트
```svelte
<!-- ThemeProvider.svelte -->
<script>
  import { setContext } from 'svelte';
  import { themeStore } from '$lib/stores/theme';
  
  setContext('theme', themeStore);
</script>

<slot />
```

### 2. 테마 훅
```svelte
<!-- useTheme.svelte -->
<script>
  import { getContext } from 'svelte';
  
  export const theme = getContext('theme');
</script>
```

### 3. 테마 적용 예시
```svelte
<!-- 컴포넌트에서 테마 사용 -->
<script>
  import { useTheme } from '$lib/hooks/useTheme';
  
  const { theme } = useTheme();
</script>

<div class="bg-white dark:bg-gray-900 text-gray-900 dark:text-white">
  <h1 class="text-2xl font-bold">제목</h1>
  <p class="text-gray-600 dark:text-gray-300">내용</p>
</div>
```

## 📱 반응형 디자인

### 1. 브레이크포인트
```css
/* Tailwind CSS 브레이크포인트 */
sm: 640px   /* 모바일 */
md: 768px   /* 태블릿 */
lg: 1024px  /* 데스크톱 */
xl: 1280px  /* 대형 데스크톱 */
2xl: 1536px /* 초대형 데스크톱 */
```

### 2. 반응형 컴포넌트 예시
```svelte
<div class="
  w-full 
  sm:w-1/2 
  md:w-1/3 
  lg:w-1/4 
  xl:w-1/5
">
  <Card>
    <p>반응형 카드</p>
  </Card>
</div>
```

## 🔧 컴포넌트 개발 가이드

### 1. 컴포넌트 구조
```svelte
<!-- ComponentName.svelte -->
<script lang="ts">
  // 타입 정의
  interface Props {
    // props 타입 정의
  }
  
  // props 선언
  export let prop1: string;
  export let prop2: number = 0;
  
  // 이벤트 정의
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();
  
  // 함수 정의
  function handleClick() {
    dispatch('click', { data: 'example' });
  }
</script>

<!-- HTML 템플릿 -->
<div class="component-container">
  <!-- 컴포넌트 내용 -->
</div>

<!-- 스타일 -->
<style>
  .component-container {
    /* 컴포넌트 스타일 */
  }
</style>
```

### 2. 접근성 고려사항
```svelte
<!-- 접근성 속성 추가 -->
<button 
  aria-label="메뉴 열기"
  aria-expanded={isOpen}
  role="button"
  tabindex="0"
  on:click={handleClick}
  on:keydown={handleKeydown}
>
  메뉴
</button>
```

### 3. 테스트 작성
```typescript
// ComponentName.test.ts
import { render, fireEvent } from '@testing-library/svelte';
import ComponentName from './ComponentName.svelte';

describe('ComponentName', () => {
  test('renders correctly', () => {
    const { getByText } = render(ComponentName, {
      props: { prop1: 'test' }
    });
    
    expect(getByText('test')).toBeInTheDocument();
  });
  
  test('handles click events', () => {
    const { getByRole } = render(ComponentName);
    const button = getByRole('button');
    
    fireEvent.click(button);
    // 이벤트 테스트
  });
});
```

## 📚 컴포넌트 라이브러리

### 1. 컴포넌트 목록
- **공통 컴포넌트**: Button, Card, Input, ThemeToggle
- **MAICE 컴포넌트**: MessageList, UnifiedInput, SessionManager, ChatHeader, MarkdownRenderer, LatexModal
- **레이아웃 컴포넌트**: Header, Sidebar, Footer, Container
- **폼 컴포넌트**: Form, Field, Select, Checkbox, Radio

### 2. 컴포넌트 문서화
각 컴포넌트는 다음 정보를 포함해야 합니다:
- 사용법 및 예시
- Props 타입 정의
- 이벤트 정의
- 스타일 가이드
- 접근성 고려사항
- 테스트 케이스

### 3. 컴포넌트 버전 관리
- 시맨틱 버저닝 사용
- Breaking change 문서화
- 마이그레이션 가이드 제공
