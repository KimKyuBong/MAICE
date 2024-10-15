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
    if len(tokens) <= max_tokens:
        return text
    return encoding.decode(tokens[:max_tokens])

def num_tokens_from_string(string: str) -> int:
    """문자열의 토큰 수를 계산합니다."""
    encoding = tiktoken.encoding_for_model("gpt-4o")
    num_tokens = len(encoding.encode(string))
    return num_tokens

def evaluate_math_communication(student_answer, relevant_info=None):
    prompt = f"""
    학생 답변: {student_answer}

    위의 학생 답변을 평가하고 다음 기준에 따라 1-5점으로 채점하세요:
    1. 수학적 이해도
    2. 논리적 설명
    3. 용어 정확성
    4. 문제 해결 명확성
    5. 의사소통 능력

    학생이 풀어야 하는 문제를 인지하고, 학생의 답변이 적절한지를 단계적으로 분석하고 평가해야 합니다.
    각 항목에 대해 1-5 점수를 부여하고, 특히 틀린 부분이 있다면 반드시 지적하고 올바른 내용을 설명해야 합니다.
    피드백에 반드시 latex문법을 지킨 수식이 있어야 합니다.
    학생들이 올바른 풀이를 유도할 수 있도록 설명해주세요.


    다음 JSON 형식으로 정확히 응답하세요:

    {{
        "mathematical_understanding": {{"score": 점수, "feedback": "피드백"}},
        "logical_explanation": {{"score": 점수, "feedback": "피드백"}},
        "term_accuracy": {{"score": 점수, "feedback": "피드백"}},
        "problem_solving_clarity": {{"score": 점수, "feedback": "피드백"}},
        "communication_skills": {{"score": 점수, "feedback": "피드백"}}
    }}
    """
    
    total_tokens = num_tokens_from_string(prompt)
    if total_tokens > 4000:
        logger.warning("입력이 너무 깁니다. 관련 정보를 줄여주세요.")
        return {"error": "입력이 너무 깁니다. 관련 정보를 줄여주세요."}
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "수학 교육 전문가로서 JSON으로 응답하세요. 키는 영어, 피드백은 한국어로 작성하세요."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=1000
        )
        
        response_content = response.choices[0].message.content
        logger.info(f"OpenAI API 응답 내용: {response_content}")
        
        # JSON 문자열 정리
        json_content = re.search(r'\{.*\}', response_content, re.DOTALL)
        if json_content:
            json_content = json_content.group()
            # LaTeX 수식의 백슬래시 이스케이프 처리
            json_content = json_content.replace('\\', '\\\\')  # 백슬래시 이스케이프
        else:
            raise ValueError("JSON 형식의 응답을 찾을 수 없습니다.")
        
        # 불필요한 이스케이프 문자 제거
        json_content = json_content.replace('\\"', '"').replace('\\n', ' ')
        
        evaluation_result = json.loads(json_content)
        return evaluation_result
    except json.JSONDecodeError as e:
        logger.error(f"JSON 디코딩 오류: {str(e)}")
        return {"error": "JSON 형식이 올바르지 않습니다."}
    except ValueError as e:
        logger.error(f"값 오류: {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"예상치 못한 오류 발생: {str(e)}")
        return {"error": f"평가 결과를 처리하는 중 오류가 발생했습니다: {str(e)}"}