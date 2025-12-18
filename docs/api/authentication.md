# MAICE 인증 API 문서

## 📋 개요

MAICE 시스템의 인증 API는 JWT 토큰 기반의 사용자 인증과 역할 기반 접근 제어(RBAC)를 제공합니다.

## 🔐 인증 엔드포인트

### 1. 사용자 로그인

**POST** `/api/auth/login`

사용자 인증을 수행하고 JWT 토큰을 발급합니다.

#### 요청 본문
```json
{
  "username": "string",
  "password": "string"
}
```

#### 응답 (성공)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": 1,
    "username": "student1",
    "email": "student1@example.com",
    "role": "student"
  }
}
```

#### 응답 (실패)
```json
{
  "detail": "Invalid credentials"
}
```

### 2. 사용자 로그아웃

**POST** `/api/auth/logout`

사용자를 로그아웃하고 토큰을 무효화합니다.

#### 요청 헤더
```
Authorization: Bearer <token>
```

#### 응답
```json
{
  "message": "Successfully logged out"
}
```

### 3. 현재 사용자 정보 조회

**GET** `/api/auth/me`

현재 인증된 사용자의 정보를 조회합니다.

#### 요청 헤더
```
Authorization: Bearer <token>
```

#### 응답
```json
{
  "id": 1,
  "username": "student1",
  "email": "student1@example.com",
  "role": "student",
  "created_at": "2025-01-27T10:00:00Z"
}
```

## 👥 사용자 관리 API

### 1. 사용자 목록 조회 (관리자)

**GET** `/api/users/`

관리자 권한으로 모든 사용자 목록을 조회합니다.

#### 요청 헤더
```
Authorization: Bearer <admin_token>
```

#### 응답
```json
[
  {
    "id": 1,
    "username": "student1",
    "email": "student1@example.com",
    "role": "student",
    "created_at": "2025-01-27T10:00:00Z"
  },
  {
    "id": 2,
    "username": "teacher1",
    "email": "teacher1@example.com",
    "role": "teacher",
    "created_at": "2025-01-27T10:00:00Z"
  }
]
```

### 2. 특정 사용자 조회

**GET** `/api/users/{user_id}`

특정 사용자의 정보를 조회합니다.

#### 요청 헤더
```
Authorization: Bearer <token>
```

#### 응답
```json
{
  "id": 1,
  "username": "student1",
  "email": "student1@example.com",
  "role": "student",
  "created_at": "2025-01-27T10:00:00Z"
}
```

### 3. 사용자 생성 (관리자)

**POST** `/api/users/`

새로운 사용자를 생성합니다.

#### 요청 본문
```json
{
  "username": "newstudent",
  "email": "newstudent@example.com",
  "password": "securepassword",
  "role": "student"
}
```

#### 응답
```json
{
  "id": 3,
  "username": "newstudent",
  "email": "newstudent@example.com",
  "role": "student",
  "created_at": "2025-01-27T10:00:00Z"
}
```

### 4. 사용자 정보 수정

**PUT** `/api/users/{user_id}`

사용자 정보를 수정합니다.

#### 요청 본문
```json
{
  "email": "updated@example.com",
  "role": "teacher"
}
```

#### 응답
```json
{
  "id": 1,
  "username": "student1",
  "email": "updated@example.com",
  "role": "teacher",
  "created_at": "2025-01-27T10:00:00Z"
}
```

## 🔒 권한 및 역할

### 사용자 역할
- **student**: 학생 - MAICE 채팅 시스템 사용
- **teacher**: 교사 - 학생 관리 및 학습 진도 확인
- **admin**: 관리자 - 시스템 전체 관리

### 권한 매트릭스
| 기능 | student | teacher | admin |
|------|---------|---------|-------|
| MAICE 채팅 | ✅ | ✅ | ✅ |
| 세션 조회 | ✅ (본인) | ✅ (모든) | ✅ (모든) |
| 사용자 관리 | ❌ | ❌ | ✅ |
| 시스템 설정 | ❌ | ❌ | ✅ |

## 🛡️ 보안 고려사항

### 1. 토큰 보안
- JWT 토큰 만료 시간: 1시간
- 토큰 갱신 메커니즘
- 로그아웃 시 토큰 무효화

### 2. 비밀번호 보안
- bcrypt 해싱
- 최소 길이 요구사항
- 복잡성 검증

### 3. API 보안
- CORS 설정
- 요청 속도 제한
- 입력 데이터 검증

## 📝 에러 코드

### 인증 관련 에러
- `401 Unauthorized`: 인증 실패
- `403 Forbidden`: 권한 부족
- `422 Unprocessable Entity`: 입력 데이터 오류

### 일반 에러
- `400 Bad Request`: 잘못된 요청
- `404 Not Found`: 리소스 없음
- `500 Internal Server Error`: 서버 오류

## 🔧 개발자 가이드

### 토큰 사용 예시
```javascript
// 로그인
const response = await fetch('/api/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    username: 'student1',
    password: 'password123'
  })
});

const data = await response.json();
const token = data.access_token;

// 인증된 요청
const userResponse = await fetch('/api/auth/me', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

### 토큰 갱신
```javascript
// 토큰 만료 시 자동 갱신
if (response.status === 401) {
  // 로그인 페이지로 리다이렉트
  window.location.href = '/login';
}
```
