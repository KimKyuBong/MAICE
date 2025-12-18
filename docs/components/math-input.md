# 수학 입력 시스템

MAICE 시스템의 MathLive 기반 수학 입력 시스템을 상세히 설명합니다.

## 🎯 개요

MAICE는 MathLive 라이브러리를 활용하여 고등학교 수학 수준의 복잡한 수식을 입력할 수 있는 인터페이스를 제공합니다.

## 📚 MathLive 참조 문서

개발 시 반드시 공식 문서를 참조하세요:
- **API 참조**: https://mathlive.io/mathfield/api/
- **커스터마이징 가이드**: https://mathlive.io/mathfield/guides/customizing/
- **상호작용 가이드**: https://mathlive.io/mathfield/guides/interacting/

## 🧩 컴포넌트 구조

### InlineMathInput 컴포넌트

```typescript
// $lib/components/maice/InlineMathInput.svelte
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { MathField } from 'mathlive';
  
  export let value: string = '';
  export let placeholder: string = '수식을 입력하세요';
  export let onInput: (value: string) => void;
  export let disabled: boolean = false;
  export let theme: 'light' | 'dark' = 'light';
  
  let mathField: MathField | null = null;
  let container: HTMLDivElement;
  
  onMount(() => {
    // MathField 초기화
    mathField = new MathField(container, {
      virtualKeyboardMode: 'manual',
      virtualKeyboards: ['numeric', 'functions', 'greek', 'geometry'],
      smartFence: true,
      smartSuperscript: true,
      removeExtraneousParentheses: true,
      defaultMode: 'math',
      macros: {
        // 커스텀 매크로 정의
        '\\RR': '\\mathbb{R}',
        '\\NN': '\\mathbb{N}',
        '\\ZZ': '\\mathbb{Z}',
        '\\QQ': '\\mathbb{Q}',
        '\\CC': '\\mathbb{C}'
      }
    });
    
    // 이벤트 리스너 등록
    mathField.addEventListener('input', handleInput);
    mathField.addEventListener('change', handleChange);
    
    // 초기값 설정
    if (value) {
      mathField.value = value;
    }
  });
  
  onDestroy(() => {
    if (mathField) {
      mathField.dispose();
    }
  });
  
  function handleInput(event: CustomEvent) {
    const newValue = event.detail.value;
    value = newValue;
    onInput?.(newValue);
  }
  
  function handleChange(event: CustomEvent) {
    const newValue = event.detail.value;
    value = newValue;
    onInput?.(newValue);
  }
  
  // 외부에서 값 변경 시 동기화
  $: if (mathField && mathField.value !== value) {
    mathField.value = value;
  }
</script>

<div 
  bind:this={container}
  class="math-input-container"
  class:disabled
  data-theme={theme}
></div>

<style>
  .math-input-container {
    border: 2px solid var(--maice-border);
    border-radius: 8px;
    padding: 12px;
    min-height: 48px;
    background: var(--maice-surface);
    transition: border-color 0.2s ease;
  }
  
  .math-input-container:focus-within {
    border-color: var(--maice-primary);
    box-shadow: 0 0 0 3px var(--maice-primary-light);
  }
  
  .math-input-container.disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  
  /* MathLive 스타일 커스터마이징 */
  :global(.ML__fieldcontainer) {
    font-size: 16px;
    line-height: 1.5;
  }
  
  :global(.ML__fieldcontainer:focus) {
    outline: none;
  }
  
  /* 다크 테마 지원 */
  [data-theme="dark"] :global(.ML__fieldcontainer) {
    color: var(--maice-text);
  }
  
  [data-theme="dark"] :global(.ML__fieldcontainer .ML__base) {
    color: var(--maice-text);
  }
</style>
```

## 🎨 테마 지원

### 라이트/다크 테마 자동 전환

```typescript
// 테마 변경 감지 및 적용
$: if (mathField) {
  const themeClass = theme === 'dark' ? 'dark' : 'light';
  mathField.style = {
    '--maice-primary': theme === 'dark' ? '#3b82f6' : '#2563eb',
    '--maice-text': theme === 'dark' ? '#f1f5f9' : '#1e293b',
    '--maice-surface': theme === 'dark' ? '#1e293b' : '#ffffff'
  };
}
```

### CSS 변수 활용

```css
/* app.css에 추가 */
:root {
  --maice-primary: #2563eb;
  --maice-primary-light: rgba(37, 99, 235, 0.1);
  --maice-border: #e2e8f0;
  --maice-surface: #ffffff;
  --maice-text: #1e293b;
}

[data-theme="dark"] {
  --maice-primary: #3b82f6;
  --maice-primary-light: rgba(59, 130, 246, 0.1);
  --maice-border: #334155;
  --maice-surface: #1e293b;
  --maice-text: #f1f5f9;
}
```

## ⌨️ 가상 키보드 설정

### 키보드 레이아웃 커스터마이징

```typescript
const keyboardLayouts = {
  // 기본 숫자 키보드
  numeric: {
    rows: [
      ['7', '8', '9', '\\div'],
      ['4', '5', '6', '\\times'],
      ['1', '2', '3', '-'],
      ['0', '.', '=', '+']
    ]
  },
  
  // 함수 키보드
  functions: {
    rows: [
      ['\\sin', '\\cos', '\\tan', '\\log'],
      ['\\ln', '\\sqrt', '\\pi', 'e'],
      ['\\left(', '\\right)', '\\left[', '\\right]'],
      ['x', 'y', 'z', '\\theta']
    ]
  },
  
  // 그리스 문자 키보드
  greek: {
    rows: [
      ['\\alpha', '\\beta', '\\gamma', '\\delta'],
      ['\\epsilon', '\\zeta', '\\eta', '\\theta'],
      ['\\iota', '\\kappa', '\\lambda', '\\mu'],
      ['\\nu', '\\xi', '\\omicron', '\\pi']
    ]
  }
};
```

### 키보드 토글 기능

```typescript
// 가상 키보드 표시/숨김 토글
function toggleVirtualKeyboard() {
  if (mathField) {
    const isVisible = mathField.isVirtualKeyboardVisible;
    if (isVisible) {
      mathField.hideVirtualKeyboard();
    } else {
      mathField.showVirtualKeyboard();
    }
  }
}

// 키보드 레이아웃 변경
function switchKeyboardLayout(layout: string) {
  if (mathField) {
    mathField.setVirtualKeyboardLayout(layout);
  }
}
```

## 🔧 고급 설정

### 매크로 정의

```typescript
const customMacros = {
  // 집합 기호
  '\\RR': '\\mathbb{R}',
  '\\NN': '\\mathbb{N}',
  '\\ZZ': '\\mathbb{Z}',
  '\\QQ': '\\mathbb{Q}',
  '\\CC': '\\mathbb{C}',
  
  // 벡터 기호
  '\\vec': '\\overrightarrow{#1}',
  '\\unit': '\\hat{#1}',
  
  // 미분 기호
  '\\diff': '\\frac{d#1}{d#2}',
  '\\pdiff': '\\frac{\\partial #1}{\\partial #2}',
  
  // 적분 기호
  '\\intinf': '\\int_{-\\infty}^{\\infty}',
  '\\intab': '\\int_{#1}^{#2}',
  
  // 행렬 기호
  '\\mat': '\\begin{pmatrix} #1 \\end{pmatrix}',
  '\\det': '\\begin{vmatrix} #1 \\end{vmatrix}'
};
```

### 스마트 기능 설정

```typescript
const smartFeatures = {
  // 자동 괄호 매칭
  smartFence: true,
  
  // 자동 위첨자
  smartSuperscript: true,
  
  // 불필요한 괄호 제거
  removeExtraneousParentheses: true,
  
  // 자동 분수 변환
  smartFraction: true,
  
  // 자동 제곱근 변환
  smartSquareRoot: true
};
```

## 📱 모바일 최적화

### 터치 인터페이스 설정

```typescript
const mobileOptimizations = {
  // 터치 친화적 키보드
  virtualKeyboardMode: 'manual',
  
  // 터치 제스처 지원
  touchEvents: true,
  
  // 모바일 키보드 크기 조정
  virtualKeyboardSize: 'large',
  
  // 스와이프 제스처
  swipeGestures: true
};
```

### 반응형 키보드 레이아웃

```css
/* 모바일에서 키보드 크기 조정 */
@media (max-width: 768px) {
  :global(.ML__virtual-keyboard) {
    font-size: 18px;
    padding: 8px;
  }
  
  :global(.ML__virtual-keyboard .ML__keyboard-key) {
    min-height: 44px;
    min-width: 44px;
  }
}
```

## 🧪 테스트 및 검증

### 수식 유효성 검사

```typescript
function validateMathExpression(expression: string): boolean {
  try {
    // MathLive의 내장 파서 사용
    const parsed = mathField.parse(expression);
    return parsed !== null;
  } catch (error) {
    console.error('수식 파싱 오류:', error);
    return false;
  }
}

// 실시간 유효성 검사
function handleInput(event: CustomEvent) {
  const expression = event.detail.value;
  const isValid = validateMathExpression(expression);
  
  // 유효성 상태 업데이트
  updateValidationState(isValid);
}
```

### 접근성 지원

```typescript
// 스크린 리더 지원
function announceExpression(expression: string) {
  const spokenExpression = mathField.speak(expression);
  // ARIA 라벨 업데이트
  container.setAttribute('aria-label', spokenExpression);
}

// 키보드 네비게이션
function handleKeyDown(event: KeyboardEvent) {
  switch (event.key) {
    case 'Enter':
      // 수식 완료
      onComplete?.(mathField.value);
      break;
    case 'Escape':
      // 입력 취소
      onCancel?.();
      break;
    case 'Tab':
      // 다음 요소로 이동
      event.preventDefault();
      focusNextElement();
      break;
  }
}
```

## 🔗 통합 예시

### 채팅 인터페이스와의 통합

```typescript
// maice/+page.svelte에서 사용 예시
<script lang="ts">
  import InlineMathInput from '$lib/components/maice/InlineMathInput.svelte';
  
  let mathInput = '';
  let showMathInput = false;
  
  function handleMathInput(value: string) {
    mathInput = value;
  }
  
  function insertMathExpression() {
    if (mathInput.trim()) {
      // 수식을 채팅 입력창에 삽입
      const formattedExpression = `$${mathInput}$`;
      insertIntoChatInput(formattedExpression);
      
      // 수식 입력 모드 종료
      showMathInput = false;
      mathInput = '';
    }
  }
</script>

{#if showMathInput}
  <div class="math-input-modal">
    <InlineMathInput 
      bind:value={mathInput}
      onInput={handleMathInput}
      placeholder="수식을 입력하세요"
      theme={currentTheme}
    />
    <div class="math-input-actions">
      <button on:click={insertMathExpression}>삽입</button>
      <button on:click={() => showMathInput = false}>취소</button>
    </div>
  </div>
{/if}
```

## 🐛 문제 해결

### 일반적인 문제들

#### MathLive 라이브러리 로드 실패
```typescript
// 라이브러리 로드 확인
async function ensureMathLiveLoaded(): Promise<boolean> {
  try {
    const { MathField } = await import('mathlive');
    return typeof MathField !== 'undefined';
  } catch (error) {
    console.error('MathLive 로드 실패:', error);
    return false;
  }
}
```

#### 수식 렌더링 오류
```typescript
// 렌더링 오류 처리
function handleRenderError(error: Error) {
  console.error('수식 렌더링 오류:', error);
  
  // 폴백: 일반 텍스트로 표시
  showFallbackText(mathInput);
  
  // 사용자에게 알림
  showNotification('수식 입력에 문제가 발생했습니다. 다시 시도해주세요.');
}
```

#### 성능 최적화
```typescript
// 디바운싱을 통한 성능 최적화
import { debounce } from '$lib/utils/debounce';

const debouncedInput = debounce((value: string) => {
  onInput?.(value);
}, 300);

function handleInput(event: CustomEvent) {
  debouncedInput(event.detail.value);
}
```

## 📚 관련 문서

- [프론트엔드 컴포넌트](./frontend-components.md) - 전체 컴포넌트 가이드
- [프론트엔드 아키텍처](../architecture/frontend-architecture.md) - 프론트엔드 구조
- [테마 시스템](./theme-system.md) - 테마 구현 가이드
- [MathLive 공식 문서](https://mathlive.io/) - 공식 라이브러리 문서
