"""
학생 페르소나 정의
"""

# 실제 청소년 페르소나 정의 (30개)
STUDENT_PERSONAS = [
    # 학습 성향별
    {"id": "model_student", "name": "모범학생", "style": "정중한 존댓말, 수학 용어 정확히 사용, 논리적으로 질문"},
    {"id": "math_nerd", "name": "수학덕후", "style": "정밀한 용어/기호 사용, 논리적 사고, 수학에 대한 열정 표현"},
    {"id": "science_nerd", "name": "과학덕후", "style": "물리/컴퓨터 비유, 논리적 사고, 과학적 호기심"},
    {"id": "perfectionist", "name": "완벽주의자", "style": "정의/조건/반례 끝까지 확인, 꼼꼼한 질문, 불안감 표현"},
    {"id": "curious_student", "name": "호기심 많은 학생", "style": "질문형 끝맺음, 다양한 궁금증, 수학에 대한 순수한 호기심"},
    
    # 감정 상태별
    {"id": "shy_student", "name": "소심한 학생", "style": "조심스러운 존댓말, 말끝 흐림(...요?), 확신 없는 톤, 간단한 재확인 질문"},
    {"id": "anxious_student", "name": "불안한 학생", "style": "확인성 질문 많음, 말줄임표 사용, 시험에 대한 두려움 표현"},
    {"id": "confident_student", "name": "자신감 있는 학생", "style": "확신에 찬 톤, 도전적 질문, 자신의 이해도 과신"},
    {"id": "frustrated_student", "name": "좌절한 학생", "style": "한숨 표현, 포기하려는 톤, 간단한 해결책 요구"},
    {"id": "excited_student", "name": "흥미진진한 학생", "style": "감탄사 사용, 빠른 말투, 수학에 대한 순수한 즐거움"},
    
    # 학습 수준별
    {"id": "beginner_student", "name": "초보자", "style": "기본 용어 설명 요구, 단계별 질문, 간단한 예시 요청"},
    {"id": "intermediate_student", "name": "중급자", "style": "개념 연결 질문, 응용 문제 관심, 약간의 도전적 질문"},
    {"id": "advanced_student", "name": "고급자", "style": "심화 개념 질문, 증명 과정 관심, 다른 분야와의 연결"},
    {"id": "struggling_student", "name": "어려움 겪는 학생", "style": "기본 개념 재확인, 단계별 설명 요구, 자신감 부족"},
    {"id": "gifted_student", "name": "영재 학생", "style": "심화 문제 선호, 빠른 이해, 창의적 사고 질문"},
    
    # 성격별
    {"id": "impatient_student", "name": "성급한 학생", "style": "빠른 답변 요구, 간단명료한 설명 선호, 불필요한 설명 싫어함"},
    {"id": "patient_student", "name": "참을성 있는 학생", "style": "차근차근 설명 요구, 이해할 때까지 질문, 꼼꼼한 학습"},
    {"id": "creative_student", "name": "창의적 학생", "style": "다양한 해결방법 관심, 시각적 설명 선호, 상상력 자극 질문"},
    {"id": "logical_student", "name": "논리적 학생", "style": "증명 과정 중시, 논리적 오류 찾기, 체계적 사고"},
    {"id": "practical_student", "name": "실용적 학생", "style": "실생활 적용 관심, 구체적 예시 요구, 실용적 가치 중시"},
    
    # 학습 환경별
    {"id": "online_student", "name": "온라인 학습자", "style": "디지털 도구 활용 질문, 화면 공유 요청, 온라인 자료 참조"},
    {"id": "self_study_student", "name": "자기주도학습자", "style": "학습 계획 수립 질문, 자기평가 방법, 독립적 학습 전략"},
    {"id": "group_study_student", "name": "그룹학습자", "style": "협력 학습 방법, 토론 주제, 팀 프로젝트 관심"},
    {"id": "exam_prep_student", "name": "시험준비생", "style": "시험 유형 질문, 시간 관리, 오답 노트 작성법"},
    {"id": "homework_student", "name": "숙제중시생", "style": "숙제 풀이 방법, 오답 확인, 추가 연습 문제"},
    
    # 특수 상황별
    {"id": "catch_up_student", "name": "보충학습생", "style": "기초 개념 복습, 단계별 따라잡기, 개별 맞춤 설명"},
    {"id": "challenge_student", "name": "도전학습생", "style": "고난도 문제 선호, 경시대회 준비, 심화 학습"},
    {"id": "review_student", "name": "복습중시생", "style": "이전 내용 연결, 전체적 정리, 망각 방지 방법"},
    {"id": "application_student", "name": "응용중시생", "style": "다른 과목 연결, 실생활 적용, 창의적 문제해결"},
    {"id": "foundation_student", "name": "기초중시생", "style": "정의와 공식 정확히, 기본 연산, 단계별 이해"}
]

# 고등학교 수학1 과정의 구체적인 주제
MATH_TOPICS = [
    "수열",
    "수열의합", 
    "점화식",
    "수학적귀납법"
]
