# MathLive 주요 속성 및 설정 가이드

## 기본 속성

### math-mode
- **기본값**: `'auto'`
- **설명**: 입력 필드의 수식 모드를 제어
- **값**:
  - `'text'`: 일반 텍스트 모드로 고정
  - `'math'`: 수식 모드로 고정
  - `'auto'`: 사용자 입력에 따라 자동 전환

### math-style
- **기본값**: `'display'`
- **설명**: 수식 표시 스타일
- **값**:
  - `'display'`: 블록 수식 ($$...$$)
  - `'inline'`: 인라인 수식 ($...$)

### math-delimiters
- **기본값**: `{inline: ['$', '$'], display: ['$$', '$$']}`
- **설명**: 수식 구분자 설정

### smart-fence
- **기본값**: `true`
- **설명**: 스마트 괄호 자동 완성

### smart-superscript
- **기본값**: `true`
- **설명**: 스마트 위첨자 자동 완성

### smart-subscript
- **기본값**: `true`
- **설명**: 스마트 아래첨자 자동 완성

## 이벤트 처리

### 주요 이벤트
- `input`: 입력 값 변경 시
- `change`: 값 변경 완료 시
- `focus`: 포커스 받을 때
- `blur`: 포커스 잃을 때
- `keydown`: 키 입력 시

### 수식 모드 전환 방법
```javascript
// 수식 모드로 전환
mathField.setOptions({ mathMode: 'math' });

// 텍스트 모드로 전환
mathField.setOptions({ mathMode: 'text' });

// 자동 모드로 전환
mathField.setOptions({ mathMode: 'auto' });
```

## 사용자 정의 수식 모드 전환

### 방법 1: 특정 키 입력 시 전환
```javascript
mathField.addEventListener('input', (event) => {
    const value = mathField.getValue();
    if (value.includes('$')) {
        mathField.setOptions({ mathMode: 'math' });
        mathField.setValue(value.replace('$', ''));
    }
});
```

### 방법 2: 포커스 시 텍스트 모드 유지
```javascript
mathField.addEventListener('focus', () => {
    mathField.setOptions({ mathMode: 'text' });
});
```

### 방법 3: 수식 시작 키 입력 시 전환
```javascript
mathField.addEventListener('keydown', (event) => {
    if (event.key === '$' || event.key === '\\') {
        mathField.setOptions({ mathMode: 'math' });
    }
});
```

## 모바일 최적화 설정

### 터치 입력 최적화
```javascript
mathField.setOptions({
    mathMode: 'text',
    smartFence: true,
    smartSuperscript: true,
    smartSubscript: true,
    virtualKeyboardMode: 'manual' // 가상 키보드 수동 제어
});
```

### 가상 키보드 제어
```javascript
// 가상 키보드 표시
mathField.showVirtualKeyboard();

// 가상 키보드 숨김
mathField.hideVirtualKeyboard();

// 가상 키보드 토글
mathField.toggleVirtualKeyboard();
```

### 수식 키패드 자동 표시 비활성화
```javascript
// 수식 키패드 자동 표시 완전 비활성화
mathField.setOptions({
    virtualKeyboardMode: 'manual',      // 수동 제어
    virtualKeyboardPolicy: 'manual'     // 정책 수동
});

// 포커스 시 키패드 숨기기
mathField.addEventListener('focus', () => {
    mathField.hideVirtualKeyboard();
});
```

## 문제 해결

### 포커스 시 자동 수식 모드 전환 방지
```javascript
// 초기 설정
mathField.setOptions({ mathMode: 'text' });

// 포커스 시에도 텍스트 모드 유지
mathField.addEventListener('focus', () => {
    if (mathField.getOptions().mathMode !== 'math') {
        mathField.setOptions({ mathMode: 'text' });
    }
});
```

### 사용자 입력 시작 시에만 수식 모드 전환
```javascript
let hasUserInput = false;

mathField.addEventListener('input', () => {
    if (!hasUserInput) {
        hasUserInput = true;
        mathField.setOptions({ mathMode: 'math' });
    }
});

mathField.addEventListener('focus', () => {
    hasUserInput = false;
    mathField.setOptions({ mathMode: 'text' });
});
```
