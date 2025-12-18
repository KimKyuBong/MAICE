# MAICE 시스템 Blue-Green 무중단 배포 가이드

## 📋 개요

MAICE 시스템은 **Blue-Green 배포 전략**을 통해 **완전한 무중단 배포(Zero Downtime Deployment)**를 구현합니다.

### 주요 특징
- ✅ **0초 다운타임**: 배포 중에도 서비스 중단 없음
- ✅ **즉시 롤백**: 문제 발생 시 10초 이내 이전 버전으로 복구
- ✅ **안전한 배포**: 새 버전 검증 후 트래픽 전환
- ✅ **자동화**: Jenkins 파이프라인 완전 자동화

---

## 🏗️ 아키텍처

### Blue-Green 배포 구조

```
┌─────────────────────────────────────────┐
│          Nginx (Reverse Proxy)          │
│                                         │
│   upstream maice_backend {              │
│     server maice-back-blue:8000;  ← 활성│
│     server maice-back-green:8000 backup;│
│   }                                     │
└─────────────────────────────────────────┘
              │                    │
              ▼                    ▼
   ┌──────────────────┐  ┌──────────────────┐
   │ maice-back-blue  │  │ maice-back-green │
   │  (현재 활성)      │  │  (대기 중)        │
   │  v1.0.0         │  │  v0.9.0         │
   └──────────────────┘  └──────────────────┘
```

### 배포 프로세스

```
1. 현재 상태 확인
   ├─ Blue 활성, Green 대기
   
2. 새 버전을 Green에 배포
   ├─ Green 컨테이너 시작
   ├─ 헬스체크 통과 확인
   
3. Nginx upstream 전환 (무중단)
   ├─ Green → 활성
   ├─ Blue → 백업
   └─ nginx -s reload (graceful)
   
4. 검증 및 이전 버전 유지
   ├─ Green 트래픽 처리 확인
   └─ Blue 롤백용 대기
```

---

## 🚀 배포 방법

### 1. Jenkins를 통한 자동 배포 (권장)

#### 배포 실행
1. Jenkins 파이프라인 실행
2. 파라미터 선택:
   - `DEPLOY_ENV`: production
   - `FORCE_REBUILD`: false (변경사항만 빌드)
3. "Build" 클릭

#### 자동 수행 작업
- ✅ 이미지 빌드 및 Registry 푸시
- ✅ 현재 활성 환경 자동 감지 (Blue/Green)
- ✅ 비활성 환경에 새 버전 배포
- ✅ 헬스체크 및 검증
- ✅ Nginx upstream 무중단 전환
- ✅ 배포 후 모니터링

### 2. 수동 배포

#### 전제 조건
```bash
# 환경 변수 설정 필요
export REGISTRY_URL="your-registry:5000"
export BUILD_NUMBER="123"
export BACKEND_IMAGE="maice-back"
export DATABASE_URL="postgresql://..."
export OPENAI_API_KEY="sk-..."
export GOOGLE_CLIENT_ID="..."
export GOOGLE_CLIENT_SECRET="..."
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="..."
export SESSION_SECRET_KEY="..."
```

#### 배포 실행
```bash
cd /path/to/MAICESystem
./scripts/deploy_backend_blue_green.sh backend
```

#### 예상 출력
```
ℹ️  Blue-Green 무중단 배포 시작... (대상: backend)
✅ 모든 필수 환경 변수 확인 완료
ℹ️  현재 활성 환경: blue
ℹ️  새 배포 환경: green
ℹ️  새 green 환경에 백엔드 컨테이너 실행 중...
✅ 컨테이너 실행 완료: abc123def456
✅ 헬스체크 성공!
ℹ️  Nginx upstream 설정 변경 중 (무중단 전환)...
✅ Nginx upstream 전환 완료: blue → green
========================================
✅ Blue-Green 무중단 배포 완료!
========================================
✅ 현재 활성 환경: green
✅ 이전 환경 (롤백용): blue
```

---

## 🔄 롤백 방법

### 자동 롤백

배포 중 오류 발생 시 **자동으로 롤백**됩니다:
- 헬스체크 실패
- 컨테이너 시작 실패
- Nginx 설정 오류

### 수동 롤백

#### 즉시 롤백 (10초 이내)
```bash
./scripts/rollback_backend_blue_green.sh
```

#### 롤백 프로세스
1. 현재 활성 환경 확인 (예: Green)
2. 이전 환경 헬스체크 (Blue)
3. Nginx upstream 전환 (Green → Blue)
4. 검증 및 완료

#### 예상 출력
```
❌ ========================================
❌ Blue-Green 배포 롤백 시작
❌ ========================================
ℹ️  현재 활성 환경: green
ℹ️  롤백 대상 환경: blue
✅ 롤백 대상 환경 헬스체크 성공
ℹ️  Nginx upstream 설정 롤백 중...
✅ Nginx upstream 롤백 완료: green → blue
========================================
✅ 롤백 완료!
========================================
✅ 현재 활성 환경: blue
```

---

## 🔍 모니터링 및 검증

### 배포 상태 확인

#### 컨테이너 상태
```bash
docker ps --filter "name=maice-back" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

출력 예시:
```
NAMES               STATUS              PORTS
maice-back-green    Up 5 minutes        8000/tcp
maice-back-blue     Up 2 hours          8000/tcp
```

#### 활성 환경 확인 (Nginx 설정)
```bash
docker exec nginx cat /etc/nginx/conf.d/default.conf | grep -A 5 "upstream maice_backend"
```

출력 예시:
```nginx
upstream maice_backend {
    # Green 환경 (새로 배포된 환경 - 활성)
    server maice-back-green:8000 max_fails=3 fail_timeout=30s;
    
    # Blue 환경 (이전 환경 - 백업)
    server maice-back-green:8000 max_fails=3 fail_timeout=30s backup;
```

#### 헬스체크
```bash
# 직접 헬스체크
curl http://localhost/health

# 컨테이너별 헬스체크
docker exec maice-back-blue curl -f http://localhost:8000/health/simple
docker exec maice-back-green curl -f http://localhost:8000/health/simple
```

### 로그 확인

```bash
# 활성 환경 로그
docker logs maice-back-green --tail 100 -f

# 이전 환경 로그
docker logs maice-back-blue --tail 100 -f

# Nginx 로그
docker logs nginx --tail 100 -f
```

---

## 🛠️ 트러블슈팅

### 문제 1: 배포 중 헬스체크 실패

**증상**:
```
❌ 새 green 환경 헬스체크 최종 실패
```

**해결 방법**:
1. 컨테이너 로그 확인:
   ```bash
   docker logs maice-back-green --tail 50
   ```

2. 환경 변수 확인:
   ```bash
   docker exec maice-back-green env | grep -E "(DATABASE_URL|OPENAI_API_KEY|REDIS_URL)"
   ```

3. 데이터베이스 연결 확인:
   ```bash
   docker exec maice-back-green curl -f http://localhost:8000/health
   ```

4. 수동 롤백:
   ```bash
   ./scripts/rollback_backend_blue_green.sh
   ```

### 문제 2: 롤백 대상 환경이 없음

**증상**:
```
❌ 롤백 대상 환경(maice-back-blue)이 실행되지 않고 있습니다
```

**원인**: 
- 최초 배포 시 이전 버전 없음
- 컨테이너가 수동으로 삭제됨

**해결 방법**:
1. 이전 버전 이미지가 있다면 수동 복구:
   ```bash
   # 이전 빌드 번호 확인
   docker images | grep maice-back
   
   # 이전 버전으로 컨테이너 재시작
   docker run -d --name maice-back-blue \
     --network maicesystem_maice_network \
     -e DATABASE_URL="..." \
     maice-back:이전빌드번호
   ```

2. 또는 새 배포 진행 (현재 버전 유지)

### 문제 3: Nginx reload 실패

**증상**:
```
❌ Nginx 설정 파일 문법 검증 실패
```

**해결 방법**:
1. Nginx 설정 문법 확인:
   ```bash
   docker exec nginx nginx -t
   ```

2. 설정 파일 백업본으로 복구:
   ```bash
   docker cp nginx:/etc/nginx/conf.d/default.conf.backup \
              nginx:/etc/nginx/conf.d/default.conf
   docker exec nginx nginx -s reload
   ```

### 문제 4: 양쪽 환경 모두 실행 중

**증상**:
두 컨테이너가 모두 실행 중이지만 활성 환경을 알 수 없음

**해결 방법**:
```bash
# Nginx upstream 설정 확인
docker exec nginx cat /etc/nginx/conf.d/default.conf | grep -A 5 "upstream"

# backup 키워드가 없는 서버가 활성 환경
```

---

## 📊 성능 비교

### 기존 배포 vs Blue-Green 배포

| 항목 | 기존 방식 | Blue-Green | 개선율 |
|-----|----------|-----------|--------|
| 다운타임 | 3-10초 | **0초** | ✅ 100% |
| 롤백 시간 | 5-10분 | **10초** | ✅ 95% |
| 배포 안전성 | 중간 | **높음** | ✅ 향상 |
| 리소스 사용 | 낮음 | 중간 | - |

---

## 🔐 보안 고려사항

### 환경 변수 관리
- ✅ Jenkins Credentials로 민감 정보 관리
- ✅ 컨테이너 환경 변수는 런타임에만 주입
- ✅ 로그에 민감 정보 마스킹

### 네트워크 격리
- ✅ Blue/Green 모두 동일한 Docker 네트워크 사용
- ✅ 외부 포트 노출 없음 (Nginx만 80/443 노출)

---

## 📚 추가 자료

- [무중단 배포 아키텍처](./zero-downtime-deployment.md)
- [Jenkins 파이프라인 가이드](./jenkins-pipeline.md)
- [Docker Compose 설정](../../docker-compose.prod.yml)
- [Nginx 설정](../../nginx/conf.d/maice-prod.conf)

---

## 🤝 도움말

문제가 발생하거나 도움이 필요한 경우:
1. 로그 확인
2. 헬스체크 실행
3. 필요시 수동 롤백
4. 개발팀에 문의

**긴급 롤백 핫라인**: `./scripts/rollback_backend_blue_green.sh`

