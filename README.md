# MAICE System (Mathematics AI Chatbot Education System)

## 📋 프로젝트 개요

MAICE System은 고등학교 수학 교육을 위한 AI 기반 채팅 시스템으로, Bloom의 학습 목표 분류법을 기반으로 한 4단계 지식 분류 시스템과 3단계 게이팅 메커니즘을 통해 개인화된 수학 교육을 제공하는 통합 플랫폼입니다.

**핵심 특징:**
- 🧠 **AI 기반 질문 분류 및 품질 평가**: 12개 세부 항목으로 질문 품질을 자동 평가 (총 15점 만점)
- 🎯 **커리큘럼 기반 학습 가이드**: 교과과정 위계성을 고려한 맞춤형 답변 제공
- 📊 **실시간 학습 진도 추적**: 학생별 학습 상태 및 어려움 영역 분석
- 🔄 **대화 세션 관리**: Redis Streams 기반 신뢰성 있는 연속적 학습 대화 지원
- 📈 **교사 평가 시스템**: 질문-답변 품질에 대한 다차원 평가 (5점 척도)
- 🤖 **멀티 에이전트 시스템**: 5개 독립 에이전트의 협업을 통한 지능적 답변 생성
- 🎨 **모던 웹 인터페이스**: SvelteKit 기반 반응형 UI, MathLive 수식 입력, 다크/라이트 테마

## 🏗️ 시스템 아키텍처

### 전체 구조
```
┌─────────────────────────────────────────────────────────────────┐
│                        MAICE System                            │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Frontend      │    Backend      │        Agent System         │
│   (SvelteKit)   │   (FastAPI)     │        (Python)             │
├─────────────────┼─────────────────┼─────────────────────────────┤
│ • 채팅 UI        │ • API 서버      │ • Question Classifier       │
│ • 수식 입력      │ • 인증/세션     │ • Question Improvement     │
│ • 테마 지원      │ • 메시지 큐     │ • Answer Generator          │
│ • 실시간 스트리밍│ • 데이터 관리   │ • Observer Agent            │
│ • SPA 모드       │ • JWT 인증      │ • FreeTalker Agent         │
└─────────────────┴─────────────────┴─────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │    Infrastructure     │
                    ├─────────────────────────┤
                    │ • PostgreSQL Database  │
                    │ • Redis (Streams/PubSub)│
                    │ • Docker Containers    │
                    │ • Nginx Reverse Proxy  │
                    └─────────────────────────┘
```

### 프로젝트 구조
```
MAICESystem/
├── back/                 # FastAPI 백엔드 서버 (API 전용)
├── front/               # SvelteKit 프론트엔드 (SPA 모드)
├── agent/               # AI 에이전트 시스템 (멀티프로세스)
├── tester/              # 시스템 테스트 및 평가 도구
├── nginx/               # 리버스 프록시 및 정적 파일 서빙
├── docs/                # 체계화된 문서 시스템
├── deploy-scripts/      # 배포 스크립트 (Groovy Pipeline 등)
└── docker-compose.yml   # 전체 시스템 오케스트레이션
```

## 🚀 주요 구성 요소

### 1. 백엔드 서버 (back/)
- **기술 스택**: FastAPI 0.115.0, SQLAlchemy 2.0.23, PostgreSQL 15, Redis 7, Alembic
- **아키텍처**: API 전용 서버 (SPA 모드 지원)
- **주요 기능**:
  - JWT 기반 사용자 인증 및 권한 관리 (학생/교사/관리자)
  - Google OAuth 2.0 소셜 로그인 지원
  - Redis Streams 기반 AI 에이전트 통신
  - 대화 세션 관리 및 연속성 유지
  - 실시간 스트리밍 API (Server-Sent Events)
  - 데이터베이스 마이그레이션 (Alembic)
  - 설문 응답 및 피드백 수집
  - A/B 테스트 지원 (Agent vs FreePass 모드)
  - Google Gemini (Generative AI) 통합 지원

#### API 구조
- `/api/v1/auth/` - 인증 관련 (JWT, Google OAuth, 토큰 관리)
- `/api/v1/users/` - 사용자 관리 및 프로필
- `/api/v1/student/` - 학생 인터페이스 (질문 작성, 답변 확인, 학습 진도)
- `/api/v1/admin/` - 관리자 기능 (시스템 관리, 통계)
- `/api/v1/exports/` - 데이터 내보내기 (CSV, JSON)

#### 핵심 데이터 모델
- **UserModel**: 사용자 정보, Google OAuth, 역할, A/B 테스트 모드
- **QuestionModel**: 질문-답변, 메시지 타입, 대화 세션 연결
- **ConversationSession**: 대화 세션, 단계별 진행 상황 추적
- **SessionSummary**: 세션별 요약 및 메타데이터
- **SurveyResponseModel**: 사용자 피드백 및 만족도 조사
- **TeacherEvaluationModel**: 교사별 질문-답변 평가 (5점 척도)
- **MAICEEvaluationModel**: AI 자동 평가 (12개 세부 항목, 15점 만점)
- **StudentLearningStatus**: 학습 상태, 어려움 영역, 다음 단계 추천

### 2. 프론트엔드 (front/)
- **기술 스택**: SvelteKit 2.0 (SPA 모드), TypeScript, Tailwind CSS 4.x, Vite 5.x
- **배포 방식**: 정적 파일 빌드 + Nginx 서빙 (개발: Hot Reload 지원)
- **주요 기능**:
  - 반응형 웹 인터페이스 (다크/라이트 테마 지원)
  - 실시간 채팅 인터페이스 (Server-Sent Events 스트리밍)
  - 사용자별 맞춤 대시보드 (학생/교사/관리자)
  - MathLive 기반 수학 수식 입력 및 렌더링
  - KaTeX를 통한 수학 수식 표시
  - ProseMirror 기반 리치 텍스트 에디터
  - DOMPurify를 통한 XSS 방지
  - Google OAuth 2.0 소셜 로그인
  - A/B 테스트 모드 지원 (Agent/FreePass)

#### 페이지 구조
- `/` - 로그인 페이지 (Google OAuth 지원)
- `/dashboard` - 학생 대시보드 (학습 진도, 질문 이력)
- `/admin` - 관리자 대시보드 (시스템 관리, 통계)
- `/maice/` - MAICE AI 챗봇 인터페이스 (실시간 채팅)
- `/survey/` - 설문 응답 및 피드백

### 3. AI 에이전트 시스템 (agent/)
- **아키텍처**: 멀티프로세스 기반 독립 에이전트 시스템
- **통신 방식**: Redis Streams (백엔드 통신) + Redis Pub/Sub (에이전트 간 협업)
- **핵심 기능**:
  - 질문 분류 및 품질 평가 (12개 세부 항목, 15점 만점)
  - 교육적 답변 생성 및 명료화
  - 커리큘럼 기반 학습 가이드
  - 대화 세션 요약 및 학습 진도 추적
  - 자유 대화 및 일반 질문 처리
  - 교과과정 용어 분석 및 검증 (RAG 기반)

#### 에이전트 구성 (6개 독립 에이전트)
- **QuestionClassifierAgent**: 질문 유형 분류 및 품질 평가
  - 12개 세부 항목별 점수 평가 (0, 0.5, 1점)
  - 답변 가능성 판단 (answerable/needs_clarify)
  - 적절한 처리 경로 선택
- **QuestionImprovementAgent**: 질문 명료화 및 개선
  - 모호한 질문의 명확화 요청
  - 추가 정보 요청 및 질문 개선 제안
- **AnswerGeneratorAgent**: 교육적 답변 생성
  - 수학적 답변 생성 및 단계별 해설
  - 커리큘럼 기반 학습 목표 고려
- **ObserverAgent**: 학습 관찰 및 진도 추적
  - 학습 진도 추적 및 어려움 영역 식별
  - 세션 요약 생성 및 다음 단계 추천
- **FreeTalkerAgent**: 자유 대화 및 일반 질문 처리
  - 수학 외 일반 질문 처리
  - 친근한 대화 및 학습 동기 부여
- **CurriculumTermAgent**: 교과과정 용어 분석 및 검증
  - 질문 내 핵심 수학 개념 추출 및 수준 판단
  - RAG 기반 교과과정/교과서 검색
  - 답변 용어 적절성 검증 및 수정 제안

#### 도구 (Tools) - 7개 Desmos 통합 도구
- **desmos_graph_tool.py**: 기본 그래프 생성 및 시각화
- **desmos_advanced_tools.py**: 고급 수학 도구 (미분, 적분, 통계)
- **desmos_interactive_tools.py**: 인터랙티브 수학 요소
- **desmos_mcp_system.py**: MCP (Model Context Protocol) 통합
- **desmos_mcp_tools.py**: MCP 기반 수학 도구
- **latex_formatter_tool.py**: LaTeX 수식 포맷팅
- **math_solving_tool.py**: 단계별 수학 문제 해결

#### 질문 품질 평가 시스템 (12개 항목)
1. **수학적 개념/원리의 정확성** (0, 0.5, 1점)
2. **교과과정 내 위계성 파악** (0, 0.5, 1점)
3. **수학적 용어 사용의 적절성** (0, 0.5, 1점)
4. **문제해결 방향의 구체성** (0, 0.5, 1점)
5. **핵심 질문의 단일성** (0, 0.5, 1점)
6. **조건 제시의 완결성** (0, 0.5, 1점)
7. **문장 구조의 논리성** (0, 0.5, 1점)
8. **질문 의도의 명시성** (0, 0.5, 1점)
9. **현재 학습 단계 설명** (0, 0.5, 1점)
10. **선수학습 내용 언급** (0, 0.5, 1점)
11. **구체적 어려움 명시** (0, 0.5, 1점)
12. **학습 목표 제시** (0, 0.5, 1점)

**총점**: 12점 (우수: 10점 이상, 수학 관련성: 8점 이상)

### 4. 테스터 시스템 (tester/)
- **기능**: 
  - 시스템 성능 평가 및 벤치마킹
  - 질문-답변 품질 테스트 (A/B 테스트)
  - 다양한 시나리오 시뮬레이션
  - Deepfake 질문 생성기 (실제 사용자 질문 패턴 모방)
  - 질문 분류 알고리즘 정확도 테스트
  - 동시 사용자 부하 테스트 (50+ 동시 연결)
  - MCP 스트리밍 성능 테스트

## 🐳 Docker 구성

### 서비스 구성
- **PostgreSQL 15**: 메인 데이터베이스 (maice_web, maice_agent)
- **Redis 7**: 캐싱, 세션 관리, Streams, Pub/Sub
- **maice-back**: FastAPI 백엔드 서버 (API 전용)
- **maice-front**: SvelteKit 프론트엔드 (개발: Hot Reload, 프로덕션: 정적 파일)
- **maice-agent**: AI 에이전트 서비스 (멀티프로세스 워커)
- **Nginx**: 리버스 프록시 및 정적 파일 서빙 (프로덕션)

### 포트 구성
- **개발 환경**:
  - Frontend: 5173 (Vite 개발 서버)
  - Backend: 8000 (FastAPI)
  - PostgreSQL: 5432
  - Redis: 6379
- **프로덕션 환경**:
  - Nginx: 80 (HTTP), 443 (HTTPS)
  - 내부 통신: Docker 네트워크 (maice_network)

### 환경 변수
- **AI 모델**: `OPENAI_CHAT_MODEL=GPT-4o-mini`
- **에이전트 모드**: `ORCHESTRATOR_MODE=decentralized`
- **스트리밍**: `FORCE_NON_STREAMING=1`
- **명료화**: `AUTO_PROMOTE_AFTER_CLARIFICATION=0`
- **A/B 테스트**: `ENABLE_MAICE_TEST=true`
- **Google OAuth**: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`

## 🔧 설치 및 실행

### 1. 환경 설정
```bash
# 저장소 클론
git clone <repository-url>
cd MAICESystem

# 환경 변수 파일 생성
cp env.example .env
# .env 파일에 필요한 설정 입력 (Google OAuth, OpenAI API 키 등)
```

### 2. SPA 모드 배포 구조
프로젝트는 **SPA (Single Page Application)** 모드로 구성되어 있습니다:

- **프로덕션**: 정적 파일 빌드 → Nginx 서빙
- **개발**: Vite 개발 서버 (Hot Reload 지원)

**주요 특징:**
- SSR 제거로 성능 최적화
- 정적 파일 캐싱으로 로딩 속도 향상
- 실시간 채팅에 최적화된 구조
- Google OAuth 2.0 소셜 로그인 지원

### 3. Docker Compose로 실행 (권장)
```bash
# 전체 시스템 시작 (개발 환경)
docker-compose up -d

# 특정 서비스만 시작
docker-compose up -d postgres redis maice-back maice-front maice-agent

# 로그 확인
docker-compose logs -f maice-back
docker-compose logs -f maice-agent
```

### 4. 개발 모드 실행 (로컬)
```bash
# 백엔드 개발 서버
cd back
uvicorn main:app --reload --host 0.0.0.0 --port 8000 --loop uvloop

# 프론트엔드 개발 서버
cd front
yarn dev

# AI 에이전트 (별도 터미널)
cd agent
python worker.py
```

## 📊 데이터베이스

### 데이터베이스 구성
- **maice_web**: 메인 웹 애플리케이션 데이터 (사용자, 세션, 질문-답변)
- **maice_agent**: AI 에이전트 전용 데이터 (에이전트 상태, 로그)

### 마이그레이션
```bash
# 백엔드 데이터베이스 마이그레이션
cd back
python migrate.py

# 에이전트 데이터베이스 마이그레이션
cd agent
python -c "from database.connection import init_db; import asyncio; asyncio.run(init_db())"
```

### 관리자 계정 생성
```bash
cd back/scripts
python create_admin.py
```

## 🔐 인증 시스템

### 사용자 역할
- **학생**: 질문 작성, 답변 확인, 학습 진도 추적, A/B 테스트 참여
- **교사**: 학생 관리, 질문 평가, 그룹 분석, 피드백 제공
- **관리자**: 시스템 전체 관리, 사용자 권한 관리, 통계 모니터링

### 인증 방식
- **JWT 토큰**: 상태 비저장 인증 (Access Token + Refresh Token)
- **Google OAuth 2.0**: 소셜 로그인 지원
- **비밀번호 해싱**: bcrypt 기반 안전한 저장
- **역할 기반 접근 제어**: RBAC (Role-Based Access Control)

### 보안 기능
- **XSS 방지**: DOMPurify를 통한 입력 검증
- **CSRF 보호**: SameSite 쿠키 설정
- **HTTPS 강제**: 프로덕션 환경에서 SSL/TLS 암호화
- **환경 변수**: 민감한 정보 보호

## 🤖 AI 에이전트 기능

### 질문 처리 파이프라인
1. **질문 수신** → 프론트엔드 (SvelteKit) → 백엔드 API
2. **Redis Streams 전송** → 백엔드에서 AI 에이전트로 질문 전달
3. **질문 분류** → QuestionClassifierAgent가 질문 유형 및 품질 평가 (12개 항목)
4. **라우팅 결정** → answerable/needs_clarify 판단
5. **답변 생성** → AnswerGeneratorAgent 또는 QuestionImprovementAgent 실행
6. **실시간 스트리밍** → Server-Sent Events로 프론트엔드에 전송
7. **학습 관찰** → ObserverAgent가 세션 요약 및 진도 추적

### 멀티 에이전트 협업
- **Redis Streams**: 백엔드 ↔ 에이전트 통신 (신뢰성 보장)
- **Redis Streams**: 에이전트 간 협업 및 워크플로우 오케스트레이션
- **멀티프로세스**: 각 에이전트가 독립 프로세스로 실행
- **자동 재시작**: 에이전트 장애 시 자동 복구

### 학습 진도 추적
- **대화 세션별 진행 상황**: 초기 질문 → 명확화 → 답변 → 피드백
- **학습 단계별 상태**: 현재 단계, 다음 단계, 어려움 영역
- **개인별 맞춤 가이드**: 이해 수준에 따른 학습 방향 제시
- **A/B 테스트 지원**: Agent 모드 vs FreePass 모드 비교

### 지식 코드 체계 (Bloom의 분류법 기반)
- **K1**: 기본 개념 (0-5점) - 기억, 이해
- **K2**: 응용 문제 (6-10점) - 적용, 분석
- **K3**: 심화 문제 (11-15점) - 종합, 평가
- **K4**: 창의적 사고 (12점 이상) - 창조

## 🧪 테스트 및 평가

### 테스트 실행
```bash
# 고급 테스터 (성능 벤치마킹)
cd tester
python run_advanced_tester.py

# Deepfake 질문 생성기 (실제 사용자 패턴 모방)
python run_deepfake_generator.py

# 질문 분류 알고리즘 테스트
python question_classification_tester.py

# 동시 사용자 부하 테스트
python parallel_test_50_results.py

# MCP 스트리밍 성능 테스트
python mcp_stream_direct_results.py
```

### 평가 지표
- **질문 품질**: 12개 세부 항목별 점수 (총 15점 만점)
- **답변 정확도**: 수학적 정확성, 교육적 가치
- **응답 시간**: 실시간 처리 속도 (평균 2-5초)
- **동시 처리**: 50+ 동시 사용자 지원
- **사용자 만족도**: 설문 응답 기반 피드백 (20문항 학생 설문, 15문항 교사 평가)
- **A/B 테스트**: Agent 모드 vs FreePass 모드 효과 비교

## 📁 프로젝트 구조 상세

```
MAICESystem/
├── back/                          # FastAPI 백엔드 서버 (API 전용)
│   ├── app/                      # 애플리케이션 코어
│   │   ├── api/routers/         # API 라우터
│   │   │   ├── auth.py          # JWT 인증, Google OAuth
│   │   │   ├── google_auth.py   # Google OAuth 2.0
│   │   │   ├── users.py         # 사용자 관리
│   │   │   ├── admin.py         # 관리자 기능
│   │   │   ├── maice.py         # MAICE 채팅 API
│   │   │   └── exports.py       # 데이터 내보내기
│   │   ├── core/                # 핵심 기능 (DB, Redis, 미들웨어)
│   │   ├── models/              # SQLAlchemy 데이터 모델
│   │   ├── services/            # 비즈니스 로직
│   │   ├── schemas/             # Pydantic 스키마
│   │   └── utils/               # 유틸리티 함수
│   ├── alembic/                 # 데이터베이스 마이그레이션
│   ├── scripts/                 # 관리 스크립트
│   ├── main.py                  # FastAPI 애플리케이션 진입점
│   └── api_router.py            # API 라우터 통합
├── front/                        # SvelteKit 프론트엔드 (SPA 모드)
│   ├── src/                     # 소스 코드
│   │   ├── lib/                 # 컴포넌트 및 스토어
│   │   │   ├── components/      # UI 컴포넌트
│   │   │   ├── stores/          # 상태 관리 (Svelte stores)
│   │   │   └── utils/           # 유틸리티 함수
│   │   └── routes/              # 페이지 라우트
│   │       ├── dashboard/       # 학생 대시보드
│   │       ├── admin/           # 관리자 페이지
│   │       ├── maice/           # AI 챗봇 인터페이스
│   │       └── survey/          # 설문 응답
│   ├── static/                  # 정적 파일
│   ├── package.json             # 의존성 관리 (SvelteKit 2.0)
│   └── svelte.config.js         # SvelteKit 설정 (SPA 모드)
├── agent/                        # AI 에이전트 시스템 (멀티프로세스)
│   ├── agents/                  # 에이전트 구현
│   │   ├── question_classifier/ # 질문 분류 에이전트
│   │   ├── question_improvement/# 질문 명료화 에이전트
│   │   ├── answer_generator/    # 답변 생성 에이전트
│   │   ├── observer/            # 학습 관찰 에이전트
│   │   ├── freetalker/          # 자유 대화 에이전트
│   │   ├── tools/               # 7개 Desmos 통합 도구
│   │   └── common/              # 공통 기능
│   ├── core/                    # 공통 기능
│   ├── database/                # 데이터베이스 연결
│   └── worker.py                # 멀티프로세스 워커
├── tester/                       # 테스트 시스템
│   ├── run_advanced_tester.py   # 고급 성능 테스터
│   ├── run_deepfake_generator.py # Deepfake 질문 생성기
│   ├── question_classification_tester.py # 분류 알고리즘 테스트
│   └── *.json                   # 테스트 결과 파일
├── docs/                         # 체계화된 문서 시스템
│   ├── getting-started/         # 시작 가이드
│   ├── architecture/            # 아키텍처 문서
│   ├── api/                     # API 문서
│   ├── components/              # 컴포넌트 가이드
│   ├── deployment/              # 배포 가이드
│   ├── testing/                 # 테스트 가이드
│   ├── experiments/             # 실험 도구
│   └── troubleshooting/         # 문제 해결
├── nginx/                        # 웹 서버 설정
├── docker-compose.yml           # Docker 서비스 오케스트레이션
└── env.example                  # 환경 변수 템플릿
```

## 🚧 개발 상태

### 완료된 기능 ✅
- **인증 시스템**: JWT 기반 로그인, Google OAuth 2.0, 역할별 권한 관리
- **사용자 관리**: 학생/교사/관리자 역할 시스템, A/B 테스트 모드 지원
- **AI 에이전트**: 5개 독립 에이전트, 멀티프로세스 아키텍처
- **Desmos 통합**: 7개 수학 도구 및 MCP 시스템 완전 구현
- **데이터베이스**: 완전한 스키마, 마이그레이션, 이중 DB 구조
- **Docker 컨테이너화**: 전체 시스템 오케스트레이션, 개발/프로덕션 환경
- **프론트엔드**: SvelteKit 2.0 SPA 모드, MathLive 수식 입력, 다크/라이트 테마
- **질문 품질 평가**: 12개 세부 항목 자동 평가 (15점 만점)
- **대화 세션 관리**: Redis Streams 기반 연속적 학습 대화 지원
- **학습 진도 추적**: 개인별 맞춤 학습 가이드, 어려움 영역 분석
- **실시간 스트리밍**: Server-Sent Events 기반 실시간 채팅
- **테스트 시스템**: 성능 벤치마킹, Deepfake 생성기, 부하 테스트

### 진행 중인 기능 🔄
- **질문 분류 알고리즘**: 정확도 향상 및 새로운 유형 추가
- **답변 품질 평가**: AI 기반 자동 평가 시스템 고도화
- **프론트엔드 UI/UX**: 사용자 경험 개선 및 접근성 향상
- **성과 분석**: 학습 효과 측정 및 시각화 대시보드
- **A/B 테스트**: Agent vs FreePass 모드 효과 분석

### 계획된 기능 📋
- **실시간 협업**: 학생 간 질문 공유 및 토론 기능
- **학습 진도 대시보드**: 시각적 학습 진행 상황 분석
- **모바일 앱**: React Native 기반 모바일 지원
- **다국어 지원**: 한국어 외 언어 확장
- **AI 모델 최적화**: 성능 및 정확도 향상
- **고급 분석**: 학습 패턴 분석 및 개인화 추천

## 🚀 성능 및 확장성

### 현재 성능
- **동시 사용자**: 50+ 명 지원 (테스트 완료)
- **응답 시간**: 평균 2-5초 (질문 처리)
- **처리량**: 분당 50+ 질문 처리 (동시 사용자 50명 기준)
- **가용성**: 99.9% 이상 (Docker 기반 안정성)
- **스트리밍**: 실시간 Server-Sent Events 지원
- **에이전트**: 5개 독립 프로세스, 자동 재시작

### 확장 계획
- **수평 확장**: 에이전트 서버 다중화, 로드 밸런싱
- **캐싱 전략**: Redis 클러스터 구성, 분산 캐싱
- **데이터베이스**: 읽기 전용 복제본 추가, 샤딩
- **CDN**: 정적 파일 전송 최적화, 글로벌 배포
- **마이크로서비스**: 서비스별 독립 배포 및 확장

## 🤝 기여 방법

### 개발 환경 설정
1. 저장소 포크 및 클론
2. 환경 변수 설정 (`.env` 파일)
3. Docker Compose로 개발 환경 실행
4. 기능 브랜치 생성
5. 코드 작성 및 테스트
6. Pull Request 생성

### 코딩 스타일
- **Python**: PEP 8 준수, 타입 힌트 사용, async/await 패턴
- **TypeScript**: ESLint 규칙 준수, Svelte 5 문법
- **커밋 메시지**: Conventional Commits 형식
- **문서화**: 모든 API 및 함수에 docstring 작성
- **테스트**: 새로운 기능에 대한 테스트 코드 작성

### 문서 기여
- **API 문서**: 새로운 엔드포인트 문서화
- **아키텍처**: 시스템 변경사항 반영
- **가이드**: 사용자 및 개발자 가이드 업데이트

## 📄 라이선스

이 프로젝트는 교육 목적으로 개발되었으며, MIT 라이선스 하에 배포됩니다.

## 📞 문의 및 지원

- **이슈 트래커**: GitHub Issues
- **문서**: `/docs` 폴더의 체계화된 문서
- **커뮤니티**: 개발자 포럼

## 🔗 관련 문서

- [시스템 개요](./docs/architecture/overview.md) - 전체 아키텍처 이해
- [API 문서](./docs/api/maice-api.md) - 상세 API 가이드
- [설치 가이드](./docs/getting-started/installation.md) - 설치 및 설정
- [테스트 가이드](./docs/testing/testing-strategy.md) - 테스트 실행 방법
- [배포 가이드](./docs/deployment/production-deployment.md) - 프로덕션 배포

---

**MAICE System** - 수학 교육의 미래를 위한 AI 챗봇 시스템

*Bloom의 학습 목표 분류법 기반 4단계 지식 분류 시스템과 3단계 게이팅 메커니즘을 통해 개인화된 수학 교육을 제공합니다.*
# Jenkinsfile reload Mon Sep  1 16:12:33 UTC 2025
# Reload Jenkinsfile Mon Sep  1 16:29:58 UTC 2025
# Jenkins cache refresh
