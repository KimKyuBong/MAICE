# MAICE 시스템 모니터링 가이드

## 📊 모니터링 개요

MAICE 시스템의 상태를 실시간으로 모니터링하고 문제를 조기에 발견하는 방법을 설명합니다.

## 🎯 핵심 모니터링 지표

### 1. 시스템 리소스
- **CPU 사용률**: < 70%
- **메모리 사용률**: < 80%
- **디스크 사용률**: < 85%
- **네트워크 대역폭**: < 100Mbps

### 2. 애플리케이션 지표
- **응답 시간**: < 5초 (95%ile)
- **에러율**: < 1%
- **처리량**: > 40 QPS
- **가용성**: > 99.9%

### 3. 비즈니스 지표
- **사용자 만족도**: > 4.0/5.0
- **질문 해결률**: > 95%
- **학습 효과**: A/B 테스트 결과 기반

## 🔍 모니터링 도구

### 1. Docker 모니터링
```bash
# 컨테이너 리소스 사용량
docker stats

# 특정 컨테이너 모니터링
docker stats maice-back maice-agent maice-front

# 컨테이너 상태 확인
docker ps -a
```

### 2. 로그 모니터링
```bash
# 실시간 로그 모니터링
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f maice-back
docker-compose logs -f maice-agent

# 에러 로그만 필터링
docker-compose logs -f maice-back | grep ERROR
docker-compose logs -f maice-agent | grep ERROR
```

### 3. 데이터베이스 모니터링
```bash
# PostgreSQL 상태 확인
docker exec -it maicesystem_postgres_1 psql -U postgres -d maice_web -c "SELECT * FROM pg_stat_activity;"

# Redis 상태 확인
docker exec -it maicesystem_redis_1 redis-cli info

# Redis 메모리 사용량
docker exec -it maicesystem_redis_1 redis-cli info memory
```

## 📈 성능 모니터링

### 1. 백엔드 성능
```bash
# FastAPI 성능 모니터링
curl -s http://localhost:8000/health | jq

# 응답 시간 측정
time curl -s http://localhost:8000/api/v1/auth/me
```

### 2. 프론트엔드 성능
```bash
# 프론트엔드 서버 상태
curl -s http://localhost:5173

# 빌드 성능 확인
cd front
yarn build --analyze
```

### 3. AI 에이전트 성능
```bash
# 에이전트 프로세스 상태
docker exec -it maicesystem_maice-agent_1 ps aux

# 에이전트 메모리 사용량
docker exec -it maicesystem_maice-agent_1 free -h
```

## 🚨 알림 설정

### 1. 로그 기반 알림
```bash
# 에러 로그 모니터링 스크립트
#!/bin/bash
while true; do
  if docker-compose logs --tail=100 maice-back | grep -q "ERROR"; then
    echo "ERROR detected in maice-back at $(date)" | mail -s "MAICE Error Alert" admin@example.com
  fi
  sleep 60
done
```

### 2. 리소스 기반 알림
```bash
# CPU 사용률 모니터링
#!/bin/bash
CPU_USAGE=$(docker stats --no-stream --format "table {{.CPUPerc}}" maice-back | tail -n 1 | sed 's/%//')
if (( $(echo "$CPU_USAGE > 80" | bc -l) )); then
  echo "High CPU usage: ${CPU_USAGE}% at $(date)" | mail -s "MAICE High CPU Alert" admin@example.com
fi
```

### 3. 헬스 체크 알림
```bash
# 헬스 체크 모니터링
#!/bin/bash
HEALTH_STATUS=$(curl -s http://localhost:8000/health | jq -r '.status')
if [ "$HEALTH_STATUS" != "healthy" ]; then
  echo "System health check failed: $HEALTH_STATUS at $(date)" | mail -s "MAICE Health Check Failed" admin@example.com
fi
```

## 🔧 문제 진단

### 1. 일반적인 문제 진단
```bash
# 시스템 리소스 확인
docker system df
docker system prune -f

# 컨테이너 재시작
docker-compose restart maice-back
docker-compose restart maice-agent

# 로그 레벨 변경
docker-compose down
docker-compose up -d --build
```

### 2. 데이터베이스 문제 진단
```bash
# PostgreSQL 연결 테스트
docker exec -it maicesystem_postgres_1 psql -U postgres -d maice_web -c "SELECT 1;"

# 데이터베이스 크기 확인
docker exec -it maicesystem_postgres_1 psql -U postgres -d maice_web -c "SELECT pg_size_pretty(pg_database_size('maice_web'));"

# 활성 연결 확인
docker exec -it maicesystem_postgres_1 psql -U postgres -d maice_web -c "SELECT count(*) FROM pg_stat_activity;"
```

### 3. Redis 문제 진단
```bash
# Redis 연결 테스트
docker exec -it maicesystem_redis_1 redis-cli ping

# Redis 메모리 사용량
docker exec -it maicesystem_redis_1 redis-cli info memory

# Redis 키 개수
docker exec -it maicesystem_redis_1 redis-cli dbsize
```

## 📊 모니터링 대시보드

### 1. 간단한 대시보드 스크립트
```bash
#!/bin/bash
# MAICE 시스템 상태 대시보드

echo "=== MAICE System Status Dashboard ==="
echo "Timestamp: $(date)"
echo

# 시스템 리소스
echo "=== System Resources ==="
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
echo

# 서비스 상태
echo "=== Service Status ==="
docker-compose ps
echo

# 데이터베이스 상태
echo "=== Database Status ==="
docker exec -it maicesystem_postgres_1 psql -U postgres -d maice_web -c "SELECT 'PostgreSQL' as service, 'healthy' as status;"
docker exec -it maicesystem_redis_1 redis-cli ping
echo

# 최근 에러 로그
echo "=== Recent Errors ==="
docker-compose logs --tail=10 maice-back | grep ERROR || echo "No recent errors"
echo
```

### 2. 웹 기반 모니터링
```html
<!DOCTYPE html>
<html>
<head>
    <title>MAICE System Monitor</title>
    <meta http-equiv="refresh" content="30">
</head>
<body>
    <h1>MAICE System Monitor</h1>
    <div id="status">
        <h2>System Status</h2>
        <p>Backend: <span id="backend-status">Checking...</span></p>
        <p>Frontend: <span id="frontend-status">Checking...</span></p>
        <p>Agent: <span id="agent-status">Checking...</span></p>
        <p>Database: <span id="db-status">Checking...</span></p>
    </div>
    
    <script>
        // 헬스 체크 함수들
        async function checkBackend() {
            try {
                const response = await fetch('http://localhost:8000/health');
                const data = await response.json();
                document.getElementById('backend-status').textContent = data.status;
            } catch (error) {
                document.getElementById('backend-status').textContent = 'Error';
            }
        }
        
        async function checkFrontend() {
            try {
                const response = await fetch('http://localhost:5173');
                document.getElementById('frontend-status').textContent = 'Healthy';
            } catch (error) {
                document.getElementById('frontend-status').textContent = 'Error';
            }
        }
        
        // 모든 체크 실행
        checkBackend();
        checkFrontend();
    </script>
</body>
</html>
```

## 🚨 장애 대응

### 1. 서비스 장애 대응
```bash
# 1. 서비스 상태 확인
docker-compose ps

# 2. 로그 확인
docker-compose logs --tail=50 maice-back

# 3. 서비스 재시작
docker-compose restart maice-back

# 4. 전체 재시작 (필요시)
docker-compose down
docker-compose up -d
```

### 2. 데이터베이스 장애 대응
```bash
# 1. 데이터베이스 연결 확인
docker exec -it maicesystem_postgres_1 psql -U postgres -d maice_web -c "SELECT 1;"

# 2. 데이터베이스 재시작
docker-compose restart postgres

# 3. 백업에서 복원 (필요시)
docker exec -it maicesystem_postgres_1 psql -U postgres -d maice_web < backup.sql
```

### 3. AI 에이전트 장애 대응
```bash
# 1. 에이전트 프로세스 확인
docker exec -it maicesystem_maice-agent_1 ps aux

# 2. 에이전트 재시작
docker-compose restart maice-agent

# 3. 개별 에이전트 테스트
docker exec -it maicesystem_maice-agent_1 python -m agents.question_classifier.agent
```

## 📋 모니터링 체크리스트

### 일일 체크리스트
- [ ] 시스템 리소스 사용량 확인
- [ ] 서비스 상태 확인
- [ ] 에러 로그 확인
- [ ] 데이터베이스 상태 확인
- [ ] Redis 상태 확인

### 주간 체크리스트
- [ ] 로그 파일 정리
- [ ] 데이터베이스 백업 확인
- [ ] 성능 지표 분석
- [ ] 보안 업데이트 확인
- [ ] 용량 사용량 확인

### 월간 체크리스트
- [ ] 전체 시스템 성능 분석
- [ ] 용량 계획 검토
- [ ] 보안 감사
- [ ] 백업 복원 테스트
- [ ] 모니터링 도구 업데이트

## 🔗 관련 문서

- [문제 해결 가이드](./common-issues.md) - 일반적인 문제 해결
- [디버깅 가이드](./debugging-guide.md) - 상세 디버깅 방법
- [성능 벤치마크](../architecture/performance-benchmarks.md) - 성능 기준
- [배포 가이드](../deployment/production-deployment.md) - 프로덕션 배포