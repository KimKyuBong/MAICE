# MAICE 시스템 디버깅 가이드

## 📋 개요

MAICE 시스템의 디버깅 방법과 문제 해결 절차에 대한 상세한 가이드입니다.

## 🔍 시스템 모니터링

### 1. Docker 컨테이너 상태 확인
```bash
# 모든 컨테이너 상태 확인
docker ps -a

# 특정 서비스 로그 확인
docker logs maice-back --tail 100 -f
docker logs maice-agent --tail 100 -f
docker logs maicesystem_postgres_1 --tail 50 -f
docker logs maicesystem_redis_1 --tail 50 -f
docker logs maicesystem_nginx_1 --tail 50 -f

# 컨테이너 리소스 사용량 확인
docker stats
```

### 2. 네트워크 연결 확인
```bash
# 컨테이너 간 네트워크 연결 확인
docker network ls
docker network inspect maicesystem_maice_network

# 포트 연결 확인
netstat -tlnp | grep -E "(8000|3000|5432|6379|80|443)"

# 컨테이너 내부 네트워크 확인
docker exec maice-back netstat -tlnp
docker exec maice-agent netstat -tlnp
```

### 3. 데이터베이스 연결 확인
```bash
# PostgreSQL 연결 확인
docker exec maicesystem_postgres_1 psql -U postgres -d maice_web -c "SELECT version();"

# Redis 연결 확인
docker exec maicesystem_redis_1 redis-cli ping

# 데이터베이스 테이블 확인
docker exec maicesystem_postgres_1 psql -U postgres -d maice_web -c "\dt"
```

## 🐛 백엔드 디버깅

### 1. API 엔드포인트 디버깅
```bash
# 헬스체크 확인
curl -f http://localhost/health

# API 응답 확인
curl -f http://localhost/api/student/test

# 인증 API 테스트
curl -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass"}'

# MAICE API 테스트
curl -X POST http://localhost/api/maice/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"question":"테스트 질문","session_id":1}'
```

### 2. 로그 분석
```bash
# 백엔드 로그 실시간 모니터링
docker logs maice-back --tail 100 -f | grep -E "(ERROR|WARNING|INFO)"

# 특정 에러 패턴 검색
docker logs maice-back --tail 1000 | grep -i "error"

# API 요청 로그 확인
docker logs maice-back --tail 1000 | grep -E "(POST|GET|PUT|DELETE)"
```

### 3. 데이터베이스 디버깅
```bash
# 데이터베이스 연결 풀 상태 확인
docker exec maice-back python -c "
from app.database.postgres_db import get_db
import asyncio
async def check_db():
    db = get_db()
    result = await db.execute('SELECT 1')
    print('Database connection OK')
asyncio.run(check_db())
"

# 마이그레이션 상태 확인
docker exec maice-back python migration_check.py

# 데이터베이스 쿼리 실행
docker exec maicesystem_postgres_1 psql -U postgres -d maice_web -c "
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats 
WHERE schemaname = 'public'
ORDER BY tablename, attname;
"
```

## 🤖 에이전트 디버깅

### 1. 에이전트 상태 확인
```bash
# 에이전트 프로세스 확인
docker exec maice-agent ps aux

# 에이전트 로그 확인
docker logs maice-agent --tail 100 -f

# Redis Streams 상태 확인
docker exec maicesystem_redis_1 redis-cli XINFO STREAM maice:backend_to_agent
docker exec maicesystem_redis_1 redis-cli XINFO STREAM maice:agent_to_backend
```

### 2. Redis 통신 디버깅
```bash
# Redis Streams 메시지 확인
docker exec maicesystem_redis_1 redis-cli XREAD STREAMS maice:backend_to_agent maice:agent_to_backend 0

# Redis Pub/Sub 채널 확인
docker exec maicesystem_redis_1 redis-cli PUBSUB CHANNELS "maice:*"

# Redis 메모리 사용량 확인
docker exec maicesystem_redis_1 redis-cli INFO memory
```

### 3. LLM 호출 디버깅
```bash
# OpenAI API 키 확인
docker exec maice-agent env | grep OPENAI_API_KEY

# LLM 응답 시간 측정
docker logs maice-agent --tail 1000 | grep -E "LLM.*response.*time"

# 프롬프트 디버깅
docker logs maice-agent --tail 1000 | grep -E "prompt.*debug"
```

## 🎨 프론트엔드 디버깅

### 1. 브라우저 개발자 도구
```javascript
// 콘솔에서 API 호출 확인
fetch('/api/maice/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + localStorage.getItem('token')
  },
  body: JSON.stringify({
    question: '테스트 질문',
    session_id: 1
  })
}).then(response => response.json())
  .then(data => console.log(data));

// 네트워크 탭에서 요청/응답 확인
// Elements 탭에서 DOM 구조 확인
// Console 탭에서 JavaScript 에러 확인
```

### 2. Svelte 개발자 도구
```bash
# Svelte 개발 서버 실행
cd front
npm run dev

# 브라우저에서 http://localhost:5173 접속
# 개발자 도구에서 Svelte 탭 확인
```

### 3. 테스트 디버깅
```bash
# 프론트엔드 테스트 실행
cd front
npm run test

# 특정 테스트 디버깅
npm run test Button.test.ts -- --reporter=verbose

# E2E 테스트 디버깅
npm run test:e2e -- --headed --debug
```

## 🔧 성능 디버깅

### 1. 응답 시간 측정
```bash
# API 응답 시간 측정
time curl -f http://localhost/api/student/test

# 데이터베이스 쿼리 성능 확인
docker exec maicesystem_postgres_1 psql -U postgres -d maice_web -c "
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;
"
```

### 2. 메모리 사용량 확인
```bash
# 컨테이너 메모리 사용량
docker stats --no-stream

# 프로세스별 메모리 사용량
docker exec maice-back ps aux --sort=-%mem
docker exec maice-agent ps aux --sort=-%mem

# 시스템 메모리 사용량
free -h
```

### 3. CPU 사용량 확인
```bash
# 컨테이너 CPU 사용량
docker stats --no-stream

# 프로세스별 CPU 사용량
docker exec maice-back top -bn1
docker exec maice-agent top -bn1

# 시스템 CPU 사용량
top -bn1
```

## 🚨 일반적인 문제 해결

### 1. 컨테이너 시작 실패
```bash
# 컨테이너 로그 확인
docker logs <container_name> --tail 100

# 환경변수 확인
docker exec <container_name> env | grep -E "(DATABASE|REDIS|OPENAI)"

# 네트워크 확인
docker network inspect maicesystem_maice_network

# 볼륨 마운트 확인
docker inspect <container_name> | grep -A 10 "Mounts"
```

### 2. 데이터베이스 연결 실패
```bash
# PostgreSQL 서비스 상태 확인
docker exec maicesystem_postgres_1 pg_isready -U postgres

# 데이터베이스 존재 확인
docker exec maicesystem_postgres_1 psql -U postgres -l

# 연결 풀 확인
docker exec maicesystem_postgres_1 psql -U postgres -d maice_web -c "
SELECT 
    state,
    count(*)
FROM pg_stat_activity 
GROUP BY state;
"
```

### 3. Redis 연결 실패
```bash
# Redis 서비스 상태 확인
docker exec maicesystem_redis_1 redis-cli ping

# Redis 메모리 사용량 확인
docker exec maicesystem_redis_1 redis-cli INFO memory

# Redis 키 확인
docker exec maicesystem_redis_1 redis-cli KEYS "*"
```

### 4. API 응답 없음
```bash
# Nginx 설정 확인
docker exec maicesystem_nginx_1 nginx -t

# Nginx 로그 확인
docker logs maicesystem_nginx_1 --tail 100

# 백엔드 프로세스 확인
docker exec maice-back ps aux

# 포트 확인
docker exec maice-back netstat -tlnp
```

## 🔍 로그 분석 도구

### 1. 로그 집계 및 분석
```bash
# 에러 로그 집계
docker logs maice-back --tail 10000 | grep -i error | sort | uniq -c | sort -nr

# API 요청 패턴 분석
docker logs maice-back --tail 10000 | grep -E "(POST|GET|PUT|DELETE)" | awk '{print $7}' | sort | uniq -c | sort -nr

# 응답 시간 분석
docker logs maice-back --tail 10000 | grep -E "response.*time" | awk '{print $NF}' | sort -n
```

### 2. 실시간 모니터링
```bash
# 실시간 로그 모니터링
docker logs maice-back --tail 100 -f | grep -E "(ERROR|WARNING)"

# 다중 컨테이너 로그 모니터링
docker-compose logs -f --tail=100

# 특정 패턴 모니터링
docker logs maice-back --tail 100 -f | grep -E "(timeout|connection|failed)"
```

### 3. 로그 파일 저장
```bash
# 로그 파일로 저장
docker logs maice-back --tail 10000 > backend.log
docker logs maice-agent --tail 10000 > agent.log
docker logs maicesystem_postgres_1 --tail 1000 > postgres.log
docker logs maicesystem_redis_1 --tail 1000 > redis.log
docker logs maicesystem_nginx_1 --tail 1000 > nginx.log
```

## 🛠️ 디버깅 도구

### 1. Python 디버깅
```python
# 백엔드 디버깅
import pdb; pdb.set_trace()

# 로깅 설정
import logging
logging.basicConfig(level=logging.DEBUG)

# 비동기 디버깅
import asyncio
asyncio.run(debug_function())
```

### 2. JavaScript 디버깅
```javascript
// 프론트엔드 디버깅
console.log('Debug info:', data);
debugger; // 브라우저에서 중단점

// 에러 핸들링
try {
  // 코드
} catch (error) {
  console.error('Error:', error);
}
```

### 3. 데이터베이스 디버깅
```sql
-- 쿼리 실행 계획 확인
EXPLAIN ANALYZE SELECT * FROM users WHERE username = 'testuser';

-- 인덱스 사용량 확인
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

## 📊 성능 프로파일링

### 1. 백엔드 프로파일링
```python
# cProfile 사용
import cProfile
cProfile.run('your_function()')

# line_profiler 사용
@profile
def your_function():
    # 코드
    pass
```

### 2. 프론트엔드 프로파일링
```javascript
// 성능 측정
const start = performance.now();
// 코드 실행
const end = performance.now();
console.log(`Execution time: ${end - start} milliseconds`);

// 메모리 사용량 측정
console.log(performance.memory);
```

### 3. 데이터베이스 프로파일링
```sql
-- 쿼리 성능 분석
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    stddev_time,
    rows
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;
```

## 🔄 문제 해결 체크리스트

### 1. 시스템 상태 확인
- [ ] Docker 컨테이너 실행 상태
- [ ] 네트워크 연결 상태
- [ ] 데이터베이스 연결 상태
- [ ] Redis 연결 상태
- [ ] 디스크 공간 확인
- [ ] 메모리 사용량 확인

### 2. 애플리케이션 상태 확인
- [ ] API 엔드포인트 응답
- [ ] 에이전트 프로세스 상태
- [ ] 로그 에러 확인
- [ ] 환경변수 설정 확인
- [ ] 설정 파일 확인

### 3. 성능 상태 확인
- [ ] 응답 시간 측정
- [ ] CPU 사용량 확인
- [ ] 메모리 사용량 확인
- [ ] 데이터베이스 쿼리 성능
- [ ] Redis 메모리 사용량

### 4. 보안 상태 확인
- [ ] API 키 유효성
- [ ] 인증 토큰 유효성
- [ ] 네트워크 보안 설정
- [ ] 데이터베이스 접근 권한
- [ ] 로그 보안 확인
