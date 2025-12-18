# MAICE 프로덕션 배포 가이드

## 📋 배포 전 체크리스트

### 1. 환경 준비
- [ ] Jenkins 서버 접근 가능
- [ ] Docker Registry (192.168.1.107:5000) 접근 가능
- [ ] KB-Web 서버 접근 가능
- [ ] PostgreSQL 데이터베이스 접근 가능

### 2. Jenkins Credentials 확인
다음 Credentials가 Jenkins에 등록되어 있어야 합니다:

```
- OPENAI_API_KEY (String)
- GEMINI_API_KEY (String)
- CLOUDE_API_KEY (String)
- ADMIN_USERNAME (String)
- ADMIN_PASSWORD (String)
- SESSION_SECRET_KEY (String)
- GOOGLE_CLIENT_ID (String)
- GOOGLE_CLIENT_SECRET (String)
- GOOGLE_REDIRECT_URI (String)
```

### 3. 데이터베이스 마이그레이션 준비
- [ ] 기존 데이터 백업 완료
- [ ] 마이그레이션 스크립트 검토 완료

## 🔄 배포 프로세스

### 1. 자동 배포 (Jenkins)

#### 프로덕션 배포
```bash
# Jenkins 파이프라인에서 다음 파라미터로 실행:
DEPLOY_ENV: production
SKIP_TESTS: false
FORCE_REBUILD: false (필요시 true)
```

#### 스테이징 배포
```bash
# Jenkins 파이프라인에서 다음 파라미터로 실행:
DEPLOY_ENV: staging
SKIP_TESTS: false
FORCE_REBUILD: false
```

### 2. 수동 배포 (긴급시)

#### 2.1 코드 배포
```bash
# 1. 저장소 업데이트
git pull origin main

# 2. Docker 이미지 빌드
docker build -f back/Dockerfile -t maice-system-back:manual back/
docker build -f agent/Dockerfile -t maice-system-agent:manual agent/

# 3. 프론트엔드 빌드
cd front
yarn install
yarn build
cd ..
```

#### 2.2 데이터베이스 마이그레이션
```bash
cd back

# 마이그레이션 필요성 확인
python migration_check.py

# 마이그레이션 실행 (필요시)
python migrate.py
```

#### 2.3 서비스 배포
```bash
# 기존 서비스 중지
docker compose -f docker-compose.prod.yml down

# 새 서비스 시작
docker compose -f docker-compose.prod.yml up -d postgres redis nginx

# 백엔드/에이전트 컨테이너 실행
# (환경변수는 실제 값으로 대체)
docker run -d --name maice-back --network maicesystem_maice_network \
    -e DATABASE_URL=postgresql://postgres:postgres@postgres:5432/maice_web \
    -e REDIS_URL=redis://redis:6379 \
    -e OPENAI_API_KEY="sk-..." \
    # ... 기타 환경변수
    maice-system-back:manual

docker run -d --name maice-agent --network maicesystem_maice_network \
    -e REDIS_URL=redis://redis:6379 \
    -e OPENAI_API_KEY="sk-..." \
    # ... 기타 환경변수
    maice-system-agent:manual
```

## 🔍 배포 후 확인

### 1. 헬스체크
```bash
# 백엔드 API 확인
curl -f http://localhost/health

# 프론트엔드 확인
curl -f http://localhost/

# 데이터베이스 연결 확인
curl -f http://localhost/api/student/test
```

### 2. 로그 확인
```bash
# 백엔드 로그
docker logs maice-back --tail 50

# 에이전트 로그
docker logs maice-agent --tail 50

# Nginx 로그
docker logs maicesystem_nginx_1 --tail 50

# PostgreSQL 로그
docker logs maicesystem_postgres_1 --tail 50
```

### 3. 서비스 상태 확인
```bash
# 컨테이너 상태
docker ps

# 네트워크 연결 확인
docker network inspect maicesystem_maice_network
```

## 🚨 문제 해결

### 1. 마이그레이션 실패
```bash
# 데이터베이스 상태 확인
python migration_check.py

# 수동 마이그레이션 재시도
python migrate.py

# 백업에서 복구 (최후 수단)
# psql -h localhost -U postgres -d maice_web < backup_before_migration_YYYYMMDD_HHMMSS.sql
```

### 2. 컨테이너 시작 실패
```bash
# 로그 확인
docker logs [container_name] --tail 100

# 환경변수 확인
docker exec [container_name] env | grep -E "(DATABASE|REDIS|OPENAI)"

# 네트워크 확인
docker network ls
docker network inspect maicesystem_maice_network
```

### 3. API 응답 없음
```bash
# Nginx 설정 확인
docker exec maicesystem_nginx_1 nginx -t

# 백엔드 프로세스 확인
docker exec maice-back ps aux

# 포트 확인
docker exec maice-back netstat -tlnp
```

## 📊 모니터링

### 1. 시스템 리소스
```bash
# Docker 리소스 사용량
docker stats

# 디스크 사용량
df -h

# 메모리 사용량
free -h
```

### 2. 애플리케이션 메트릭
- 백엔드 API 응답 시간
- 에이전트 처리 시간
- 데이터베이스 연결 수
- Redis 연결 수

## 🔄 롤백 절차

### 자동 롤백 (Jenkins)
Jenkins 파이프라인이 실패하면 자동으로 이전 버전으로 롤백됩니다.

### 수동 롤백
```bash
# 1. 이전 이미지로 컨테이너 재시작
docker stop maice-back maice-agent
docker rm maice-back maice-agent

# 2. 이전 버전 실행
docker run -d --name maice-back ... maice-system-back:previous
docker run -d --name maice-agent ... maice-system-agent:previous

# 3. 데이터베이스 롤백 (필요시)
# 백업에서 복구
```

## 📞 지원 연락처

배포 중 문제가 발생하면 다음으로 연락하세요:
- 개발팀: [연락처]
- 인프라팀: [연락처]
- 긴급상황: [연락처]
