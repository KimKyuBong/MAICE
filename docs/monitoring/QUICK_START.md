# 🚀 모니터링 빠른 시작 가이드

## 1️⃣ 기본 설정 확인

```bash
# 에이전트가 실행 중인지 확인
docker-compose ps maice-agent

# 에이전트 로그에서 메트릭 초기화 확인
docker-compose logs maice-agent | grep "메트릭 수집기 초기화 완료"
```

**예상 출력:**
```
✅ [QuestionClassifier] 메트릭 수집기 초기화 완료
✅ [AnswerGenerator] 메트릭 수집기 초기화 완료
✅ [Observer] 메트릭 수집기 초기화 완료
```

## 2️⃣ 데이터 생성하기

메트릭 데이터를 보려면 먼저 질문을 처리해야 합니다:

1. 프론트엔드에서 질문 입력
2. 또는 API로 직접 요청:

```bash
# 예시: curl로 질문 보내기 (토큰 필요)
curl -X POST http://localhost:8000/api/maice/question \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "미분이란 무엇인가요?",
    "session_id": 1
  }'
```

## 3️⃣ 메트릭 확인하기

### 방법 1: Redis CLI로 직접 확인

```bash
# 메트릭 키 목록
docker-compose exec redis redis-cli KEYS "maice:metrics:*"

# QuestionClassifier 요청 수
docker-compose exec redis redis-cli GET "maice:metrics:QuestionClassifier:counter:classification_requests_total"

# AnswerGenerator 성공 수
docker-compose exec redis redis-cli GET "maice:metrics:AnswerGenerator:counter:answer_success_total"
```

### 방법 2: API로 확인 (추천)

```bash
# 1. 관리자 로그인 (토큰 획득)
# 2. 에이전트 상태 조회
curl -X GET http://localhost:8000/api/monitoring/agents/status \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"

# 3. QuestionClassifier 상세 메트릭
curl -X GET http://localhost:8000/api/monitoring/agents/QuestionClassifier/metrics \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"

# 4. 전체 시스템 요약
curl -X GET http://localhost:8000/api/monitoring/metrics/summary \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

## 4️⃣ 처리 로그 확인하기 ⭐️

특정 세션의 처리 과정을 추적:

```bash
# 세션 ID 123의 처리 로그
curl -X GET http://localhost:8000/api/monitoring/processing-logs/123 \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

**응답 예시:**
```json
{
  "session_id": 123,
  "logs": [
    {
      "agent_name": "QuestionClassifier",
      "stage": "classification_start",
      "message": "질문 분류 시작",
      "timestamp": "2025-11-06T18:00:00+09:00"
    },
    {
      "agent_name": "QuestionClassifier",
      "stage": "classification_complete",
      "message": "분류 완료: K2 - answerable",
      "timestamp": "2025-11-06T18:00:01+09:00"
    },
    {
      "agent_name": "AnswerGenerator",
      "stage": "answer_start",
      "message": "답변 생성 시작",
      "timestamp": "2025-11-06T18:00:02+09:00"
    },
    {
      "agent_name": "AnswerGenerator",
      "stage": "answer_complete",
      "message": "답변 생성 완료",
      "timestamp": "2025-11-06T18:00:05+09:00"
    }
  ],
  "total": 4
}
```

## 5️⃣ 처리 요약 통계 확인 ⭐️

최근 1시간 동안의 처리 통계:

```bash
curl -X GET http://localhost:8000/api/monitoring/processing-summary?hours=1 \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

## 6️⃣ 테스트 스크립트 사용

프로젝트 루트에 제공된 테스트 스크립트를 사용하세요:

```bash
cd /Users/hwansi/Project/MAICESystem
./test_monitoring.sh
```

## 🎨 프론트엔드에서 사용하기

### React/Svelte 컴포넌트 예시

```typescript
import { onMount } from 'svelte';

let agentMetrics = {};
let processingLogs = [];

// 실시간 업데이트 (5초마다)
onMount(() => {
  const interval = setInterval(async () => {
    // 에이전트 상태 조회
    const statusRes = await fetch('/api/monitoring/agents/status', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    agentMetrics = await statusRes.json();
  }, 5000);

  return () => clearInterval(interval);
});

// 세션별 처리 로그 조회
async function loadProcessingLogs(sessionId: number) {
  const res = await fetch(`/api/monitoring/processing-logs/${sessionId}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  processingLogs = await res.json();
}
```

## 🔍 일반적인 문제 해결

### 메트릭이 보이지 않아요

**원인**: 아직 요청이 처리되지 않았습니다.

**해결**:
1. 프론트엔드에서 질문을 보내보세요
2. 15초 정도 기다린 후 다시 확인
3. 에이전트 로그 확인: `docker-compose logs -f maice-agent`

### 처리 로그가 없어요

**원인**: 해당 세션 ID에 대한 요청이 없거나, 세션 ID가 잘못되었습니다.

**해결**:
1. 올바른 세션 ID 사용
2. Redis에서 직접 확인:
```bash
docker-compose exec redis redis-cli KEYS "maice:agent_to_backend_stream_session_*"
```

### API 접근이 안 돼요 (403 Forbidden)

**원인**: 관리자 권한이 필요합니다.

**해결**:
1. 관리자 계정으로 로그인
2. Bearer 토큰을 헤더에 포함
3. 토큰이 만료되었다면 다시 로그인

## 📊 추천 모니터링 대시보드 레이아웃

```
┌─────────────────────────────────────────────┐
│  📊 MAICE 에이전트 모니터링 대시보드         │
├─────────────────────────────────────────────┤
│                                              │
│  📈 전체 통계                                │
│  ┌──────────┬──────────┬──────────┬────────┐│
│  │ 전체요청 │ 평균시간 │  에러율  │ 활성   ││
│  │   150    │  1.5s    │   3.3%   │  세션5 ││
│  └──────────┴──────────┴──────────┴────────┘│
│                                              │
│  🤖 에이전트 상태                            │
│  ┌──────────────────────────────────────┐  │
│  │ ✅ QuestionClassifier   150 req  97% │  │
│  │ ✅ AnswerGenerator      145 req  99% │  │
│  │ ✅ Observer              50 req 100% │  │
│  └──────────────────────────────────────┘  │
│                                              │
│  📝 최근 처리 로그 (세션 123)                │
│  ┌──────────────────────────────────────┐  │
│  │ 18:00:00  QuestionClassifier  시작   │  │
│  │ 18:00:01  QuestionClassifier  완료   │  │
│  │ 18:00:02  AnswerGenerator     시작   │  │
│  │ 18:00:05  AnswerGenerator     완료   │  │
│  └──────────────────────────────────────┘  │
│                                              │
└─────────────────────────────────────────────┘
```

## 🎯 다음 단계

1. ✅ 메트릭 수집 확인
2. ✅ 처리 로그 확인
3. 📊 대시보드 UI 구현
4. 🚨 알림 시스템 추가 (선택)
5. 📈 성능 분석 및 최적화

## 💡 팁

- **주기적 모니터링**: 5초마다 자동 업데이트
- **이상 감지**: 에러율 10% 초과 시 알림
- **성능 최적화**: 평균 응답 시간 추적
- **디버깅**: 처리 로그로 정확한 단계 파악

---

**🎉 이제 에이전트 처리 과정을 실시간으로 모니터링할 수 있습니다!**

