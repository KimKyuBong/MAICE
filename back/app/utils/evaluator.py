import os
import logging
from dotenv import load_dotenv
from openai import OpenAI
import json
import re
import tiktoken

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# .env 파일에서 환경 변수 로드
load_dotenv()

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def truncate_text(text, max_tokens):
    """텍스트를 최대 토큰 수로 자릅니다."""
    encoding = tiktoken.encoding_for_model("gpt-4o")
    tokens = encoding.encode(text)
    return encoding.decode(tokens[:max_tokens])

def num_tokens_from_string(string: str) -> int:
    """문자열의 토큰 수를 계산합니다."""
    encoding = tiktoken.encoding_for_model("gpt-4o")
    return len(encoding.encode(string))

def process_json_content(json_content):
    """JSON 콘텐츠를 처리하고 정제합니다."""
    # 백슬래시를 임시 특수 문자로 치환
    json_content = json_content.replace('\\', '§')
    
    # 줄바꿈 문자 제거 및 연속된 공백 제거
    json_content = re.sub(r'\s+', ' ', json_content.replace('\n', ' '))
    
    return json_content

def evaluate_math_communication(student_answer, relevant_info=None):
    if not student_answer or not isinstance(student_answer, str) or len(student_answer.strip()) == 0:
        return {"error": "유효한 학생 답변이 제공되지 않았습니다."}
    
    prompt = f"""
학생 답변: {student_answer}

위의 학생 답변을 평가하고 다음 기준에 따라 1-5점으로 채점하세요:
1. 수학적 이해도
2. 논리적 설명
3. 용어 정확성
4. 문제 해결 명확성
5. 의사소통 능력

각 항목에 대해:
- 1-5 점수를 부여하세요.
- 학생 답변에서 직접 인용하여 잘한 점과 개선이 필요한 점을 구체적으로 지적하세요.
- 개선이 필요한 경우, 어떻게 개선할 수 있는지 구체적인 방향을 제시하세요.
- 관련된 수학적 개념을 명확히 언급하고, 그 개념이 어떻게 올바르게 적용되어야 하는지 설명하세요.
- 학생의 풀이 과정을 단계별로 분석하고, 각 단계에 대한 피드백을 제공하세요.
- 피드백에 LaTeX 수식을 적극적으로 활용하여 수학적 표현을 정확하게 전달하세요. LaTeX 수식은 반드시 \\( 와 \\) 로 감싸주세요.

반드시 다음 JSON 형식으로 정확히 응답하세요. 응답에는 JSON 형식 외의 다른 텍스트를 포함하지 마세요:

{{
    "mathematical_understanding": {{
        "score": 점수,
        "feedback": "피드백",
        "improvement": "개선 방향",
        "concept_explanation": "관련 수학적 개념 설명"
    }},
    "logical_explanation": {{
        "score": 점수,
        "feedback": "피드백",
        "improvement": "개선 방향",
        "step_analysis": "단계별 분석"
    }},
    "term_accuracy": {{
        "score": 점수,
        "feedback": "피드백",
        "improvement": "개선 방향",
        "correct_usage": "올바른 용어 사용 예시"
    }},
    "problem_solving_clarity": {{
        "score": 점수,
        "feedback": "피드백",
        "improvement": "개선 방향",
        "clear_solution": "명확한 해결 과정 예시"
    }},
    "communication_skills": {{
        "score": 점수,
        "feedback": "피드백",
        "improvement": "개선 방향",
        "effective_communication": "효과적인 의사소통 방법"
    }}
}}
"""
    
    if num_tokens_from_string(prompt) > 4000:
        logger.warning("입력이 너무 깁니다. 관련 정보를 줄여주세요.")
        return {"error": "입력이 너무 깁니다. 관련 정보를 줄여주세요."}
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "수학 교육 전문가로서 JSON으로 응답하세요. 키는 영어, 피드백은 한국어로 작성하세요."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )
         
        response_content = response.choices[0].message.content
        logger.info(f"OpenAI API 응답 내용: {response_content}")
        
        json_match = re.search(r'\{[\s\S]*\}', response_content)
        if not json_match:
            raise ValueError("JSON 형식의 응답을 찾을 수 없습니다.")
        
        json_content = process_json_content(json_match.group())
        evaluation_result = json.loads(json_content)
        return evaluation_result

    except json.JSONDecodeError as e:
        logger.error(f"JSON 디코딩 오류: {str(e)}")
        logger.error(f"문제의 JSON 문자열: {json_content}")
        return {"error": f"평가 결과를 처리하는 중 JSON 디코딩 오류가 발생했습니다: {str(e)}"}
    except ValueError as e:
        logger.error(f"값 오류: {str(e)}")
        return {"error": f"평가 결과 처리 중 값 오류가 발생했습니다: {str(e)}"}
    except Exception as e:
        logger.error(f"예상치 못한 오류 발생: {str(e)}")
        return {"error": f"평가 중 예상치 못한 오류가 발했습니다: {str(e)}"}
