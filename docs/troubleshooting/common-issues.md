# 일반적인 문제 해결

MAICE 시스템에서 자주 발생하는 문제들과 해결 방법을 정리합니다.

## 🔐 인증 관련 문제

### Google OAuth 로그인 실패

**증상**: Google 로그인 버튼 클릭 시 오류 발생

**원인**:
- Google OAuth 설정 오류
- CORS 설정 문제
- 환경 변수 누락

**해결 방법**:
```bash
# 1. 환경 변수 확인
echo $GOOGLE_CLIENT_ID
echo $GOOGLE_CLIENT_SECRET

# 2. Google Cloud Console 설정 확인
# - 승인된 리디렉션 URI: http://localhost:8000/api/v1/auth/google/callback
# - 승인된 JavaScript 원본: http://localhost:3000

# 3. CORS 설정 확인
# back/app/core/cors.py
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://yourdomain.com"
]
```

### JWT 토큰 만료

**증상**: 로그인 후 일정 시간 후 자동 로그아웃

**원인**:
- 토큰 만료 시간 설정이 짧음
- 토큰 갱신 로직 오류

**해결 방법**:
```python
# back/app/core/config.py
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1시간으로 연장

# 프론트엔드에서 토큰 갱신
async function refreshToken() {
  try {
    const response = await fetch('/api/v1/auth/refresh', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${currentToken}`
      }
    });
    
    if (response.ok) {
      const data = await response.json();
      updateToken(data.access_token);
    }
  } catch (error) {
    console.error('토큰 갱신 실패:', error);
    logout();
  }
}
```

## 💬 채팅 관련 문제

### 실시간 스트리밍 중단

**증상**: 채팅 중 응답이 중간에 끊어짐

**원인**:
- 네트워크 연결 불안정
- Redis Streams 연결 문제
- 에이전트 처리 오류

**해결 방법**:
```bash
# 1. Redis 연결 상태 확인
docker-compose exec redis redis-cli ping

# 2. Redis Streams 상태 확인
docker-compose exec redis redis-cli XINFO STREAMS maice:questions

# 3. 에이전트 로그 확인
docker-compose logs -f agent

# 4. 네트워크 연결 테스트
curl -N http://localhost:8000/api/v1/maice/chat/streaming
```

### 청크 순서 뒤바뀜 문제

**증상**: 스트리밍 응답의 텍스트가 뒤섞여서 표시됨

**원인**: Redis Streams에서 청크가 순서대로 도착하지 않음

**해결 방법**:
```typescript
// front/src/lib/utils/chunk-buffer.ts
export class ChunkBufferManager {
  private buffers: Map<string, ChunkBuffer> = new Map();
  
  addChunk(streamId: string, chunk: SSEMessage): void {
    if (!this.buffers.has(streamId)) {
      this.buffers.set(streamId, new ChunkBuffer());
    }
    
    const buffer = this.buffers.get(streamId)!;
    buffer.addChunk(chunk);
    
    // 순서대로 정렬된 청크 처리
    const orderedChunks = buffer.getOrderedChunks();
    this.processOrderedChunks(streamId, orderedChunks);
  }
}
```

## 🗄️ 데이터베이스 관련 문제

### 연결 실패

**증상**: 데이터베이스 연결 오류 메시지

**원인**:
- PostgreSQL 서비스 중단
- 연결 정보 오류
- 네트워크 문제

**해결 방법**:
```bash
# 1. PostgreSQL 서비스 상태 확인
docker-compose ps postgres

# 2. 연결 테스트
docker-compose exec postgres pg_isready -U maice_user

# 3. 데이터베이스 재시작
docker-compose restart postgres

# 4. 연결 정보 확인
docker-compose exec back python -c "
import os
print('DATABASE_URL:', os.getenv('DATABASE_URL'))
"
```

### 마이그레이션 실패

**증상**: 데이터베이스 스키마 업데이트 실패

**원인**:
- 마이그레이션 파일 충돌
- 데이터베이스 락
- 스키마 불일치

**해결 방법**:
```bash
# 1. 마이그레이션 상태 확인
docker-compose exec back alembic current

# 2. 마이그레이션 히스토리 확인
docker-compose exec back alembic history

# 3. 특정 마이그레이션으로 롤백
docker-compose exec back alembic downgrade <revision_id>

# 4. 마이그레이션 재실행
docker-compose exec back alembic upgrade head

# 5. 충돌 해결
docker-compose exec back alembic merge -m "merge conflict resolution"
```

## 🧠 AI 에이전트 관련 문제

### 에이전트 응답 없음

**증상**: 질문을 보냈지만 AI 응답이 없음

**원인**:
- 에이전트 서비스 중단
- Redis 통신 문제
- OpenAI API 오류

**해결 방법**:
```bash
# 1. 에이전트 서비스 상태 확인
docker-compose ps agent

# 2. 에이전트 로그 확인
docker-compose logs -f agent

# 3. Redis 연결 확인
docker-compose exec redis redis-cli ping

# 4. OpenAI API 키 확인
docker-compose exec agent python -c "
import os
print('OpenAI API Key:', 'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET')
"

# 5. 에이전트 재시작
docker-compose restart agent
```

### 질문 분류 오류

**증상**: 질문이 잘못된 카테고리로 분류됨

**원인**:
- 분류 모델 성능 문제
- 질문 형식 문제
- 학습 데이터 부족

**해결 방법**:
```python
# agent/agents/question_classifier/prompt.py
# 프롬프트 개선
QUESTION_CLASSIFICATION_PROMPT = """
다음 질문을 분석하여 적절한 카테고리로 분류해주세요:

질문: {question}

분류 기준:
1. 수학 주제 (대수, 기하, 미적분 등)
2. 질문 유형 (개념 질문, 문제 해결, 증명 등)
3. 난이도 (기초, 중급, 고급)
4. 답변 가능성 (answerable, needs_clarify, out_of_scope)

분류 결과를 JSON 형태로 반환해주세요.
"""
```

## 🎨 프론트엔드 관련 문제

### MathLive 수식 입력 오류

**증상**: 수식 입력이 작동하지 않음

**원인**:
- MathLive 라이브러리 로드 실패
- 브라우저 호환성 문제
- JavaScript 오류

**해결 방법**:
```typescript
// front/src/lib/components/maice/InlineMathInput.svelte
onMount(async () => {
  try {
    // MathLive 라이브러리 동적 로드
    const { MathField } = await import('mathlive');
    
    if (!MathField) {
      throw new Error('MathLive 라이브러리를 로드할 수 없습니다');
    }
    
    // MathField 초기화
    mathField = new MathField(container, {
      virtualKeyboardMode: 'manual',
      smartFence: true,
      smartSuperscript: true
    });
    
  } catch (error) {
    console.error('MathLive 초기화 실패:', error);
    // 폴백: 일반 텍스트 입력으로 전환
    showFallbackInput = true;
  }
});
```

### 테마 전환 문제

**증상**: 라이트/다크 테마가 제대로 전환되지 않음

**원인**:
- CSS 변수 설정 오류
- 로컬 스토리지 문제
- 컴포넌트 상태 동기화 문제

**해결 방법**:
```typescript
// front/src/lib/stores/theme.ts
class ThemeStore {
  setTheme(theme: 'light' | 'dark' | 'auto'): void {
    this.state.update(current => {
      const newState = { ...current, current: theme };
      
      // 로컬 스토리지에 저장
      localStorage.setItem('maice_theme', theme);
      
      // DOM에 테마 클래스 적용
      document.documentElement.setAttribute('data-theme', theme);
      
      // 시스템 테마 감지 (auto 모드)
      if (theme === 'auto') {
        const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', systemTheme);
        newState.isDark = systemTheme === 'dark';
      } else {
        newState.isDark = theme === 'dark';
      }
      
      return newState;
    });
  }
}
```

## 🚀 성능 관련 문제

### 느린 응답 속도

**증상**: 채팅 응답이 매우 느림

**원인**:
- 서버 리소스 부족
- 데이터베이스 쿼리 최적화 부족
- 네트워크 지연

**해결 방법**:
```bash
# 1. 서버 리소스 확인
docker stats

# 2. 데이터베이스 쿼리 최적화
docker-compose exec postgres psql -U maice_user -d maice_db -c "
EXPLAIN ANALYZE SELECT * FROM messages WHERE session_id = 123;
"

# 3. 인덱스 추가
docker-compose exec postgres psql -U maice_user -d maice_db -c "
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
"

# 4. Redis 캐싱 활용
# back/app/services/cache_service.py
async def get_cached_sessions(user_id: int) -> List[Session]:
    cache_key = f"sessions:user:{user_id}"
    cached = await redis_client.get(cache_key)
    
    if cached:
        return json.loads(cached)
    
    sessions = await session_repository.get_user_sessions(user_id)
    await redis_client.setex(cache_key, 300, json.dumps(sessions))  # 5분 캐시
    
    return sessions
```

### 메모리 사용량 증가

**증상**: 서버 메모리 사용량이 계속 증가

**원인**:
- 메모리 누수
- 캐시 크기 증가
- 연결 풀 문제

**해결 방법**:
```python
# back/app/core/database.py
# 연결 풀 설정 최적화
engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,           # 기본값: 5
    max_overflow=20,        # 기본값: 10
    pool_pre_ping=True,     # 연결 상태 확인
    pool_recycle=3600       # 1시간마다 연결 재생성
)

# 메모리 사용량 모니터링
import psutil
import logging

def log_memory_usage():
    memory = psutil.virtual_memory()
    logging.info(f"메모리 사용량: {memory.percent}% ({memory.used / 1024**3:.2f}GB / {memory.total / 1024**3:.2f}GB)")
```

## 🔧 개발 환경 문제

### Hot Reload 작동 안함

**증상**: 코드 변경 시 자동 재시작이 안됨

**원인**:
- 파일 감시 설정 문제
- 볼륨 마운트 오류
- 권한 문제

**해결 방법**:
```yaml
# docker-compose.dev.yml
services:
  back:
    volumes:
      - ./back:/app
      - /app/__pycache__  # 캐시 제외
    environment:
      - PYTHONUNBUFFERED=1
    command: uvicorn main:app --reload --host 0.0.0.0 --port 8000

  front:
    volumes:
      - ./front:/app
      - /app/node_modules  # node_modules 제외
    environment:
      - CHOKIDAR_USEPOLLING=true  # 파일 감시 개선
```

### 포트 충돌

**증상**: 포트가 이미 사용 중이라는 오류

**원인**:
- 다른 서비스가 같은 포트 사용
- 이전 컨테이너가 완전히 종료되지 않음

**해결 방법**:
```bash
# 1. 사용 중인 포트 확인
netstat -tulpn | grep :3000
netstat -tulpn | grep :8000

# 2. 프로세스 종료
sudo kill -9 <PID>

# 3. Docker 컨테이너 완전 정리
docker-compose down --volumes --remove-orphans
docker system prune -a

# 4. 다른 포트 사용
# docker-compose.yml에서 포트 변경
ports:
  - "3001:3000"  # 프론트엔드
  - "8001:8000"  # 백엔드
```

## 📊 모니터링 및 디버깅

### 로그 분석 도구

```bash
# 실시간 로그 모니터링
docker-compose logs -f | grep ERROR

# 특정 시간대 로그 확인
docker-compose logs --since="2024-01-15T10:00:00" --until="2024-01-15T11:00:00"

# 로그 파일로 저장
docker-compose logs > system.log 2>&1

# 구조화된 로그 분석
docker-compose logs | jq '.message, .level, .timestamp'
```

### 성능 모니터링

```bash
# 시스템 리소스 모니터링
htop
iotop
nethogs

# Docker 컨테이너 리소스 사용량
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

# 데이터베이스 성능 모니터링
docker-compose exec postgres psql -U maice_user -d maice_db -c "
SELECT * FROM pg_stat_activity WHERE state = 'active';
"
```

## 🔗 관련 문서

- [Docker 설정 가이드](../deployment/docker-setup.md) - Docker 관련 문제 해결
- [디버깅 가이드](./debugging-guide.md) - 상세 디버깅 방법
- [시스템 아키텍처](../architecture/overview.md) - 전체 시스템 이해
