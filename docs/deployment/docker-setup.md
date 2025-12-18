# Docker 설정 가이드

MAICE 시스템의 Docker 기반 배포 및 설정을 상세히 설명합니다.

## 🐳 Docker 구조

### 전체 서비스 구성
```yaml
# docker-compose.yml
version: '3.8'

services:
  # 프론트엔드 (SvelteKit)
  front:
    build:
      context: ./front
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - VITE_API_BASE_URL=http://localhost:8000
    depends_on:
      - back
    volumes:
      - ./front:/app
      - /app/node_modules

  # 백엔드 (FastAPI)
  back:
    build:
      context: ./back
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://maice_user:password@postgres:5432/maice_db
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
    volumes:
      - ./back:/app

  # AI 에이전트 시스템
  agent:
    build:
      context: ./agent
      dockerfile: Dockerfile
    environment:
      - REDIS_URL=redis://redis:6379
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - redis
    volumes:
      - ./agent:/app

  # PostgreSQL 데이터베이스
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=maice_db
      - POSTGRES_USER=maice_user
      - POSTGRES_PASSWORD=password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./back/scripts/init.sql:/docker-entrypoint-initdb.d/init.sql

  # Redis (Streams & Pub/Sub)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  # Nginx 리버스 프록시
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/conf.d:/etc/nginx/conf.d
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - front
      - back

volumes:
  postgres_data:
  redis_data:
```

## 🚀 개발 환경 설정

### 개발용 Docker Compose
```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  front:
    build:
      context: ./front
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    environment:
      - VITE_API_BASE_URL=http://localhost:8000
      - VITE_DEV_MODE=true
    volumes:
      - ./front:/app
      - /app/node_modules
    command: npm run dev

  back:
    build:
      context: ./back
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://maice_user:password@postgres:5432/maice_db
      - REDIS_URL=redis://redis:6379
      - DEBUG=true
      - LOG_LEVEL=DEBUG
    volumes:
      - ./back:/app
    command: uvicorn main:app --reload --host 0.0.0.0 --port 8000

  agent:
    build:
      context: ./agent
      dockerfile: Dockerfile.dev
    environment:
      - REDIS_URL=redis://redis:6379
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DEBUG=true
    volumes:
      - ./agent:/app
    command: python worker.py --debug
```

### Dockerfile 예시

#### 프론트엔드 Dockerfile
```dockerfile
# front/Dockerfile
FROM node:18-alpine

WORKDIR /app

# 의존성 설치
COPY package*.json ./
RUN npm ci --only=production

# 소스 코드 복사
COPY . .

# 빌드
RUN npm run build

# 포트 노출
EXPOSE 3000

# 실행
CMD ["npm", "run", "preview"]
```

#### 백엔드 Dockerfile
```dockerfile
# back/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 포트 노출
EXPOSE 8000

# 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 에이전트 Dockerfile
```dockerfile
# agent/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 실행
CMD ["python", "worker.py"]
```

## 🔧 환경 변수 설정

### .env 파일 예시
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
JWT_SECRET_KEY=your_jwt_secret_key_change_in_production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Google OAuth 설정
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# AI 서비스 설정
OPENAI_API_KEY=your_openai_api_key

# 환경 설정
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# 보안 설정
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
ALLOWED_HOSTS=localhost,yourdomain.com
```

## 🚀 배포 명령어

### 기본 배포
```bash
# 전체 시스템 빌드 및 실행
docker-compose up --build -d

# 특정 서비스만 빌드
docker-compose build front
docker-compose build back
docker-compose build agent

# 서비스 재시작
docker-compose restart front
docker-compose restart back
docker-compose restart agent
```

### 개발 환경 실행
```bash
# 개발 모드로 실행
docker-compose -f docker-compose.dev.yml up --build

# 백그라운드 실행
docker-compose -f docker-compose.dev.yml up -d

# 로그 확인
docker-compose -f docker-compose.dev.yml logs -f
```

### 데이터베이스 마이그레이션
```bash
# 마이그레이션 실행
docker-compose exec back alembic upgrade head

# 마이그레이션 생성
docker-compose exec back alembic revision --autogenerate -m "description"

# 마이그레이션 히스토리 확인
docker-compose exec back alembic history
```

## 📊 모니터링 및 로그

### 로그 확인
```bash
# 모든 서비스 로그
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f front
docker-compose logs -f back
docker-compose logs -f agent

# 실시간 로그 모니터링
docker-compose logs --tail=100 -f back
```

### 서비스 상태 확인
```bash
# 실행 중인 컨테이너 확인
docker-compose ps

# 리소스 사용량 확인
docker stats

# 특정 서비스 상태 확인
docker-compose exec back curl http://localhost:8000/health
```

### 헬스 체크 설정
```yaml
# docker-compose.yml에 추가
services:
  back:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  front:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## 🔒 보안 설정

### SSL/TLS 설정
```nginx
# nginx/conf.d/ssl.conf
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    location / {
        proxy_pass http://front:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /api/ {
        proxy_pass http://back:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 네트워크 보안
```yaml
# docker-compose.yml에 추가
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true

services:
  front:
    networks:
      - frontend
  back:
    networks:
      - frontend
      - backend
  agent:
    networks:
      - backend
  postgres:
    networks:
      - backend
  redis:
    networks:
      - backend
```

## 🧹 정리 및 유지보수

### 정리 명령어
```bash
# 사용하지 않는 컨테이너 정리
docker container prune

# 사용하지 않는 이미지 정리
docker image prune

# 사용하지 않는 볼륨 정리
docker volume prune

# 전체 정리
docker system prune -a
```

### 백업 및 복원
```bash
# 데이터베이스 백업
docker-compose exec postgres pg_dump -U maice_user maice_db > backup.sql

# 데이터베이스 복원
docker-compose exec -T postgres psql -U maice_user maice_db < backup.sql

# Redis 백업
docker-compose exec redis redis-cli BGSAVE
docker cp $(docker-compose ps -q redis):/data/dump.rdb ./redis-backup.rdb
```

### 업데이트 프로세스
```bash
# 새 버전으로 업데이트
git pull origin main
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 마이그레이션 실행
docker-compose exec back alembic upgrade head
```

## 🐛 문제 해결

### 일반적인 문제들

#### 포트 충돌
```bash
# 사용 중인 포트 확인
netstat -tulpn | grep :3000
netstat -tulpn | grep :8000

# 다른 포트로 변경
# docker-compose.yml에서 포트 매핑 수정
```

#### 메모리 부족
```bash
# 메모리 사용량 확인
docker stats

# 메모리 제한 설정
services:
  back:
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

#### 데이터베이스 연결 실패
```bash
# 데이터베이스 상태 확인
docker-compose exec postgres pg_isready -U maice_user

# 연결 테스트
docker-compose exec back python -c "
import psycopg2
conn = psycopg2.connect('postgresql://maice_user:password@postgres:5432/maice_db')
print('연결 성공')
"
```

## 🔗 관련 문서

- [프로덕션 배포](./production-deployment.md) - 운영 환경 배포
- [Jenkins CI/CD](./jenkins-ci.md) - 지속적 통합/배포
- [문제 해결](../troubleshooting/common-issues.md) - 일반적인 문제 해결
- [시스템 아키텍처](../architecture/overview.md) - 전체 시스템 구조
