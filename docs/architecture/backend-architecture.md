# 백엔드 아키텍처

MAICE 시스템의 FastAPI 기반 백엔드 아키텍처를 상세히 설명합니다.

## 🏗️ 전체 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                        Backend (FastAPI)                       │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   API Layer     │  Service Layer  │      Data Layer            │
│   (Controllers) │ (Business Logic)│    (Repositories)           │
├─────────────────┼─────────────────┼─────────────────────────────┤
│ • /api/v1/auth/ │ • MaiceService  │ • UserRepository           │
│ • /api/v1/users/│ • ChatService   │ • SessionRepository        │
│ • /api/v1/maice/│ • AuthService   │ • MessageRepository        │
│ • /api/v1/student/│ • StreamingProcessor│ • AgentResponseRepository│
│ • /api/v1/teacher/│ • SessionManager │ • LearningSummaryRepository│
└─────────────────┴─────────────────┴─────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │    External Services  │
                    ├─────────────────────────┤
                    │ • PostgreSQL Database  │
                    │ • Redis (Streams/PubSub)│
                    │ • AI Agent System      │
                    │ • Google OAuth          │
                    └─────────────────────────┘
```

## 🔌 API 레이어 (Controllers)

### 인증 API (`/api/v1/auth/`)
```python
# 주요 엔드포인트
POST /auth/login          # Google OAuth 로그인
POST /auth/refresh        # 토큰 갱신
POST /auth/logout         # 로그아웃
GET  /auth/me            # 현재 사용자 정보
```

### 사용자 관리 API (`/api/v1/users/`)
```python
# 주요 엔드포인트
GET    /users/           # 사용자 목록 (관리자)
GET    /users/{user_id}  # 특정 사용자 정보
PUT    /users/{user_id}  # 사용자 정보 수정
DELETE /users/{user_id}  # 사용자 삭제 (관리자)
```

### MAICE 핵심 API (`/api/v1/maice/`)
```python
# 주요 엔드포인트
POST /maice/chat/streaming    # 실시간 채팅 스트리밍
GET  /maice/sessions/         # 대화 세션 목록
GET  /maice/sessions/{id}      # 특정 세션 상세
POST /maice/sessions/         # 새 세션 생성
PUT  /maice/sessions/{id}     # 세션 정보 수정
```

### 학생 인터페이스 API (`/api/v1/student/`)
```python
# 주요 엔드포인트
GET  /student/dashboard       # 학생 대시보드
POST /student/questions/      # 질문 제출
GET  /student/progress/       # 학습 진도 확인
```

### 교사 인터페이스 API (`/api/v1/teacher/`)
```python
# 주요 엔드포인트
GET  /teacher/dashboard       # 교사 대시보드
GET  /teacher/students/       # 학생 목록 관리
GET  /teacher/sessions/       # 학생 세션 모니터링
POST /teacher/feedback/       # 피드백 제공
```

## 🧩 서비스 레이어 (Business Logic)

### MaiceService (통합 서비스)
```python
class MaiceService:
    """MAICE 통합 서비스 - 전체 비즈니스 로직 조정"""
    
    async def process_chat_streaming(
        self,
        question: str,
        user_id: int,
        session_id: Optional[int] = None,
        message_type: str = "question",
        conversation_history: Optional[List[str]] = None
    ) -> AsyncGenerator[str, None]:
        """실시간 채팅 스트리밍 처리"""
```

### ChatService (대화 조정자)
```python
class ChatService(IChatService):
    """대화 세션 조정 서비스"""
    
    async def start_new_session(self, user_id: int) -> SessionResponse:
        """새 대화 세션 시작"""
    
    async def get_session_history(self, session_id: int) -> List[MessageResponse]:
        """세션 히스토리 조회"""
    
    async def update_session(self, session_id: int, data: SessionUpdateRequest) -> SessionResponse:
        """세션 정보 업데이트"""
```

### AIAgentService (AI 에이전트 통신)
```python
class AIAgentService:
    """AI 에이전트와의 통신 서비스"""
    
    async def send_question_to_agent(
        self, 
        question: str, 
        session_id: int, 
        user_id: int
    ) -> AsyncGenerator[str, None]:
        """에이전트에 질문 전송 및 스트리밍 응답 수신"""
    
    async def process_agent_response(
        self, 
        response_data: Dict[str, Any]
    ) -> None:
        """에이전트 응답 처리 및 저장"""
```

### SessionManager (세션 관리)
```python
class SessionManager:
    """세션 라이프사이클 관리"""
    
    async def create_session(self, user_id: int, title: str = None) -> Session:
        """새 세션 생성"""
    
    async def get_active_session(self, user_id: int) -> Optional[Session]:
        """활성 세션 조회"""
    
    async def update_session_summary(self, session_id: int, summary: str) -> None:
        """세션 요약 업데이트"""
```

## 💾 데이터 레이어 (Repositories)

### UserRepository
```python
class UserRepository:
    """사용자 데이터 접근"""
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """ID로 사용자 조회"""
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """이메일로 사용자 조회"""
    
    async def create(self, user_data: UserCreateRequest) -> User:
        """새 사용자 생성"""
```

### SessionRepository
```python
class SessionRepository:
    """대화 세션 데이터 접근"""
    
    async def get_by_id(self, session_id: int) -> Optional[Session]:
        """ID로 세션 조회"""
    
    async def get_user_sessions(self, user_id: int) -> List[Session]:
        """사용자의 모든 세션 조회"""
    
    async def create(self, session_data: SessionCreateRequest) -> Session:
        """새 세션 생성"""
```

### MessageRepository
```python
class MessageRepository:
    """메시지 데이터 접근"""
    
    async def get_session_messages(self, session_id: int) -> List[Message]:
        """세션의 모든 메시지 조회"""
    
    async def create(self, message_data: MessageCreateRequest) -> Message:
        """새 메시지 생성"""
    
    async def update(self, message_id: int, data: MessageUpdateRequest) -> Message:
        """메시지 업데이트"""
```

## 🔄 비동기 처리 아키텍처

### FastAPI 비동기 지원
```python
# 비동기 엔드포인트 예시
@router.post("/chat/streaming")
async def chat_streaming(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
) -> StreamingResponse:
    """실시간 채팅 스트리밍"""
    
    async def generate_response():
        async for chunk in maice_service.process_chat_streaming(
            question=request.question,
            user_id=current_user.id,
            session_id=request.session_id
        ):
            yield f"data: {json.dumps(chunk)}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache"}
    )
```

### Redis Streams 통합
```python
class RedisAgentClient:
    """Redis Streams를 통한 에이전트 통신"""
    
    async def send_question(self, question_data: Dict[str, Any]) -> str:
        """질문을 에이전트에 전송"""
    
    async def read_responses(self, stream_name: str) -> AsyncGenerator[Dict[str, Any], None]:
        """에이전트 응답 스트림 읽기"""
```

## 🛡️ 보안 아키텍처

### JWT 인증
```python
class AuthService:
    """인증 서비스"""
    
    def create_access_token(self, user_data: Dict[str, Any]) -> str:
        """액세스 토큰 생성"""
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """토큰 검증"""
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """사용자 인증"""
```

### 권한 관리
```python
# 의존성 주입을 통한 권한 검사
def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """현재 사용자 조회"""
    
def require_role(required_role: str):
    """역할 기반 접근 제어"""
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role:
            raise HTTPException(status_code=403, detail="권한이 없습니다")
        return current_user
    return role_checker
```

## 📊 모니터링 및 로깅

### 구조화된 로깅
```python
import structlog

logger = structlog.get_logger()

# 로그 예시
logger.info(
    "chat_request_received",
    user_id=user.id,
    session_id=session_id,
    question_length=len(question)
)
```

### 성능 모니터링
```python
# 응답 시간 측정
@router.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

## 🔧 설정 관리

### 환경별 설정
```python
# config.py
class Settings(BaseSettings):
    # 데이터베이스 설정
    database_url: str
    redis_url: str
    
    # JWT 설정
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    
    # Google OAuth 설정
    google_client_id: str
    google_client_secret: str
    
    class Config:
        env_file = ".env"

settings = Settings()
```

## 🚀 확장성 고려사항

### 마이크로서비스 분리 가능성
- **인증 서비스**: 독립적인 인증 마이크로서비스
- **채팅 서비스**: 핵심 채팅 로직 분리
- **분석 서비스**: 학습 데이터 분석 전용 서비스

### 캐싱 전략
```python
# Redis 캐싱 예시
@cache(expire=300)  # 5분 캐시
async def get_user_sessions(user_id: int) -> List[Session]:
    """사용자 세션 목록 캐싱"""
```

## 🔗 관련 문서

- [시스템 개요](./overview.md) - 전체 시스템 구조
- [에이전트 시스템](./agent-system.md) - AI 에이전트 아키텍처
- [데이터 플로우](./data-flow.md) - 시스템 내 데이터 흐름
- [API 문서](../api/maice-api.md) - 상세 API 문서
