# MAICE 개발자 가이드

## 🚀 개발 환경 설정

### 1. 필수 요구사항
- **Docker**: 20.10 이상
- **Docker Compose**: 2.0 이상
- **Git**: 2.30 이상
- **Node.js**: 18 이상 (로컬 개발용)
- **Python**: 3.9 이상 (로컬 개발용)

### 2. 저장소 클론 및 설정
```bash
# 저장소 클론
git clone <repository-url>
cd MAICESystem

# 환경 변수 설정
cp env.example .env
# .env 파일 편집하여 필요한 설정 입력
```

### 3. Docker 기반 개발 환경
```bash
# 전체 시스템 시작
docker-compose up -d

# 특정 서비스만 시작
docker-compose up -d postgres redis maice-back maice-front maice-agent

# 로그 확인
docker-compose logs -f maice-back
docker-compose logs -f maice-agent
```

## 🏗️ 프로젝트 구조 이해

### 백엔드 (back/)
```
back/
├── app/
│   ├── api/routers/     # API 라우터
│   ├── core/           # 핵심 기능 (DB, Redis, 미들웨어)
│   ├── models/         # SQLAlchemy 데이터 모델
│   ├── services/       # 비즈니스 로직
│   ├── schemas/        # Pydantic 스키마
│   └── utils/          # 유틸리티 함수
├── alembic/            # 데이터베이스 마이그레이션
├── scripts/            # 관리 스크립트
├── main.py             # FastAPI 애플리케이션 진입점
└── api_router.py       # API 라우터 통합
```

### 프론트엔드 (front/)
```
front/
├── src/
│   ├── lib/
│   │   ├── components/  # UI 컴포넌트
│   │   ├── stores/      # Svelte stores
│   │   └── utils/       # 유틸리티 함수
│   └── routes/          # 페이지 라우트
├── static/              # 정적 파일
├── package.json         # 의존성 관리
└── svelte.config.js     # SvelteKit 설정
```

### AI 에이전트 (agent/)
```
agent/
├── agents/              # 에이전트 구현
│   ├── question_classifier/
│   ├── question_improvement/
│   ├── answer_generator/
│   ├── observer/
│   ├── freetalker/
│   ├── tools/           # 7개 Desmos 통합 도구
│   └── common/          # 공통 기능
├── core/                # 공통 기능
├── database/            # 데이터베이스 연결
└── worker.py            # 멀티프로세스 워커
```

## 🔧 개발 워크플로우

### 1. 기능 개발
```bash
# 새 기능 브랜치 생성
git checkout -b feature/new-feature

# 개발 작업 수행
# ...

# 커밋
git add .
git commit -m "feat: add new feature"

# 푸시
git push origin feature/new-feature
```

### 2. 로컬 개발 서버 실행
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

### 3. 데이터베이스 마이그레이션
```bash
# 백엔드 데이터베이스 마이그레이션
cd back
python migrate.py

# 에이전트 데이터베이스 마이그레이션
cd agent
python -c "from database.connection import init_db; import asyncio; asyncio.run(init_db())"
```

## 🧪 테스트 실행

### 1. 단위 테스트
```bash
# 백엔드 테스트
cd back
python -m pytest tests/

# 프론트엔드 테스트
cd front
yarn test
```

### 2. 통합 테스트
```bash
# 전체 시스템 테스트
cd tester
python run_advanced_tester.py

# 성능 테스트
python parallel_test_50_results.py
```

### 3. A/B 테스트
```bash
# A/B 테스트 실행
python AB_test_experiment.py
```

## 📝 코딩 스타일 가이드

### Python (백엔드)
```python
# PEP 8 준수
# 타입 힌트 사용
# async/await 패턴 활용

from typing import Optional, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
) -> Optional[UserModel]:
    """사용자 정보를 조회합니다."""
    result = await db.execute(
        select(UserModel).where(UserModel.id == user_id)
    )
    return result.scalar_one_or_none()
```

### TypeScript (프론트엔드)
```typescript
// ESLint 규칙 준수
// Svelte 5 문법 사용
// 타입 안전성 확보

interface User {
  id: number;
  email: string;
  role: 'student' | 'teacher' | 'admin';
}

async function fetchUser(id: number): Promise<User | null> {
  try {
    const response = await fetch(`/api/v1/users/${id}`);
    if (!response.ok) throw new Error('Failed to fetch user');
    return await response.json();
  } catch (error) {
    console.error('Error fetching user:', error);
    return null;
  }
}
```

### 커밋 메시지 규칙
```
feat: 새로운 기능 추가
fix: 버그 수정
docs: 문서 수정
style: 코드 스타일 변경
refactor: 코드 리팩토링
test: 테스트 코드 추가/수정
chore: 빌드 과정 또는 보조 도구 변경
```

## 🔍 디버깅 가이드

### 1. 백엔드 디버깅
```bash
# 로그 확인
docker-compose logs -f maice-back

# 디버그 모드 실행
cd back
uvicorn main:app --reload --log-level debug
```

### 2. 프론트엔드 디버깅
```bash
# 개발자 도구 활성화
cd front
yarn dev --host 0.0.0.0

# 브라우저 개발자 도구에서 디버깅
```

### 3. AI 에이전트 디버깅
```bash
# 에이전트 로그 확인
docker-compose logs -f maice-agent

# 개별 에이전트 테스트
cd agent
python -m agents.question_classifier.agent
```

## 📊 성능 모니터링

### 1. 시스템 리소스 모니터링
```bash
# Docker 컨테이너 리소스 사용량
docker stats

# 특정 컨테이너 모니터링
docker stats maice-back maice-agent
```

### 2. 애플리케이션 로그 모니터링
```bash
# 실시간 로그 모니터링
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f maice-back | grep ERROR
```

### 3. 데이터베이스 모니터링
```bash
# PostgreSQL 연결 확인
docker exec -it maicesystem_postgres_1 psql -U postgres -d maice_web

# Redis 연결 확인
docker exec -it maicesystem_redis_1 redis-cli ping
```

## 🚀 배포 가이드

### 1. 개발 환경 배포
```bash
# Docker Compose로 개발 환경 실행
docker-compose up -d
```

### 2. 프로덕션 환경 배포
```bash
# 프로덕션 Docker Compose 실행
docker-compose -f docker-compose.prod.yml up -d
```

### 3. Blue-Green 배포
```bash
# Blue-Green 배포 스크립트 실행
./scripts/blue-green-deploy.sh
```

## 🔧 문제 해결

### 1. 일반적인 문제
- **포트 충돌**: 다른 서비스가 사용 중인 포트 확인
- **메모리 부족**: Docker 메모리 할당량 증가
- **네트워크 문제**: Docker 네트워크 설정 확인

### 2. 데이터베이스 문제
- **연결 실패**: 데이터베이스 서비스 상태 확인
- **마이그레이션 실패**: 마이그레이션 파일 확인
- **권한 문제**: 데이터베이스 사용자 권한 확인

### 3. AI 에이전트 문제
- **에이전트 응답 없음**: Redis 연결 상태 확인
- **메모리 누수**: 에이전트 프로세스 재시작
- **프롬프트 오류**: 프롬프트 설정 파일 확인

## 📚 추가 리소스

### 문서
- [시스템 아키텍처](../architecture/overview.md)
- [API 문서](../api/maice-api.md)
- [테스트 가이드](../testing/testing-strategy.md)

### 도구
- [Postman Collection](./postman-collection.json) - API 테스트
- [Docker Compose 파일](./docker-compose.yml) - 개발 환경
- [환경 변수 템플릿](./env.example) - 설정 가이드

### 커뮤니티
- [GitHub Issues](https://github.com/your-repo/issues) - 버그 리포트
- [Discussions](https://github.com/your-repo/discussions) - 질문 및 토론
- [Wiki](https://github.com/your-repo/wiki) - 추가 문서

## 🤝 기여하기

1. **이슈 생성**: 버그 리포트 또는 기능 요청
2. **브랜치 생성**: `feature/` 또는 `fix/` 접두사 사용
3. **코드 작성**: 코딩 스타일 가이드 준수
4. **테스트 작성**: 새로운 기능에 대한 테스트 코드
5. **Pull Request**: 상세한 설명과 함께 PR 생성

## 📞 지원

- **이메일**: dev@maice-system.com
- **Slack**: #maice-development
- **문서**: [개발자 문서](../README.md)