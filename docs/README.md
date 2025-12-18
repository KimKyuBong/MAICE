# MAICE 시스템 문서화 가이드

MAICE(Mathematical AI Chatbot for Education) 시스템의 완전한 문서화 가이드입니다. 본 시스템은 Bloom의 학습 목표 분류법을 기반으로 한 4단계 지식 분류 시스템과 3단계 게이팅 메커니즘을 통해 개인화된 수학 교육을 제공하는 AI 기반 학습 플랫폼입니다.

## 🎯 시스템 개요

MAICE는 고등학교 수학 교육을 위한 AI 기반 채팅 시스템으로, 다음과 같은 핵심 기능을 제공합니다:

- **AI 기반 질문 분류**: 12개 세부 항목으로 질문 품질 자동 평가 (15점 만점)
- **멀티 에이전트 시스템**: 5개 독립 에이전트의 협업을 통한 지능적 답변 생성
- **실시간 스트리밍**: Server-Sent Events 기반 실시간 채팅
- **커리큘럼 기반 학습**: 교과과정 위계성을 고려한 맞춤형 답변
- **학습 진도 추적**: 개인별 학습 상태 및 어려움 영역 분석
- **A/B 테스트**: Agent 모드 vs FreePass 모드 효과 비교

## 📚 문서 구조

### 🚀 [시작하기](./getting-started/)
- [설치 가이드](./getting-started/installation.md) - Docker 기반 시스템 설치 및 환경 설정
- [빠른 시작](./getting-started/quick-start.md) - 첫 번째 실행 가이드 및 기본 사용법
- [개발 환경 설정](./getting-started/development-setup.md) - 개발자를 위한 환경 구성

### 🏗️ [아키텍처](./architecture/)
- [시스템 개요](./architecture/overview.md) - 전체 시스템 구조 및 핵심 개념
- [백엔드 아키텍처](./architecture/backend-architecture.md) - FastAPI 기반 API 서버 구조
- [프론트엔드 아키텍처](./architecture/frontend-architecture.md) - SvelteKit SPA 모드 구조
- [에이전트 시스템](./architecture/agent-system.md) - 5개 독립 AI 에이전트 아키텍처
- [에이전트 프롬프트](./architecture/agent-prompts.md) - AI 에이전트 프롬프트 시스템
- [데이터 플로우](./architecture/data-flow.md) - Redis Streams 기반 데이터 흐름

### 🔌 [API 문서](./api/)
- [인증 API](./api/authentication.md) - JWT, Google OAuth 2.0 인증
- [MAICE API](./api/maice-api.md) - 핵심 채팅 및 세션 관리 API
- [스트리밍 API](./api/streaming-api.md) - Server-Sent Events 실시간 통신

### 🧩 [컴포넌트 가이드](./components/)
- [프론트엔드 컴포넌트](./components/frontend-components.md) - SvelteKit 기반 UI 컴포넌트
- [테마 시스템](./components/theme-system.md) - 라이트/다크 테마 구현
- [수학 입력 시스템](./components/math-input.md) - MathLive 기반 수식 입력

### 🚀 [배포 가이드](./deployment/)
- [Docker 설정](./deployment/docker-setup.md) - 컨테이너 기반 배포
- [프로덕션 배포](./deployment/production-deployment.md) - 운영 환경 배포
- [Jenkins CI/CD](./deployment/jenkins-ci.md) - 지속적 통합/배포 파이프라인
- [Blue-Green 배포](./deployment/BLUE_GREEN_DEPLOYMENT_GUIDE.md) - 무중단 배포 전략
- [인프라 관리](./deployment/infrastructure-management.md) - 서버 및 네트워크 관리

### 🧪 [테스트 가이드](./testing/)
- [테스트 전략](./testing/testing-strategy.md) - 성능, 부하, A/B 테스트 전략
- [테스트 실행](./testing/test-execution.md) - 테스트 실행 방법 및 결과 분석

### 📋 [실험 도구](./experiments/)
- [학생 설문조사지](./experiments/student_survey_questionnaire.md) - MAICE 시스템 학습 효과 평가용 20문항 설문지
- [교사 평가 설문지](./experiments/teacher_evaluation_questionnaire.md) - 교육적 효과성 평가용 15문항 설문지
- [A/B 테스트 실험](./experiments/AB_TEST_EXPERIMENT_PLAN.md) - Agent vs FreePass 모드 비교 실험
- [명료화 프롬프트 개선](./experiments/CLARIFICATION_PROMPT_IMPROVEMENT.md) - 질문 명료화 알고리즘 개선

### 🔧 [문제 해결](./troubleshooting/)
- [일반적인 문제](./troubleshooting/common-issues.md) - 자주 발생하는 문제와 해결책
- [디버깅 가이드](./troubleshooting/debugging-guide.md) - 시스템 모니터링 및 디버깅 방법

## 🎯 핵심 기능

### AI 기반 질문 분류
- **12개 세부 항목**: 질문 품질 자동 평가 (15점 만점)
- **커리큘럼 기반**: 교과과정 위계성을 고려한 학습 가이드
- **실시간 추적**: 개인별 학습 진도 및 어려움 영역 분석

### 멀티 에이전트 시스템
- **5개 독립 에이전트**: QuestionClassifier, QuestionImprovement, AnswerGenerator, Observer, FreeTalker
- **Redis Streams**: 백엔드 ↔ 에이전트 신뢰성 있는 통신
- **Redis Pub/Sub**: 에이전트 간 협업 및 워크플로우 오케스트레이션
- **멀티프로세스**: 각 에이전트 독립 실행, 자동 재시작

### 실시간 대화 시스템
- **Server-Sent Events**: 실시간 스트리밍 채팅
- **연속적 맥락**: 대화 세션 기반 학습 맥락 이해
- **A/B 테스트**: Agent 모드 vs FreePass 모드 비교

### 사용자 인터페이스
- **SvelteKit 2.0**: SPA 모드, 반응형 웹 인터페이스
- **MathLive**: 수학 수식 입력 및 렌더링
- **다크/라이트 테마**: 사용자 선호도 기반 테마 전환
- **Google OAuth**: 소셜 로그인 지원

## 🛠️ 기술 스택

- **백엔드**: FastAPI 0.104.1, SQLAlchemy 2.0.23, PostgreSQL 15, Redis 7
- **프론트엔드**: SvelteKit 2.0, TypeScript, Tailwind CSS 4.x, Vite 5.x
- **AI 에이전트**: Python, Redis Streams, OpenAI GPT-4o-mini
- **인프라**: Docker, Nginx, Jenkins CI/CD
- **도구**: 7개 Desmos 통합 도구, MCP 시스템

## 📖 빠른 시작

1. [설치 가이드](./getting-started/installation.md)를 따라 Docker 기반 시스템을 설치하세요
2. [빠른 시작](./getting-started/quick-start.md)을 통해 첫 번째 실행을 해보세요
3. [시스템 개요](./architecture/overview.md)에서 전체 아키텍처를 파악하세요
4. [에이전트 시스템](./architecture/agent-system.md)에서 5개 AI 에이전트 구조를 이해하세요
5. [MAICE API](./api/maice-api.md)에서 핵심 API 사용법을 확인하세요
6. [테스트 가이드](./testing/testing-strategy.md)에서 시스템 테스트 방법을 학습하세요

## 🤝 기여하기

문서 개선이나 새로운 내용 추가에 기여하고 싶으시다면:

1. **문서 구조**: 각 섹션별 명확한 분류와 일관된 스타일 유지
2. **코드 예제**: 실제 동작하는 코드와 설정 예제 제공
3. **다이어그램**: Mermaid를 활용한 시각적 설명 추가
4. **업데이트**: 시스템 변경사항을 문서에 즉시 반영

## 📝 문서 업데이트

이 문서는 시스템의 현재 상태를 반영하여 작성되었습니다. 시스템 업데이트 시 관련 문서도 함께 업데이트해주세요.

## 🔄 최근 업데이트

- **2025-01-27**: 문서 구조 완전 재정리 및 통합
- **멀티 에이전트 시스템**: 5개 독립 에이전트 아키텍처 문서화
- **Redis Streams**: 실시간 통신 및 데이터 플로우 문서화
- **A/B 테스트**: Agent vs FreePass 모드 실험 도구 추가
- **Docker 구성**: 개발/프로덕션 환경 분리 가이드
- **성능 테스트**: 부하 테스트 및 벤치마킹 도구 문서화
