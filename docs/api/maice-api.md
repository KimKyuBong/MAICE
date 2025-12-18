# MAICE API 문서

MAICE 시스템의 핵심 채팅 및 세션 관리 API를 상세히 설명합니다.

## 🔐 인증

모든 API 요청은 JWT 토큰을 통한 인증이 필요합니다.

### 헤더 설정
```http
Authorization: Bearer <your_jwt_token>
Content-Type: application/json
```

### 토큰 갱신
```http
POST /api/v1/auth/refresh
```

## 💬 채팅 API

### 실시간 채팅 스트리밍

**엔드포인트**: `POST /api/v1/maice/chat/streaming`

**설명**: 실시간으로 AI 응답을 스트리밍으로 받는 채팅 API

**요청 본문**:
```json
{
  "question": "이차방정식 x² + 5x + 6 = 0의 해를 구해주세요",
  "session_id": 123,
  "message_type": "question",
  "conversation_history": [
    "이전 대화 내용 1",
    "이전 대화 내용 2"
  ]
}
```

**응답**: Server-Sent Events (SSE) 스트림
```
data: {"type": "chunk", "content": "이차방정식", "chunk_index": 0}

data: {"type": "chunk", "content": " x² + 5x + 6 = 0", "chunk_index": 1}

data: {"type": "complete", "message_id": 456, "session_id": 123}

data: {"type": "summary", "content": "학습 요약 내용..."}
```

**응답 타입**:
- `chunk`: 스트리밍 텍스트 청크
- `complete`: 메시지 완료 알림
- `summary`: 학습 요약
- `error`: 오류 발생

### 일반 채팅 (비스트리밍)

**엔드포인트**: `POST /api/v1/maice/chat`

**요청 본문**:
```json
{
  "question": "삼각함수 sin(π/2)의 값을 구해주세요",
  "session_id": 123
}
```

**응답**:
```json
{
  "message_id": 789,
  "content": "sin(π/2) = 1입니다.",
  "session_id": 123,
  "created_at": "2024-01-15T10:30:00Z",
  "agent_responses": [
    {
      "agent_type": "answer_generator",
      "response_data": {
        "answer": "sin(π/2) = 1",
        "explanation": "단위원에서 각도 π/2는 90도입니다..."
      }
    }
  ]
}
```

## 📚 세션 관리 API

### 세션 목록 조회

**엔드포인트**: `GET /api/v1/maice/sessions`

**쿼리 파라미터**:
- `page`: 페이지 번호 (기본값: 1)
- `limit`: 페이지당 항목 수 (기본값: 20)
- `user_id`: 특정 사용자의 세션만 조회 (관리자만)

**응답**:
```json
{
  "sessions": [
    {
      "id": 123,
      "title": "이차방정식 학습",
      "user_id": 456,
      "created_at": "2024-01-15T09:00:00Z",
      "updated_at": "2024-01-15T10:30:00Z",
      "message_count": 5,
      "last_message": "이차방정식의 해를 구해주세요"
    }
  ],
  "total": 25,
  "page": 1,
  "limit": 20
}
```

### 특정 세션 조회

**엔드포인트**: `GET /api/v1/maice/sessions/{session_id}`

**응답**:
```json
{
  "id": 123,
  "title": "이차방정식 학습",
  "user_id": 456,
  "created_at": "2024-01-15T09:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "learning_summary": {
    "id": 789,
    "summary": "이차방정식의 기본 개념과 해법을 학습했습니다.",
    "difficult_concepts": ["판별식", "근의 공식"],
    "recommended_topics": ["이차함수", "이차부등식"]
  },
  "messages": [
    {
      "id": 101,
      "content": "이차방정식의 해를 구해주세요",
      "type": "question",
      "created_at": "2024-01-15T09:00:00Z"
    },
    {
      "id": 102,
      "content": "이차방정식 x² + 5x + 6 = 0의 해는...",
      "type": "answer",
      "created_at": "2024-01-15T09:01:00Z"
    }
  ]
}
```

### 새 세션 생성

**엔드포인트**: `POST /api/v1/maice/sessions`

**요청 본문**:
```json
{
  "title": "새로운 수학 학습 세션"
}
```

**응답**:
```json
{
  "id": 124,
  "title": "새로운 수학 학습 세션",
  "user_id": 456,
  "created_at": "2024-01-15T11:00:00Z",
  "updated_at": "2024-01-15T11:00:00Z",
  "message_count": 0
}
```

### 세션 정보 수정

**엔드포인트**: `PUT /api/v1/maice/sessions/{session_id}`

**요청 본문**:
```json
{
  "title": "수정된 세션 제목"
}
```

**응답**:
```json
{
  "id": 123,
  "title": "수정된 세션 제목",
  "user_id": 456,
  "created_at": "2024-01-15T09:00:00Z",
  "updated_at": "2024-01-15T11:30:00Z",
  "message_count": 5
}
```

### 세션 삭제

**엔드포인트**: `DELETE /api/v1/maice/sessions/{session_id}`

**응답**:
```json
{
  "message": "세션이 성공적으로 삭제되었습니다.",
  "deleted_session_id": 123
}
```

## 👤 사용자 관련 API

### 현재 사용자 정보

**엔드포인트**: `GET /api/v1/auth/me`

**응답**:
```json
{
  "id": 456,
  "email": "student@example.com",
  "name": "김학생",
  "role": "student",
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-15T10:00:00Z"
}
```

### 사용자 학습 통계

**엔드포인트**: `GET /api/v1/student/progress`

**응답**:
```json
{
  "total_sessions": 15,
  "total_questions": 45,
  "learning_time_minutes": 180,
  "difficult_concepts": [
    {
      "concept": "이차방정식",
      "attempts": 8,
      "success_rate": 0.75
    }
  ],
  "recent_sessions": [
    {
      "session_id": 123,
      "title": "이차방정식 학습",
      "created_at": "2024-01-15T09:00:00Z",
      "message_count": 5
    }
  ]
}
```

## 🎓 교사 전용 API

### 학생 목록 조회

**엔드포인트**: `GET /api/v1/teacher/students`

**쿼리 파라미터**:
- `page`: 페이지 번호
- `limit`: 페이지당 항목 수
- `search`: 학생 이름 검색

**응답**:
```json
{
  "students": [
    {
      "id": 456,
      "name": "김학생",
      "email": "student@example.com",
      "total_sessions": 15,
      "last_activity": "2024-01-15T10:00:00Z",
      "learning_progress": {
        "completed_topics": 8,
        "difficult_areas": ["이차방정식", "삼각함수"]
      }
    }
  ],
  "total": 30,
  "page": 1,
  "limit": 20
}
```

### 학생 세션 모니터링

**엔드포인트**: `GET /api/v1/teacher/sessions`

**쿼리 파라미터**:
- `student_id`: 특정 학생의 세션만 조회
- `date_from`: 시작 날짜
- `date_to`: 종료 날짜

**응답**:
```json
{
  "sessions": [
    {
      "id": 123,
      "student_name": "김학생",
      "title": "이차방정식 학습",
      "created_at": "2024-01-15T09:00:00Z",
      "message_count": 5,
      "learning_summary": "이차방정식의 기본 개념을 이해했습니다.",
      "difficulty_level": "medium"
    }
  ],
  "total": 45,
  "page": 1,
  "limit": 20
}
```

### 피드백 제공

**엔드포인트**: `POST /api/v1/teacher/feedback`

**요청 본문**:
```json
{
  "session_id": 123,
  "student_id": 456,
  "feedback": "이차방정식의 개념을 잘 이해했습니다. 다음 단계로 이차함수를 학습해보세요.",
  "rating": 4,
  "suggestions": ["이차함수", "이차부등식"]
}
```

**응답**:
```json
{
  "feedback_id": 789,
  "message": "피드백이 성공적으로 저장되었습니다."
}
```

## 🔧 관리자 API

### 전체 시스템 통계

**엔드포인트**: `GET /api/v1/admin/stats`

**응답**:
```json
{
  "total_users": 150,
  "active_users_today": 45,
  "total_sessions": 1250,
  "total_questions": 3750,
  "system_health": {
    "database_status": "healthy",
    "redis_status": "healthy",
    "agent_status": "healthy"
  },
  "usage_stats": {
    "questions_per_day": 150,
    "average_session_duration": 12.5,
    "most_popular_topics": ["이차방정식", "삼각함수", "미분"]
  }
}
```

## ⚠️ 오류 처리

### 오류 응답 형식
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "요청 데이터가 유효하지 않습니다.",
    "details": {
      "question": "질문은 필수입니다."
    }
  }
}
```

### 주요 오류 코드
- `UNAUTHORIZED`: 인증 실패
- `FORBIDDEN`: 권한 없음
- `NOT_FOUND`: 리소스 없음
- `VALIDATION_ERROR`: 요청 데이터 오류
- `RATE_LIMIT_EXCEEDED`: 요청 한도 초과
- `INTERNAL_SERVER_ERROR`: 서버 내부 오류

## 📊 요청 제한

### Rate Limiting
- **일반 API**: 분당 60회 요청
- **스트리밍 API**: 분당 10회 요청
- **관리자 API**: 분당 120회 요청

### 요청 크기 제한
- **일반 요청**: 최대 1MB
- **파일 업로드**: 최대 10MB

## 🔗 관련 문서

- [인증 API](./authentication.md) - 상세 인증 가이드
- [스트리밍 API](./streaming-api.md) - 실시간 스트리밍 가이드
- [백엔드 아키텍처](../architecture/backend-architecture.md) - 백엔드 구조 이해
