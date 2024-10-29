import os
import json
import logging
from openai import OpenAI
from app.utils.image_analyzer import analyze_math_image
from db_manager import DBManager
from dotenv import load_dotenv
import re
# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# .env 파일에서 환경 변수 로드
load_dotenv()

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def load_grading_criteria(json_path='grading_criteria.json'):
    """채점 기준을 JSON 파일에서 로드"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            criteria = json.load(f)
        logger.info(f"채점 기준 로드 완료: {len(criteria)}개 문항")
        return criteria
    except Exception as e:
        logger.error(f"채점 기준 로드 실패: {str(e)}")
        return None


def grade_answer_with_gpt(answer_text, criteria):
    """GPT를 사용하여 답안 채점"""
    prompt = (
        f"학생의 답안: {answer_text}\n\n"
        f"채점 기준: {criteria['정답']}\n\n"
        f"유의사항: {', '.join(criteria['유의사항'])}\n\n"
        f"각 세부 채점 기준에 따라 0.5점 단위로 감점하여 점수를 부여하세요. "
        f"다음 JSON 형식으로 정확히 응답해주세요. 응답에는 JSON 형식 외의 다른 텍스트를 포함하지 마세요:\n\n"
        f"{{"
        f"  \"total_score\": 채점된 학생점수,"
        f"  \"feedback\": \"전체 피드백\","
        f"  \"detailed_scores\": ["
        f"    {{"
        f"      \"criteria\": \"채점 기준 항목\","
        f"      \"score\": 채점된 세부점수,"
        f"      \"feedback\": \"해당 항목 피드백\""
        f"    }},"
        f"    ..."
        f"  ]"
        f"}}"
        f"\n\n배점은 {criteria['배점']}점입니다."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system",
                    "content": "수학 교육 전문가로서 JSON으로만 응답하세요. 키는 영어, 값은 한국어로 작성하세요."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )
        gpt_response = response.choices[0].message.content.strip()
        logger.info(f"GPT 채점 결과: {gpt_response}")

        # GPT의 응답을 JSON으로 파싱
        try:
            # 완전한 JSON 객체를 찾기 위한 정규 표현식
            json_match = re.search(r'\{[\s\S]*\}', gpt_response)
            if json_match:
                gpt_result = json.loads(json_match.group())
            else:
                raise ValueError("No valid JSON found in the response")

            total_score = gpt_result.get('total_score', 0)
            feedback = gpt_result.get('feedback', '피드백 없음')
            detailed_scores = gpt_result.get('detailed_scores', [])
        except json.JSONDecodeError:
            logger.error("GPT 응답을 JSON으로 파싱하는 데 실패했습니다.")
            total_score = 0
            feedback = "JSON 파싱 실패"
            detailed_scores = []

        return {
            'total_score': total_score,
            'max_score': criteria['배점'],
            'gpt_feedback': feedback,
            'detailed_scores': detailed_scores
        }
    except Exception as e:
        logger.error(f"GPT 채점 실패: {str(e)}")
        return {
            'total_score': 0,
            'max_score': criteria['배점'],
            'gpt_feedback': "채점 실패",
            'detailed_scores': []
        }


def grade_student_solutions(base_path='image/students', criteria_path='grading_criteria.json', db_manager=None):
    """학생 답안을 채점하고 결과를 저장"""
    criteria = load_grading_criteria(criteria_path)
    if not criteria:
        return {}

    results = {}

    for student_id in os.listdir(base_path):
        student_path = os.path.join(base_path, student_id)
        if not os.path.isdir(student_path):
            continue

        logger.info(f"\n=== 학생 {student_id} 채점 시작 ===")
        student_results = []

        for file_name in os.listdir(student_path):
            if not file_name.endswith('.png'):
                continue

            problem_key = f"문항{file_name.split('.')[0]}"
            image_path = os.path.join(student_path, file_name)

            logger.info(f"{problem_key} 채점 중...")

            # 이미지에서 텍스트 추출
            extracted_text = analyze_math_image(image_path)
            if not extracted_text:
                logger.error(f"텍스트 추출 실패: {image_path}")
                continue

            # 채점 기준 확인 및 채점
            if problem_key in criteria:
                evaluation = grade_answer_with_gpt(
                    extracted_text, criteria[problem_key])
                grading_data = {
                    student_id: [{
                        'problem_key': problem_key,
                        'extracted_text': extracted_text,
                        'evaluation': evaluation,
                        'max_score': criteria[problem_key]['배점']
                    }]
                }

                # DB에 즉시 저장
                if db_manager:
                    try:
                        db_manager.save_grading_results(grading_data)
                        logger.info(f"{problem_key} 채점 결과 DB 저장 완료")
                    except Exception as e:
                        logger.error(f"DB 저장 실패 ({problem_key}): {str(e)}")

                student_results.append(grading_data)
                logger.info(f"{problem_key} 채점 완료")
            else:
                logger.warning(f"{problem_key}의 채점 기준을 찾을 수 없음")

        results[student_id] = student_results

    return results


if __name__ == "__main__":
    # DB 매니저 초기화
    db_manager = DBManager()

    # 채점 실행 (DB 매니저 전달)
    grading_results = grade_student_solutions(db_manager=db_manager)

    # 결과 출력
    for student_id, evaluations in grading_results.items():
        print(f"\n학생 {student_id} 채점 결과:")

        # DB에서 결과 조회
        stored_results = db_manager.get_student_results(student_id)
        total_score = 0
        max_total = 0

        for result in stored_results:
            problem_key = result['problem_key']
            answer_text = result['answer_text']
            gpt_feedback = result['evaluation']['gpt_feedback']
            max_score = result['max_score']
            score = result['total_score']

            print(f"\n[{problem_key}]")
            print(f"학생 답안: {answer_text[:200]}...")
            print(f"배점: {max_score}")
            print(f"획득 점수: {score}")
            print(f"GPT 피드백: {gpt_feedback}")

            total_score += score
            max_total += max_score

        if max_total > 0:
            print(
                f"\n총점: {total_score}/{max_total} ({(total_score/max_total*100):.1f}%)")
