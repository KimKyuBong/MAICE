# MAICE 시스템 무중단 배포 가이드

## 개요

MAICE 시스템은 Blue-Green 배포 방식을 사용하여 무중단 배포를 구현합니다. 이 시스템은 백엔드 서비스의 가용성을 보장하면서 새로운 버전을 배포할 수 있습니다.

## 주요 구성 요소

### 1. Blue-Green 배포 아키텍처

```
┌─────────────────┐    ┌─────────────────┐
│   Nginx Proxy   │    │   Nginx Proxy   │
│                 │    │                 │
│  Upstream:      │    │  Upstream:      │
│  - Blue (활성)   │    │  - Green (활성)  │
│  - Green (백업)  │    │  - Blue (백업)   │
└─────────────────┘    └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│ maice-back-blue │    │maice-back-green │
│   (포트: 8000)   │    │   (포트: 8000)   │
└─────────────────┘    └─────────────────┘
```

### 2. 핵심 스크립트

- **`deploy_backend_blue_green.sh`**: Blue-Green 무중단 배포 실행
- **`rollback_backend.sh`**: 배포 실패 시 자동 롤백
- **`monitor_deployment.sh`**: 배포 후 상태 모니터링
- **`traffic_control.sh`**: 트래픽 제어 및 전환

### 3. Nginx Upstream 설정

```nginx
upstream maice_backend {
    # Blue 환경 (기본)
    server maice-back-blue:8000 max_fails=3 fail_timeout=30s;
    # Green 환경 (배포 시 활성화)
    server maice-back-green:8000 max_fails=3 fail_timeout=30s backup;
    
    keepalive 32;
}
```

## 배포 프로세스

### 1. 자동 배포 (Jenkins)

Jenkins 파이프라인에서 다음 단계로 무중단 배포를 수행합니다:

1. **이미지 빌드 및 푸시**
2. **현재 환경 확인** (Blue 또는 Green)
3. **새 환경에 컨테이너 배포**
4. **헬스체크 수행** (최대 30회 재시도)
5. **Nginx upstream 전환**
6. **기존 환경 정리**
7. **배포 상태 모니터링**

### 2. 수동 배포

```bash
# Blue-Green 배포 실행
./scripts/deploy_backend_blue_green.sh backend

# 배포 상태 모니터링
./scripts/monitor_deployment.sh

# 트래픽 제어
./scripts/traffic_control.sh status
./scripts/traffic_control.sh switch green
```

### 3. 롤백

```bash
# 자동 롤백 (배포 실패 시)
./scripts/rollback_backend.sh

# 수동 롤백
./scripts/traffic_control.sh switch blue
```

## 헬스체크

### 백엔드 헬스체크 엔드포인트

```http
GET /health
```

응답 예시:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "uptime_seconds": 3600,
  "version": "1.0.0",
  "environment": "production",
  "database": "healthy",
  "redis": "healthy"
}
```

### 헬스체크 기준

- **API 응답**: HTTP 200 상태 코드
- **데이터베이스 연결**: PostgreSQL 연결 확인
- **Redis 연결**: Redis 연결 확인
- **응답 시간**: 5초 이내 응답

## 모니터링

### 배포 상태 모니터링

배포 후 다음 항목들을 자동으로 모니터링합니다:

1. **헬스체크**: 컨테이너 상태 확인
2. **API 테스트**: 엔드포인트 응답 확인
3. **리소스 사용량**: CPU/메모리 사용률
4. **로그 분석**: 에러/예외 발생 여부

### 모니터링 명령어

```bash
# 배포 상태 확인
./scripts/monitor_deployment.sh

# 트래픽 상태 확인
./scripts/traffic_control.sh status

# 컨테이너 상태 확인
docker ps --filter "name=maice-back-"
```

## 트러블슈팅

### 일반적인 문제

1. **헬스체크 실패**
   ```bash
   # 컨테이너 로그 확인
   docker logs maice-back-blue --tail 50
   
   # 수동 헬스체크
   docker exec maice-back-blue curl http://localhost:8000/health
   ```

2. **Nginx upstream 전환 실패**
   ```bash
   # Nginx 설정 확인
   docker exec nginx nginx -T | grep upstream
   
   # Nginx 재시작
   docker exec nginx nginx -s reload
   ```

3. **배포 롤백**
   ```bash
   # 즉시 롤백
   ./scripts/rollback_backend.sh
   
   # 수동 트래픽 전환
   ./scripts/traffic_control.sh switch blue
   ```

### 로그 확인

```bash
# 백엔드 로그
docker logs maice-back-blue --tail 100 -f
docker logs maice-back-green --tail 100 -f

# Nginx 로그
docker logs nginx --tail 100 -f

# 에이전트 로그
docker logs maice-agent --tail 100 -f
```

## 보안 고려사항

1. **환경 변수**: 민감한 정보는 Jenkins Credentials로 관리
2. **네트워크**: Docker 네트워크를 통한 서비스 간 통신
3. **헬스체크**: 내부 네트워크에서만 접근 가능
4. **롤백**: 자동 롤백으로 서비스 가용성 보장

## 성능 최적화

1. **Keepalive**: Nginx upstream keepalive 설정
2. **커넥션 풀**: 데이터베이스 커넥션 풀링
3. **캐싱**: Redis를 통한 응답 캐싱
4. **리소스 모니터링**: CPU/메모리 사용률 추적

## 확장성

### 수평 확장

- 여러 백엔드 인스턴스 추가 가능
- 로드밸런싱을 통한 트래픽 분산
- 헬스체크 기반 자동 장애 조치

### 수직 확장

- 컨테이너 리소스 동적 조정
- 메모리/CPU 사용률 기반 스케일링
- 성능 모니터링을 통한 최적화

## 결론

MAICE 시스템의 무중단 배포는 Blue-Green 방식을 통해 서비스 가용성을 보장하며, 자동화된 헬스체크와 롤백 메커니즘으로 안정적인 배포를 제공합니다.
