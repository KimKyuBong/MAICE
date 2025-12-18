# 설치 가이드

MAICE 시스템을 로컬 환경에 설치하고 실행하는 방법을 안내합니다.

## 📋 사전 요구사항

### 필수 소프트웨어
- **Docker**: 20.10.0 이상
- **Docker Compose**: 2.0.0 이상
- **Git**: 2.30.0 이상

### 권장 사양
- **메모리**: 최소 8GB RAM
- **저장공간**: 최소 10GB 여유 공간
- **CPU**: 4코어 이상

## 🚀 설치 과정

### 1. 저장소 클론
```bash
git clone https://github.com/your-org/MAICESystem.git
cd MAICESystem
```

### 2. 환경 변수 설정
```bash
cp env.example .env
```

`.env` 파일을 편집하여 필요한 환경 변수를 설정합니다:

```env
# 데이터베이스 설정
POSTGRES_DB=maice_db
POSTGRES_USER=maice_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Redis 설정
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# JWT 설정
JWT_SECRET_KEY=your_jwt_secret_key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Google OAuth 설정
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# AI 서비스 설정
OPENAI_API_KEY=your_openai_api_key
```

### 3. Docker 컨테이너 빌드 및 실행
```bash
# 전체 시스템 빌드
docker-compose build

# 백그라운드에서 실행
docker-compose up -d
```

### 4. 데이터베이스 마이그레이션
```bash
# 백엔드 컨테이너에서 마이그레이션 실행
docker-compose exec back alembic upgrade head
```

### 5. 테스트 사용자 생성 (선택사항)
```bash
# 테스트용 사용자 계정 생성
docker-compose exec back python scripts/create_test_users.py
```

## 🔍 설치 확인

### 서비스 상태 확인
```bash
# 모든 서비스 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs -f
```

### 웹 인터페이스 접속
- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs

## 🐛 문제 해결

### 포트 충돌
```bash
# 사용 중인 포트 확인
netstat -tulpn | grep :3000
netstat -tulpn | grep :8000

# 다른 포트로 변경하려면 docker-compose.yml 수정
```

### 컨테이너 재시작
```bash
# 특정 서비스 재시작
docker-compose restart front
docker-compose restart back
docker-compose restart agent

# 전체 시스템 재시작
docker-compose down
docker-compose up -d
```

### 로그 확인
```bash
# 특정 서비스 로그
docker-compose logs front
docker-compose logs back
docker-compose logs agent

# 실시간 로그 모니터링
docker-compose logs -f back
```

## 📚 다음 단계

설치가 완료되면 다음 문서를 참고하세요:

- [빠른 시작](./quick-start.md) - 첫 번째 사용법
- [개발 환경 설정](./development-setup.md) - 개발을 위한 추가 설정
- [시스템 개요](../architecture/overview.md) - 전체 시스템 이해
