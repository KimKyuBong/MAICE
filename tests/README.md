# Tests Directory

이 디렉토리는 MAICE 시스템의 테스트 관련 파일들을 관리합니다.

## 구조

### `scripts/`
테스트 스크립트들이 위치합니다:
- `test_*.py`: 각종 기능 테스트 스크립트
- `parallel_test*.py`: 병렬 처리 테스트 스크립트
- `debug_*.py`: 디버깅용 스크립트
- `check_response_content.py`: 응답 내용 검증 스크립트
- `clarification_test.py`: 명확화 테스트 스크립트

### `results/`
테스트 실행 결과 파일들이 위치합니다:
- `*_results.json`: 각종 테스트 결과 JSON 파일
- `cookies.txt`: 테스트용 쿠키 파일

## 사용법

테스트 스크립트를 실행하려면:
```bash
cd tests/scripts
python test_script_name.py
```

결과 파일은 `results/` 디렉토리에서 확인할 수 있습니다.
