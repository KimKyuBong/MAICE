# CurriculumTermAgent

교과과정 용어 분석 및 검증 에이전트입니다. 한국 고등학교 수학 교과과정에 맞는 적절한 용어를 제안하고, 응답의 용어를 검증합니다.

## 주요 기능

### 1. 질문 분석 및 용어 제안
- 질문에서 핵심 수학 개념 추출
- 교과과정에 맞는 적절한 용어 제안
- 개념 수준 판단 (고등학교 1-3학년)
- 피해야 할 고급/전문 용어 식별

### 2. 용어 검증
- 응답 내용의 수학 용어 검증
- 교과과정에 부적절한 용어 식별
- 적절한 대안 용어 제안
- 자동 텍스트 수정

### 3. RAG 기반 검색
- 교과과정 데이터베이스 검색
- 교과서 내용 검색
- 의미 확장을 통한 관련 개념 검색
- 점수화를 통한 결과 순위 결정

## 설치 및 설정

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 데이터베이스 준비
`tools/rag/unified_corpus.db` 파일이 필요합니다. 이 파일은 교과과정과 교과서 PDF를 처리하여 생성됩니다.

## 사용법

### 1. 독립 실행
```bash
# 대화형 모드
python run_agent.py

# 단일 질문 분석
python run_agent.py "미분과 적분의 기본 정리에 대해 설명해주세요"
```

### 2. Python 코드에서 사용
```python
import asyncio
from agent.agents.curriculum_term.agent import CurriculumTermAgent

async def main():
    agent = CurriculumTermAgent()
    
    # 질문 분석
    result = await agent.analyze_question_and_suggest_terms(
        "수열의 일반항을 구하는 방법을 알려주세요"
    )
    print(result)
    
    # 용어 검증
    verification = await agent.verify_final_response({
        "answer": "도함수를 이용하여 함수의 극값을 구합니다."
    }, "answer")
    print(verification)

asyncio.run(main())
```

### 3. 멀티 에이전트 시스템에서 사용
```python
# 분산형 Redis 이벤트 시스템 사용
# 각 에이전트가 독립적으로 실행되며 Redis 이벤트를 통해 통신
# curriculum 에이전트가 자동으로 포함됩니다
```

## API 참조

### CurriculumTermAgent

#### `analyze_question_and_suggest_terms(question: str, context: str = "") -> Dict[str, Any]`
질문을 분석하여 교과과정에 맞는 용어를 제안합니다.

**반환값:**
```python
{
    "success": bool,
    "suggested_terms": List[str],      # 제안된 용어 목록
    "concept_level": str,              # 적정 개념 수준
    "avoid_terms": List[str],          # 피해야 할 용어 목록
    "analysis": str,                   # 분석 결과 요약
    "recommendations": List[str]       # 권장사항 목록
}
```

#### `verify_final_response(response_data: Dict[str, Any], response_type: str) -> Dict[str, Any]`
응답 내용의 용어를 검증하고 수정 제안을 제공합니다.

**반환값:**
```python
{
    "curriculum_verified": bool,       # 검증 완료 여부
    "term_violations": List[Dict],     # 용어 위반 목록
    "term_suggestions": List[Dict],    # 용어 제안 목록
    "text_corrected": bool,            # 텍스트 수정 여부
    "verification_error": str          # 검증 오류 (있는 경우)
}
```

### CurriculumTermTool

#### `search(query: str, k: int = 5) -> Dict[str, Any]`
교과과정과 교과서를 통합 검색합니다.

**반환값:**
```python
{
    "query": str,                      # 검색 쿼리
    "curriculum_results": List,        # 교과과정 검색 결과
    "textbook_results": List,          # 교과서 검색 결과
    "total": int                       # 총 결과 수
}
```

## 데이터 구조

### 교과과정 청크
- `chunk_type`: achievement_standard, teaching_method
- `title`: 성취기준 제목
- `content`: 성취기준 내용
- `keywords`: 관련 키워드 (JSON)
- `grade_level`: 학년 수준
- `subject`: 과목
- `topic`: 주제

### 교과서 청크
- `chunk_type`: concept_explanation, example_solution, unit_title, subunit_title
- `title`: 청크 제목
- `content`: 청크 내용
- `keywords`: 관련 키워드 (JSON)
- `related_concepts`: 관련 개념 (JSON)

## 설정

### 환경 변수
- `OPENAI_API_KEY`: OpenAI API 키 (선택사항)

### 로깅
로깅 레벨은 `logging.basicConfig()`로 설정할 수 있습니다:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

## 문제 해결

### 1. 데이터베이스 오류
```
데이터베이스를 찾을 수 없습니다.
```
- `tools/rag/unified_corpus.db` 파일이 존재하는지 확인
- 파일 경로가 올바른지 확인

### 2. 검색 결과가 없는 경우
- 검색 쿼리가 너무 구체적일 수 있음
- 더 일반적인 용어로 검색해보기
- 데이터베이스에 해당 내용이 포함되어 있는지 확인

### 3. 용어 검증이 너무 엄격한 경우
- `_verify_single_term` 메서드의 로직을 조정
- 고급 용어 목록을 수정

## 개발자 정보

### 아키텍처
- **Agent**: 이벤트 기반 비동기 처리
- **Tool**: RAG 검색 및 용어 분석
- **Database**: SQLite 기반 통합 코퍼스
- **Search**: 의미 확장 및 점수화 기반 검색

### 확장 방법
1. 새로운 수학 개념 추가: `_concept_relations` 및 `_synonyms` 수정
2. 고급 용어 추가: `_identify_advanced_terms` 수정
3. 검색 로직 개선: `_calculate_relevance_score` 수정

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
