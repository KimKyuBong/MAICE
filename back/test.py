import os
import base64
from groq import Groq

# 키를 여기에 넣어주세요
GROQ_API_KEY="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"

# Groq 클라이언트 초기화
client = Groq(
    api_key=GROQ_API_KEY
)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def chat_with_ai():
    print("AI 챗봇과 대화를 시작합니다. 종료하려면 '끝내기'를 입력하세요.")
    print("'이미지'를 입력하면 자동으로 'image/test.png' 파일을 처리합니다.")
    
    conversation_history = []
    
    while True:
        user_input = input("당신: ")
        if user_input.lower() == '끝내기':
            print("대화를 종료합니다.")
            break
        
        if user_input.lower() == '이미지':
            image_path = "image/test.png"
            try:
                base64_image = encode_image(image_path)
                user_input = f"다음은 'image/test.png' 파일의 base64로 인코딩된 이미지입니다. 이 이미지에 대해 설명해주세요: {base64_image[:100]}... (생략)"
            except Exception as e:
                print(f"이미지 처리 중 오류 발생: {e}")
                continue
        
        conversation_history.append({"role": "user", "content": user_input})
        
        chat_completion = client.chat.completions.create(
            messages=conversation_history,
            model="llama3-8b-8192",
        )
        
        ai_response = chat_completion.choices[0].message.content
        print("AI: ", ai_response)
        
        conversation_history.append({"role": "assistant", "content": ai_response})

if __name__ == "__main__":
    chat_with_ai()