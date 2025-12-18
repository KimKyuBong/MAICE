# MAICE 테스트 전략

## 📋 개요

MAICE 시스템의 테스트 전략은 단위 테스트, 통합 테스트, E2E 테스트를 포함한 포괄적인 테스트 접근법을 제공합니다.

## 🧪 테스트 피라미드

### 1. 단위 테스트 (70%)
- 개별 함수/메서드 테스트
- 컴포넌트 단위 테스트
- 빠른 실행 속도
- 높은 커버리지

### 2. 통합 테스트 (20%)
- API 엔드포인트 테스트
- 데이터베이스 연동 테스트
- 에이전트 간 통신 테스트
- 중간 실행 속도

### 3. E2E 테스트 (10%)
- 전체 사용자 시나리오 테스트
- 브라우저 자동화 테스트
- 느린 실행 속도
- 핵심 플로우 검증

## 🔧 백엔드 테스트

### 1. API 테스트
```python
# tests/api/test_maice_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_chat_endpoint():
    response = client.post("/api/maice/chat", json={
        "question": "이차함수 그래프 그리기",
        "session_id": 1
    })
    assert response.status_code == 200
    assert "answer" in response.json()

def test_authentication():
    response = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "testpass"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
```

### 2. 서비스 테스트
```python
# tests/services/test_chat_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from app.services.chat_service import ChatService

@pytest.fixture
def mock_agent_service():
    return AsyncMock()

@pytest.fixture
def chat_service(mock_agent_service):
    return ChatService(mock_agent_service)

@pytest.mark.asyncio
async def test_process_question_streaming(chat_service, mock_agent_service):
    # Given
    question = "테스트 질문"
    user_id = 1
    session_id = 1
    
    # When
    await chat_service.process_question_streaming(question, user_id, session_id)
    
    # Then
    mock_agent_service.process_question_streaming.assert_called_once_with(
        question, user_id, session_id
    )
```

### 3. 데이터베이스 테스트
```python
# tests/database/test_models.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import User, Question, Answer

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # 테이블 생성
    Base.metadata.create_all(engine)
    
    yield session
    session.close()

def test_user_creation(db_session):
    user = User(username="testuser", email="test@example.com")
    db_session.add(user)
    db_session.commit()
    
    assert user.id is not None
    assert user.username == "testuser"
```

## 🤖 에이전트 테스트

### 1. 에이전트 단위 테스트
```python
# tests/agents/test_question_classifier.py
import pytest
from unittest.mock import Mock, patch
from agent.agents.question_classifier import QuestionClassifierAgent

@pytest.fixture
def classifier_agent():
    return QuestionClassifierAgent()

@pytest.mark.asyncio
async def test_classify_question(classifier_agent):
    # Given
    question = "이차함수의 정의를 알려주세요"
    
    # When
    with patch('agent.agents.question_classifier.call_llm') as mock_llm:
        mock_llm.return_value = {
            "knowledge_code": "K1",
            "quality": "answerable",
            "missing_fields": [],
            "unit_tags": ["이차함수"],
            "reasoning": "사실적 지식 질문"
        }
        
        result = await classifier_agent.classify_question(question)
    
    # Then
    assert result["knowledge_code"] == "K1"
    assert result["quality"] == "answerable"
```

### 2. 프롬프트 테스트
```python
# tests/agents/test_prompts.py
import pytest
from agent.agents.question_classifier import QuestionClassifierAgent

def test_system_prompt_generation():
    agent = QuestionClassifierAgent()
    prompt = agent._build_system_prompt()
    
    assert "대한민국 고등학교 수학 교육과정" in prompt
    assert "K1" in prompt
    assert "K2" in prompt
    assert "K3" in prompt
    assert "K4" in prompt
```

### 3. Redis 통신 테스트
```python
# tests/agents/test_redis_communication.py
import pytest
import asyncio
from agent.utils.redis_streams_client import RedisStreamsClient

@pytest.fixture
async def redis_client():
    client = RedisStreamsClient()
    await client.initialize()
    yield client
    await client.close()

@pytest.mark.asyncio
async def test_message_sending(redis_client):
    # Given
    message = {"test": "data"}
    stream = "test_stream"
    
    # When
    await redis_client.send_message(stream, message)
    
    # Then
    messages = await redis_client.read_messages(stream, count=1)
    assert len(messages) == 1
    assert messages[0]["test"] == "data"
```

## 🎨 프론트엔드 테스트

### 1. 컴포넌트 테스트
```typescript
// tests/components/Button.test.ts
import { render, fireEvent } from '@testing-library/svelte';
import Button from '$lib/components/common/Button.svelte';

describe('Button', () => {
  test('renders correctly', () => {
    const { getByRole } = render(Button, {
      props: { variant: 'primary' }
    });
    
    const button = getByRole('button');
    expect(button).toBeInTheDocument();
    expect(button).toHaveClass('bg-blue-600');
  });
  
  test('handles click events', () => {
    const { getByRole } = render(Button);
    const button = getByRole('button');
    
    fireEvent.click(button);
    // 이벤트 테스트
  });
});
```

### 2. 스토어 테스트
```typescript
// tests/stores/theme.test.ts
import { get } from 'svelte/store';
import { themeStore, themeActions } from '$lib/stores/theme';

describe('Theme Store', () => {
  test('initializes with default theme', () => {
    const theme = get(themeStore);
    expect(theme.current).toBe('auto');
    expect(theme.isDark).toBe(false);
  });
  
  test('sets theme correctly', () => {
    themeActions.setTheme('dark');
    const theme = get(themeStore);
    expect(theme.current).toBe('dark');
    expect(theme.isDark).toBe(true);
  });
});
```

### 3. API 클라이언트 테스트
```typescript
// tests/api/maice-client.test.ts
import { vi } from 'vitest';
import { MaiceAPIClient } from '$lib/api/maice-client';

describe('MaiceAPIClient', () => {
  test('sends chat request correctly', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ answer: 'test answer' })
    });
    
    global.fetch = mockFetch;
    
    const client = new MaiceAPIClient('test-token');
    const result = await client.chat('test question', 1);
    
    expect(mockFetch).toHaveBeenCalledWith('/api/maice/chat', {
      method: 'POST',
      headers: {
        'Authorization': 'Bearer test-token',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        question: 'test question',
        session_id: 1
      })
    });
  });
});
```

## 🔄 통합 테스트

### 1. API 통합 테스트
```python
# tests/integration/test_api_integration.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_complete_chat_flow():
    # 1. 로그인
    login_response = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "testpass"
    })
    token = login_response.json()["access_token"]
    
    # 2. 채팅 요청
    chat_response = client.post("/api/maice/chat", 
        json={"question": "테스트 질문", "session_id": 1},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert chat_response.status_code == 200
    
    # 3. 세션 조회
    session_response = client.get("/api/maice/sessions/1",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert session_response.status_code == 200
```

### 2. 에이전트 통합 테스트
```python
# tests/integration/test_agent_integration.py
import pytest
import asyncio
from agent.worker import AgentWorker

@pytest.mark.asyncio
async def test_agent_workflow():
    worker = AgentWorker()
    await worker.initialize()
    
    # 질문 분류 테스트
    question = "이차함수 그래프 그리기"
    result = await worker.process_question(question)
    
    assert result["knowledge_code"] in ["K1", "K2", "K3", "K4"]
    assert result["quality"] in ["answerable", "needs_clarify", "unanswerable"]
    
    await worker.cleanup()
```

## 🎭 E2E 테스트

### 1. Playwright 테스트
```typescript
// tests/e2e/chat-flow.spec.ts
import { test, expect } from '@playwright/test';

test.describe('MAICE Chat Flow', () => {
  test('complete chat session', async ({ page }) => {
    // 1. 로그인 페이지 접속
    await page.goto('/');
    
    // 2. 로그인
    await page.fill('[data-testid="username"]', 'testuser');
    await page.fill('[data-testid="password"]', 'testpass');
    await page.click('[data-testid="login-button"]');
    
    // 3. MAICE 페이지로 이동
    await page.waitForURL('/maice');
    
    // 4. 질문 입력
    await page.fill('[data-testid="question-input"]', '이차함수 그래프 그리기');
    await page.click('[data-testid="send-button"]');
    
    // 5. 답변 확인
    await expect(page.locator('[data-testid="message-list"]')).toContainText('이차함수');
    
    // 6. 테마 전환 테스트
    await page.click('[data-testid="theme-toggle"]');
    await expect(page.locator('html')).toHaveClass(/dark/);
  });
});
```

### 2. 사용자 시나리오 테스트
```typescript
// tests/e2e/user-scenarios.spec.ts
import { test, expect } from '@playwright/test';

test.describe('User Scenarios', () => {
  test('student learning session', async ({ page }) => {
    // 학생 로그인
    await page.goto('/');
    await page.fill('[data-testid="username"]', 'student1');
    await page.fill('[data-testid="password"]', 'password123');
    await page.click('[data-testid="login-button"]');
    
    // 수학 질문 시리즈
    const questions = [
      '이차함수란 무엇인가요?',
      '이차함수 그래프를 그리는 방법을 알려주세요',
      '이차함수의 최댓값과 최솟값을 구하는 방법은?'
    ];
    
    for (const question of questions) {
      await page.fill('[data-testid="question-input"]', question);
      await page.click('[data-testid="send-button"]');
      await page.waitForSelector('[data-testid="answer-complete"]');
    }
    
    // 세션 히스토리 확인
    await page.click('[data-testid="session-history"]');
    await expect(page.locator('[data-testid="session-list"]')).toContainText('이차함수');
  });
});
```

## 📊 테스트 커버리지

### 1. 백엔드 커버리지
```bash
# pytest-cov를 사용한 커버리지 측정
pytest --cov=app --cov-report=html --cov-report=term
```

### 2. 프론트엔드 커버리지
```bash
# vitest를 사용한 커버리지 측정
npm run test:coverage
```

### 3. 커버리지 목표
- **단위 테스트**: 90% 이상
- **통합 테스트**: 80% 이상
- **E2E 테스트**: 핵심 플로우 100%

## 🚀 테스트 자동화

### 1. CI/CD 파이프라인
```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  backend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd back
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: |
          cd back
          pytest --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd front
          npm install
      - name: Run tests
        run: |
          cd front
          npm run test
      - name: Run E2E tests
        run: |
          cd front
          npm run test:e2e
```

### 2. 테스트 데이터 관리
```python
# tests/fixtures/test_data.py
import pytest
from app.models import User, Question, Answer

@pytest.fixture
def sample_user():
    return User(
        username="testuser",
        email="test@example.com",
        role="student"
    )

@pytest.fixture
def sample_questions():
    return [
        Question(
            question_text="이차함수란 무엇인가요?",
            knowledge_code="K1",
            quality="answerable"
        ),
        Question(
            question_text="이차함수 그래프 그리기",
            knowledge_code="K3",
            quality="answerable"
        )
    ]
```

## 🔍 테스트 디버깅

### 1. 테스트 실패 분석
```bash
# 상세한 테스트 출력
pytest -v --tb=long

# 특정 테스트만 실행
pytest tests/test_specific.py::test_function

# 실패한 테스트만 재실행
pytest --lf
```

### 2. 로그 확인
```python
# 테스트 중 로그 확인
import logging
logging.basicConfig(level=logging.DEBUG)

def test_with_logging():
    logger = logging.getLogger(__name__)
    logger.info("테스트 시작")
    # 테스트 로직
    logger.info("테스트 완료")
```

### 3. 테스트 환경 설정
```python
# conftest.py
import pytest
import os

@pytest.fixture(scope="session")
def test_environment():
    os.environ["TESTING"] = "true"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["REDIS_URL"] = "redis://localhost:6379/1"
    yield
    os.environ.pop("TESTING", None)
```
