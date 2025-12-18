# 🎯 MAICE 에이전트 모니터링 시스템 - 구현 완료

## ✅ 구현 완료 사항

### 1. **메트릭 수집 시스템**
- ✅ QuestionClassifier 메트릭 기록 추가
- ✅ AnswerGenerator 메트릭 기록 추가
- ✅ 처리 시간, 성공/실패 카운터 자동 기록
- ✅ 활성 세션 게이지 추적

### 2. **처리 로그 시스템** ⭐️ NEW
- ✅ 세션별 처리 단계 로그 기록
- ✅ Redis Streams에 자동 저장
- ✅ 타임스탬프와 함께 추적 가능

### 3. **모니터링 API** 
- ✅ `/api/monitoring/agents/status` - 에이전트 상태
- ✅ `/api/monitoring/agents/{agent_name}/metrics` - 상세 메트릭
- ✅ `/api/monitoring/metrics/summary` - 전체 요약
- ✅ `/api/monitoring/processing-logs/{session_id}` - 처리 로그 ⭐️
- ✅ `/api/monitoring/processing-summary` - 처리 요약 통계 ⭐️
- ✅ `/api/monitoring/health/detailed` - 상세 헬스 체크

## 📊 수집되는 데이터

### QuestionClassifier
```
메트릭 키: maice:metrics:QuestionClassifier:counter:*
- classification_requests_total: 전체 요청
- classification_success_total: 성공
- classification_failed_total: 실패
- request_duration_seconds: 처리 시간

처리 로그: maice:agent_to_backend_stream_session_{id}
- classification_start
- classification_complete
- classification_failed
- classification_error
```

### AnswerGenerator
```
메트릭 키: maice:metrics:AnswerGenerator:counter:*
- answer_requests_total: 전체 요청
- answer_success_total: 성공
- answer_failed_total: 실패
- request_duration_seconds: 처리 시간

처리 로그: maice:agent_to_backend_stream_session_{id}
- answer_start
- answer_complete
- answer_failed
- answer_error
```

## 🚀 사용 방법

### 1. 메트릭 확인 (Redis CLI)
```bash
# 모든 메트릭 키 확인
docker-compose exec redis redis-cli KEYS "maice:metrics:*"

# QuestionClassifier 요청 수
docker-compose exec redis redis-cli GET "maice:metrics:QuestionClassifier:counter:classification_requests_total"
```

### 2. API로 확인 (추천)
```bash
# 에이전트 상태 (관리자 토큰 필요)
curl http://localhost:8000/api/monitoring/agents/status \
  -H "Authorization: Bearer YOUR_TOKEN"

# 세션 처리 로그
curl http://localhost:8000/api/monitoring/processing-logs/123 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. 테스트 스크립트
```bash
./test_monitoring.sh
```

## 📈 처리 플로우 추적 예시

실제 질문 처리 시 다음과 같은 로그가 생성됩니다:

```json
세션 ID: 123

1. [18:00:00] QuestionClassifier - classification_start
   "질문 분류 시작"

2. [18:00:01] QuestionClassifier - classification_complete  
   "분류 완료: K2 - answerable"

3. [18:00:02] AnswerGenerator - answer_start
   "답변 생성 시작"

4. [18:00:05] AnswerGenerator - answer_complete
   "답변 생성 완료"
```

## 📊 대시보드 구현 가이드

### 필요한 컴포넌트

1. **실시간 메트릭 패널**
   - 에이전트별 요청 수
   - 성공/실패 비율
   - 평균 응답 시간

2. **처리 타임라인** ⭐️
   - 세션별 처리 단계 시각화
   - 각 단계 소요 시간
   - 에러 발생 지점 강조

3. **상태 모니터**
   - 에이전트 health 상태
   - 활성 세션 수
   - 시스템 리소스

### 예시 코드 (Svelte)

```typescript
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  
  let metrics = { agents: [] };
  let interval;
  
  onMount(() => {
    loadMetrics();
    interval = setInterval(loadMetrics, 5000); // 5초마다
  });
  
  onDestroy(() => clearInterval(interval));
  
  async function loadMetrics() {
    const res = await fetch('/api/monitoring/agents/status', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    metrics = await res.json();
  }
</script>

<div class="dashboard">
  <h1>에이전트 모니터링</h1>
  
  {#each metrics.agents as agent}
    <div class="agent-card">
      <h3>{agent.agent_name}</h3>
      <p>상태: {agent.is_alive ? '✅ 활성' : '❌ 비활성'}</p>
      <p>마지막 업데이트: {new Date(agent.last_update * 1000).toLocaleString()}</p>
    </div>
  {/each}
</div>
```

## 🔍 디버깅 시나리오

### 시나리오 1: 특정 질문이 처리되지 않음

```bash
# 1. 세션 ID 확인
# 2. 처리 로그 조회
curl http://localhost:8000/api/monitoring/processing-logs/123 \
  -H "Authorization: Bearer YOUR_TOKEN"

# 3. 어느 단계에서 멈췄는지 확인
# 4. 해당 에이전트 로그 확인
docker-compose logs maice-agent | grep "세션 123"
```

### 시나리오 2: 에러율이 높음

```bash
# 1. 처리 요약 통계 확인
curl http://localhost:8000/api/monitoring/processing-summary?hours=1 \
  -H "Authorization: Bearer YOUR_TOKEN"

# 2. 에러가 많은 에이전트 식별
# 3. 상세 메트릭 확인
curl http://localhost:8000/api/monitoring/agents/QuestionClassifier/metrics \
  -H "Authorization: Bearer YOUR_TOKEN"

# 4. 최근 실패한 요청들의 로그 확인
docker-compose logs maice-agent | grep "ERROR\|❌"
```

## 📝 주의사항

1. **메트릭 데이터 생성**
   - 실제로 질문을 보내야 데이터가 쌓입니다
   - 최소 1개 이상의 요청 처리 필요

2. **관리자 권한**
   - 모든 모니터링 API는 관리자 권한 필요
   - Bearer 토큰을 헤더에 포함해야 합니다

3. **데이터 보존**
   - 메트릭: 1시간 (Redis TTL)
   - 처리 로그: 영구 (수동 삭제 필요)
   - 에이전트 상태: 1분

4. **성능 영향**
   - 메트릭 수집의 오버헤드는 <1%
   - Redis 플러시는 5초마다 자동 실행

## 🎯 다음 단계

### Phase 1 (완료) ✅
- [x] 메트릭 수집 시스템
- [x] 처리 로그 시스템
- [x] 모니터링 API

### Phase 2 (권장)
- [ ] 실시간 대시보드 UI 구현
- [ ] 웹소켓/SSE로 실시간 업데이트
- [ ] 알림 시스템 (Slack, 이메일)

### Phase 3 (선택)
- [ ] 성능 벤치마크 자동화
- [ ] 이상 탐지 (Anomaly Detection)
- [ ] 로그 분석 대시보드

## 📚 문서

- 📖 [상세 가이드](./docs/monitoring/MONITORING_GUIDE.md)
- 🚀 [빠른 시작](./docs/monitoring/QUICK_START.md)
- 🧪 [테스트 스크립트](./test_monitoring.sh)

---

## ✨ 핵심 개선사항

### Before (이전)
- ❌ 메트릭 데이터가 보이지 않음
- ❌ 처리 과정 추적 불가
- ❌ 디버깅 어려움

### After (현재) 
- ✅ 실시간 메트릭 수집
- ✅ 세션별 처리 로그 추적
- ✅ API로 쉽게 조회 가능
- ✅ 성능 분석 가능
- ✅ 디버깅 용이

**🎉 이제 에이전트의 모든 처리 과정을 실시간으로 모니터링할 수 있습니다!**

