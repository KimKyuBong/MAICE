# MAICE 시스템 테스터

MAICE 시스템의 다양한 에이전트들을 테스트하기 위한 고급 테스터입니다.

## 📁 프로젝트 구조

```
tester/
├── core/                   # 핵심 테스터 클래스들
│   ├── __init__.py
│   ├── base_tester.py     # 기본 테스터 클래스
│   └── advanced_tester.py # 고급 테스터 클래스
├── personas/               # 학생 페르소나 관련
│   ├── __init__.py
│   ├── student_personas.py # 학생 페르소나 정의
│   └── persona_manager.py  # 페르소나 관리
├── handlers/               # 이벤트 핸들러들
│   ├── __init__.py
│   ├── message_handler.py  # 메시지 처리
│   └── clarification_handler.py # 명료화 처리
├── utils/                  # 유틸리티 함수들
│   ├── __init__.py
│   ├── data_loader.py     # 데이터 로딩
│   └── question_generator.py # 질문 생성
├── main.py                 # 메인 실행 파일
├── .env.example           # 환경 설정 예시
└── README.md              # 이 파일
```

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 환경 설정 파일 복사
cp env_example.txt .env

# 환경 변수 편집
nano .env
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 테스터 실행

```bash
# 기본 실행 (combined 모드, 5개 질문)
python main.py

# 환경 변수로 설정
TEST_MODE=persona NUM_QUESTIONS=10 python main.py
```

## 🎯 테스트 모드

### Combined 모드 (기본)
- 원문 질문 + 페르소나 기반 질문을 모두 테스트
- 가장 포괄적인 테스트

### Original 모드
- 실제 학생 질문 데이터만 테스트
- 데이터셋 기반 테스트

### Persona 모드
- 다양한 학생 페르소나 기반 질문만 테스트
- 페르소나별 동작 검증

## 📊 로깅

테스터는 상세한 로그를 생성합니다:

- **파일 로그**: `advanced_tester.log`
- **콘솔 출력**: 실시간 진행 상황
- **에러 추적**: 상세한 에러 정보

## 🔧 설정 옵션

| 환경 변수 | 기본값 | 설명 |
|-----------|--------|------|
| `TEST_MODE` | `combined` | 테스트 모드 |
| `NUM_QUESTIONS` | `5` | 테스트 질문 수 |
| `REDIS_URL` | `redis://localhost:6379` | Redis 연결 URL |
| `LOG_LEVEL` | `INFO` | 로그 레벨 |

## 📝 사용 예시

### 기본 테스트
```bash
python main.py
```

### 페르소나 전용 테스트
```bash
TEST_MODE=persona python main.py
```

### 많은 질문으로 테스트
```bash
NUM_QUESTIONS=20 python main.py
```

## 🐛 문제 해결

### Redis 연결 오류
```bash
# Redis 서버 상태 확인
redis-cli ping

# Docker로 Redis 실행
docker run -d -p 6379:6379 redis:alpine
```

### OpenAI API 오류
```bash
# API 키 설정 확인
echo $OPENAI_API_KEY

# .env 파일에 API 키 추가
OPENAI_API_KEY=your_actual_api_key
```

## 📈 성능 최적화

- **병렬 처리**: 여러 학생의 질문을 동시에 처리
- **Redis 연결 풀**: 효율적인 Redis 연결 관리
- **비동기 처리**: I/O 대기 시간 최소화

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 있습니다.
