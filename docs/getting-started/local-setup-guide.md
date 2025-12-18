# 🛠️ MAICE 프로젝트 로컬 개발 환경 구축 가이드

이 가이드는 `macOS` 환경(사용자 환경 기준)을 기준으로 작성되었으나, Windows/Linux에서도 명령어만 일부 수정하여 동일하게 적용 가능합니다.
이 가이드는 **하이브리드 방식(DB/Redis는 Docker, 앱은 로컬 실행)**을 사용하여 개발 속도를 높이고 디버깅을 용이하게 하는 방법을 안내합니다.

## ✅ 0. 필수 요구 사항 (Prerequisites)

시작하기 전에 다음 도구들이 설치되어 있어야 합니다.

1.  **Docker & Docker Compose**: (PostgreSQL, Redis 실행용)
    *   [Docker Desktop 설치](https://www.docker.com/products/docker-desktop/)
2.  **Python 3.11+**: (Backend, Agent 실행용)
3.  **Node.js 18+ & Yarn**: (Frontend 실행용)
    *   `npm install -g yarn`

---

## ⚙️ 1. 환경 변수 및 인프라 설정

가장 먼저 데이터베이스와 메시지 큐(Redis)를 준비합니다.

### 1-1. 저장소 클론 및 이동
```bash
git clone https://github.com/KimKyuBong/MAICE.git
cd MAICE
```

### 1-2. 환경 변수 설정 (.env)
프로젝트 루트의 `.env.example`을 복사하여 `.env`를 생성합니다.

```bash
cp env.example .env
```

**⚠️ 중요: `.env` 파일 필수 수정 항목**
텍스트 에디터로 `.env`를 열어 아래 값들을 채워넣어야 정상 작동합니다.

*   `OPENAI_API_KEY`: `sk-...` (OpenAI 키 필수)
*   `GEMINI_API_KEY`: (선택, 멀티모달 기능 사용 시)
*   `DATABASE_URL`: `postgresql://postgres:postgres@localhost:5432/maice_web` (로컬 Docker 기준)
*   `REDIS_URL`: `redis://localhost:6379` (로컬 Docker 기준)
*   `GOOGLE_CLIENT_ID`: (선택, 소셜 로그인 테스트 시 필요)

### 1-3. 인프라 실행 (PostgreSQL, Redis)
Docker Compose를 사용하여 DB와 Redis만 백그라운드로 실행합니다.

```bash
# 전체 앱을 띄우지 않고 db와 redis만 실행
docker-compose up -d postgres redis
```

---

## 🐍 2. Backend (FastAPI) 설정

백엔드 서버를 설정하고 데이터베이스 스키마를 생성합니다.

### 2-1. 가상환경 구성 및 의존성 설치
```bash
cd back

# 가상환경 생성 (Python 3.11 권장)
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2-2. 데이터베이스 마이그레이션 (초기화)
DB 테이블을 생성합니다.

```bash
# 백엔드 DB 마이그레이션
python migrate.py

# (선택) 관리자 계정 생성 스크립트가 있다면 실행
# python scripts/create_test_users.py
```

### 2-3. 서버 실행
```bash
# 개발 모드 실행 (코드 수정 시 자동 재시작)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
👉 **확인**: 브라우저에서 `http://localhost:8000/docs` 접속 시 Swagger UI가 나오면 성공.

---

## 🖥️ 3. Frontend (SvelteKit) 설정

프론트엔드를 실행하여 UI를 확인합니다. 새 터미널을 열어 진행하세요.

### 3-1. 의존성 설치
```bash
cd front

# 패키지 설치
yarn install
```

### 3-2. 환경 변수 설정 (.env.local)
프론트엔드용 환경 변수를 설정합니다.

```bash
# .env.local 파일 생성
echo "VITE_API_BASE_URL=http://localhost:8000" > .env.local
```

### 3-3. 서버 실행
```bash
yarn dev
```
👉 **확인**: 브라우저에서 `http://localhost:5173` 접속 시 로그인 화면이 나오면 성공.

---

## 🤖 4. AI Agent (Python Worker) 설정

실제 답변을 생성하는 AI 에이전트를 실행합니다. 새 터미널을 열어 진행하세요.

### 4-1. 가상환경 구성 (Backend와 분리 권장)
```bash
cd agent

# 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 4-2. 에이전트 DB 초기화
에이전트가 사용하는 별도의 DB 테이블을 생성합니다.

```bash
python -c "from database.connection import init_db; import asyncio; asyncio.run(init_db())"
```

### 4-3. 에이전트 실행
```bash
python worker.py
```
👉 **확인**: 로그에 `QuestionClassifierAgent initialized`, `Worker started` 등의 메시지가 뜨면 성공.

---

## 🧪 5. 전체 동작 테스트 (재현 확인)

모든 서버가 켜져 있는 상태에서 다음 시나리오를 수행해보세요.

1.  **프론트엔드 접속**: `http://localhost:5173`
2.  **로그인**: (Google 로그인이 설정 안 되었다면, DB에 직접 유저를 넣거나 익명/테스트 로그인 기능 확인 필요)
    *   *Tip*: 개발 중에는 보통 백엔드 인증을 우회하거나 테스트 토큰을 사용합니다. `back/scripts/create_test_users.py`가 있다면 실행하여 테스트 계정을 만드세요.
3.  **채팅 입력**: "미분이란 무엇인가요?" 입력.
4.  **로그 확인**:
    *   **Frontend**: 메시지 전송 로그.
    *   **Backend**: `/api/v1/student/chat` 요청 수신 및 Redis Stream 발행 로그.
    *   **Agent**: Redis Stream 수신 -> 분류(Classifier) -> 답변 생성(Generator) 로그 출력.

---

## 🚑 트러블슈팅 (자주 발생하는 문제)

1.  **DB 연결 오류 (`connection refused`)**:
    *   `docker ps`로 `postgres` 컨테이너가 떠 있는지 확인하세요.
    *   `.env`의 `DATABASE_URL`이 `localhost`로 되어 있는지 확인하세요. (Docker 내부끼리 통신할 때만 서비스명 `postgres`를 사용합니다.)

2.  **Redis 연결 오류**:
    *   `redis-cli ping` 명령어로 PONG이 오는지 확인하세요.
    *   `.env`의 `REDIS_URL`을 확인하세요.

3.  **Frontend API 호출 실패 (CORS)**:
    *   브라우저 콘솔(F12)을 확인하세요.
    *   Backend `main.py`의 `CORSMiddleware` 설정에 `http://localhost:5173`이 허용되어 있는지 확인하세요.

4.  **OpenAI Rate Limit / Key Error**:
    *   Agent 실행 로그에서 401(Auth) 또는 429(Rate Limit) 에러가 뜨면 `.env`의 API Key를 점검하세요.
