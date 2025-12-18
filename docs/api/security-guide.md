# MAICE API 보안 가이드

## 🔐 보안 개요

MAICE 시스템의 API 보안 정책, 인증 방식, 그리고 보안 모범 사례를 설명합니다.

## 🛡️ 보안 아키텍처

### 1. 인증 계층
```
┌─────────────────────────────────────────────────────────┐
│                    클라이언트                           │
├─────────────────────────────────────────────────────────┤
│  JWT Token / Google OAuth 2.0 / Session Management     │
├─────────────────────────────────────────────────────────┤
│                    API Gateway                          │
├─────────────────────────────────────────────────────────┤
│  Rate Limiting / CORS / Input Validation / XSS Protection │
├─────────────────────────────────────────────────────────┤
│                    백엔드 서비스                        │
├─────────────────────────────────────────────────────────┤
│  Role-Based Access Control / Data Encryption           │
├─────────────────────────────────────────────────────────┤
│                    데이터베이스                         │
└─────────────────────────────────────────────────────────┘
```

### 2. 보안 구성 요소
- **JWT 토큰**: 상태 비저장 인증
- **Google OAuth 2.0**: 소셜 로그인
- **HTTPS**: 모든 통신 암호화
- **CORS**: Cross-Origin Resource Sharing 제어
- **Rate Limiting**: API 요청 제한
- **Input Validation**: 입력 데이터 검증
- **XSS Protection**: Cross-Site Scripting 방지

## 🔑 인증 및 권한

### 1. JWT 토큰 인증
```javascript
// 토큰 획득
const loginResponse = await fetch('/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username, password })
});

const { access_token, refresh_token } = await loginResponse.json();

// API 요청에 토큰 포함
const apiResponse = await fetch('/api/v1/student/sessions', {
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  }
});
```

### 2. Google OAuth 2.0
```javascript
// Google OAuth 로그인
const googleLoginUrl = '/api/v1/auth/google';
window.location.href = googleLoginUrl;

// 콜백 처리
const urlParams = new URLSearchParams(window.location.search);
const code = urlParams.get('code');
if (code) {
  const response = await fetch('/api/v1/auth/google/callback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code })
  });
}
```

### 3. 역할 기반 접근 제어 (RBAC)
```python
# 백엔드에서 권한 확인
from fastapi import Depends, HTTPException, status
from app.core.auth import get_current_user
from app.models.models import UserRole

async def require_teacher_role(
    current_user: UserModel = Depends(get_current_user)
):
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher role required"
        )
    return current_user

# 교사 전용 API
@router.get("/teacher/students", dependencies=[Depends(require_teacher_role)])
async def get_students():
    # 교사만 접근 가능
    pass
```

## 🚫 보안 위협 및 대응

### 1. SQL 인젝션 방지
```python
# SQLAlchemy ORM 사용 (자동 이스케이프)
from sqlalchemy import select
from app.models.models import UserModel

# 안전한 쿼리
async def get_user_by_email(email: str, db: AsyncSession):
    result = await db.execute(
        select(UserModel).where(UserModel.email == email)
    )
    return result.scalar_one_or_none()

# 위험한 쿼리 (사용 금지)
# query = f"SELECT * FROM users WHERE email = '{email}'"  # ❌
```

### 2. XSS (Cross-Site Scripting) 방지
```javascript
// 프론트엔드에서 DOMPurify 사용
import DOMPurify from 'dompurify';

function sanitizeInput(input) {
  return DOMPurify.sanitize(input);
}

// 사용자 입력 표시 시
const userInput = "<script>alert('XSS')</script>";
const safeInput = sanitizeInput(userInput);
document.getElementById('content').innerHTML = safeInput;
```

### 3. CSRF (Cross-Site Request Forgery) 방지
```python
# SameSite 쿠키 설정
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://maice.kbworks.xyz"],  # 신뢰할 수 있는 도메인만
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### 4. Rate Limiting
```python
# 요청 제한 미들웨어 (현재 구현 예정)
# TODO: slowapi 또는 FastAPI-limiter 라이브러리 도입 예정

# 현재는 기본적인 요청 제한을 위한 로직 구현
from collections import defaultdict
import time

# 간단한 메모리 기반 Rate Limiting
request_counts = defaultdict(list)

def check_rate_limit(client_ip: str, limit: int = 60, window: int = 60) -> bool:
    """간단한 Rate Limiting 체크"""
    now = time.time()
    # 윈도우 내의 요청만 유지
    request_counts[client_ip] = [
        req_time for req_time in request_counts[client_ip] 
        if now - req_time < window
    ]
    
    if len(request_counts[client_ip]) >= limit:
        return False
    
    request_counts[client_ip].append(now)
    return True

# API 엔드포인트에 제한 적용 (예정)
@router.post("/chat/streaming")
async def chat_streaming(request: Request, ...):
    client_ip = request.client.host
    if not check_rate_limit(client_ip, limit=10, window=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    # ... 기존 로직
```

## 🔒 데이터 보호

### 1. 비밀번호 해싱
```python
import bcrypt

def hash_password(password: str) -> str:
    """비밀번호를 해시화합니다."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호가 올바른지 확인합니다."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
```

### 2. 민감한 데이터 암호화
```python
from cryptography.fernet import Fernet
import os

# 환경 변수에서 키 가져오기
encryption_key = os.getenv('ENCRYPTION_KEY')
cipher_suite = Fernet(encryption_key)

def encrypt_data(data: str) -> str:
    """데이터를 암호화합니다."""
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    """암호화된 데이터를 복호화합니다."""
    return cipher_suite.decrypt(encrypted_data.encode()).decode()
```

### 3. 환경 변수 보안
```bash
# .env 파일 보안 설정 (Docker 환경)
# 호스트에서 파일 권한 제한
chmod 600 .env

# Docker 컨테이너 내부에서는 자동으로 보호됨
# 컨테이너 간 환경 변수 전달은 Docker secrets 사용 권장

# 환경 변수 예시
DATABASE_URL=postgresql://user:password@postgres:5432/maice_web
REDIS_URL=redis://redis:6379
JWT_SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-encryption-key-here
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Docker Compose에서 환경 변수 보안 설정
# docker-compose.yml에서 env_file 사용
services:
  maice-back:
    env_file:
      - .env
    # 또는 개별 환경 변수 설정
    environment:
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - DATABASE_URL=${DATABASE_URL}
```

## 🛡️ 보안 모니터링

### 1. 로그 모니터링
```python
import logging
from datetime import datetime

# 보안 이벤트 로깅
security_logger = logging.getLogger('security')

def log_security_event(event_type: str, user_id: int, details: str):
    """보안 이벤트를 로깅합니다."""
    security_logger.warning(f"Security Event: {event_type} - User: {user_id} - Details: {details}")

# 로그인 실패 추적
def track_failed_login(email: str, ip_address: str):
    log_security_event("FAILED_LOGIN", 0, f"Email: {email}, IP: {ip_address}")
```

### 2. 의심스러운 활동 감지
```python
# 로그인 시도 제한
from collections import defaultdict
import time

failed_attempts = defaultdict(list)

def check_login_attempts(email: str, ip_address: str) -> bool:
    """로그인 시도 제한을 확인합니다."""
    now = time.time()
    key = f"{email}:{ip_address}"
    
    # 5분 이내 5회 이상 실패 시 차단
    recent_attempts = [t for t in failed_attempts[key] if now - t < 300]
    if len(recent_attempts) >= 5:
        log_security_event("LOGIN_BLOCKED", 0, f"Email: {email}, IP: {ip_address}")
        return False
    
    return True
```

### 3. 보안 헬스 체크
```python
# 보안 상태 확인
async def security_health_check():
    """보안 상태를 확인합니다."""
    checks = {
        "jwt_secret_set": bool(os.getenv('JWT_SECRET_KEY')),
        "encryption_key_set": bool(os.getenv('ENCRYPTION_KEY')),
        "https_enabled": os.getenv('ENVIRONMENT') == 'production',
        "cors_configured": True,  # CORS 설정 확인
    }
    
    return {
        "security_status": "healthy" if all(checks.values()) else "unhealthy",
        "checks": checks
    }
```

## 📋 보안 체크리스트

### 개발 시 체크리스트
- [ ] 모든 사용자 입력 검증
- [ ] SQL 인젝션 방지 (ORM 사용)
- [ ] XSS 방지 (입력/출력 필터링)
- [ ] CSRF 방지 (SameSite 쿠키)
- [ ] Rate Limiting 적용
- [ ] 민감한 데이터 암호화
- [ ] 환경 변수 보안 설정
- [ ] 로그에 민감한 정보 포함 금지

### 배포 시 체크리스트
- [ ] HTTPS 강제 설정
- [ ] 보안 헤더 설정
- [ ] 데이터베이스 접근 제한
- [ ] 방화벽 설정
- [ ] 정기적인 보안 업데이트
- [ ] 백업 암호화
- [ ] 모니터링 시스템 구축

### 운영 시 체크리스트
- [ ] 정기적인 보안 감사
- [ ] 로그 모니터링
- [ ] 침입 탐지 시스템
- [ ] 취약점 스캔
- [ ] 보안 패치 적용
- [ ] 접근 권한 검토
- [ ] 데이터 백업 검증

## 🚨 보안 사고 대응

### 1. 사고 대응 절차
```bash
# 1. 사고 확인 및 격리
docker-compose down
docker-compose up -d --no-deps postgres redis

# 2. 로그 수집
docker-compose logs --tail=1000 > security_incident.log

# 3. 시스템 상태 확인
docker ps -a
docker stats

# 4. 보안 패치 적용
git pull origin main
docker-compose up -d --build
```

### 2. 복구 절차
```bash
# 1. 백업에서 복원
docker exec -it maicesystem_postgres_1 psql -U postgres -d maice_web < backup.sql

# 2. 시스템 재시작
docker-compose down
docker-compose up -d

# 3. 보안 상태 확인
curl -s http://localhost:8000/health | jq
```

## 🔗 관련 문서

- [인증 API](./authentication.md) - 인증 관련 API
- [MAICE API](./maice-api.md) - 핵심 API 문서
- [모니터링 가이드](../troubleshooting/monitoring-guide.md) - 시스템 모니터링
- [배포 가이드](../deployment/production-deployment.md) - 프로덕션 배포