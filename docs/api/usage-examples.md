# MAICE API 사용 예제

## 📖 개요

MAICE 시스템의 API를 실제로 사용하는 방법을 예제와 함께 설명합니다.

## 🔐 인증 설정

### JWT 토큰 획득
```javascript
// 로그인 API 호출
const loginResponse = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    username: 'student@example.com',
    password: 'password123'
  })
});

const loginData = await loginResponse.json();
const accessToken = loginData.access_token;
```

### Google OAuth 로그인
```javascript
// Google OAuth 로그인
const googleLoginUrl = 'http://localhost:8000/api/v1/auth/google';
window.location.href = googleLoginUrl;
```

## 💬 채팅 API 사용

### 1. 실시간 스트리밍 채팅

#### JavaScript (프론트엔드)
```javascript
async function sendQuestion(question, sessionId) {
  const response = await fetch('http://localhost:8000/api/v1/student/chat/streaming', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      question: question,
      session_id: sessionId,
      message_type: 'question'
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        handleStreamingData(data);
      }
    }
  }
}

function handleStreamingData(data) {
  switch (data.type) {
    case 'chunk':
      // 스트리밍 텍스트 청크 표시
      displayChunk(data.content);
      break;
    case 'complete':
      // 메시지 완료 알림
      console.log('Message completed:', data.message_id);
      break;
    case 'summary':
      // 학습 요약 표시
      displaySummary(data.content);
      break;
    case 'error':
      // 오류 처리
      handleError(data.message);
      break;
  }
}
```

#### Python (백엔드/테스트)
```python
import requests
import json

def send_question_streaming(question, session_id, access_token):
    url = "http://localhost:8000/api/v1/student/chat/streaming"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    data = {
        "question": question,
        "session_id": session_id,
        "message_type": "question"
    }
    
    response = requests.post(url, headers=headers, json=data, stream=True)
    
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = json.loads(line[6:])
                print(f"Type: {data['type']}, Content: {data.get('content', '')}")
```

### 2. 일반 채팅 (비스트리밍)

```javascript
async function sendQuestionNormal(question, sessionId) {
  const response = await fetch('http://localhost:8000/api/v1/student/chat', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      question: question,
      session_id: sessionId
    })
  });

  const data = await response.json();
  return data;
}
```

## 📚 세션 관리

### 1. 세션 목록 조회
```javascript
async function getSessions(page = 1, limit = 20) {
  const response = await fetch(`http://localhost:8000/api/v1/student/sessions?page=${page}&limit=${limit}`, {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    }
  });

  const data = await response.json();
  return data.sessions;
}
```

### 2. 새 세션 생성
```javascript
async function createSession(title) {
  const response = await fetch('http://localhost:8000/api/v1/student/sessions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      title: title
    })
  });

  const data = await response.json();
  return data;
}
```

### 3. 특정 세션 조회
```javascript
async function getSession(sessionId) {
  const response = await fetch(`http://localhost:8000/api/v1/student/sessions/${sessionId}`, {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    }
  });

  const data = await response.json();
  return data;
}
```

## 👤 사용자 관리

### 1. 현재 사용자 정보
```javascript
async function getCurrentUser() {
  const response = await fetch('http://localhost:8000/api/v1/auth/me', {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    }
  });

  const data = await response.json();
  return data;
}
```

### 2. 사용자 학습 통계
```javascript
async function getUserProgress() {
  const response = await fetch('http://localhost:8000/api/v1/student/progress', {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    }
  });

  const data = await response.json();
  return data;
}
```

## 🎓 교사 기능

### 1. 학생 목록 조회
```javascript
async function getStudents(page = 1, limit = 20, search = '') {
  const params = new URLSearchParams({
    page: page,
    limit: limit,
    ...(search && { search: search })
  });

  const response = await fetch(`http://localhost:8000/api/v1/teacher/students?${params}`, {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    }
  });

  const data = await response.json();
  return data.students;
}
```

### 2. 피드백 제공
```javascript
async function provideFeedback(sessionId, studentId, feedback, rating, suggestions) {
  const response = await fetch('http://localhost:8000/api/v1/teacher/feedback', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: sessionId,
      student_id: studentId,
      feedback: feedback,
      rating: rating,
      suggestions: suggestions
    })
  });

  const data = await response.json();
  return data;
}
```

## 🔧 관리자 기능

### 1. 시스템 통계
```javascript
async function getSystemStats() {
  const response = await fetch('http://localhost:8000/api/v1/admin/stats', {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    }
  });

  const data = await response.json();
  return data;
}
```

### 2. 데이터 내보내기
```javascript
async function exportData(format = 'csv', dataType = 'sessions') {
  const response = await fetch(`http://localhost:8000/api/v1/exports/${dataType}?format=${format}`, {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    }
  });

  if (format === 'csv') {
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${dataType}.csv`;
    a.click();
  } else {
    const data = await response.json();
    return data;
  }
}
```

## 📊 설문 응답

### 1. 학생 설문 제출
```javascript
async function submitStudentSurvey(sessionId, responses) {
  const response = await fetch('http://localhost:8000/api/v1/student/survey', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: sessionId,
      responses: responses
    })
  });

  const data = await response.json();
  return data;
}
```

### 2. 교사 평가 제출
```javascript
async function submitTeacherEvaluation(sessionId, studentId, evaluation) {
  const response = await fetch('http://localhost:8000/api/v1/teacher/evaluation', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: sessionId,
      student_id: studentId,
      evaluation: evaluation
    })
  });

  const data = await response.json();
  return data;
}
```

## ⚠️ 오류 처리

### 1. 일반적인 오류 처리
```javascript
async function handleApiCall(apiFunction) {
  try {
    const result = await apiFunction();
    return { success: true, data: result };
  } catch (error) {
    if (error.response) {
      // 서버 응답 오류
      const errorData = error.response.data;
      return {
        success: false,
        error: errorData.error?.message || '서버 오류가 발생했습니다.',
        code: errorData.error?.code || 'UNKNOWN_ERROR'
      };
    } else if (error.request) {
      // 네트워크 오류
      return {
        success: false,
        error: '네트워크 연결을 확인해주세요.',
        code: 'NETWORK_ERROR'
      };
    } else {
      // 기타 오류
      return {
        success: false,
        error: '알 수 없는 오류가 발생했습니다.',
        code: 'UNKNOWN_ERROR'
      };
    }
  }
}
```

### 2. 토큰 갱신 (현재 구현 예정)
```javascript
// 현재는 refresh_token 엔드포인트가 구현되지 않음
// Google OAuth를 통한 자동 토큰 갱신 사용

async function refreshToken() {
  try {
    // 현재 구현: Google OAuth 토큰 자동 갱신
    // Google OAuth 라이브러리가 자동으로 토큰을 갱신함
    
    // 향후 구현 예정: JWT refresh token 엔드포인트
    const response = await fetch('http://localhost:8000/api/v1/auth/refresh', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      }
    });

    if (response.ok) {
      const data = await response.json();
      accessToken = data.access_token;
      return true;
    } else {
      // 토큰 갱신 실패, 로그인 페이지로 리다이렉트
      window.location.href = '/login';
      return false;
    }
  } catch (error) {
    console.error('Token refresh failed:', error);
    window.location.href = '/login';
    return false;
  }
}
```

## 🔗 관련 문서

- [MAICE API](./maice-api.md) - 상세 API 문서
- [인증 API](./authentication.md) - 인증 관련 API
- [스트리밍 API](./streaming-api.md) - 실시간 스트리밍 API
- [시스템 아키텍처](../architecture/overview.md) - 전체 시스템 구조