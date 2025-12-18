# MAICE 테스트 실행 가이드

## 📋 개요

MAICE 시스템의 테스트 실행 방법과 결과 분석에 대한 상세한 가이드입니다.

## 🚀 테스트 실행 환경 설정

### 1. 개발 환경 설정
```bash
# 프로젝트 루트에서
git clone <repository-url>
cd MAICESystem

# Docker 환경 실행
docker-compose up -d postgres redis

# 백엔드 의존성 설치
cd back
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio

# 프론트엔드 의존성 설치
cd ../front
npm install
npm install -D @playwright/test vitest
```

### 2. 테스트 데이터베이스 설정
```bash
# 테스트용 데이터베이스 생성
createdb maice_test

# 환경변수 설정
export TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/maice_test"
export TEST_REDIS_URL="redis://localhost:6379/1"
```

## 🧪 백엔드 테스트 실행

### 1. 단위 테스트
```bash
# 모든 테스트 실행
cd back
pytest

# 특정 모듈 테스트
pytest tests/api/
pytest tests/services/
pytest tests/models/

# 상세 출력과 함께 실행
pytest -v

# 실패한 테스트만 재실행
pytest --lf
```

### 2. 커버리지 측정
```bash
# 커버리지 리포트 생성
pytest --cov=app --cov-report=html --cov-report=term

# HTML 리포트 확인
open htmlcov/index.html

# 특정 모듈 커버리지
pytest --cov=app.services --cov-report=term
```

### 3. 비동기 테스트
```bash
# 비동기 테스트 실행
pytest -v tests/test_async.py

# 특정 비동기 테스트
pytest tests/test_async.py::test_async_function -v
```

### 4. 에이전트 테스트
```bash
# 에이전트 테스트 실행
cd agent
pytest tests/

# 특정 에이전트 테스트
pytest tests/test_question_classifier.py -v

# Redis 통신 테스트
pytest tests/test_redis_communication.py -v
```

## 🎨 프론트엔드 테스트 실행

### 1. 단위 테스트 (Vitest)
```bash
# 모든 테스트 실행
cd front
npm run test

# 특정 파일 테스트
npm run test Button.test.ts

# 워치 모드로 실행
npm run test:watch

# 커버리지 측정
npm run test:coverage
```

### 2. 컴포넌트 테스트
```bash
# 컴포넌트 테스트 실행
npm run test:components

# 특정 컴포넌트 테스트
npm run test:components Button

# 스토어 테스트
npm run test:stores
```

### 3. E2E 테스트 (Playwright)
```bash
# E2E 테스트 실행
npm run test:e2e

# 특정 브라우저에서 실행
npm run test:e2e -- --project=chromium

# 헤드리스 모드 비활성화
npm run test:e2e -- --headed

# 특정 테스트 실행
npm run test:e2e chat-flow.spec.ts
```

## 🔄 통합 테스트 실행

### 1. API 통합 테스트
```bash
# 전체 시스템 실행
docker-compose up -d

# API 통합 테스트
cd back
pytest tests/integration/ -v

# 특정 API 테스트
pytest tests/integration/test_maice_api.py -v
```

### 2. 에이전트 통합 테스트
```bash
# 에이전트 통합 테스트
cd agent
pytest tests/integration/ -v

# Redis 통신 테스트
pytest tests/integration/test_redis_integration.py -v
```

### 3. 전체 시스템 테스트
```bash
# 전체 시스템 테스트 스크립트
./scripts/run-integration-tests.sh

# 특정 시나리오 테스트
./scripts/test-chat-scenario.sh
```

## 📊 테스트 결과 분석

### 1. 테스트 리포트 생성
```bash
# JUnit XML 리포트 생성
pytest --junitxml=test-results.xml

# HTML 리포트 생성
pytest --html=test-report.html --self-contained-html

# JSON 리포트 생성
pytest --json-report --json-report-file=test-report.json
```

### 2. 커버리지 분석
```bash
# 커버리지 리포트 생성
pytest --cov=app --cov-report=html --cov-report=term --cov-report=xml

# 커버리지 임계값 설정
pytest --cov=app --cov-fail-under=80

# 특정 파일 제외
pytest --cov=app --cov-report=html --cov-omit="*/tests/*"
```

### 3. 성능 테스트
```bash
# 성능 테스트 실행
pytest tests/performance/ -v

# 벤치마크 테스트
pytest tests/benchmark/ --benchmark-only

# 메모리 사용량 측정
pytest tests/memory/ --memray
```

## 🐛 테스트 디버깅

### 1. 실패한 테스트 분석
```bash
# 상세한 실패 정보
pytest -v --tb=long

# 첫 번째 실패에서 중단
pytest -x

# 실패한 테스트만 재실행
pytest --lf

# 특정 테스트 디버깅
pytest tests/test_specific.py::test_function -v -s
```

### 2. 로그 확인
```bash
# 테스트 중 로그 출력
pytest -v -s --log-cli-level=DEBUG

# 특정 로거 레벨 설정
pytest --log-cli-level=INFO --log-cli-format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s"
```

### 3. 브레이크포인트 디버깅
```python
# 테스트 중 브레이크포인트 설정
import pdb; pdb.set_trace()

# 또는 pytest의 내장 디버거 사용
pytest --pdb
```

## 🚀 CI/CD에서 테스트 실행

### 1. Jenkins 파이프라인
```groovy
stage('Test') {
    steps {
        sh 'cd back && pytest --cov=app --cov-report=xml'
        sh 'cd front && npm run test:coverage'
        sh 'cd front && npm run test:e2e'
    }
    post {
        always {
            publishTestResults testResultsPattern: '**/test-results.xml'
            publishCoverage adapters: [
                coberturaAdapter('back/coverage.xml'),
                jacocoAdapter('front/coverage/lcov.info')
            ]
        }
    }
}
```

### 2. GitHub Actions
```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
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
```

## 📈 테스트 메트릭 모니터링

### 1. 테스트 실행 시간 측정
```bash
# 실행 시간 측정
time pytest tests/

# 느린 테스트 찾기
pytest --durations=10

# 프로파일링
pytest --profile
```

### 2. 테스트 품질 메트릭
```bash
# 테스트 복잡도 측정
pytest --cov=app --cov-report=term-missing

# 중복 테스트 찾기
pytest --collect-only | grep -E "test_.*_duplicate"

# 테스트 의존성 분석
pytest --deps
```

### 3. 테스트 안정성 측정
```bash
# 테스트 재실행으로 안정성 확인
for i in {1..10}; do pytest tests/; done

# 플레이키 테스트 안정성
npm run test:e2e -- --repeat-each=5
```

## 🔧 테스트 환경 최적화

### 1. 병렬 테스트 실행
```bash
# pytest-xdist를 사용한 병렬 실행
pip install pytest-xdist
pytest -n auto

# 특정 워커 수로 실행
pytest -n 4
```

### 2. 테스트 캐싱
```bash
# pytest-cache를 사용한 캐싱
pytest --cache-clear
pytest --cache-show
```

### 3. 테스트 데이터 관리
```bash
# 테스트 데이터베이스 초기화
./scripts/reset-test-db.sh

# 테스트 데이터 시드
./scripts/seed-test-data.sh
```

## 📝 테스트 문서화

### 1. 테스트 케이스 문서화
```python
def test_user_login():
    """
    사용자 로그인 테스트
    
    Given: 유효한 사용자 자격증명
    When: 로그인 API 호출
    Then: 성공적인 로그인 및 토큰 반환
    """
    # 테스트 구현
    pass
```

### 2. 테스트 결과 문서화
```bash
# 테스트 결과를 마크다운으로 생성
pytest --html=test-report.html --self-contained-html

# 커버리지 리포트를 README에 포함
pytest --cov=app --cov-report=term --cov-report=html
```

### 3. 테스트 가이드 업데이트
```bash
# 테스트 실행 가이드 업데이트
./scripts/generate-test-docs.sh

# 테스트 결과를 문서에 반영
./scripts/update-test-results.sh
```
