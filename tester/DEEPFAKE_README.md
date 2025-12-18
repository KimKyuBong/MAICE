# 🎭 딥페이크식 학생 질문 생성기

실제 학생들이 GPT에 질문한 형태를 분석해서 비슷한 문체와 패턴으로 새로운 질문을 생성하는 시스템입니다.

## 🚀 주요 기능

### 1. 기본 딥페이크 생성기 (`deepfake_question_generator.py`)
- **패턴 분석**: 실제 학생 질문의 문체, 감정, 긴급함 등을 분석
- **스타일 분류**: 존댓말/반말, 이모지 사용, 말줄임표 등 스타일별 분류
- **주제 변환**: 수학 주제별로 키워드를 매핑하여 새로운 질문 생성
- **난이도 조정**: naive부터 olympiad까지 5단계 난이도별 질문 생성

### 2. LLM 기반 딥페이크 생성기 (`llm_deepfake_generator.py`)
- **AI 학습**: OpenAI GPT 모델이 실제 학생 스타일을 학습
- **고품질 생성**: 더 자연스럽고 현실적인 학생 질문 생성
- **스타일 검증**: 생성된 질문의 품질을 자동으로 검증
- **폴백 시스템**: LLM 실패 시 기본 템플릿으로 대체

## 📊 분석 가능한 스타일 특징

### 문체 패턴
- **존댓말/반말**: formal, informal, mixed
- **문장 끝 표현**: question, formal, informal, ellipsis, exclamation

### 감정 상태
- **frustrated**: 답답하고 짜증나는 톤
- **anxious**: 불안하고 긴장된 톤
- **confused**: 헷갈리고 어려워하는 톤
- **excited**: 흥미롭고 궁금해하는 톤
- **desperate**: 급하고 절박한 톤
- **neutral**: 평온하고 차분한 톤

### 수학적 특징
- **어휘 수준**: basic, intermediate, advanced
- **긴급함 수준**: 0-5점 척도
- **불확실함 수준**: 0-5점 척도

## 🎯 지원하는 수학 주제

- **수열**: 등차수열, 등비수열, 일반항, 공차, 공비
- **점화식**: 선형점화식, 지수점화식, 재귀
- **귀납법**: 수학적귀납법, 귀납가정, 귀납단계
- **수열의합**: 등차수열의합, 등비수열의합, 시그마

## 🛠️ 설치 및 설정

### 1. 필요한 패키지 설치
```bash
cd tester
pip install -r requirements.txt
```

### 2. OpenAI API 키 설정 (LLM 생성기 사용 시)
```bash
export OPENAI_API_KEY='your-api-key-here'
```

### 3. 데이터 파일 확인
`data/evaluation_statistics.json` 파일이 있는지 확인하세요.

## 🚀 사용 방법

### 1. 실행 스크립트 사용 (권장)
```bash
cd tester
python run_deepfake_generator.py
```

메뉴에서 선택:
- **1**: LLM 기반 생성기 (OpenAI API 필요)
- **2**: 기본 생성기 (API 불필요)
- **3**: 둘 다 실행

### 2. 직접 실행

#### 기본 생성기
```python
from deepfake_question_generator import DeepfakeQuestionGenerator

generator = DeepfakeQuestionGenerator()

# 단일 질문 생성
question = generator.generate_deepfake_question('수열', difficulty='intermediate')

# 여러 질문 생성
questions = generator.generate_multiple_questions('점화식', count=5, style_variety=True)

# 스타일 분석
style_stats = generator.get_style_statistics()
```

#### LLM 생성기
```python
import asyncio
from llm_deepfake_generator import LLMDeepfakeGenerator

async def main():
    generator = LLMDeepfakeGenerator(openai_api_key='your-key')
    
    # LLM으로 질문 생성
    question = await generator.generate_llm_deepfake_question('수열', difficulty='advanced')
    
    # 여러 질문 생성
    questions = await generator.generate_multiple_llm_questions('귀납법', count=3)

asyncio.run(main())
```

## 📈 생성 예시

### 기본 생성기
```
🎯 주제: 수열
----------------------------------------
naive       : 등차수열의 일반항을 구하는 방법이 뭔가요?
basic       : 등비수열의 공비를 어떻게 구하나요?
intermediate: 수열의 합을 계산하는 공식이 궁금해요
advanced    : 복잡한 수열의 일반항을 구하는 과정이 헷갈려요
olympiad    : 올림피아드 수준의 수열 문제를 풀고 싶어요
```

### LLM 생성기
```
🎯 주제: 점화식
----------------------------------------
naive       : 점화식이 뭔지 잘 모르겠어요... 간단하게 설명해주세요
basic       : 점화식을 푸는 기본 방법을 알려주세요
intermediate: 점화식의 일반항을 구하는 과정에서 막히는 부분이 있어요
advanced    : 복잡한 점화식을 체계적으로 해결하는 방법을 궁금해요
```

## 🔍 스타일 분석 기능

### 질문 스타일 분석
```python
# 특정 질문의 스타일 분석
analysis = generator.analyze_question_style("등차수열이 헷갈려요...")
print(analysis)
# 출력: {'formality': 'informal', 'emotion': 'confused', 'uncertainty_level': 2, ...}

# 유사한 스타일의 질문 찾기
similar_questions = generator.find_similar_style_questions(analysis, count=5)
```

### 통계 정보
```python
# 스타일별 통계
style_stats = generator.get_style_statistics()
# 출력: {'formal': 45, 'informal': 32, 'mixed': 23, ...}

# 주제별 통계
topic_stats = generator.get_topic_statistics()
# 출력: {'수열': 28, '점화식': 15, '귀납법': 12, ...}
```

## ⚙️ 고급 설정

### LLM 모델 변경
```python
generator = LLMDeepfakeGenerator(
    openai_api_key='your-key',
    model='gpt-3.5-turbo'  # 기본값: gpt-4
)
```

### 스타일 가이드 커스터마이징
```python
# 커스텀 스타일 가이드 생성
custom_guide = generator._generate_style_guide({
    'formality': 'informal',
    'emotion': 'desperate',
    'urgency': 5,
    'uncertainty': 3
})
```

## 📝 로그 및 모니터링

- **기본 생성기**: `deepfake_generator.log`
- **LLM 생성기**: `llm_deepfake_generator.log`
- **콘솔 출력**: 실시간 진행 상황 및 결과 표시

## 🚨 주의사항

1. **API 비용**: LLM 생성기는 OpenAI API 사용량에 따라 비용이 발생합니다
2. **데이터 품질**: 실제 학생 질문 데이터의 품질이 생성 결과에 영향을 줍니다
3. **스타일 일치**: 생성된 질문이 원본 스타일과 100% 일치하지 않을 수 있습니다

## 🔧 문제 해결

### 일반적인 오류

1. **데이터 파일을 찾을 수 없음**
   - `data/evaluation_statistics.json` 파일 경로 확인
   - 파일 형식이 올바른지 확인

2. **OpenAI API 오류**
   - API 키가 올바르게 설정되었는지 확인
   - API 할당량 및 비용 한도 확인

3. **패키지 import 오류**
   - `pip install -r requirements.txt` 실행
   - Python 버전 호환성 확인 (3.8+ 권장)

## 📚 추가 자료

- [OpenAI API 문서](https://platform.openai.com/docs)
- [Python asyncio 가이드](https://docs.python.org/3/library/asyncio.html)
- [정규표현식 참고](https://docs.python.org/3/library/re.html)

## 🤝 기여하기

버그 리포트, 기능 제안, 코드 개선 등 모든 기여를 환영합니다!

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
