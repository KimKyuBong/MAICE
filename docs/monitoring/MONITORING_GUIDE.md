# 🔍 MAICE 에이전트 모니터링 가이드

## 📊 개요

MAICE 시스템의 에이전트 처리 과정과 결과를 실시간으로 모니터링할 수 있는 시스템입니다.

## 🎯 모니터링 기능

### 1. **실시간 메트릭 수집**

각 에이전트는 다음 메트릭을 자동으로 수집합니다:

#### 카운터 (Counter)
- `classification_requests_total` - 전체 분류 요청 수
- `classification_success_total` - 분류 성공 수
- `classification_failed_total` - 분류 실패 수
- `answer_requests_total` - 전체 답변 요청 수
- `answer_success_total` - 답변 성공 수
- `answer_failed_total` - 답변 실패 수

#### 게이지 (Gauge)
- `active_sessions` - 현재 활성 세션 수

#### 히스토그램 (Histogram)
- `request_duration_seconds` - 요청 처리 시간 분포
  - min, max, avg, p50, p95, p99

### 2. **처리 로그 시스템**

각 처리 단계마다 로그가 Redis Streams에 기록됩니다:

#### QuestionClassifier
- `classification_start` - 분류 시작
- `classification_complete` - 분류 완료
- `classification_failed` - 분류 실패
- `classification_error` - 오류 발생

#### AnswerGenerator
- `answer_start` - 답변 생성 시작
- `answer_complete` - 답변 생성 완료
- `answer_failed` - 답변 생성 실패
- `answer_error` - 오류 발생

## 🔌 API 엔드포인트

모든 API는 관리자 권한이 필요합니다 (`/api/monitoring/*`)

### 1. 에이전트 상태 조회

```http
GET /api/monitoring/agents/status
```

**응답 예시:**
```json
{
  "timestamp": "2025-11-06T18:00:00+09:00",
  "agents": [
    {
      "agent_name": "QuestionClassifier",
      "is_alive": true,
      "last_update": 1730880000.0,
      "metrics_count": 5
    }
  ],
  "total_agents": 5,
  "active_agents": 5
}
```

### 2. 에이전트별 상세 메트릭

```http
GET /api/monitoring/agents/{agent_name}/metrics
```

**응답 예시:**
```json
{
  "agent_name": "QuestionClassifier",
  "timestamp": "2025-11-06T18:00:00+09:00",
  "counters": {
    "classification_requests_total": 150,
    "classification_success_total": 145,
    "classification_failed_total": 5
  },
  "gauges": {
    "active_sessions": 3
  },
  "histograms": {
    "request_duration_seconds": {
      "count": 150,
      "min": 0.5,
      "max": 3.2,
      "avg": 1.2,
      "p50": 1.1,
      "p95": 2.5,
      "p99": 3.0
    }
  }
}
```

### 3. 전체 시스템 메트릭 요약

```http
GET /api/monitoring/metrics/summary
```

**응답 예시:**
```json
{
  "timestamp": "2025-11-06T18:00:00+09:00",
  "system": {
    "total_requests": 300,
    "total_errors": 10,
    "error_rate": 3.33,
    "avg_response_time": 1.5,
    "active_sessions": 5
  },
  "agents": [
    {
      "name": "QuestionClassifier",
      "requests": 150,
      "errors": 5,
      "error_rate": 3.33,
      "avg_response_time": 1.2,
      "active_sessions": 3
    }
  ],
  "database": {
    "total_questions": 1500,
    "active_sessions": 10
  }
}
```

### 4. 세션별 처리 로그 ⭐️ NEW

```http
GET /api/monitoring/processing-logs/{session_id}
```

**응답 예시:**
```json
{
  "session_id": 123,
  "logs": [
    {
      "message_id": "1730880000000-0",
      "agent_name": "QuestionClassifier",
      "stage": "classification_start",
      "message": "질문 분류 시작",
      "timestamp": "2025-11-06T18:00:00+09:00"
    },
    {
      "message_id": "1730880001000-0",
      "agent_name": "QuestionClassifier",
      "stage": "classification_complete",
      "message": "분류 완료: K2 - answerable",
      "timestamp": "2025-11-06T18:00:01+09:00"
    },
    {
      "message_id": "1730880002000-0",
      "agent_name": "AnswerGenerator",
      "stage": "answer_start",
      "message": "답변 생성 시작",
      "timestamp": "2025-11-06T18:00:02+09:00"
    }
  ],
  "total": 3
}
```

### 5. 처리 요약 통계 ⭐️ NEW

```http
GET /api/monitoring/processing-summary?hours=1
```

**응답 예시:**
```json
{
  "timestamp": "2025-11-06T18:00:00+09:00",
  "time_range_hours": 1,
  "agents": [
    {
      "agent_name": "QuestionClassifier",
      "total_requests": 150,
      "successful": 145,
      "failed": 5,
      "success_rate": 96.67,
      "avg_duration_seconds": 1.2
    },
    {
      "agent_name": "AnswerGenerator",
      "total_requests": 145,
      "successful": 143,
      "failed": 2,
      "success_rate": 98.62,
      "avg_duration_seconds": 2.5
    }
  ]
}
```

### 6. 상세 헬스 체크

```http
GET /api/monitoring/health/detailed
```

## 🎨 프론트엔드 통합

### 예시: 실시간 모니터링 대시보드

```typescript
// API 호출 예시
async function fetchAgentMetrics() {
  const response = await fetch('/api/monitoring/agents/status', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  const data = await response.json();
  return data;
}

// 처리 로그 실시간 조회
async function fetchProcessingLogs(sessionId: number) {
  const response = await fetch(`/api/monitoring/processing-logs/${sessionId}`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  const logs = await response.json();
  
  // 로그를 타임라인으로 표시
  logs.logs.forEach(log => {
    console.log(`[${log.timestamp}] ${log.agent_name}: ${log.message}`);
  });
}

// 주기적 업데이트 (5초마다)
setInterval(async () => {
  const metrics = await fetchAgentMetrics();
  updateDashboard(metrics);
}, 5000);
```

## 📈 Redis 직접 조회

개발 중에는 Redis CLI로 직접 확인할 수 있습니다:

```bash
# 모든 메트릭 키 조회
docker-compose exec redis redis-cli KEYS "maice:metrics:*"

# QuestionClassifier 요청 수
docker-compose exec redis redis-cli GET "maice:metrics:QuestionClassifier:counter:classification_requests_total"

# AnswerGenerator 평균 처리 시간
docker-compose exec redis redis-cli HGETALL "maice:metrics:AnswerGenerator:histogram:request_duration_seconds{operation=answer_generation}"

# 에이전트 상태 확인
docker-compose exec redis redis-cli HGETALL "maice:agent_status:QuestionClassifier"

# 세션별 처리 로그 확인
docker-compose exec redis redis-cli XREVRANGE "maice:agent_to_backend_stream_session_123" + - COUNT 10
```

## 🔧 메트릭 플러시 주기

- **자동 플러시**: 5초마다 Redis에 저장
- **TTL**: 메트릭 데이터는 1시간 동안 유지
- **상태 정보**: 1분 동안 유지

## 🚨 알림 설정 (향후 확장)

다음 상황에서 알림을 보낼 수 있습니다:

1. **에러율 급증** - 에러율이 10% 초과
2. **응답 시간 지연** - 평균 응답 시간이 5초 초과
3. **에이전트 다운** - 1분 이상 업데이트 없음
4. **처리 실패** - 연속 3회 이상 실패

## 📊 대시보드 구성 예시

### 1. 개요 패널
- 전체 요청 수
- 평균 응답 시간
- 에러율
- 활성 세션 수

### 2. 에이전트별 상태
- 각 에이전트의 상태 (healthy/degraded/down)
- 처리량 (requests/sec)
- 성공률

### 3. 처리 타임라인
- 세션별 처리 과정 시각화
- 각 단계별 소요 시간
- 에러 발생 지점 강조

### 4. 성능 차트
- 시간대별 요청 수
- 응답 시간 분포
- 에러 발생 추이

## 🔍 디버깅 팁

### 1. 메트릭이 보이지 않을 때

```bash
# 에이전트 로그 확인
docker-compose logs -f maice-agent | grep "메트릭\|metrics"

# Redis 연결 확인
docker-compose exec redis redis-cli PING

# 메트릭 초기화 확인
docker-compose logs maice-agent | grep "메트릭 수집기 초기화"
```

### 2. 처리 로그가 없을 때

- 실제로 질문을 보내서 데이터를 생성해야 합니다
- 세션 ID가 정확한지 확인
- Redis Streams가 생성되었는지 확인

### 3. 성능이 느릴 때

- 메트릭 수집이 성능에 미치는 영향은 최소 (<1%)
- Redis 연결 상태 확인
- 메트릭 플러시 간격 조정 (기본 5초)

## 🎯 사용 시나리오

### 시나리오 1: 실시간 디버깅

```
1. 사용자가 질문 입력
2. 관리자 대시보드에서 해당 세션 ID 확인
3. /api/monitoring/processing-logs/{session_id} 호출
4. 각 에이전트의 처리 과정 확인
5. 에러 발생 시 정확한 단계와 메시지 확인
```

### 시나리오 2: 성능 분석

```
1. /api/monitoring/processing-summary?hours=24 호출
2. 에이전트별 성공률, 평균 처리 시간 확인
3. 병목 지점 식별
4. 성능 개선 작업 진행
```

### 시나리오 3: 장애 대응

```
1. /api/monitoring/agents/status로 에이전트 상태 확인
2. 다운된 에이전트 식별
3. 해당 에이전트 로그 확인
4. 재시작 또는 수동 개입
```

## 📝 참고사항

- 모든 타임스탬프는 ISO 8601 형식 (KST)
- 메트릭 데이터는 메모리와 Redis에 이중 저장
- 처리 로그는 Redis Streams에 영구 저장
- 관리자 권한 필요 (Bearer 토큰)

## 🔗 관련 문서

- [에이전트 아키텍처](../architecture/AGENT_ARCHITECTURE.md)
- [Redis Streams 가이드](../architecture/REDIS_STREAMS.md)
- [API 문서](../api/MONITORING_API.md)

