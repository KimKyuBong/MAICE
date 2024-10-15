import base64
from app.utils.evaluator import client

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

    다음 JSON 형식으로 정확히 응답하세요:
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

    # 응답 내용을 문자열로 처리
    response_content = response.choices[0].message.content.strip()
    print(f"응답 내용: {response_content}")  # 응답 내용 출력

    # 문자열에서 필요한 데이터 추출
    # 예를 들어, "extracted_text" 부분만 추출할 수 있습니다.
    if "extracted_text" in response_content:
        start = response_content.index("extracted_text") + len("extracted_text") + 3  # +3 for ': "'
        end = response_content.index('"', start)
        extracted_text = response_content[start:end]
        return {"extracted_text": extracted_text}

    return None  # 필요한 데이터가 없을 경우 None 반환
