import base64
from app.utils.evaluator import client
import re
import json

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_math_image(image_path):
    base64_image = encode_image(image_path)

    prompt = """
    이 이미지는 수학 풀이를 포함하고 있습니다. 다음 작업을 수행해주세요:
    1. 이미지에 있는 모든 수학 식을 LaTeX 형식으로 변환하세요.
    2. 이미지에 있는 모든 한글 텍스트를 그대로 추출하세요.
    3. 추출한 수학 식과 한글 텍스트를 순서대로 나열하여 전체 풀이 과정을 재구성하세요.

    응답 형식:
    {
        "extracted_text": "[여기에 LaTeX 수식과 한글 텍스트를 포함한 전체 내용을 작성]"
    }
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        max_tokens=1500
    )

    # JSON 문자열 정리
    response_content = response.choices[0].message.content.strip()

    # 응답 내용에서 'json' 접두사 제거
    if response_content.startswith("json"):
        response_content = response_content[4:].strip()

    # text{} 부분 제거
    response_content = re.sub(r'\\text\{.*?\}', '', response_content)

    # 이스케이프 문자 처리
    response_content = response_content.replace('\\', '')  # 이스케이프 문자 제거

    # JSON 형식 확인 및 정리
    try:
        extracted_data = json.loads(response_content)
    except json.JSONDecodeError as e:
        print(f"JSON 형식 오류: {e}")
        print(f"응답 내용: {response_content}")
        return None  # JSON 응답이 올바르지 않은 경우 None 반환

    return extracted_data  # JSON 객체 반환
