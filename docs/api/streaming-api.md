# MAICE 스트리밍 API 문서

## 📋 개요

MAICE 스트리밍 API는 실시간 채팅과 답변 생성을 위한 Server-Sent Events (SSE) 기반 스트리밍 통신을 제공합니다.

## 🔄 스트리밍 엔드포인트

### 1. MAICE 채팅 스트리밍

**POST** `/api/maice/chat`

MAICE와의 실시간 채팅을 위한 스트리밍 엔드포인트입니다.

#### 요청 헤더
```
Authorization: Bearer <token>
Content-Type: application/json
Accept: text/event-stream
```

#### 요청 본문
```json
{
  "question": "이차함수의 그래프를 그리는 방법을 알려주세요",
  "session_id": 12345,
  "mode": "agent" // "agent" 또는 "freepass"
}
```

#### 스트리밍 응답 형식
```
data: {"type": "classification_start", "session_id": 12345, "timestamp": "2025-01-27T10:00:00Z"}

data: {"type": "classification_complete", "session_id": 12345, "result": {"knowledge_code": "K3", "quality": "answerable"}, "timestamp": "2025-01-27T10:00:01Z"}

data: {"type": "answer_chunk", "session_id": 12345, "chunk_id": 1, "chunk_index": 0, "content": "이차함수 그래프를 그리는 방법을 단계별로 설명해드릴게요!", "timestamp": "2025-01-27T10:00:02Z"}

data: {"type": "answer_chunk", "session_id": 12345, "chunk_id": 2, "chunk_index": 1, "content": "## 📋 **단계별 문제 해결 과정**", "timestamp": "2025-01-27T10:00:03Z"}

data: {"type": "answer_complete", "session_id": 12345, "total_chunks": 15, "timestamp": "2025-01-27T10:00:30Z"}

data: {"type": "summary_complete", "session_id": 12345, "summary": "이차함수 그래프 그리기 학습 완료", "timestamp": "2025-01-27T10:00:31Z"}
```

## 📊 메시지 타입

### 1. 분류 관련 메시지

#### classification_start
```json
{
  "type": "classification_start",
  "session_id": 12345,
  "timestamp": "2025-01-27T10:00:00Z"
}
```

#### classification_complete
```json
{
  "type": "classification_complete",
  "session_id": 12345,
  "result": {
    "knowledge_code": "K3",
    "quality": "answerable",
    "unit_tags": ["이차함수", "그래프"],
    "reasoning": "이차함수 그래프 그리기 방법에 대한 절차적 질문"
  },
  "timestamp": "2025-01-27T10:00:01Z"
}
```

### 2. 명료화 관련 메시지

#### clarification_required
```json
{
  "type": "clarification_required",
  "session_id": 12345,
  "questions": [
    "어떤 종류의 이차함수 그래프를 그리고 싶으신가요? 😊",
    "구체적으로 어떤 부분이 어려우신가요? 💡"
  ],
  "timestamp": "2025-01-27T10:00:01Z"
}
```

#### clarification_complete
```json
{
  "type": "clarification_complete",
  "session_id": 12345,
  "improved_question": "표준형 이차함수 y = ax² + bx + c의 그래프를 그리는 단계별 방법",
  "timestamp": "2025-01-27T10:00:05Z"
}
```

### 3. 답변 관련 메시지

#### answer_chunk
```json
{
  "type": "answer_chunk",
  "session_id": 12345,
  "chunk_id": 1,
  "chunk_index": 0,
  "content": "이차함수 그래프를 그리는 방법을 단계별로 설명해드릴게요!",
  "timestamp": "2025-01-27T10:00:02Z"
}
```

#### answer_complete
```json
{
  "type": "answer_complete",
  "session_id": 12345,
  "total_chunks": 15,
  "answer_type": "K3",
  "timestamp": "2025-01-27T10:00:30Z"
}
```

### 4. 요약 관련 메시지

#### summary_complete
```json
{
  "type": "summary_complete",
  "session_id": 12345,
  "summary": "이차함수 그래프 그리기 학습 완료 - 표준형 변환과 꼭짓점 찾기 방법 학습",
  "timestamp": "2025-01-27T10:00:31Z"
}
```

### 5. 에러 메시지

#### error
```json
{
  "type": "error",
  "session_id": 12345,
  "error_code": "AGENT_TIMEOUT",
  "message": "에이전트 응답 시간 초과",
  "timestamp": "2025-01-27T10:00:30Z"
}
```

## 🔧 프론트엔드 구현

### JavaScript EventSource 사용
```javascript
class MaiceStreamingClient {
  constructor(token) {
    this.token = token;
    this.eventSource = null;
  }

  async startChat(question, sessionId, mode = 'agent') {
    const response = await fetch('/api/maice/chat', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream'
      },
      body: JSON.stringify({
        question,
        session_id: sessionId,
        mode
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    this.eventSource = new EventSource(response.url);
    return this.eventSource;
  }

  handleStreamEvents(eventSource, callbacks) {
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        switch (data.type) {
          case 'classification_start':
            callbacks.onClassificationStart?.(data);
            break;
          case 'classification_complete':
            callbacks.onClassificationComplete?.(data);
            break;
          case 'clarification_required':
            callbacks.onClarificationRequired?.(data);
            break;
          case 'answer_chunk':
            callbacks.onAnswerChunk?.(data);
            break;
          case 'answer_complete':
            callbacks.onAnswerComplete?.(data);
            break;
          case 'summary_complete':
            callbacks.onSummaryComplete?.(data);
            break;
          case 'error':
            callbacks.onError?.(data);
            break;
        }
      } catch (error) {
        console.error('Error parsing stream data:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('Stream error:', error);
      callbacks.onStreamError?.(error);
    };
  }

  close() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}
```

### 청크 순서 정렬 (ChunkBuffer)
```javascript
class ChunkBuffer {
  constructor(timeout = 2000, maxGap = 20) {
    this.buffer = new Map();
    this.timeouts = new Map();
    this.timeout = timeout;
    this.maxGap = maxGap;
  }

  addChunk(chunk) {
    const { chunk_id, chunk_index, content } = chunk;
    
    // 청크 저장
    this.buffer.set(chunk_index, { chunk_id, content });
    
    // 타임아웃 설정
    const timeoutId = setTimeout(() => {
      this.flushPendingChunks();
    }, this.timeout);
    
    this.timeouts.set(chunk_index, timeoutId);
    
    // 연속된 청크 확인
    this.checkForConsecutiveChunks();
  }

  checkForConsecutiveChunks() {
    let index = 0;
    const chunks = [];
    
    while (this.buffer.has(index)) {
      chunks.push(this.buffer.get(index));
      this.buffer.delete(index);
      clearTimeout(this.timeouts.get(index));
      this.timeouts.delete(index);
      index++;
    }
    
    if (chunks.length > 0) {
      return chunks;
    }
    
    return null;
  }

  flushPendingChunks() {
    const chunks = Array.from(this.buffer.values())
      .sort((a, b) => a.chunk_index - b.chunk_index);
    
    this.buffer.clear();
    this.timeouts.forEach(timeoutId => clearTimeout(timeoutId));
    this.timeouts.clear();
    
    return chunks;
  }
}
```

## ⚡ 성능 최적화

### 1. 청크 크기 최적화
- 적절한 청크 크기로 응답 시간과 네트워크 효율성 균형
- 일반적으로 50-200자 단위로 청크 분할

### 2. 타임아웃 관리
- 청크 타임아웃: 2초
- 전체 응답 타임아웃: 30초
- 연결 타임아웃: 60초

### 3. 에러 처리
- 네트워크 오류 시 자동 재연결
- 부분 응답 복구
- 사용자 친화적 에러 메시지

## 🔍 디버깅

### 스트림 디버깅
```javascript
// 스트림 상태 모니터링
const debugStream = (eventSource) => {
  eventSource.addEventListener('open', () => {
    console.log('Stream opened');
  });
  
  eventSource.addEventListener('message', (event) => {
    console.log('Received:', event.data);
  });
  
  eventSource.addEventListener('error', (event) => {
    console.error('Stream error:', event);
  });
};
```

### 로그 확인
```bash
# 백엔드 로그
docker logs maice-back --tail 100 -f

# 에이전트 로그
docker logs maice-agent --tail 100 -f

# Redis 스트림 확인
redis-cli XREAD STREAMS maice:backend_to_agent maice:agent_to_backend 0
```
