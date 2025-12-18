# 개발 환경 설정

MAICE 시스템 개발을 위한 환경 설정 가이드입니다.

## 🛠️ 개발 환경 요구사항

### 필수 소프트웨어
- **Node.js**: 18.0.0 이상
- **Python**: 3.11 이상
- **PostgreSQL**: 14.0 이상
- **Redis**: 6.0 이상
- **Docker**: 20.10.0 이상 (선택사항)

### 개발 도구
- **VS Code**: 권장 IDE
- **Git**: 버전 관리
- **Postman**: API 테스트 (선택사항)

## 🚀 개발 환경 구성

### 1. 저장소 클론 및 브랜치 설정
```bash
git clone https://github.com/your-org/MAICESystem.git
cd MAICESystem
git checkout -b feature/your-feature-name
```

### 2. 환경 변수 설정
```bash
# 개발용 환경 변수 파일 생성
cp env.example .env.dev

# 개발용 설정으로 수정
vim .env.dev
```

개발용 환경 변수 예시:
```env
# 개발 환경 플래그
ENVIRONMENT=development
DEBUG=true

# 데이터베이스 설정 (로컬)
POSTGRES_DB=maice_dev
POSTGRES_USER=maice_dev
POSTGRES_PASSWORD=dev_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis 설정 (로컬)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# JWT 설정 (개발용)
JWT_SECRET_KEY=dev_secret_key_change_in_production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# Google OAuth (개발용)
GOOGLE_CLIENT_ID=your_dev_client_id
GOOGLE_CLIENT_SECRET=your_dev_client_secret
```

### 3. 프론트엔드 개발 환경
```bash
cd front

# 의존성 설치
npm install
# 또는
yarn install

# 개발 서버 실행
npm run dev
# 또는
yarn dev
```

### 4. 백엔드 개발 환경
```bash
cd back

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt

# 개발 서버 실행
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 에이전트 개발 환경
```bash
cd agent

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt

# 에이전트 실행
python worker.py
```

## 🗄️ 데이터베이스 설정

### PostgreSQL 설치 및 설정
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS (Homebrew)
brew install postgresql
brew services start postgresql

# Windows
# PostgreSQL 공식 사이트에서 설치
```

### 데이터베이스 생성
```bash
# PostgreSQL 접속
sudo -u postgres psql

# 데이터베이스 및 사용자 생성
CREATE DATABASE maice_dev;
CREATE USER maice_dev WITH PASSWORD 'dev_password';
GRANT ALL PRIVILEGES ON DATABASE maice_dev TO maice_dev;
\q
```

### 마이그레이션 실행
```bash
cd back
alembic upgrade head
```

## 🔧 개발 도구 설정

### VS Code 확장 프로그램
권장 확장 프로그램:
- **Python**: Python 언어 지원
- **Svelte for VS Code**: Svelte 문법 지원
- **Tailwind CSS IntelliSense**: Tailwind CSS 자동완성
- **GitLens**: Git 기능 확장
- **Docker**: Docker 파일 지원
- **PostgreSQL**: PostgreSQL 쿼리 지원

### VS Code 설정 (.vscode/settings.json)
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "typescript.preferences.importModuleSpecifier": "relative",
  "svelte.enable-ts-plugin": true
}
```

## 🧪 테스트 환경

### 프론트엔드 테스트
```bash
cd front

# 단위 테스트 실행
npm run test

# E2E 테스트 실행
npm run test:e2e

# 테스트 커버리지 확인
npm run test:coverage
```

### 백엔드 테스트
```bash
cd back

# 단위 테스트 실행
pytest

# 특정 테스트 실행
pytest tests/test_api.py

# 테스트 커버리지 확인
pytest --cov=app tests/
```

### 에이전트 테스트
```bash
cd agent

# 에이전트 테스트 실행
pytest tests/

# 특정 에이전트 테스트
pytest tests/test_question_classifier.py
```

## 🔍 디버깅 설정

### 백엔드 디버깅
```bash
# 디버그 모드로 실행
uvicorn main:app --reload --log-level debug

# 특정 모듈 디버깅
python -m pdb -c continue main.py
```

### 프론트엔드 디버깅
```bash
# 개발 서버 실행 (소스맵 포함)
npm run dev -- --sourcemap

# 브라우저 개발자 도구에서 디버깅
# Chrome DevTools > Sources 탭 활용
```

### 에이전트 디버깅
```bash
# 로그 레벨 설정
export LOG_LEVEL=DEBUG

# 에이전트 실행
python worker.py
```

## 📊 성능 모니터링

### 개발용 모니터링 도구
```bash
# 시스템 리소스 모니터링
htop

# 데이터베이스 연결 모니터링
pg_stat_activity

# Redis 모니터링
redis-cli monitor
```

### 프로파일링
```bash
# Python 프로파일링
python -m cProfile main.py

# 메모리 프로파일링
pip install memory-profiler
python -m memory_profiler main.py
```

## 🚀 배포 테스트

### 로컬 Docker 테스트
```bash
# 개발용 Docker Compose 실행
docker-compose -f docker-compose.dev.yml up --build

# 특정 서비스만 빌드
docker-compose build front
docker-compose build back
docker-compose build agent
```

### 스테이징 환경 테스트
```bash
# 스테이징 환경 배포
docker-compose -f docker-compose.staging.yml up -d

# 헬스 체크
curl http://localhost:8000/health
curl http://localhost:3000
```

## 📚 개발 가이드라인

### 코드 스타일
- **Python**: Black, isort 사용
- **TypeScript**: ESLint, Prettier 사용
- **Svelte**: 공식 스타일 가이드 준수

### 커밋 메시지 규칙
```
feat: 새로운 기능 추가
fix: 버그 수정
docs: 문서 수정
style: 코드 스타일 변경
refactor: 코드 리팩토링
test: 테스트 추가/수정
chore: 빌드 프로세스 또는 보조 도구 변경
```

### 브랜치 전략
- `main`: 프로덕션 브랜치
- `develop`: 개발 브랜치
- `feature/*`: 기능 개발 브랜치
- `hotfix/*`: 긴급 수정 브랜치

## 🔗 유용한 링크

- [시스템 아키텍처](../architecture/overview.md)
- [API 문서](../api/maice-api.md)
- [컴포넌트 가이드](../components/frontend-components.md)
- [문제 해결](../troubleshooting/debugging-guide.md)
