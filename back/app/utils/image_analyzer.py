import base64
import logging
from app.utils.evaluator import client

logger = logging.getLogger(__name__)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_math_image(image_path):
    base64_image = encode_image(image_path)

    prompt = """
    이 이미지는 수학 풀이를 포함하고 있습니다. 다음 작업을 수행해주세요:
    1. 이미지에 있는 모든 수학 식을 LaTeX 형식으로 변환하세요.
    2. 이미지에 있는 모든 한글 텍스트를 그대로 추출하세요.
    3. 추출한 수학 식과 한글 텍스트를 원문형태를 유지하여 하나의 텍스트로 만드세요.
    """

    try:
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
            max_tokens=4000
        )

        extracted_text = response.choices[0].message.content.strip()
        logger.info(f"추출된 텍스트: {extracted_text[:200]}...")  # 처음 200자만 로깅
        return extracted_text

    except Exception as e:
        logger.error(f"이미지 분석 중 오류 발생: {str(e)}")
        return None
