# MAICE 디자인 시스템 🎨

일관성 있고 현대적인 무채색 위주의 디자인 시스템입니다.

## 🎯 디자인 원칙

### 1. 색상 체계
- **무채색 위주**: Slate, Gray, Zinc 계열의 세련된 색상
- **일관성**: 모든 컴포넌트에서 동일한 색상 팔레트 사용
- **접근성**: 충분한 대비와 가독성 보장

### 2. 레이아웃
- **간격**: 8px 기반의 일관된 간격 시스템
- **테두리**: 둥근 모서리 (rounded-2xl)로 부드러운 느낌
- **그림자**: 깊이감을 주는 계층적 그림자 시스템

### 3. 상호작용
- **전환 효과**: 200ms의 자연스러운 애니메이션
- **호버 상태**: 명확한 피드백 제공
- **포커스**: 접근성을 고려한 포커스 표시

## 🎨 색상 팔레트

### 주요 색상
```css
--color-primary: #1e293b (slate-800)
--color-primary-hover: #0f172a (slate-900)
--color-secondary: #4b5563 (gray-600)
--color-text-primary: #1e293b (slate-800)
--color-text-secondary: #475569 (slate-600)
```

### 상태 색상
```css
--color-success: #10b981 (green-500)
--color-warning: #f59e0b (amber-500)
--color-error: #ef4444 (red-500)
--color-info: #3b82f6 (blue-500)
```

## 🧩 컴포넌트 스타일

### 카드 (Card)
```html
<!-- 기본 카드 -->
<div class="maice-card p-8">
  <!-- 내용 -->
</div>

<!-- 고급 카드 -->
<div class="maice-card-elevated p-8">
  <!-- 내용 -->
</div>
```

### 버튼 (Button)
```html
<!-- 주요 버튼 -->
<button class="maice-btn-primary">
  주요 액션
</button>

<!-- 보조 버튼 -->
<button class="maice-btn-secondary">
  보조 액션
</button>

<!-- 고스트 버튼 -->
<button class="maice-btn-ghost">
  링크 스타일
</button>
```

### 입력 필드 (Input)
```html
<!-- 기본 입력 -->
<input class="maice-input" type="text" placeholder="입력하세요" />

<!-- 에러 상태 -->
<input class="maice-input-error" type="text" placeholder="입력하세요" />
```

### 로고 (Logo)
```html
<!-- 기본 로고 -->
<div class="maice-logo">
  <svg>...</svg>
</div>

<!-- 작은 로고 -->
<div class="maice-logo-sm">
  <svg>...</svg>
</div>

<!-- 큰 로고 -->
<div class="maice-logo-lg">
  <svg>...</svg>
</div>
```

## 📱 반응형 유틸리티

### 컨테이너
```css
.maice-container      /* max-w-md (28rem) */
.maice-container-lg  /* max-w-2xl (42rem) */
.maice-container-xl  /* max-w-4xl (56rem) */
```

### 애니메이션
```css
.maice-fade-in       /* 페이드 인 */
.maice-slide-up      /* 아래에서 위로 슬라이드 */
.maice-scale-in      /* 스케일 인 */
```

## 🔧 사용 예시

### 로그인 페이지
```html
<div class="min-h-screen maice-bg-gradient flex items-center justify-center p-4">
  <div class="maice-container">
    <!-- 로고 -->
    <div class="maice-logo mb-8">
      <svg>...</svg>
    </div>
    
    <!-- 카드 -->
    <div class="maice-card p-8">
      <form class="space-y-4">
        <input class="maice-input" type="email" placeholder="이메일" />
        <input class="maice-input" type="password" placeholder="비밀번호" />
        <button class="maice-btn-primary w-full">로그인</button>
      </form>
    </div>
  </div>
</div>
```

### 대시보드 카드
```html
<div class="maice-card-elevated p-6 maice-fade-in">
  <h3 class="text-xl font-semibold text-slate-800 mb-4">통계</h3>
  <div class="space-y-2">
    <div class="flex justify-between">
      <span class="text-slate-600">총 사용자</span>
      <span class="font-semibold text-slate-800">1,234</span>
    </div>
  </div>
</div>
```

## 📋 체크리스트

새로운 컴포넌트를 만들 때 다음을 확인하세요:

- [ ] MAICE 색상 팔레트 사용
- [ ] 일관된 간격 (8px 기반)
- [ ] 둥근 모서리 (rounded-xl 이상)
- [ ] 적절한 그림자 적용
- [ ] 호버/포커스 상태 구현
- [ ] 전환 효과 추가 (200ms)
- [ ] 반응형 디자인 고려
- [ ] 접근성 확인

## 🚀 확장 가이드

### 새로운 컴포넌트 추가
1. CSS 변수 정의 (필요시)
2. 유틸리티 클래스 생성
3. 사용 예시 문서화
4. 디자인 가이드 업데이트

### 테마 변경
색상 팔레트를 변경하려면 `:root`의 CSS 변수만 수정하면 됩니다.

---

**참고**: 이 디자인 시스템은 Tailwind CSS와 함께 사용되며, 일관성 있는 사용자 경험을 제공합니다.



