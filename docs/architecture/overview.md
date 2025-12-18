# 시스템 개요

MAICE(Mathematical AI Chatbot for Education) 시스템의 전체 아키텍처와 핵심 개념을 소개합니다.

## 🎯 시스템 목표

MAICE는 고등학교 수학 교육을 위한 AI 기반 채팅 시스템으로, Bloom의 학습 목표 분류법을 기반으로 한 4단계 지식 분류 시스템과 3단계 게이팅 메커니즘을 통해 개인화된 수학 교육을 제공합니다.

### 핵심 목표
- **지능적인 질문 분류**: 12개 세부 항목으로 질문 품질 자동 평가 (15점 만점)
- **멀티 에이전트 협업**: 5개 독립 AI 에이전트의 협업을 통한 지능적 답변 생성
- **커리큘럼 기반 학습**: 교과과정의 위계성을 고려한 맞춤형 답변 제공
- **실시간 학습 추적**: 개인별 학습 진도와 어려움 영역을 실시간으로 모니터링
- **연속적 대화 관리**: Redis Streams 기반 신뢰성 있는 지속적 학습 대화 지원
- **A/B 테스트**: Agent 모드 vs FreePass 모드 효과 비교를 통한 학습 최적화

## 🏗️ 전체 시스템 구조

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

## 🔄 핵심 워크플로우

### 1. 질문 처리 파이프라인
```
사용자 질문 입력
        ↓
   질문 분류 에이전트
        ↓
   ┌─────────────┐
   │ 분류 결과   │
   └─────────────┘
        ↓
   ┌─────────────┐    ┌─────────────┐
   │ 명료화 필요  │    │ 답변 가능   │
   │ (needs_clarify) │    │ (answerable) │
   └─────────────┘    └─────────────┘
        ↓                    ↓
명료화 에이전트        답변 생성 에이전트
        ↓                    ↓
   명료화 질문           최종 답변 생성
        ↓                    ↓
   사용자 응답 ←─────────────┘
        ↓
   관찰 에이전트
        ↓
   학습 요약 생성
```

### 2. 실시간 스트리밍 처리
```
사용자 질문
    ↓
백엔드 API
    ↓
Redis Streams (질문 전송)
    ↓
AI 에이전트 처리
    ↓
Redis Streams (답변 스트리밍)
    ↓
Server-Sent Events (SSE)
    ↓
프론트엔드 실시간 업데이트
```

## 🧠 AI 에이전트 시스템

### 에이전트 구성
1. **QuestionClassifierAgent**: 질문 분류 및 라우팅
   - 질문의 품질 평가 (12개 세부 항목)
   - 답변 가능성 판단
   - 적절한 처리 경로 선택

2. **QuestionImprovementAgent**: 명료화 처리
   - 모호한 질문의 명확화
   - 추가 정보 요청
   - 질문 개선 제안

3. **AnswerGeneratorAgent**: 답변 생성
   - 수학적 답변 생성
   - 단계별 해설 제공
   - 학습 목표 고려

4. **ObserverAgent**: 학습 관찰
   - 학습 진도 추적
   - 어려움 영역 식별
   - 세션 요약 생성

### 에이전트 간 통신
- **Redis Streams**: 백엔드 ↔ 에이전트 통신 (신뢰성 보장)
- **Redis Pub/Sub**: 에이전트 ↔ 에이전트 통신 (워크플로우 오케스트레이션)

## 💾 데이터 아키텍처

### 데이터베이스 설계
```
Users (사용자)
├── id, email, role, created_at
└── Sessions (대화 세션)
    ├── id, user_id, title, created_at
    └── Messages (메시지)
        ├── id, session_id, content, type, timestamp
        └── Agent_Responses (에이전트 응답)
            ├── id, message_id, agent_type, response_data
            └── Learning_Summaries (학습 요약)
                └── id, session_id, summary_data, created_at
```

### Redis 활용
- **Streams**: 메시지 큐 및 이벤트 스트리밍
- **Pub/Sub**: 실시간 알림 및 에이전트 협업
- **Cache**: 세션 데이터 및 임시 저장

## 🔐 보안 아키텍처

### 인증 및 권한
- **JWT 토큰**: 상태 비저장 인증
- **Google OAuth**: 소셜 로그인
- **역할 기반 접근 제어**: 학생/교사/관리자 권한 분리

### 데이터 보호
- **HTTPS**: 모든 통신 암호화
- **환경 변수**: 민감한 정보 보호
- **SQL 인젝션 방지**: SQLAlchemy ORM 사용

## 📊 모니터링 및 로깅

### 로깅 전략
- **구조화된 로그**: JSON 형태의 로그 메시지
- **로그 레벨**: DEBUG, INFO, WARNING, ERROR
- **중앙 집중식 로깅**: Docker 로그 수집

### 모니터링 지표
- **성능**: 응답 시간, 처리량
- **에러율**: 실패한 요청 비율
- **리소스 사용량**: CPU, 메모리, 디스크

## 🚀 확장성 고려사항

### 수평적 확장
- **마이크로서비스 아키텍처**: 독립적 서비스 배포
- **컨테이너화**: Docker 기반 배포
- **로드 밸런싱**: Nginx를 통한 트래픽 분산

### 성능 최적화
- **비동기 처리**: FastAPI의 비동기 지원
- **캐싱 전략**: Redis를 통한 데이터 캐싱
- **데이터베이스 최적화**: 인덱싱 및 쿼리 최적화

## 🔗 관련 문서

- [백엔드 아키텍처](./backend-architecture.md) - FastAPI 기반 백엔드 구조
- [프론트엔드 아키텍처](./frontend-architecture.md) - SvelteKit 기반 프론트엔드 구조
- [에이전트 시스템](./agent-system.md) - AI 에이전트 아키텍처 및 통신
- [데이터 플로우](./data-flow.md) - 시스템 내 데이터 흐름
