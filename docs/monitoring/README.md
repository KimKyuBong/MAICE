# MAICE 모니터링 시스템

## 📊 개요

MAICE 시스템의 실시간 모니터링 및 시각화 솔루션입니다. 에이전트 성능 추적, 시스템 헬스 체크, 워크플로우 시각화를 제공합니다.

## 🏗️ 아키텍처

### 구성 요소

```
┌─────────────────────────────────────────────────────┐
│                   프론트엔드                         │
│  - 실시간 대시보드 (/admin/monitoring)              │
│  - 워크플로우 시각화                                 │
│  - 10초 자동 새로고침                                │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│                 백엔드 API                           │
│  - /api/monitoring/agents/status                    │
│  - /api/monitoring/metrics/summary                  │
│  - /api/monitoring/health/detailed                  │
│  - /api/monitoring/performance/timeline             │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│                   Redis                              │
│  - 메트릭 저장 (5초마다 플러시)                     │
│  - 에이전트 상태 추적                                │
│  - TTL: 1시간 (메트릭), 1분 (상태)                  │
└─────────────────────────────────────────────────────┘
                         ↑
┌─────────────────────────────────────────────────────┐
│                에이전트 시스템                       │
│  - 각 에이전트마다 AgentMetrics 인스턴스            │
│  - 자동 메트릭 수집 및 전송                          │
│  - BaseAgent에 통합                                  │
└─────────────────────────────────────────────────────┘
```

## 📁 파일 구조

### 백엔드

```
agent/
├── core/
│   └── metrics.py                  # 메트릭 수집 시스템 (NEW)
│       ├── AgentMetrics            # 에이전트별 메트릭 수집기
│       ├── MetricType              # 카운터, 게이지, 히스토그램
│       └── get_all_agent_metrics() # 전역 조회 함수
│
└── agents/
    └── base_agent.py               # 메트릭 통합 (UPDATED)
        ├── initialize_metrics()    # 메트릭 초기화
        ├── record_operation_*()    # 메트릭 기록 헬퍼
        └── get_status()            # 메트릭 포함 상태 반환

back/
└── app/
    └── api/
        └── routers/
            └── monitoring.py       # 모니터링 API (NEW)
                ├── GET /agents/status
                ├── GET /agents/{name}/metrics
                ├── GET /metrics/summary
                ├── GET /performance/timeline
                └── GET /health/detailed
```

### 프론트엔드

```
front/
├── src/
│   ├── lib/
│   │   ├── api.ts                                    # API 함수 추가 (UPDATED)
│   │   │   ├── getAgentsStatus()
│   │   │   ├── getMetricsSummary()
│   │   │   └── getDetailedHealth()
│   │   │
│   │   └── components/
│   │       └── monitoring/
│   │           └── WorkflowVisualization.svelte      # 워크플로우 시각화 (NEW)
│   │
│   └── routes/
│       └── admin/
│           ├── +page.svelte                          # 모니터링 링크 추가 (UPDATED)
│           └── monitoring/
│               └── +page.svelte                      # 실시간 모니터링 페이지 (NEW)
```

## 🚀 주요 기능

### 1. 에이전트 메트릭 수집 (`agent/core/metrics.py`)

#### 메트릭 타입

- **Counter**: 누적 카운터 (요청 수, 에러 수)
- **Gauge**: 현재 값 (메모리, 활성 세션)
- **Histogram**: 분포 (응답 시간)
- **Timer**: 시간 측정

#### 사용 예시

```python
# BaseAgent에서 자동 초기화
async def initialize(self):
    await self.initialize_metrics()  # AgentMetrics 생성

# 작업 기록
self.record_operation_start("classify_question")

# 시간 측정
async with self.metrics.measure_time("process_question"):
    await process_question()

# 성공/실패 기록
self.record_operation_success("classify_question", duration=1.5)
self.record_operation_error("classify_question", "timeout")
```

#### Redis 저장 구조

```
maice:metrics:{agent_name}:counter:{metric_name}    # 카운터 값
maice:metrics:{agent_name}:gauge:{metric_name}      # 게이지 값
maice:metrics:{agent_name}:histogram:{metric_name}  # 히스토그램 통계
maice:agent_status:{agent_name}                     # 에이전트 상태
```

### 2. 백엔드 모니터링 API (`back/app/api/routers/monitoring.py`)

#### 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/monitoring/agents/status` | GET | 모든 에이전트 상태 조회 |
| `/api/monitoring/agents/{name}/metrics` | GET | 특정 에이전트 상세 메트릭 |
| `/api/monitoring/metrics/summary` | GET | 전체 시스템 메트릭 요약 |
| `/api/monitoring/performance/timeline` | GET | 시간별 성능 추이 |
| `/api/monitoring/health/detailed` | GET | 상세 헬스 체크 |

#### 응답 예시

```json
{
  "timestamp": "2025-01-17T10:30:00",
  "system": {
    "total_requests": 1234,
    "total_errors": 5,
    "error_rate": 0.41,
    "avg_response_time": 2.5,
    "active_sessions": 12
  },
  "agents": [
    {
      "name": "QuestionClassifierAgent",
      "requests": 500,
      "errors": 2,
      "error_rate": 0.4,
      "avg_response_time": 1.2,
      "active_sessions": 3
    }
  ]
}
```

### 3. 실시간 모니터링 대시보드 (`/admin/monitoring`)

#### 주요 화면

1. **전체 상태 요약**
   - 전체 요청 수
   - 평균 응답 시간
   - 에러율
   - 활성 에이전트 수

2. **에이전트 상태**
   - 실시간 상태 (정상/중지됨)
   - 마지막 업데이트 시간
   - 메트릭 개수

3. **워크플로우 시각화**
   - 질문 → 분류 → 명료화/답변 → 관찰 흐름
   - 각 에이전트 요청 수
   - 상태별 색상 표시 (활성/대기/오류)

4. **에이전트별 성능**
   - 요청 수, 에러 수, 에러율
   - 평균 응답 시간
   - 활성 세션 수

5. **시스템 헬스**
   - API 서버 상태
   - 데이터베이스 상태
   - Redis 상태 (메모리 사용량)

#### 특징

- **10초 자동 새로고침**: 실시간 데이터 업데이트
- **다크모드 지원**: 무채색 디자인
- **반응형 디자인**: 모바일/태블릿/데스크톱

### 4. 워크플로우 시각화 (`WorkflowVisualization.svelte`)

#### 시각화 요소

```
   👤 사용자
    ↓
🔍 질문 분류 (QuestionClassifierAgent)
    ↓
  ┌─┴─┬─────┐
  ↓   ↓     ↓
 ✨  💬    🗨️
명료화 답변  자유
  ↓   ↓     ↓
  └─┬─┘     │
    ↓       │
 👁️ 관찰    │
    ↓       │
   ✅ 완료 ←┘
```

#### 상태 표시

- **초록색 테두리**: 활성 (요청 처리 중)
- **회색 테두리**: 대기 중
- **빨간색 테두리**: 오류 발생 (에러율 > 10%)

## 🔧 설정

### 환경 변수

```bash
REDIS_URL=redis://redis:6379  # Redis 연결 URL
```

### 메트릭 설정

```python
# agent/core/metrics.py
_flush_interval = 5  # Redis 플러시 간격 (초)

# Redis TTL
counter/gauge: 3600초 (1시간)
histogram: 3600초 (1시간)
agent_status: 60초 (1분)
```

### 프론트엔드 설정

```typescript
// front/src/routes/admin/monitoring/+page.svelte
const REFRESH_INTERVAL = 10000; // 자동 새로고침 간격 (ms)
```

## 📊 메트릭 수집 흐름

```
1. 에이전트 초기화
   └─> AgentMetrics 생성 및 Redis 연결

2. 작업 수행
   └─> metrics.record_request() 호출
       └─> 메모리에 메트릭 저장

3. 백그라운드 플러시 (5초마다)
   └─> Redis에 메트릭 저장
       ├─> counter: SET key value EX 3600
       ├─> gauge: SET key value EX 3600
       ├─> histogram: HSET key field value EX 3600
       └─> agent_status: HSET key field value EX 60

4. 백엔드 API 조회
   └─> Redis에서 메트릭 읽기
       └─> JSON 응답 반환

5. 프론트엔드 표시
   └─> 10초마다 API 호출
       └─> 실시간 대시보드 업데이트
```

## 🎯 사용 방법

### 1. 시스템 시작

```bash
# Docker Compose로 전체 시스템 시작
docker-compose up -d

# 에이전트 로그 확인 (메트릭 초기화 확인)
docker-compose logs -f maice-agent | grep metrics
```

### 2. 모니터링 대시보드 접속

```
http://localhost:5173/admin/monitoring
```

### 3. API 직접 호출 (테스트)

```bash
# 에이전트 상태 조회
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/monitoring/agents/status

# 메트릭 요약
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/monitoring/metrics/summary

# 상세 헬스 체크
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/monitoring/health/detailed
```

## 🐛 디버깅

### 메트릭이 수집되지 않는 경우

1. **에이전트 로그 확인**
   ```bash
   docker-compose logs maice-agent | grep "메트릭 수집기"
   ```
   - `✅ 메트릭 수집기 초기화 완료` 확인
   - `❌ 메트릭 수집기 초기화 실패` 시 Redis 연결 확인

2. **Redis 확인**
   ```bash
   docker exec -it maicesystem_redis_1 redis-cli
   > KEYS maice:metrics:*
   > HGETALL maice:agent_status:QuestionClassifierAgent
   ```

3. **백엔드 API 테스트**
   ```bash
   curl http://localhost:8000/api/monitoring/agents/status
   ```

### 대시보드가 로드되지 않는 경우

1. **브라우저 콘솔 확인**
   - 네트워크 탭에서 API 호출 상태 확인
   - 401 에러 → 로그인 확인
   - 500 에러 → 백엔드 로그 확인

2. **인증 확인**
   - 관리자 권한 필요 (role === 'admin')
   - JWT 토큰 유효성 확인

## 📈 성능 영향

### 메모리 사용량

- **에이전트당**: ~1-2MB (메트릭 저장)
- **Redis**: ~10-20MB (전체 메트릭)

### CPU 오버헤드

- **메트릭 수집**: < 1% (비동기 처리)
- **Redis 플러시**: < 1% (5초마다)

### 네트워크

- **Redis 트래픽**: ~1KB/s per agent
- **API 트래픽**: ~10KB/request

## 🔮 향후 개선 사항

### 단기 (1-2주)

- [ ] 차트 라이브러리 통합 (Chart.js)
  - 시간별 요청 수 라인 차트
  - 에이전트별 부하 바 차트
  - 응답 시간 히스토그램

- [ ] 알림 시스템
  - 에이전트 다운 감지
  - 에러율 임계값 초과
  - Slack/이메일 알림

- [ ] 로그 수집 시스템
  - Redis에 최근 로그 저장
  - 로그 뷰어 UI
  - 에러 로그 필터링

### 중기 (1개월)

- [ ] 메트릭 히스토리
  - 시계열 데이터베이스 (InfluxDB/TimescaleDB)
  - 장기 메트릭 보관
  - 트렌드 분석

- [ ] 고급 시각화
  - Mermaid.js 워크플로우
  - 인터랙티브 차트
  - 커스터마이징 가능한 대시보드

- [ ] 성능 분석 도구
  - 병목 지점 식별
  - 최적화 제안
  - A/B 테스트 메트릭

### 장기 (3개월+)

- [ ] Prometheus/Grafana 통합
  - 표준 메트릭 포맷
  - 고급 쿼리 및 알림
  - 업계 표준 도구 사용

- [ ] 분산 추적 (Distributed Tracing)
  - OpenTelemetry 통합
  - 요청 흐름 추적
  - 성능 병목 분석

## 📚 참고 자료

### 관련 문서

- [MAICE 시스템 아키텍처](../architecture/overview.md)
- [에이전트 시스템](../architecture/agent-system.md)
- [API 문서](../api/maice-api.md)

### 외부 리소스

- [Redis 문서](https://redis.io/docs/)
- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [Svelte 문서](https://svelte.dev/)

## 👥 기여

모니터링 시스템 개선에 기여하고 싶다면:

1. 이슈 생성: 버그 리포트 또는 기능 제안
2. Pull Request: 코드 개선 또는 문서 업데이트
3. 피드백: 사용 경험 및 개선 아이디어 공유

---

**마지막 업데이트**: 2025-01-17
**작성자**: MAICE Development Team



