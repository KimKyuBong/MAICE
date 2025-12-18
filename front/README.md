# MAICE Frontend - SvelteKit + Tailwind CSS

현대적이고 일관성 있는 디자인 시스템을 갖춘 AI 학습 도우미 시스템의 프론트엔드입니다.

## 🎨 디자인 시스템

### 특징
- **무채색 위주**: Slate, Gray, Zinc 계열의 세련된 색상
- **일관성**: 모든 컴포넌트에서 동일한 디자인 언어 사용
- **현대적**: Backdrop blur, 그라데이션, 부드러운 애니메이션
- **접근성**: 충분한 대비와 키보드 네비게이션 지원

### 주요 컴포넌트
- **Button**: Primary, Secondary, Ghost 변형
- **Input**: 라벨, 에러 상태, 유효성 검사 지원
- **Card**: 기본 및 고급 카드 스타일
- **Logo**: 다양한 크기의 로고 컴포넌트

### 사용법
```svelte
<script>
  import { Button, Input, Card } from '$lib/components';
</script>

<Card variant="elevated" padding="lg" animation="fade-in">
  <Input 
    label="이메일" 
    type="email" 
    placeholder="your@email.com" 
    required 
  />
  <Button variant="primary" fullWidth loading={isLoading}>
    로그인
  </Button>
</Card>
```


## 🚀 기술 스택

- **프레임워크**: SvelteKit 2.0
- **스타일링**: Tailwind CSS v4
- **언어**: TypeScript
- **빌드 도구**: Vite
- **패키지 매니저**: Yarn

## 📁 프로젝트 구조

```
front/
├── src/
│   ├── lib/
│   │   ├── components/          # 재사용 가능한 컴포넌트
│   │   │   ├── Button.svelte
│   │   │   ├── Input.svelte
│   │   │   ├── Card.svelte
│   │   │   └── index.ts
│   │   ├── api.ts              # API 통신 서비스
│   │   └── mock-api.ts         # Mock API (개발용)
│   ├── routes/                 # SvelteKit 라우트
│   │   ├── +page.svelte        # 로그인 페이지
│   │   ├── admin/+page.svelte  # 관리자 대시보드
│   │   └── student/[token]/+page.svelte  # 학생 채팅
│   └── app.css                 # 디자인 시스템 CSS
├── static/                     # 정적 파일
├── DESIGN_SYSTEM.md            # 디자인 시스템 가이드
└── README.md                   # 프로젝트 문서
```

## 🎯 주요 기능

### 1. 인증 시스템
- 로그인/회원가입 페이지
- JWT 토큰 기반 인증
- 역할 기반 접근 제어 (학생, 교사, 관리자)

### 2. AI 챗봇 서비스
- 실시간 질문-답변
- 스트리밍 응답 지원
- 대화 히스토리 관리
- 피드백 시스템

### 3. 관리자 대시보드
- 실시간 시스템 모니터링
- 사용자 활동 추적
- 통계 및 분석

### 4. 학생 학습 도구
- 개인화된 학습 경험
- 질문 한도 관리
- 학습 진행 상황 추적

## 🛠️ 개발 환경 설정

### 1. 의존성 설치
```bash
cd front
yarn install
```

### 2. 환경 변수 설정
```bash
# .env.local 파일 생성
VITE_API_BASE_URL=http://localhost:8000
VITE_USE_MOCK_API=false
```

### 3. 개발 서버 실행
```bash
yarn dev
```

### 4. 빌드
```bash
yarn build
```

## 🎨 디자인 시스템 사용법

### CSS 변수
```css
:root {
  --color-primary: #1e293b;      /* Slate 800 */
  --color-secondary: #4b5563;    /* Gray 600 */
  --color-text-primary: #1e293b; /* Slate 800 */
  --spacing-md: 1rem;            /* 16px */
  --radius-xl: 1rem;             /* 16px */
}
```

### 유틸리티 클래스
```css
.maice-card          /* 기본 카드 스타일 */
.maice-btn-primary   /* 주요 버튼 스타일 */
.maice-input         /* 입력 필드 스타일 */
.maice-logo          /* 로고 스타일 */
.maice-fade-in       /* 페이드 인 애니메이션 */
```

### 반응형 유틸리티
```css
.maice-container      /* max-w-md */
.maice-container-lg  /* max-w-2xl */
.maice-container-xl  /* max-w-4xl */
```

## 🔧 API 연동

### 백엔드 통신
- FastAPI 백엔드와 RESTful API 통신
- JWT 토큰 기반 인증
- 실시간 스트리밍 응답 지원

### Mock API
- 백엔드 없이 프론트엔드 개발 가능
- `VITE_USE_MOCK_API=true`로 활성화

## 📱 반응형 디자인

- **모바일 우선**: 모바일 디바이스부터 시작하여 데스크톱으로 확장
- **브레이크포인트**: Tailwind CSS의 기본 브레이크포인트 활용
- **터치 친화적**: 모바일 사용자를 위한 터치 인터페이스

## 🚀 배포

### Docker
```bash
docker build -t maice-frontend .
docker run -p 80:80 maice-frontend
```

### 정적 호스팅
```bash
yarn build
# build/ 폴더를 정적 호스팅 서비스에 업로드
```

## 🤝 기여 가이드

### 디자인 시스템 확장
1. CSS 변수 추가 (필요시)
2. 유틸리티 클래스 생성
3. 컴포넌트 구현
4. 문서 업데이트

### 코드 스타일
- TypeScript 사용
- Svelte 컴포넌트 규칙 준수
- Tailwind CSS 클래스 우선 사용
- 접근성 고려

## 📚 참고 자료

- [SvelteKit 공식 문서](https://kit.svelte.dev/)
- [Tailwind CSS v4 문서](https://tailwindcss.com/)
- [MAICE 디자인 시스템 가이드](./DESIGN_SYSTEM.md)

## 📄 라이선스

© 2025 MAICE System. All rights reserved.

---

**개발팀**: MAICE Frontend Team  
**최종 업데이트**: 2025년 12월
