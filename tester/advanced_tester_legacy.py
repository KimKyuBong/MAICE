#!/usr/bin/env python3
"""
고급 테스터 에이전트 - simple_test.py 로직 기반으로 명료화 과정 포함
학생 페르소나로 다양한 수준과 방법으로 질문하고 명료화 과정도 수행
"""

import asyncio
import json
import logging
import os
import random
import httpx
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv
import redis.asyncio as redis
import time

# .env 파일 로드
load_dotenv()

# OpenAI 클라이언트
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("openai를 사용할 수 없습니다. 'pip install openai'를 실행하세요.")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('advanced_tester.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Redis 채널 상수 (event_bus.py와 일치)
USER_QUESTION = "user.question"
CLARIFICATION_REQUESTED = "clarification.requested"
CLARIFICATION_QUESTION = "clarification.question"
USER_CLARIFICATION = "user.clarification"
CLARIFICATION_COMPLETED = "clarification.completed"
ANSWER_REQUESTED = "answer.requested"
ANSWER_COMPLETED = "answer.completed"

# ObserverAgent 이벤트 채널
STUDENT_STATUS_UPDATED = "student.status_updated"
SESSION_TITLE_UPDATED = "session.title_updated"
CONVERSATION_SUMMARY_UPDATED = "conversation.summary_updated"

# 실제 학생 질문 데이터 로드 함수
def load_questions_from_dataset(path: str, max_items: int = 2000) -> List[str]:
    """데이터셋에서 실제 학생 질문들을 로드"""
    questions: List[str] = []
    if not path or not os.path.exists(path):
        return questions
    try:
        with open(path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                if idx >= max_items:
                    break
                try:
                    obj = json.loads(line)
                    if not isinstance(obj, dict):
                        continue
                    # 다양한 키에서 질문 텍스트 추출
                    for key in ("question", "query", "utterance", "student_question", "content", "text"):
                        val = obj.get(key)
                        if isinstance(val, str) and 5 <= len(val) <= 500:
                            questions.append(val.strip())
                            break
                except Exception:
                    continue
    except Exception:
        pass
    return questions

# 고등학교 수학1 과정의 구체적인 주제
MATH_TOPICS = [
    "수열",
    "수열의합", 
    "점화식",
    "수학적귀납법"
]

# 실제 청소년 페르소나 정의 (30개)
PERSONAS = [
    # 학습 성향별
    {"id": "model_student", "name": "모범학생", "style": "정중한 존댓말, 수학 용어 정확히 사용, 논리적으로 질문"},
    {"id": "math_nerd", "name": "수학덕후", "style": "정밀한 용어/기호 사용, 논리적 사고, 수학에 대한 열정 표현"},
    {"id": "science_nerd", "name": "과학덕후", "style": "물리/컴퓨터 비유, 논리적 사고, 과학적 호기심"},
    {"id": "perfectionist", "name": "완벽주의자", "style": "정의/조건/반례 끝까지 확인, 꼼꼼한 질문, 불안감 표현"},
    {"id": "curious_student", "name": "호기심 많은 학생", "style": "질문형 끝맺음, 다양한 궁금증, 수학에 대한 순수한 호기심"},
    
    # 감정 상태별
    {"id": "shy_student", "name": "소심한 학생", "style": "조심스러운 존댓말, 말끝 흐림(...요?), 확신 없는 톤, 간단한 재확인 질문"},
    {"id": "anxious_student", "name": "불안한 학생", "style": "확인성 질문 많음, 말줄임표 사용, 시험에 대한 두려움 표현"},
    {"id": "stressed_student", "name": "스트레스 받는 학생", "style": "짜증나는 톤, 반말, 수학에 대한 스트레스, 짧고 직설적 표현"},
    {"id": "math_phobic", "name": "수학 포기자", "style": "자기비하, 수학에 대한 두려움, 쉬운 표현 선호, 반말/존댓말 혼용"},
    {"id": "depressed_student", "name": "우울한 학생", "style": "부정적 표현, 자기비하, 수학에 대한 절망감, 짧고 무기력한 톤"},
    {"id": "angry_student", "name": "화난 학생", "style": "공격적 표현, 반말, 수학에 대한 분노, 직설적이고 거친 톤"},
    {"id": "frustrated_student", "name": "좌절한 학생", "style": "답답함 표현, 반말, 수학에 대한 실망, 짧고 절망적인 톤"},
    
    # 성격별
    {"id": "free_spirited", "name": "자유분방한 학생", "style": "반말 위주, 구어체, 짧게 끊어 말함, 이모지 사용"},
    {"id": "gamer_student", "name": "게임덕후", "style": "게임/레벨 비유, 반존대 혼용, 게임 용어 자연스럽게 사용"},
    {"id": "contrarian", "name": "딴지거는 학생", "style": "반문/반례로 시작, 날카로운 논점 확인, 공격적 표현도 사용"},
    {"id": "lazy_student", "name": "게으른 학생", "style": "짧은 질문, 반말, 수학에 대한 무관심, 간단한 표현"},
    {"id": "overconfident", "name": "과신하는 학생", "style": "자신만만한 톤, 반말, 수학에 대한 과도한 자신감, 도전적 질문"},
    {"id": "social_student", "name": "사교적인 학생", "style": "친근한 톤, 이모지 사용, 수학을 재미있게 접근, 반존대 혼용"},
    {"id": "rebellious_student", "name": "반항적인 학생", "style": "권위에 대한 반감, 반말, 수학에 대한 거부감, 도전적 톤"},
    {"id": "sarcastic_student", "name": "비꼬는 학생", "style": "반어적 표현, 반말, 수학에 대한 조롱, 날카로운 유머"},
    {"id": "cynical_student", "name": "냉소적인 학생", "style": "부정적 시각, 반말, 수학에 대한 회의, 냉담한 톤"},
    
    # 학습 수준별
    {"id": "struggling_student", "name": "어려워하는 학생", "style": "기본 개념도 어려워함, 존댓말, 수학에 대한 두려움, 간단한 표현"},
    {"id": "slow_learner", "name": "천천히 배우는 학생", "style": "단계별로 확인, 존댓말, 수학에 대한 신중함, 꼼꼼한 질문"},
    {"id": "average_student", "name": "보통 학생", "style": "일반적인 질문, 반존대 혼용, 수학에 대한 보통 수준의 이해"},
    {"id": "fast_learner", "name": "빨리 배우는 학생", "style": "고급 개념 질문, 반말, 수학에 대한 자신감, 도전적 질문"},
    {"id": "gifted_student", "name": "영재 학생", "style": "심화 내용 질문, 반말, 수학에 대한 열정, 창의적 사고"},
    
    # 특수 상황별
    {"id": "exam_stressed", "name": "시험 스트레스 학생", "style": "시험에 대한 불안, 존댓말, 수학에 대한 압박감, 긴장된 톤"},
    {"id": "homework_burden", "name": "숙제 부담 학생", "style": "숙제에 대한 스트레스, 반말, 수학에 대한 피로감, 짧은 질문"},
    {"id": "peer_pressure", "name": "또래 압박 학생", "style": "또래와 비교, 반말, 수학에 대한 열등감, 경쟁적 톤"},
    {"id": "teacher_fear", "name": "선생님 두려움 학생", "style": "선생님에 대한 두려움, 존댓말, 수학에 대한 긴장, 조심스러운 톤"}
]

# 수준별 가중치
LEVEL_WEIGHTS = {
    "naive": 0.15,
    "basic": 0.25,
    "intermediate": 0.30,
    "advanced": 0.20,
    "olympiad": 0.10
}

class RealDataQuestionGenerator:
    """실제 학생 데이터를 활용한 질문 및 답변 생성기"""
    
    def __init__(self):
        self.real_questions = self.load_real_questions()
        self.real_answers = self.load_real_answers()
        self.topic_questions = self.categorize_by_topic()
        self.topic_answers = self.categorize_answers_by_topic()
    
    def load_real_questions(self) -> List[str]:
        """실제 학생 질문 데이터 로드"""
        try:
            # 여러 경로 시도
            possible_paths = [
                'data/evaluation_statistics.json',
                'tester/data/evaluation_statistics.json',
                '../data/evaluation_statistics.json'
            ]
            
            data = None
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    print(f"✅ 데이터 파일 로드 성공: {path}")
                    break
            
            if not data:
                print("❌ 데이터 파일을 찾을 수 없습니다")
                return []
            
            questions = []
            # 질문별_교사_평가에서 질문 추출
            if '질문별_교사_평가' in data:
                for question_id, question_data in data['질문별_교사_평가'].items():
                    if isinstance(question_data, dict) and '질문_원문' in question_data:
                        questions.append(question_data['질문_원문'])
            
            print(f"로드된 실제 질문 수: {len(questions)}")
            return questions
        except Exception as e:
            print(f"실제 데이터 로드 실패: {e}")
            return []
    
    def load_real_answers(self) -> List[str]:
        """실제 학생 답변 데이터 로드"""
        try:
            # 여러 경로 시도
            possible_paths = [
                'data/evaluation_statistics.json',
                'tester/data/evaluation_statistics.json',
                '../data/evaluation_statistics.json'
            ]
            
            data = None
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    print(f"✅ 답변 데이터 파일 로드 성공: {path}")
                    break
            
            if not data:
                print("❌ 답변 데이터 파일을 찾을 수 없습니다")
                return []
            
            answers = []
            # 질문별_교사_평가에서 답변 추출
            if '질문별_교사_평가' in data:
                for question_id, question_data in data['질문별_교사_평가'].items():
                    if isinstance(question_data, dict) and '답변_원문' in question_data:
                        answers.append(question_data['답변_원문'])
            
            print(f"로드된 실제 답변 수: {len(answers)}")
            return answers
        except Exception as e:
            print(f"실제 답변 데이터 로드 실패: {e}")
            return []
    
    def categorize_by_topic(self) -> Dict[str, List[str]]:
        """주제별로 질문 분류"""
        topics = {
            "수열": [],
            "수열의합": [], 
            "점화식": [],
            "수학적귀납법": []
        }
        
        for question in self.real_questions:
            if "수열" in question and ("합" in question or "시그마" in question):
                topics["수열의합"].append(question)
            elif "수열" in question:
                topics["수열"].append(question)
            elif "점화" in question:
                topics["점화식"].append(question)
            elif "귀납" in question:
                topics["수학적귀납법"].append(question)
        
        # 각 주제별 질문 수 출력
        for topic, questions in topics.items():
            print(f"{topic}: {len(questions)}개 질문")
        
        return topics
    
    def categorize_answers_by_topic(self) -> Dict[str, List[str]]:
        """주제별로 답변 분류 (고등학교 수학1 범위만)"""
        topics = {
            "수열": [],
            "수열의합": [], 
            "점화식": [],
            "수학적귀납법": []
        }
        
        # 고등학교 수학1 범위에 맞는 키워드 정의
        high_school_keywords = {
            "수열": ["등차수열", "등비수열", "일반항", "수열의 정의", "수열의 성질"],
            "수열의합": ["시그마", "합", "등차수열의 합", "등비수열의 합", "수열의 합"],
            "점화식": ["점화식", "재귀식", "an+1", "an-1", "일반항 구하기"],
            "수학적귀납법": ["수학적 귀납법", "귀납법", "n=1일 때", "n=k일 때", "증명"]
        }
        
        # 고등학교 범위를 벗어나는 고급 수학 키워드
        advanced_keywords = [
            "파도반", "피보나치", "행렬", "선형대수", "조합론", "위상수학",
            "미분방정식", "적분", "복소수", "군론", "환론", "체론",
            "해석학", "대수학", "기하학", "확률론", "통계학"
        ]
        
        try:
            possible_paths = [
                'data/evaluation_statistics.json',
                'tester/data/evaluation_statistics.json',
                '../data/evaluation_statistics.json'
            ]
            
            data = None
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    break
            
            if data and '질문별_교사_평가' in data:
                for question_id, question_data in data['질문별_교사_평가'].items():
                    if isinstance(question_data, dict) and '질문_원문' in question_data and '답변_원문' in question_data:
                        question = question_data['질문_원문']
                        answer = question_data['답변_원문']
                        
                        # 고등학교 범위 체크
                        if self.is_high_school_level(question, answer, advanced_keywords):
                            # 주제 분류
                            if "수열" in question and ("합" in question or "시그마" in question):
                                topics["수열의합"].append(answer)
                            elif "수열" in question:
                                topics["수열"].append(answer)
                            elif "점화" in question:
                                topics["점화식"].append(answer)
                            elif "귀납" in question:
                                topics["수학적귀납법"].append(answer)
            
            # 각 주제별 답변 수 출력
            for topic, answers in topics.items():
                print(f"{topic} 답변: {len(answers)}개 (고등학교 수학1 범위)")
            
        except Exception as e:
            print(f"답변 주제별 분류 실패: {e}")
        
        return topics
    
    def is_high_school_level(self, question: str, answer: str, advanced_keywords: List[str]) -> bool:
        """고등학교 수학1 범위에 맞는지 확인"""
        # 고급 수학 키워드가 포함되어 있으면 제외
        for keyword in advanced_keywords:
            if keyword in question or keyword in answer:
                return False
        
        # 질문과 답변이 너무 복잡하거나 고급 내용이면 제외
        if len(answer) > 1000:  # 너무 긴 답변은 제외
            return False
        
        # LaTeX 수식이 너무 복잡하면 제외 (고등학교 수준을 벗어남)
        if answer.count('\\') > 20:  # 너무 많은 LaTeX 명령어
            return False
        
        return True
    
    def get_answer_for_clarification(self, topic: str, persona: Dict) -> str:
        """실제 학생 답변을 기반으로 명료화 답변 생성"""
        if topic in self.topic_answers and self.topic_answers[topic]:
            # 실제 답변에서 랜덤 선택
            base_answer = random.choice(self.topic_answers[topic])
            
            # 답변을 간단하게 요약 (2문장 이내)
            simplified_answer = self.simplify_answer(base_answer)
            
            # 페르소나에 맞게 변형
            return self.apply_persona_to_answer(simplified_answer, persona)
        else:
            # 실제 답변이 없으면 기본 답변 생성
            return self.generate_default_answer(topic, persona)
    
    def simplify_answer(self, answer: str) -> str:
        """답변을 간단하게 요약 (2문장 이내, 고등학교 수준)"""
        # LaTeX 수식 제거하고 텍스트만 추출
        import re
        
        # 고등학교 수준에 맞는 수식만 유지 (등차, 등비, 일반항 등)
        high_school_formulas = [
            r'a_n = a_1 + \(n-1\)d',  # 등차수열
            r'a_n = a_1 \cdot r^{n-1}',  # 등비수열
            r'S_n = \frac{n\(a_1 + a_n\)}{2}',  # 등차수열의 합
            r'S_n = a_1 \cdot \frac{1-r^n}{1-r}',  # 등비수열의 합
            r'\sum_{k=1}^{n}',  # 시그마
            r'n \geq 1',  # 자연수 조건
        ]
        
        # 고등학교 수준 수식은 유지하고 나머지는 제거
        text_only = answer
        for formula in high_school_formulas:
            text_only = re.sub(formula, '', text_only)
        
        # 나머지 LaTeX 명령어 제거
        text_only = re.sub(r'\\[a-zA-Z]+{[^}]*}', '', text_only)
        text_only = re.sub(r'[\\[\]{}^_]', '', text_only)
        
        # 문장으로 분리
        sentences = text_only.split('.')
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # 2문장 이내로 제한
        if len(sentences) >= 2:
            return '. '.join(sentences[:2]) + '.'
        else:
            return '. '.join(sentences) + '.'
    
    def apply_persona_to_answer(self, answer: str, persona: Dict) -> str:
        """페르소나에 맞게 답변 변형"""
        if persona['name'] == '수학포기자':
            return f"아... {answer} 이거 너무 어려워요"
        elif persona['name'] == '게임덕후':
            return f"게임하면서 {answer} 이거 생각났는데요"
        elif persona['name'] == '과신하는학생':
            return f"{answer} 이거 쉽죠? 제가 한번 풀어볼게요"
        elif persona['name'] == '수학덕후':
            return f"{answer} 이거 정말 흥미롭네요!"
        elif persona['name'] == '평범한학생':
            return f"{answer} 이거 어떻게 푸는 건가요?"
        elif persona['name'] == '게으른학생':
            return f"아 {answer} 이거... 귀찮아서 그냥 답만 알려줘"
        elif persona['name'] == '수학회피자':
            return f"어... {answer} 이거 꼭 알아야 하나요?"
        elif persona['name'] == '호기심많은학생':
            return f"와! {answer} 이거 정말 궁금했어요!"
        elif persona['name'] == '완벽주의자':
            return f"{answer} 이거 정확하게 이해하고 싶어요"
        elif persona['name'] == '소심한학생':
            return f"혹시... {answer} 이거 물어봐도 될까요?"
        elif persona['name'] == '자유분방한학생':
            return f"야! {answer} 이거 알려줘!"
        elif persona['name'] == '사교적인학생':
            return f"안녕하세요! {answer} 이거 궁금한데 설명해주실 수 있나요?"
        elif persona['name'] == '모범학생':
            return f"{answer} 이거 제대로 이해하고 싶습니다"
        elif persona['name'] == '스트레스 받는 학생':
            return f"아... {answer} 이거 너무 스트레스 받아요"
        elif persona['name'] == '딴지거는 학생':
            return f"근데 {answer} 이거 왜 그래야 하는 거야?"
        elif persona['name'] == '과학덕후':
            return f"과학적으로 {answer} 이거 분석해보고 싶어요"
        elif persona['name'] == '불안한 학생':
            return f"혹시 {answer} 이거 틀렸을 수도 있어요..."
        else:
            return answer
    
    def generate_default_answer(self, topic: str, persona: Dict) -> str:
        """기본 답변 생성 (고등학교 수학1 범위)"""
        default_answers = {
            "수열": "등차수열이나 등비수열의 일반항을 구하는 방법을 모르겠어요",
            "수열의합": "등차수열이나 등비수열의 합을 구하는 공식을 모르겠어요",
            "점화식": "an+1 = an + d 같은 간단한 점화식을 푸는 방법을 모르겠어요",
            "수학적귀납법": "1+2+...+n = n(n+1)/2 같은 식을 수학적 귀납법으로 증명하는 방법을 모르겠어요"
        }
        
        base_answer = default_answers.get(topic, "이 문제를 푸는 방법을 모르겠어요")
        return self.apply_persona_to_answer(base_answer, persona)
    
    def get_question(self, topic: str, persona: Dict) -> Optional[str]:
        """실제 데이터에서 질문 선택 후 페르소나 적용 및 유사 질문 생성"""
        if topic in self.topic_questions and self.topic_questions[topic]:
            # 실제 데이터에서 랜덤 선택
            base_question = random.choice(self.topic_questions[topic])
            
            # 50% 확률로 원본 질문 사용, 50% 확률로 유사 질문 생성
            if random.random() < 0.5:
                final_question = base_question
            else:
                final_question = self.generate_similar_question(base_question, topic)
            
            return self.apply_persona(final_question, persona)
        return None
    
    def apply_persona(self, question: str, persona: Dict) -> str:
        """페르소나에 맞게 질문 변형"""
        if persona['name'] == '수학포기자':
            return f"아 {question} 이거 너무 어려워요..."
        elif persona['name'] == '게임덕후':
            return f"게임하면서 {question} 이거 생각났는데요"
        elif persona['name'] == '과신하는학생':
            return f"{question} 이거 쉽죠? 제가 한번 풀어볼게요"
        elif persona['name'] == '수학덕후':
            return f"{question} 이거 정말 흥미롭네요! 자세히 설명해주세요"
        elif persona['name'] == '평범한학생':
            return f"{question} 이거 어떻게 푸는 건가요?"
        elif persona['name'] == '게으른학생':
            return f"아 {question} 이거... 귀찮아서 그냥 답만 알려줘"
        elif persona['name'] == '수학회피자':
            return f"어... {question} 이거 꼭 알아야 하나요?"
        elif persona['name'] == '호기심많은학생':
            return f"와! {question} 이거 정말 궁금했어요!"
        elif persona['name'] == '완벽주의자':
            return f"{question} 이거 정확하게 이해하고 싶어요"
        elif persona['name'] == '소심한학생':
            return f"혹시... {question} 이거 물어봐도 될까요?"
        elif persona['name'] == '자유분방한학생':
            return f"야! {question} 이거 알려줘!"
        elif persona['name'] == '사교적인학생':
            return f"안녕하세요! {question} 이거 궁금한데 설명해주실 수 있나요?"
        elif persona['name'] == '모범학생':
            return f"{question} 이거 제대로 이해하고 싶습니다"
        else:
            return question
    
    def generate_similar_question(self, base_question: str, topic: str) -> str:
        """실제 데이터를 기반으로 유사한 질문 생성"""
        # 기본 질문에서 핵심 키워드 추출
        keywords = self.extract_keywords(base_question, topic)
        
        # 유사한 패턴의 질문 생성
        if "수열" in topic:
            if "합" in base_question or "시그마" in base_question:
                return f"수열의 합을 구하는 방법을 알려주세요"
            else:
                return f"수열의 일반항을 구하는 방법을 알려주세요"
        elif "점화식" in topic:
            return f"점화식을 이용해서 일반항을 구하는 방법을 알려주세요"
        elif "수학적귀납법" in topic:
            return f"수학적 귀납법을 이용한 증명 방법을 알려주세요"
        else:
            return base_question
    
    def extract_keywords(self, question: str, topic: str) -> List[str]:
        """질문에서 핵심 키워드 추출"""
        keywords = []
        if "증명" in question:
            keywords.append("증명")
        if "구하" in question:
            keywords.append("계산")
        if "설명" in question:
            keywords.append("설명")
        if "차이" in question:
            keywords.append("비교")
        if "정의" in question:
            keywords.append("정의")
        return keywords

class TesterAgent:
    """고급 테스터 에이전트 - 실제 데이터 + LLM 하이브리드 방식"""
    
    def __init__(self):
        self.redis_client = None
        self.pubsub = None
        self.llm_client = openai.AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.real_data_generator = RealDataQuestionGenerator()
        
        # 수학 주제 (고등학교 수학1 과정)
        self.MATH_TOPICS = ["수열", "수열의합", "점화식", "수학적귀납법"]
        
        # 학생 페르소나 (더 다양하고 현실적으로)
        self.PERSONAS = [
            {"name": "수학덕후", "style": "수학에 대한 깊은 호기심과 열정을 가진 학생"},
            {"name": "평범한학생", "style": "수학을 그냥 그런 과목으로 생각하는 일반적인 학생"},
            {"name": "수학포기자", "style": "수학에 대한 두려움과 포기를 느끼는 학생"},
            {"name": "게임덕후", "style": "게임에만 관심이 많고 수학은 귀찮아하는 학생"},
            {"name": "과신하는학생", "style": "자신의 수학 실력을 과대평가하는 학생"},
            {"name": "게으른학생", "style": "수학 공부를 귀찮아하고 최소한의 노력만 하는 학생"},
            {"name": "수학회피자", "style": "수학을 피하고 싶어하는 학생"},
            {"name": "호기심많은학생", "style": "수학에 대한 순수한 호기심을 가진 학생"}
        ]

class TestSession:
    """테스트 세션 관리 클래스 - 세션 일관성 보장"""
    
    def __init__(self, session_id: int):
        self.session_id = session_id
        self.questions = []
        self.responses = []
        self.clarification_history = []
        self.current_status = "active"
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
    
    def add_question(self, question: str, topic: str = None):
        """세션에 질문 추가"""
        question_data = {
            "id": len(self.questions) + 1,
            "text": question,
            "topic": topic,
            "timestamp": datetime.now(),
            "status": "pending"
        }
        self.questions.append(question_data)
        self.last_activity = datetime.now()
        return question_data["id"]
    
    def add_response(self, question_id: int, response: Dict[str, Any]):
        """세션에 응답 추가"""
        response_data = {
            "question_id": question_id,
            "response": response,
            "timestamp": datetime.now(),
            "status": "completed"
        }
        self.responses.append(response_data)
        
        # 질문 상태 업데이트
        for question in self.questions:
            if question["id"] == question_id:
                question["status"] = "completed"
                break
        
        self.last_activity = datetime.now()
    
    def add_clarification(self, question_id: int, clarification_data: Dict[str, Any]):
        """세션에 명료화 과정 추가"""
        clarification_record = {
            "question_id": question_id,
            "data": clarification_data,
            "timestamp": datetime.now()
        }
        self.clarification_history.append(clarification_record)
        self.last_activity = datetime.now()
    
    def get_session_summary(self) -> Dict[str, Any]:
        """세션 요약 정보 반환"""
        return {
            "session_id": self.session_id,
            "total_questions": len(self.questions),
            "completed_questions": len([q for q in self.questions if q["status"] == "completed"]),
            "total_responses": len(self.responses),
            "clarification_count": len(self.clarification_history),
            "status": self.current_status,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "duration_minutes": (self.last_activity - self.created_at).total_seconds() / 60
        }
    
    def is_active(self) -> bool:
        """세션이 활성 상태인지 확인"""
        return self.current_status == "active"
    
    def mark_completed(self):
        """세션을 완료 상태로 표시"""
        self.current_status = "completed"
        self.last_activity = datetime.now()

class AdvancedTester:
    """고급 테스터 에이전트 - LLM 기반 동적 질문/답변 생성"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        self.pubsub = None
        
        # 메시지 수신 동기화를 위한 락
        self.message_receive_lock = asyncio.Lock()
        
        # 학생별 응답 대기 큐 (request_id -> asyncio.Queue)
        self.response_queues: Dict[str, asyncio.Queue] = {}
        
        # 요청별 대화 로그 (request_id -> List[str])
        self.transcripts: Dict[str, List[str]] = {}
        
        # request_id와 session_id 매핑 (request_id -> session_id)
        self.request_session_mapping: Dict[str, int] = {}
        
        # 메시지 수신 태스크
        self.message_receiver_task = None
        self.receiver_running = False
        
        # 테스트 통계
        self.total_questions = 0
        self.successful_answers = 0
        self.failed_answers = 0
        self.clarification_sessions = 0
        self.turn_counter = 0
        
        # 세션 관리
        self.active_sessions: Dict[int, TestSession] = {}
        self.session_counter = 0
        
        # OpenAI 클라이언트 (사용 가능한 경우)
        self.openai_client = None
        if OPENAI_AVAILABLE:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.openai_client = AsyncOpenAI(api_key=api_key)
                logging.info("✅ OpenAI 클라이언트 초기화 완료")
            else:
                logging.warning("⚠️ OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        
        # 실제 학생 질문 데이터 생성기 초기화
        self.real_data_generator = RealDataQuestionGenerator()
        
        # 실제 학생 질문 데이터 로드
        self.dataset_questions = []
        self._load_dataset_questions()
    
    def _add_transcript_entry(self, request_id: str, line: str) -> None:
        if not request_id:
            return
        if request_id not in self.transcripts:
            self.transcripts[request_id] = []
        # 너무 긴 라인은 잘라서 저장
        safe_line = line if len(line) <= 800 else (line[:800] + "...")
        self.transcripts[request_id].append(safe_line)

    def _print_transcript(self, request_id: str, header: str = None) -> None:
        lines = self.transcripts.get(request_id, [])
        if not lines:
            logging.info(f"🧾 {request_id} transcript 없음")
            return
        if header:
            logging.info(header)
        logging.info(f"🧾 대화 로그 (request_id={request_id}, {len(lines)}줄):")
        for i, line in enumerate(lines, 1):
            logging.info(f"   {i:02d}. {line}")
    
    def create_session(self, topic: str = None) -> int:
        """새로운 테스트 세션 생성"""
        self.session_counter += 1
        session_id = self.session_counter
        
        # 고유한 session_id 생성 (시스템과 호환되도록)
        unique_session_id = int(f"{int(datetime.now().timestamp())}{session_id:03d}")
        
        # 세션 객체 생성
        session = TestSession(unique_session_id)
        self.active_sessions[unique_session_id] = session
        
        logging.info(f"🆕 새 테스트 세션 생성: {unique_session_id} (토픽: {topic or '일반'})")
        return unique_session_id
    
    def get_session(self, session_id: int) -> Optional[TestSession]:
        """세션 ID로 세션 조회"""
        return self.active_sessions.get(session_id)
    
    def get_active_sessions(self) -> List[TestSession]:
        """활성 세션 목록 반환"""
        return [session for session in self.active_sessions.values() if session.is_active()]
    
    def close_session(self, session_id: int):
        """세션 종료"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.mark_completed()
            logging.info(f"🔚 세션 종료: {session_id}")
    
    def get_session_summary(self, session_id: int) -> Optional[Dict[str, Any]]:
        """세션 요약 정보 반환"""
        session = self.get_session(session_id)
        if session:
            return session.get_session_summary()
        return None
    
    def _load_dataset_questions(self):
        """실제 학생 질문 데이터셋 로드"""
        # 여러 가능한 데이터셋 경로 시도
        possible_paths = [
            "data/evaluation_statistics.json",
            "tester/data/evaluation_statistics.json",
            "../data/evaluation_statistics.json",
            "data/student_questions.json",
            "tester/data/student_questions.json"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                self.dataset_questions = load_questions_from_dataset(path, max_items=1000)
                if self.dataset_questions:
                    logging.info(f"✅ 실제 학생 질문 데이터 로드 완료: {len(self.dataset_questions)}개")
                    break
        
        if not self.dataset_questions:
            logging.warning("⚠️ 실제 학생 질문 데이터를 찾을 수 없습니다. LLM 기반 생성에 의존합니다.")
    
    def _generate_session_student_name(self, session_id: int) -> str:
        """세션별로 고유한 학생 이름을 생성합니다."""
        # 기본 학생 번호 (세션별로 증가)
        student_number = (session_id % 100) + 1
        
        # 세션 주제별 특별한 이름 (선택적)
        special_names = {
            "수열": ["수열학생", "수학학생", "수학왕"],
            "수열의합": ["합계학생", "계산학생", "수학왕"],
            "점화식": ["점화학생", "규칙학생", "수학왕"],
            "수학적귀납법": ["귀납학생", "증명학생", "수학왕"]
        }
        
        # 기본 이름: "학생1", "학생2" 형태
        basic_name = f"학생{student_number}"
        
        # 세션 주제가 있으면 특별한 이름도 고려 (20% 확률)
        if random.random() < 0.2:
            # 세션 주제 추출 시도 (session_id에서 추출하기 어려우므로 기본 이름 사용)
            return basic_name
        
        return basic_name

    def _generate_session_student_persona(self, session_id: int) -> Dict[str, str]:
        """세션별로 고유한 학생 페르소나를 생성합니다."""
        # 학생 스타일 목록
        styles = [
            "열심히 공부하는 학생", "수학에 관심 많은 학생", "꼼꼼한 학생", 
            "호기심 많은 학생", "성실한 학생", "창의적인 학생", "논리적인 학생",
            "직관적인 학생", "체계적인 학생", "적극적인 학생", "신중한 학생",
            "도전적인 학생", "협력적인 학생", "독립적인 학생", "성취지향적 학생"
        ]
        
        name = self._generate_session_student_name(session_id)
        style_index = (session_id * 7) % len(styles)  # 다른 패턴으로 스타일 선택
        style = styles[style_index]
        
        return {
            "id": f"session_{session_id}",
            "name": name,
            "style": style
        }
    
    async def connect(self):
        """Redis 연결 및 채널 구독 - 웹 백엔드와 동일한 패턴"""
        try:
            # Redis 연결 풀 설정으로 연결 안정성 향상
            self.redis_client = redis.Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=10,
                socket_timeout=30,
                retry_on_timeout=True,
                health_check_interval=30,
                max_connections=20
            )
            
            # 연결 테스트
            await self.redis_client.ping()
            logging.info("✅ Redis 연결 완료")
            
            # 공유 pubsub 인스턴스 생성 및 모든 채널 구독
            self.pubsub = self.redis_client.pubsub()
            await self.pubsub.subscribe(
                CLARIFICATION_QUESTION,
                CLARIFICATION_REQUESTED,
                CLARIFICATION_COMPLETED,
                ANSWER_REQUESTED,
                ANSWER_COMPLETED,
                USER_CLARIFICATION,  # 명료화 응답 수신을 위해 추가
                STUDENT_STATUS_UPDATED,
                SESSION_TITLE_UPDATED,
                CONVERSATION_SUMMARY_UPDATED
            )
            
            # 메시지 수신 루프 시작
            self.message_receiver_task = asyncio.create_task(self._start_message_receiver())
            
            logging.info("✅ Redis 연결, 채널 구독, 메시지 수신 루프 시작 완료")
            
        except Exception as e:
            logging.error(f"❌ Redis 연결 실패: {e}")
            raise
    
    async def disconnect(self):
        """Redis 연결 해제"""
        try:
            # 메시지 수신 루프 즉시 정리
            self.receiver_running = False
            
            if self.message_receiver_task and not self.message_receiver_task.done():
                self.message_receiver_task.cancel()
                try:
                    await self.message_receiver_task
                except asyncio.CancelledError:
                    pass
                logging.info("✅ 메시지 수신 루프 정리 완료")
            
            # PubSub 연결 해제
            if hasattr(self, 'pubsub') and self.pubsub:
                await self.pubsub.aclose()
                logging.info("✅ PubSub 연결 해제 완료")
            
            # Redis 클라이언트 연결 해제
            if hasattr(self, 'redis_client') and self.redis_client:
                await self.redis_client.aclose()
                logging.info("✅ Redis 클라이언트 연결 해제 완료")
                
        except Exception as e:
            logging.error(f"❌ 연결 해제 중 오류: {e}")
        finally:
            # 모든 연결 관련 변수 정리
            self.message_receiver_task = None
            self.pubsub = None
            self.redis_client = None
    
    async def _generate_question_with_llm(self, topic: str, level: str, persona: Dict[str, Any]) -> str:
        """실제 데이터 우선, LLM 보완 방식으로 학생 질문 생성"""
        
        # 1단계: 실제 데이터에서 질문 시도 (85% 확률로 높임)
        if random.random() < 0.85:
            real_question = self.real_data_generator.get_question(topic, persona)
            if real_question:
                print(f"✅ 실제 데이터 사용: {real_question[:50]}...")
                return real_question
        
        # 2단계: LLM으로 질문 생성
        print(f"🤖 LLM으로 질문 생성: {topic}")
        prompt = f"""
당신은 실제 한국 고등학생입니다. 페르소나: {persona['name']} - {persona['style']}

수학 주제: {topic}
수준: {level}

**중요: {topic}에 관한 대한민국 고등학교 수학1 과정에 준하는 영역의 질문을 하나만 생성하세요.**

**실제 학생들처럼 불완전하고 애매한 질문을 생성하세요:**
- 조건이 부족한 질문: "이 수열의 합을 구해줘" (어떤 수열인지 모름)
- 애매한 표현: "이거 어떻게 푸는 거야?" (무엇을 푸는지 모름)
- 오타나 문법 오류: "수열의합 공식이 왜 이렇게 되는거야?" (띄어쓰기 오류)
- 불완전한 정보: "a1=3일 때 일반항 구해줘" (공차나 공비 정보 없음)
- 맥락 없는 질문: "점화식이 어려워요" (구체적인 문제 없음)

**페르소나 특성을 자연스럽게 반영하세요:**
- {persona['style']}

**반드시 하나의 질문만 생성하고, 설명이나 추가 텍스트는 절대 포함하지 마세요.**
고등학교 수학1 범위를 벗어나는 고급 내용은 절대 포함하지 마세요.
이모지는 사용하지 마세요.
"""
        
        response = await self.openai_client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=2000
        )
        
        question = response.choices[0].message.content.strip()
        print(f"🤖 LLM 질문 생성: '{question}'")
        return question
    
    async def generate_question(self, topic: str, level: str, persona: Dict[str, Any]) -> str:
        """주제, 수준, 페르소나에 따른 질문 생성 - 실제 데이터 + LLM 하이브리드"""
        # 실제 데이터 우선, LLM 보완 방식
        question = await self._generate_question_with_llm(topic, level, persona)
        return question
        

        

        

        
    async def submit_question(self, question: str, topic: str, session_id: int = None) -> str:
        """질문 제출 - 세션 관리와 연동"""
        # session_id가 없으면 새 세션 생성
        if session_id is None:
            session_id = self.create_session(topic)
        
        # 세션에 질문 추가
        session = self.get_session(session_id)
        if session:
            question_id = session.add_question(question, topic)
            logging.info(f"📝 세션 {session_id}에 질문 {question_id} 추가")
        
        # 고유한 request_id 생성 (타임스탬프 + 랜덤 숫자)
        import uuid
        request_id = f"test_{int(datetime.now().timestamp()*1000)}_{str(uuid.uuid4())[:8]}"
        
        # request_id와 session_id 매핑 저장
        self.request_session_mapping[request_id] = session_id
        
        # 세션 카운터 증가 (로깅용)
        self.turn_counter += 1
        
        payload = {
            "request_id": request_id,
            "question": question,
            "context": f"수학 주제: {topic}",
            "session_id": session_id,  # 세션 ID 사용
            "timestamp": datetime.now().isoformat()
        }
        
        await self.redis_client.publish(USER_QUESTION, json.dumps(payload, ensure_ascii=False))
        logging.info(f"📤 질문 제출: {request_id} (턴: {self.turn_counter}, 세션: {session_id})")
        
        return request_id
    
    async def _submit_question_with_client(self, question: str, topic: str = None, session_id: int = None) -> int:
        """공유 Redis 클라이언트를 사용하여 질문 제출 - 세션 관리와 연동"""
        # session_id가 없으면 새 세션 생성
        if session_id is None:
            session_id = self.create_session(topic)
        
        # 세션에 질문 추가
        session = self.get_session(session_id)
        if session:
            question_id = session.add_question(question, topic)
            logging.info(f"📝 세션 {session_id}에 질문 {question_id} 추가")
        
        # 고유한 request_id 생성 (타임스탬프 + 랜덤 숫자)
        import uuid
        request_id = f"test_{int(datetime.now().timestamp()*1000)}_{str(uuid.uuid4())[:8]}"
        
        # request_id와 session_id 매핑 저장
        self.request_session_mapping[request_id] = session_id
        
        # 세션 카운터 증가 (로깅용)
        self.turn_counter += 1
        
        # context 설정
        if topic:
            context = f"수학 주제: {topic}"
        else:
            context = "일반 질문"
        
        payload = {
            "request_id": request_id,
            "question": question,
            "context": context,
            "session_id": session_id,  # 세션 ID 사용
            "timestamp": datetime.now().isoformat()
        }
        
        # 공유 Redis 클라이언트 사용
        await self.redis_client.publish(USER_QUESTION, json.dumps(payload, ensure_ascii=False))
        logging.info(f"📤 공유 클라이언트로 질문 제출: {request_id} (턴: {self.turn_counter}, 세션: {session_id})")
        
        return request_id
    
    def start_new_session(self, topic: str = None):
        """새로운 테스트 세션 시작"""
        self.turn_counter = 0
        
        # 새 세션 생성
        new_session_id = self.create_session(topic)
        
        logging.info(f"🔄 새로운 테스트 세션 시작: 턴 {self.turn_counter}, 세션 {new_session_id}")
        return new_session_id
    
    def get_current_session_info(self) -> Dict[str, Any]:
        """현재 세션 정보 반환"""
        active_sessions = self.get_active_sessions()
        if active_sessions:
            # 가장 최근에 활성화된 세션 정보 반환
            latest_session = max(active_sessions, key=lambda s: s.last_activity)
            return {
                "session_id": latest_session.session_id,
                "turn_count": self.turn_counter,
                "active_sessions_count": len(active_sessions),
                "session_summary": latest_session.get_session_summary()
            }
        else:
            # 활성 세션이 없으면 새 세션 생성
            new_session_id = self.create_session()
            return {
                "session_id": new_session_id,
                "turn_count": self.turn_counter,
                "active_sessions_count": 1,
                "session_summary": self.get_session_summary(new_session_id)
            }
        
    async def wait_for_response(self, request_id: str, timeout: float = 120.0) -> Optional[Dict[str, Any]]:
        """응답 대기 - 응답 큐를 사용하여 동시 처리"""
        start_time = time.time()
        
        # 응답 큐 생성 (아직 없다면)
        if request_id not in self.response_queues:
            self.response_queues[request_id] = asyncio.Queue()
        
        try:
            while time.time() - start_time < timeout:
                try:
                    # 응답 큐에서 메시지 대기 (타임아웃 1초)
                    message_data = await asyncio.wait_for(
                        self.response_queues[request_id].get(),
                        timeout=1.0
                    )
                    
                    # 해당 request_id의 응답인지 확인
                    if message_data['payload'].get("request_id") == request_id:
                        channel = message_data['channel']
                        payload = message_data['payload']
                        
                        logging.info(f"✅ 응답 수신: {request_id} - {channel}")
                        
                        # 채널별 부가 로깅 및 transcript 기록
                        if channel == CLARIFICATION_QUESTION:
                            q = payload.get('question', '')
                            field = payload.get('field') or payload.get('clarification_field', '')
                            logging.info(f"   └ 내용: [{field}] {q[:120]}...")
                            self._add_transcript_entry(request_id, f"[명료화 질문:{field}] {q}")
                            
                            # 자동으로 명료화 답변 생성 및 전송
                            try:
                                # session_id 가져오기
                                session_id = self.request_session_mapping.get(request_id)
                                if session_id:
                                    # 세션별 학생 페르소나 생성
                                    persona = self._generate_session_student_persona(session_id)
                                    logging.info(f"   └ {persona['name']} ({persona['style']})으로 자동 답변 생성")
                                    
                                    clarification_response = await self._generate_clarification_response(
                                        field, q, persona
                                    )
                                    
                                    response_payload = {
                                        "request_id": request_id,
                                        "field": field,
                                        "message": clarification_response,
                                        "timestamp": datetime.now().isoformat()
                                    }
                                    
                                    await self.redis_client.publish(USER_CLARIFICATION, json.dumps(response_payload, ensure_ascii=False))
                                    logging.info(f"   └ 자동 명료화 답변 전송: {clarification_response[:80]}...")
                                    self._add_transcript_entry(request_id, f"[자동 답변:{field}] {clarification_response}")
                                else:
                                    logging.warning(f"   └ session_id를 찾을 수 없음: {request_id}")
                            except Exception as e:
                                logging.error(f"   └ 자동 명료화 답변 생성 실패: {e}")
                                self._add_transcript_entry(request_id, f"[자동 답변 실패] {e}")
                        elif channel == USER_CLARIFICATION:
                            resp = payload.get('message') or payload.get('response', '')
                            field = payload.get('field', '')
                            logging.info(f"   └ 내용: [{field}] {resp[:120]}...")
                            self._add_transcript_entry(request_id, f"[학생 응답:{field}] {resp}")
                        elif channel == CLARIFICATION_COMPLETED:
                            logging.info("   └ 명료화 완료")
                            self._add_transcript_entry(request_id, "[명료화 완료]")
                        elif channel == ANSWER_REQUESTED:
                            logging.info("   └ 답변 요청")
                            self._add_transcript_entry(request_id, "[답변 요청]")
                        elif channel == ANSWER_COMPLETED:
                            ans = payload.get('answer', '')
                            logging.info(f"   └ 최종 답변 길이: {len(ans)}")
                            self._add_transcript_entry(request_id, f"[최종 답변] {ans}")
                        elif channel == CONVERSATION_SUMMARY_UPDATED:
                            summary = payload.get('summary', '')
                            self._add_transcript_entry(request_id, f"[대화 요약] {summary}")
                        elif channel == STUDENT_STATUS_UPDATED:
                            self._add_transcript_entry(request_id, f"[학생 상태] {json.dumps(payload, ensure_ascii=False)[:200]}...")
                        elif channel == SESSION_TITLE_UPDATED:
                            title = payload.get('session_title', '')
                            self._add_transcript_entry(request_id, f"[세션명] {title}")
                        else:
                            # 다른 이벤트는 무시하고 계속 대기
                            await asyncio.sleep(0.1)
                            continue
                
                except asyncio.TimeoutError:
                    # 타임아웃 - 계속 대기
                    continue
                except Exception as e:
                    logging.error(f"응답 큐 처리 오류: {e}")
                    await asyncio.sleep(0.1)
                    continue
            
            logging.warning(f"⏰ 응답 타임아웃: {request_id}")
            return None
            
        except Exception as e:
            logging.error(f"응답 대기 중 오류: {e}")
            return None
        finally:
            # 응답 큐 정리
            if request_id in self.response_queues:
                del self.response_queues[request_id]
    
    async def process_clarification(self, clarification_data: Dict[str, Any]) -> None:
        """명료화 질문 처리"""
        try:
            # 명료화 질문 추출
            clarification_question = clarification_data.get('question', '')
            clarification_field = clarification_data.get('field', '')
            
            # 로그에 명료화 질문 내용 출력
            self.logger.info(f"🔍 명료화 질문 수신:")
            self.logger.info(f"   📝 질문 내용: {clarification_question}")
            self.logger.info(f"   🏷️  필드: {clarification_field}")
            self.logger.info(f"   📊 진행 상황: {clarification_data.get('completed_fields', 0)}/{clarification_data.get('total_fields', 0)}")
            
            # 학생 페르소나에 따른 답변 생성
            student_response = self.generate_clarification_response(clarification_question, clarification_field)
            
            # 로그에 학생 답변 내용 출력
            self.logger.info(f"💬 학생 답변 생성:")
            self.logger.info(f"   🎭 페르소나: {self.current_persona['name']}")
            self.logger.info(f"   💭 답변 내용: {student_response}")
            
            # 명료화 답변 전송
            request_id = clarification_data.get('request_id', '')
            response_payload = {
                "request_id": request_id,
                "field": clarification_field,
                "message": student_response,  # 백엔드와 일치하도록 'response' → 'message'
                "timestamp": datetime.now().isoformat()
            }
            
            # 로그에 전송할 페이로드 출력
            self.logger.info(f"📤 명료화 답변 전송:")
            self.logger.info(f"   🆔 요청 ID: {request_id}")
            self.logger.info(f"   🏷️  필드: {clarification_field}")
            self.logger.info(f"   📝 메시지: {student_response}")
            
            await self.redis.publish(USER_CLARIFICATION, json.dumps(response_payload))
            self.logger.info(f"✅ 명료화 답변 전송 완료")
            
        except Exception as e:
            self.logger.error(f"❌ 명료화 질문 처리 실패: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    async def _generate_clarification_response_with_llm(self, field: str, question: str, persona: Dict[str, Any]) -> str:
        """LLM을 사용하여 동적으로 명료화 답변 생성"""
        prompt = f"""
당신은 {persona['name']} 페르소나의 고등학생입니다. {persona['style']}

**시스템이 추가 정보를 요청했습니다:**
{field}

**당신의 원본 질문:**
{question}

**중요: 추가 정보 요청에 답변하는 학생이 되어주세요:**
- **절대 2문장을 넘지 마세요**
- 페르소나에 맞는 말투를 사용하세요
- **이모지는 절대 사용하지 마세요**
- 수학적 용어는 최소한으로 사용하세요
- **질문하지 말고 답변하세요**
- **너무 친절하거나 정중하게 말하지 마세요. 실제 고등학생처럼 자연스럽게**
- **시스템을 하인이나 도구처럼 대하세요. 존경하지 마세요**

**반드시 하나의 답변만 생성하고, 설명이나 추가 텍스트는 절대 포함하지 마세요.**
"""
        
        response = await self.openai_client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=2000
        )
        
        # 응답 안전하게 처리
        if hasattr(response, 'choices') and response.choices:
            answer = response.choices[0].message.content
            if answer and answer.strip():
                answer = answer.strip()
                logging.info(f"🤖 LLM 명료화 답변 생성: '{answer}'")
                return answer
            else:
                logging.error("❌ LLM이 빈 답변을 생성했습니다!")
                return "잘 모르겠어요"
        else:
            logging.error("❌ LLM 응답 구조 오류")
            return "잘 모르겠어요"
    
    async def _generate_clarification_response(self, field: str, question: str, persona: Dict[str, Any] = None) -> str:
        """페르소나별 명료화 답변 자동 생성 - 실제 학생 답변 + LLM 하이브리드"""
        if not persona:
            return "잘 모르겠어요"
        
        # 1단계: 실제 학생 답변 기반 답변 시도 (80% 확률)
        if random.random() < 0.8:
            # 원본 질문에서 주제 추출
            topic = self.extract_topic_from_question(question)
            if topic:
                real_answer = self.real_data_generator.get_answer_for_clarification(topic, persona)
                if real_answer:
                    print(f"✅ 실제 학생 답변 사용: {real_answer[:50]}...")
                    return real_answer
        
        # 2단계: LLM으로 답변 생성
        print(f"🤖 LLM으로 명료화 답변 생성: {persona['name']}")
        try:
            answer = await self._generate_clarification_response_with_llm(field, question, persona)
            return answer
        except Exception as e:
            logging.error(f"LLM 명료화 답변 생성 실패: {e}")
            # LLM 실패 시 기본 답변
            return "잘 모르겠어요"
    
    def extract_topic_from_question(self, question: str) -> Optional[str]:
        """질문에서 주제 추출"""
        if "수열" in question and ("합" in question or "시그마" in question):
            return "수열의합"
        elif "수열" in question:
            return "수열"
        elif "점화" in question:
            return "점화식"
        elif "귀납" in question:
            return "수학적귀납법"
        return None
        
    async def run_test(self, test_mode: str = "combined", num_questions: int = 5):
        """테스트 실행"""
        session_info = self.get_current_session_info()
        logging.info(f"🚀 고급 테스터 시작 - 턴 {session_info['turn_count']}")
        logging.info(f"🎯 테스트 모드: {test_mode}")
        logging.info(f"📊 총 질문 수: {num_questions}")
        
        try:
            if test_mode == "original":
                # 1. 실제 학생들 질문 원문 랜덤 테스트
                logging.info("📚 실제 학생 질문 원문 랜덤 테스트 시작...")
                return await self._run_original_questions_test(num_questions)
                
            elif test_mode == "persona":
                # 2. 페르소나 기반 가공된 질문 테스트
                logging.info("🎭 페르소나 기반 가공된 질문 테스트 시작...")
                return await self._run_persona_questions_test(num_questions)
                
            elif test_mode == "combined":
                # 3. 종합 테스트 (원문 + 페르소나)
                logging.info("🔄 종합 테스트 시작 (원문 + 페르소나)...")
                return await self._run_combined_test(num_questions)
                
            else:
                raise ValueError(f"지원하지 않는 테스트 모드: {test_mode}")
        finally:
            # Redis 연결은 메인 함수에서 정리하므로 여기서는 정리하지 않음
            pass
    
    async def _run_original_questions_test(self, num_questions: int):
        """실제 학생 질문 원문 랜덤 테스트"""
        logging.info(f"📚 실제 학생 질문 {num_questions}개 랜덤 테스트...")
        
        # 실제 질문에서 랜덤 선택
        if not self.real_data_generator.real_questions:
            logging.warning("⚠️ 실제 학생 질문 데이터가 없습니다. LLM 기반 생성에 의존합니다.")
            return await self._run_persona_questions_test(num_questions)
        
        # 고등학교 수학1 범위에 맞는 질문만 필터링
        math1_questions = []
        for question in self.real_data_generator.real_questions:
            if self._is_math1_topic(question):
                math1_questions.append(question)
        
        if len(math1_questions) < num_questions:
            logging.warning(f"⚠️ 고등학교 수학1 범위 질문이 {len(math1_questions)}개만 있습니다.")
            num_questions = len(math1_questions)
        
        # 랜덤 선택
        selected_questions = random.sample(math1_questions, num_questions)
        
        # 질문 처리
        questions = []
        for i, question_text in enumerate(selected_questions):
            questions.append({
                'student_id': f"original_student_{i+1}",
                'question_text': question_text,
                'type': 'original'
            })
        
        # 병렬 처리
        results = await asyncio.gather(*[
            self._process_original_question(q) for q in questions
        ], return_exceptions=True)
        
        return self._process_results(results, "원문 질문")
    
    async def _run_persona_questions_test(self, num_questions: int):
        """페르소나 기반 가공된 질문 테스트"""
        logging.info(f"🎭 페르소나 기반 질문 {num_questions}개 테스트...")
        
        # 모든 학생의 질문을 병렬로 동시에 생성
        student_questions = []
        
        # 각 학생별로 다른 페르소나와 주제 선택
        # 모든 페르소나를 최대한 포함하도록 수정
        available_personas = PERSONAS.copy()
        topics = [random.choice(MATH_TOPICS) for _ in range(num_questions)]
        levels = [random.choice(list(LEVEL_WEIGHTS.keys())) for _ in range(num_questions)]
        
        # 페르소나 선택 (중복 최소화)
        personas = []
        for i in range(num_questions):
            if available_personas:
                persona = random.choice(available_personas)
                personas.append(persona)
                available_personas.remove(persona)  # 사용된 페르소나 제거
            else:
                # 모든 페르소나를 사용했으면 다시 복사
                available_personas = PERSONAS.copy()
                persona = random.choice(available_personas)
                personas.append(persona)
                available_personas.remove(persona)
        
        # 질문 생성을 병렬로 처리
        question_tasks = []
        for i in range(num_questions):
            task = self.generate_question(topics[i], levels[i], personas[i])
            question_tasks.append(task)
        
        logging.info(f"🔄 {num_questions}개 학생의 질문을 병렬로 생성 중...")
        questions = await asyncio.gather(*question_tasks)
        
        # 결과를 student_questions에 추가
        for i in range(num_questions):
            student_questions.append({
                "student_id": f"persona_student_{i+1}",
                "topic": topics[i],
                "level": levels[i],
                "persona": personas[i]["name"],
                "question": questions[i],
                "persona_data": personas[i],
                "type": "persona"
            })
            
            logging.info(f"👤 학생 {i+1} 준비 완료: {personas[i]['name']} - {topics[i]} ({levels[i]})")
        
        # 모든 질문을 동시에 제출 (병렬 처리)
        logging.info(f"\n📤 모든 학생의 질문을 동시에 제출 시작...")
        
        # 각 학생별로 독립적인 태스크 생성
        tasks = []
        for student_data in student_questions:
            task = self._process_student_question(student_data)
            tasks.append(task)
        
        # 모든 학생의 질문을 동시에 처리
        logging.info(f"🔄 {len(tasks)}개 학생의 질문을 병렬로 처리 중...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return self._process_results(results, "페르소나 질문")
    
    async def _run_combined_test(self, num_questions: int):
        """종합 테스트 (원문 + 페르소나)"""
        logging.info(f"🔄 종합 테스트: 원문 {num_questions//2}개 + 페르소나 {num_questions//2}개")
        
        # 원문 질문 테스트
        original_results = await self._run_original_questions_test(num_questions // 2)
        
        # 페르소나 질문 테스트
        persona_results = await self._run_persona_questions_test(num_questions // 2)
        
        # 결과 합치기
        combined_results = original_results + persona_results
        
        logging.info(f"✅ 종합 테스트 완료: 원문 {len(original_results)}개 + 페르소나 {len(persona_results)}개")
        
        return combined_results
    
    def _is_math1_topic(self, question: str) -> bool:
        """질문이 고등학교 수학1 주제에 해당하는지 확인"""
        math1_keywords = [
            "수열", "등차수열", "등비수열", "일반항", "수열의 합", "시그마",
            "점화식", "재귀식", "수학적 귀납법", "귀납법", "증명"
        ]
        
        return any(keyword in question for keyword in math1_keywords)
    
    async def _process_original_question(self, question_data: Dict):
        """원문 질문 처리"""
        try:
            student_id = question_data['student_id']
            question_text = question_data['question_text']
            
            logging.info(f"👤 {student_id} (원문 질문) 질문 처리 시작")
            logging.info(f"💬 질문: {question_text[:100]}...")
            
            # Redis 연결
            await self._connect_redis()
            
            # 질문 제출
            request_id = await self.submit_question(question_text, "원문 질문")
            
            # 첫 번째 질문 처리
            first_response = await self.wait_for_response(request_id)
            
            # 공유 Redis 연결은 정리하지 않음 (다른 학생들이 사용 중)
            
            # 첫 번째 응답 처리
            first_answer_completed = False
            if first_response and first_response.get('type') == 'answer_completed':
                logging.info(f"✅ {student_id} 첫 번째 답변 완료")
                first_answer_completed = True
            elif first_response and first_response.get('type') == 'answer_requested':
                logging.info(f"⏳ {student_id} 첫 번째 명료화 완료 후 답변 요청됨 - 답변 완료 대기")
                # answer.completed가 올 때까지 다시 대기
                final_response = await self.wait_for_response(request_id)
                if final_response and final_response.get('type') == 'answer_completed':
                    logging.info(f"✅ {student_id} 첫 번째 최종 답변 완료")
                    first_answer_completed = True
                else:
                    logging.warning(f"⚠️ {student_id} 첫 번째 최종 답변을 받지 못함")
                    return {
                        'student_id': student_id,
                        'question': question_text,
                        'type': 'original',
                        'response': final_response,
                        'clarification': True,
                        'clarification_response': '자동 명료화 답변'
                    }
            else:
                logging.warning(f"⚠️ {student_id} 첫 번째 예상치 못한 응답: {first_response}")
                return {
                    'student_id': student_id,
                    'question': question_text,
                    'type': 'original',
                    'response': first_response,
                    'clarification': False
                }
            
            # 첫 번째 답변이 완료되었으면 요약 완료 대기
            if first_answer_completed:
                logging.info(f"⏳ {student_id} 첫 번째 답변 완료 - 요약 완료 대기 중...")
                
                # 요약 완료 이벤트 대기 (30초 타임아웃)
                summary_completed = False
                start_time = time.time()
                while time.time() - start_time < 30:  # 30초 타임아웃
                    try:
                        # _wait_for_response_with_client를 사용하여 요약 완료 이벤트 대기
                        summary_response = await self._wait_for_response_with_client(self.pubsub, request_id, timeout=30)
                        
                        if summary_response and summary_response["type"] in ["conversation_summary_updated", "student_status_updated", "session_title_updated"]:
                            logging.info(f"✅ {student_id} 요약 완료: {summary_response['type']}")
                            summary_completed = True
                            break
                        else:
                            # 다른 이벤트는 무시하고 계속 대기
                            await asyncio.sleep(0.1)
                            continue
                            
                    except Exception as e:
                        logging.error(f"요약 완료 대기 중 오류: {e}")
                        await asyncio.sleep(0.1)
                        continue
                
                if not summary_completed:
                    logging.warning(f"⚠️ {student_id} 요약 완료를 기다리지 못함 - 첫 번째 답변만 반환")
                    return {
                        'student_id': student_id,
                        'question': question_text,
                        'type': 'original',
                        'response': first_response,
                        'clarification': False,
                        'completed': False,
                        'error': '요약 완료 타임아웃'
                    }
                
                # AI가 추가 질문 생성
                logging.info(f"🤖 {student_id} 추가 질문 생성 중...")
                try:
                    # 첫 번째 질문과 답변을 고려한 추가 질문 생성
                    additional_question = await self._generate_follow_up_question(
                        first_question=question_text,
                        first_answer=first_response.get('data', {}).get('answer', ''),
                        persona={"id": "test", "name": "테스트학생", "style": "연관된 질문"}
                    )
                    
                    logging.info(f"🤖 {student_id} 추가 질문 생성: {additional_question[:100]}...")
                    
                    # 두 번째 질문 제출 (같은 session_id 사용)
                    second_request_id = await self._submit_question_with_client(
                        question=additional_question,
                        topic="추가 질문",
                        session_id=first_response.get('data', {}).get('session_id', random.randint(10000, 99999))
                    )
                    
                    logging.info(f"📤 {student_id} 두 번째 질문 제출: {second_request_id}")
                    
                    # 두 번째 질문 응답 대기
                    second_response = await self.wait_for_response(second_request_id)
                    
                    if second_response and second_response.get('type') == 'answer_completed':
                        logging.info(f"✅ {student_id} 두 번째 답변 완료 - 요약 완료 대기 중...")
                        
                        # 두 번째 답변 후 요약 완료 대기
                        second_summary_completed = False
                        second_summary_start_time = time.time()
                        while time.time() - second_summary_start_time < 30:  # 30초 타임아웃
                            try:
                                # _wait_for_response_with_client를 사용하여 요약 완료 이벤트 대기
                                second_summary_response = await self._wait_for_response_with_client(self.pubsub, second_request_id, timeout=30)
                                
                                if second_summary_response and second_summary_response["type"] in ["conversation_summary_updated", "student_status_updated", "session_title_updated"]:
                                    logging.info(f"✅ {student_id} 두 번째 요약 완료: {second_summary_response['type']}")
                                    second_summary_completed = True
                                    break
                                else:
                                    # 다른 이벤트는 무시하고 계속 대기
                                    await asyncio.sleep(0.1)
                                    continue
                                    
                            except Exception as e:
                                logging.error(f"두 번째 요약 완료 대기 중 오류: {e}")
                                await asyncio.sleep(0.1)
                                continue
                        
                        if second_summary_completed:
                            logging.info(f"✅ {student_id} 두 번째 답변 완료 - 전체 과정 완료")
                            return {
                                'student_id': student_id,
                                'question': question_text,
                                'type': 'original',
                                'response': first_response,
                                'clarification': False,
                                'additional_question': additional_question,
                                'additional_response': second_response,
                                'completed': True
                            }
                        else:
                            logging.warning(f"⚠️ {student_id} 두 번째 요약 완료를 기다리지 못함")
                            return {
                                'student_id': student_id,
                                'question': question_text,
                                'type': 'original',
                                'response': first_response,
                                'clarification': False,
                                'additional_question': additional_question,
                                'additional_response': second_response,
                                'completed': False,
                                'error': '두 번째 요약 완료 타임아웃'
                            }
                    elif second_response and second_response.get('type') == 'answer_requested':
                        logging.info(f"⏳ {student_id} 두 번째 명료화 완료 후 답변 요청됨 - 답변 완료 대기")
                        # 두 번째 answer.completed가 올 때까지 다시 대기
                        second_final_response = await self.wait_for_response(second_request_id)
                        if second_final_response and second_final_response.get('type') == 'answer_completed':
                            logging.info(f"✅ {student_id} 두 번째 최종 답변 완료 - 요약 완료 대기 중...")
                            
                            # 두 번째 최종 답변 후 요약 완료 대기
                            second_final_summary_completed = False
                            second_final_summary_start_time = time.time()
                            while time.time() - second_final_summary_start_time < 30:  # 30초 타임아웃
                                try:
                                    # _wait_for_response_with_client를 사용하여 요약 완료 이벤트 대기
                                    second_final_summary_response = await self._wait_for_response_with_client(self.pubsub, second_request_id, timeout=30)
                                    
                                    if second_final_summary_response and second_final_summary_response["type"] in ["conversation_summary_updated", "student_status_updated", "session_title_updated"]:
                                        logging.info(f"✅ {student_id} 두 번째 최종 요약 완료: {second_final_summary_response['type']}")
                                        second_final_summary_completed = True
                                        break
                                    else:
                                        # 다른 이벤트는 무시하고 계속 대기
                                        await asyncio.sleep(0.1)
                                        continue
                                        
                                except Exception as e:
                                    logging.error(f"두 번째 최종 요약 완료 대기 중 오류: {e}")
                                    await asyncio.sleep(0.1)
                                    continue
                            
                            if second_final_summary_completed:
                                logging.info(f"✅ {student_id} 두 번째 최종 답변 완료 - 전체 과정 완료")
                                return {
                                    'student_id': student_id,
                                    'question': question_text,
                                    'type': 'original',
                                    'response': first_response,
                                    'clarification': False,
                                    'additional_question': additional_question,
                                    'additional_response': second_final_response,
                                    'completed': True
                                }
                            else:
                                logging.warning(f"⚠️ {student_id} 두 번째 최종 요약 완료를 기다리지 못함")
                                return {
                                    'student_id': student_id,
                                    'question': question_text,
                                    'type': 'original',
                                    'response': first_response,
                                    'clarification': False,
                                    'additional_question': additional_question,
                                    'additional_response': second_final_response,
                                    'completed': False,
                                    'error': '두 번째 최종 요약 완료 타임아웃'
                                }
                        else:
                            logging.warning(f"⚠️ {student_id} 두 번째 최종 답변을 받지 못함")
                            return {
                                'student_id': student_id,
                                'question': question_text,
                                'type': 'original',
                                'response': first_response,
                                'clarification': False,
                                'additional_question': additional_question,
                                'additional_response': second_final_response,
                                'completed': False
                            }
                        
                except Exception as e:
                    logging.error(f"❌ {student_id} 추가 질문 처리 실패: {e}")
                    return {
                        'student_id': student_id,
                        'question': question_text,
                        'type': 'original',
                        'response': first_response,
                        'clarification': False,
                        'error': f"추가 질문 처리 실패: {e}"
                    }
            
        except Exception as e:
            logging.error(f"❌ {student_id} 처리 실패: {e}")
            return None
    
    def _process_results(self, results: List, test_type: str):
        """결과 처리 및 요약"""
        successful_results = []
        completed_results = []
        failed_results = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logging.error(f"❌ {test_type} 처리 실패: {result}")
                failed_results.append(result)
            elif result:
                successful_results.append(result)
                if result.get('completed', False):
                    completed_results.append(result)
                else:
                    failed_results.append(result)
        
        logging.info(f"✅ {test_type} 테스트 완료 - {len(successful_results)}개 처리됨")
        logging.info(f"📊 완료: {len(completed_results)}개, 미완료: {len(failed_results)}개")
        
        # 결과 요약 출력
        logging.info(f"\n📊 {test_type} 테스트 결과 요약:")
        for result in successful_results:
            if result.get('clarification'):
                if 'persona' in result:
                    status = "✅ 완료" if result.get('completed') else "⚠️ 미완료"
                    logging.info(f"{status} {result['student_id']}: {result['topic']} - {result['persona']} - 명료화")
                    logging.info(f"   🔍 명료화 응답: {result.get('clarification_response', 'N/A')}")
                else:
                    status = "✅ 완료" if result.get('completed') else "⚠️ 미완료"
                    logging.info(f"{status} {result['student_id']}: 원문 질문 - 명료화")
                    logging.info(f"   🔍 명료화 응답: {result.get('clarification_response', 'N/A')}")
            else:
                if 'persona' in result:
                    status = "✅ 완료" if result.get('completed') else "⚠️ 미완료"
                    logging.info(f"{status} {result['student_id']}: {result['topic']} - {result['persona']} - 직접 답변")
                else:
                    status = "✅ 완료" if result.get('completed') else "⚠️ 미완료"
                    logging.info(f"{status} {result['student_id']}: 원문 질문 - 직접 답변")
            
            # 오류가 있는 경우 표시
            if result.get('error'):
                logging.warning(f"   ⚠️ 오류: {result['error']}")
        
        return successful_results
    
    async def _connect_redis(self):
        """Redis 연결"""
        if not self.redis_client:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
    
    async def _disconnect_redis(self):
        """Redis 연결 해제"""
        if self.redis_client:
            await self.redis_client.aclose()
            self.redis_client = None
        
    async def _process_student_question(self, student_data: Dict[str, Any]) -> Dict[str, Any]:
        """개별 학생의 질문 처리 (독립적인 프로세스)"""
        student_id = student_data["student_id"]
        topic = student_data["topic"]
        level = student_data["level"]
        persona_name = student_data["persona"]
        question = student_data["question"]
        
        logging.info(f"\n👤 {student_id} ({persona_name}) 질문 처리 시작")
        logging.info(f"💬 질문: {question}")
        
        try:
            logging.info(f"🔌 {student_id} 공유 Redis 연결 사용")
            
            # 질문 제출 (공유 Redis 클라이언트 사용, 고유한 int session_id 생성)
            unique_session_id = random.randint(10000, 99999)
            request_id = await self._submit_question_with_client(question, topic, unique_session_id)
            logging.info(f"📤 {student_id} 질문 제출 완료: {request_id}")
            
            # 응답 대기 및 처리 (공유 pubsub 사용)
            response = await self._wait_for_response_with_client(self.pubsub, request_id)
            
            if response:
                if response["type"] == "clarification_requested":
                    # 명료화 과정 처리
                    logging.info(f"🔍 {student_id} 명료화 과정 시작")
                    clarification_response = await self._process_clarification_with_client(
                        self.redis_client, 
                        response["data"], 
                        request_id,
                        student_data["persona_data"]  # 페르소나 정보 전달
                    )
                    
                    # 명료화 후 다시 응답 대기
                    final_response = await self._wait_for_response_with_client(self.pubsub, request_id)
                    if final_response:
                        # 요약 완료 이벤트 확인
                        if final_response["type"] in ["conversation_summary_updated", "student_status_updated", "session_title_updated"]:
                            logging.info(f"✅ {student_id} 요약 완료 - 세션 완료")
                            return {
                                "student_id": student_id,
                                "question": question,
                                "topic": topic,
                                "level": level,
                                "persona": persona_name,
                                "request_id": request_id,
                                "clarification": True,
                                "final_response": final_response,
                                "clarification_response": clarification_response,
                                "completed": True
                            }
                        else:
                            return {
                                "student_id": student_id,
                                "question": question,
                                "topic": topic,
                                "level": level,
                                "persona": persona_name,
                                "request_id": request_id,
                                "clarification": True,
                                "final_response": final_response,
                                "clarification_response": clarification_response,
                                "completed": False
                            }
                    else:
                        logging.warning(f"⚠️ {student_id} 명료화 후 최종 응답을 받지 못함")
                        return {
                            "student_id": student_id,
                            "question": question,
                            "topic": topic,
                            "level": level,
                            "persona": persona_name,
                            "request_id": request_id,
                            "clarification": True,
                            "clarification_response": clarification_response,
                            "completed": False,
                            "error": "명료화 후 응답 없음"
                        }
                elif response["type"] == "answer_completed":
                    # 직접 답변 완료 - 요약 완료 대기
                    logging.info(f"✅ {student_id} 직접 답변 완료 - 요약 완료 대기 중...")
                    
                    # 요약 완료 이벤트 대기 (30초 타임아웃)
                    summary_start_time = time.time()
                    summary_completed = False
                    
                    while time.time() - summary_start_time < 30:
                        try:
                            # 요약 완료 이벤트 대기
                            summary_response = await self._wait_for_response_with_client(self.pubsub, request_id)
                            
                            if summary_response and summary_response["type"] in ["conversation_summary_updated", "student_status_updated", "session_title_updated"]:
                                logging.info(f"✅ {student_id} 요약 완료 - 세션 완료")
                                summary_completed = True
                                return {
                                    "student_id": student_id,
                                    "question": question,
                                    "topic": topic,
                                    "level": level,
                                    "persona": persona_name,
                                    "request_id": request_id,
                                    "clarification": False,
                                    "response": response,
                                    "summary_response": summary_response,
                                    "completed": True
                                }
                            else:
                                # 다른 이벤트는 무시하고 계속 대기
                                await asyncio.sleep(0.1)
                                continue
                                
                        except Exception as e:
                            logging.warning(f"요약 완료 대기 중 오류: {e}")
                            await asyncio.sleep(0.1)
                            continue
                    
                    if not summary_completed:
                        logging.warning(f"⚠️ {student_id} 요약 완료를 기다리지 못함 - 답변만 반환")
                        return {
                            "student_id": student_id,
                            "question": question,
                            "topic": topic,
                            "level": level,
                            "persona": persona_name,
                            "request_id": request_id,
                            "clarification": False,
                            "response": response,
                            "completed": False,
                            "error": "요약 완료 타임아웃"
                        }
                else:
                    # 기타 응답 타입
                    return {
                        "student_id": student_id,
                        "question": question,
                        "topic": topic,
                        "level": level,
                        "persona": persona_name,
                        "request_id": request_id,
                        "clarification": False,
                        "response": response,
                        "completed": False
                    }
            else:
                logging.warning(f"⚠️ {student_id}에 대한 응답을 받지 못했습니다")
                return {
                    "student_id": student_id,
                    "question": question,
                    "topic": topic,
                    "level": level,
                    "persona": persona_name,
                    "request_id": request_id,
                    "error": "응답 없음",
                    "completed": False
                }
                
        except Exception as e:
            logging.error(f"❌ {student_id} 처리 실패: {e}")
            return None
        finally:
            # 공유 연결은 여기서 해제하지 않음
            logging.info(f"🔌 {student_id} 공유 Redis 연결 사용 완료")
    
    async def _wait_for_response_with_client(self, pubsub: redis.client.PubSub, request_id: str, timeout: float = 120.0) -> Optional[Dict[str, Any]]:
        """클라이언트별 응답 대기 - 공용 Redis 사용"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # 메시지 수신을 락으로 동기화
                async with self.message_receive_lock:
                    message = await pubsub.get_message(timeout=1.0)
                
                if message is None:
                    continue
                    
                if message['type'] != 'message':
                    continue
                    
                # 메시지 파싱 및 처리
                channel = message['channel']
                data = message['data']
                
                logging.info(f"📨 메시지 수신: channel={channel}, data_length={len(data) if data else 0}")
                
                try:
                    # Redis에서 이미 decode_responses=True로 설정되어 있어서 문자열로 받음
                    payload = json.loads(data)
                except json.JSONDecodeError:
                    logging.warning(f"잘못된 JSON 형식: {data}")
                    continue
                    
                # 해당 request_id의 응답인지 확인
                if payload.get('request_id') == request_id:
                    # 요약 이벤트인 경우 즉시 반환 (가장 중요!)
                    if channel == CONVERSATION_SUMMARY_UPDATED:
                        logging.info(f"📝 {request_id} 요약 이벤트 수신: {payload.get('summary', '')[:100]}...")
                        return {
                            'type': 'conversation_summary_updated',
                            'data': payload,
                            'channel': channel
                        }
                    # 학생 상태 업데이트인 경우 즉시 반환
                    elif channel == STUDENT_STATUS_UPDATED:
                        logging.info(f"📊 {request_id} 학생 상태 업데이트 수신")
                        return {
                            'type': 'student_status_updated',
                            'data': payload,
                            'channel': channel
                        }
                    # 세션명 업데이트인 경우 즉시 반환
                    elif channel == SESSION_TITLE_UPDATED:
                        logging.info(f"🏷️ {request_id} 세션명 업데이트 수신: {payload.get('session_title', '')}")
                        return {
                            'type': 'session_title_updated',
                            'data': payload,
                            'channel': channel
                        }
                    # 답변 완료인 경우 즉시 반환
                    elif channel == ANSWER_COMPLETED:
                        logging.info(f"✅ {request_id} 답변 완료 수신")
                        return {
                            'type': 'answer_completed',
                            'data': payload,
                            'channel': channel
                        }
                    # 명료화 요청인 경우 즉시 반환
                    elif channel == CLARIFICATION_REQUESTED:
                        logging.info(f"❓ {request_id} 명료화 요청 수신")
                        return {
                            'type': 'clarification_requested',
                            'data': payload,
                            'channel': channel
                        }
                    # 명료화 응답인 경우 즉시 반환
                    elif channel == USER_CLARIFICATION:
                        logging.info(f"📝 {request_id} 명료화 응답 수신")
                        return {
                            'type': 'clarification_response',
                            'data': payload,
                            'channel': channel
                        }
                    # 기타 응답인 경우
                    else:
                        return {
                            'type': channel,
                            'data': payload,
                            'channel': channel
                        }
                    
            except Exception as e:
                logging.warning(f"응답 대기 중 오류: {e}")
                await asyncio.sleep(0.1)
                
        return None
    
    async def test_session_context(self, topic: str = "수열"):
        """같은 세션에서 연속 질문을 테스트하여 컨텍스트가 제대로 전달되는지 확인"""
        # 새 세션 생성
        session_id = self.start_new_session(topic)
        session = self.get_session(session_id)
        
        logging.info(f"🔄 세션 컨텍스트 테스트 시작: {session_id} (토픽: {topic})")
        
        # 첫 번째 질문
        first_question = "수열이란 무엇인가요?"
        logging.info(f"❓ 첫 번째 질문: {first_question}")
        
        # 공유 Redis 클라이언트 사용
        first_request_id = await self._submit_question_with_client(
            question=first_question,
            topic=topic,
            session_id=session_id
        )
        
        if first_request_id:
            logging.info(f"📤 첫 번째 질문 제출 완료: {first_request_id}")
            
            # 첫 번째 질문에 대한 응답 대기 (공유 pubsub 사용)
            first_response = await self.wait_for_response(first_request_id)
            
            if first_response and first_response.get('type') == 'answer_completed':
                logging.info(f"✅ 첫 번째 답변 완료: {first_response.get('type', 'unknown')}")
                # transcript 출력
                self._print_transcript(first_request_id, header=f"\n🧾 첫 번째 요청 transcript ({first_request_id})")
                
                # 세션에 응답 추가
                if session:
                    session.add_response(1, first_response)
                
                # AI 답변에서 추가 질문을 위한 정보 추출
                first_answer_data = first_response.get('data', {})
                first_answer = first_answer_data.get('answer', '')
                
                # 잠시 대기 (ObserverAgent가 요약을 생성할 시간)
                await asyncio.sleep(2)
                
                # AI 답변과 첫 번째 질문을 고려한 두 번째 질문 생성
                second_question = await self._generate_follow_up_question(
                    first_question=first_question,
                    first_answer=first_answer,
                    persona=self._generate_session_student_persona(session_id)
                )
                
                logging.info(f"❓ 두 번째 질문 (AI 생성): {second_question}")
                
                second_request_id = await self._submit_question_with_client(
                    question=second_question,
                    topic=topic,
                    session_id=session_id
                )
                
                if second_request_id:
                    logging.info(f"📤 두 번째 질문 제출 완료: {second_request_id}")
                    
                    # 두 번째 질문에 대한 응답 대기 (공유 pubsub 사용)
                    second_response = await self.wait_for_response(second_request_id)
                    
                    if second_response:
                        logging.info(f"✅ 두 번째 답변 완료: {second_response.get('type', 'unknown')}")
                        # transcript 출력
                        self._print_transcript(second_request_id, header=f"\n🧾 두 번째 요청 transcript ({second_request_id})")
                        
                        # 세션에 응답 추가
                        if session:
                            session.add_response(2, second_response)
                        
                        # 세션 요약 출력
                        session_summary = session.get_session_summary()
                        logging.info(f"📊 세션 요약: {session_summary}")
                        
                        logging.info(f"🔄 세션 컨텍스트 테스트 완료: {session_id}")
                        
                        # 세션 종료
                        self.close_session(session_id)
                        
                        return True
                    else:
                        logging.error(f"❌ 두 번째 답변 실패: {session_id}")
                else:
                    logging.error(f"❌ 두 번째 질문 제출 실패: {session_id}")
            elif first_response and first_response.get('type') == 'answer_requested':
                logging.info(f"⏳ 첫 번째 명료화 완료 후 답변 요청됨 - 답변 완료 대기")
                # answer.completed가 올 때까지 다시 대기
                first_final_response = await self.wait_for_response(first_request_id)
                if first_final_response and first_final_response.get('type') == 'answer_completed':
                    logging.info(f"✅ 첫 번째 최종 답변 완료: {first_final_response.get('type', 'unknown')}")
                    
                    # 세션에 응답 추가
                    if session:
                        session.add_response(1, first_final_response)
                    
                    # AI 답변에서 추가 질문을 위한 정보 추출
                    first_answer_data = first_final_response.get('data', {})
                    first_answer = first_answer_data.get('answer', '')
                    
                    # 잠시 대기 (ObserverAgent가 요약을 생성할 시간)
                    await asyncio.sleep(2)
                    
                    # AI 답변과 첫 번째 질문을 고려한 두 번째 질문 생성
                    second_question = await self._generate_follow_up_question(
                        first_question=first_question,
                        first_answer=first_answer,
                        persona=self._generate_session_student_persona(session_id)
                    )
                    
                    logging.info(f"❓ 두 번째 질문 (AI 생성): {second_question}")
                    
                    second_request_id = await self._submit_question_with_client(
                        question=second_question,
                        topic=topic,
                        session_id=session_id
                    )
                    
                    if second_request_id:
                        logging.info(f"📤 두 번째 질문 제출 완료: {second_request_id}")
                        
                        # 두 번째 질문에 대한 응답 대기 (공유 pubsub 사용)
                        second_response = await self.wait_for_response(second_request_id)
                        
                        if second_response:
                            logging.info(f"✅ 두 번째 답변 완료: {second_response.get('type', 'unknown')}")
                            # transcript 출력
                            self._print_transcript(second_request_id, header=f"\n🧾 두 번째 요청 transcript ({second_request_id})")
                            
                            # 세션에 응답 추가
                            if session:
                                session.add_response(2, second_response)
                            
                            # 세션 요약 출력
                            session_summary = session.get_session_summary()
                            logging.info(f"📊 세션 요약: {session_summary}")
                            
                            logging.info(f"🔄 세션 컨텍스트 테스트 완료: {session_id}")
                            
                            # 세션 종료
                            self.close_session(session_id)
                            
                            return True
                        else:
                            logging.error(f"❌ 두 번째 답변 실패: {session_id}")
                    else:
                        logging.error(f"❌ 두 번째 질문 제출 실패: {session_id}")
                else:
                    logging.error(f"❌ 첫 번째 최종 답변 실패: {session_id}")
            else:
                logging.error(f"❌ 첫 번째 답변 실패: {session_id}")
        
        return False
    

    
    async def _generate_follow_up_question(self, first_question: str, first_answer: str, persona: Dict[str, Any]) -> str:
        """AI 답변과 첫 번째 질문을 고려하여 추가 질문을 생성합니다."""
        try:
            if not OPENAI_AVAILABLE:
                # OpenAI가 없으면 기본 추가 질문 반환
                return "그럼 등차수열과 등비수열의 차이점은 무엇인가요?"
            
            # OpenAI를 사용하여 추가 질문 생성
            client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            prompt = f"""
            다음은 학생의 첫 번째 질문과 AI의 답변입니다.
            학생이 추가로 물어볼 만한 자연스러운 질문을 생성해주세요.
            
            첫 번째 질문: {first_question}
            AI 답변: {first_answer[:500]}...
            
            학생 페르소나: {persona.get('name', '학생')} - {persona.get('style', '')}
            
            요구사항:
            1. 첫 번째 질문과 AI 답변을 자연스럽게 이어가는 질문
            2. 학생의 이해 수준을 높일 수 있는 질문
            3. 한국어로 자연스럽게 표현
            4. 20자 이내로 간결하게
            
            추가 질문:
            """
            
            response = await client.chat.completions.create(
                model="gpt-5-mini",
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=500
            )
            
            follow_up_question = response.choices[0].message.content.strip()
            
            # 따옴표나 불필요한 문자 제거
            follow_up_question = follow_up_question.replace('"', '').replace("'", "").strip()
            
            logging.info(f"🤖 AI가 생성한 추가 질문: {follow_up_question}")
            return follow_up_question
            
        except Exception as e:
            logging.error(f"추가 질문 생성 실패: {e}")
            # 기본 추가 질문 반환
            return "그럼 등차수열과 등비수열의 차이점은 무엇인가요?"
        
    async def _process_clarification_with_client(self, client: redis.Redis, clarification_data: Dict[str, Any], request_id: str, persona: Dict[str, Any]) -> str:
        """특정 Redis 클라이언트를 사용한 명료화 과정 처리"""
        logging.info(f"�� {request_id} 명료화 과정 시작")
        
        # 명료화 질문 추출
        clarification_question = clarification_data.get('question', '')
        clarification_field = clarification_data.get('field', '')
        
        logging.info(f"❓ {request_id} 명료화 질문: {clarification_question}")
        logging.info(f"🎯 {request_id} 명료화 필드: {clarification_field}")
        
        # 자동 명료화 답변 생성 (실제로는 사용자 입력을 받아야 함)
        clarification_response = await self._generate_clarification_response(clarification_field, clarification_question, persona)
        logging.info(f"💭 {request_id} 생성된 명료화 답변: {clarification_response}")
        
        # 명료화 답변 전송
        response_payload = {
            "request_id": request_id,
            "field": clarification_field,
            "message": clarification_response,  # 백엔드와 일치하도록 'response' → 'message'
            "timestamp": datetime.now().isoformat()
        }
        
        await client.publish(USER_CLARIFICATION, json.dumps(response_payload, ensure_ascii=False))
        logging.info(f"📤 {request_id} 명료화 답변 전송 완료: {clarification_response}")
        
        return clarification_response

    async def _start_message_receiver(self):
        """Redis 메시지 수신 루프 - 웹 백엔드와 동일한 패턴"""
        logging.info("📡 메시지 수신 루프 시작")
        self.receiver_running = True
        
        try:
            while self.receiver_running:
                try:
                    # pubsub 연결 상태 확인
                    if not hasattr(self, 'pubsub') or self.pubsub is None:
                        logging.warning("⚠️ PubSub 연결이 설정되지 않음. 메시지 수신을 건너뜁니다.")
                        await asyncio.sleep(1.0)
                        continue
                    
                    # 메시지 수신을 락으로 동기화하여 동시 수신 방지
                    async with self.message_receive_lock:
                        # Redis에서 메시지 수신 (블로킹)
                        message = await self.pubsub.get_message(timeout=1.0)
                    
                    if message is None:
                        continue
                    
                    if message['type'] != 'message':
                        continue
                    
                    # 메시지 파싱
                    channel = message['channel']
                    data = message['data']
                    
                    logging.info(f"📨 메시지 수신: channel={channel}, data_length={len(data) if data else 0}")
                    
                    try:
                        # Redis에서 이미 decode_responses=True로 설정되어 있어서 문자열로 받음
                        payload = json.loads(data)
                    except json.JSONDecodeError:
                        logging.warning(f"잘못된 JSON 형식: {data}")
                        continue
                    
                    # request_id 추출
                    request_id = payload.get('request_id')
                    if not request_id:
                        logging.warning(f"request_id 없음: {payload}")
                        continue
                    
                    # 채널별 메시지 처리
                    if channel == USER_CLARIFICATION:
                        # 명료화 응답 처리
                        logging.info(f"📝 명료화 응답 수신: {request_id}")
                        if request_id in self.response_queues:
                            await self.response_queues[request_id].put({
                                'channel': channel,
                                'payload': payload,
                                'type': 'clarification_response'
                            })
                            logging.debug(f"📨 {request_id} 명료화 응답을 응답 큐에 전달")
                    else:
                        # 기타 채널 메시지 처리
                        if request_id in self.response_queues:
                            await self.response_queues[request_id].put({
                                'channel': channel,
                                'payload': payload
                            })
                            logging.debug(f"📨 {request_id} 응답 큐에 메시지 전달: {channel}")
                        else:
                            logging.debug(f"⚠️ {request_id} 응답 큐를 찾을 수 없음")
                        
                    # 메시지 파싱
                    channel = message['channel']
                    data = message['data']
                    
                    logging.info(f"📨 메시지 수신: channel={channel}, data_length={len(data) if data else 0}")
                    
                    try:
                        # Redis에서 이미 decode_responses=True로 설정되어 있어서 문자열로 받음
                        payload = json.loads(data)
                    except json.JSONDecodeError:
                        logging.warning(f"잘못된 JSON 형식: {data}")
                        continue
                    
                    # request_id 추출
                    request_id = payload.get('request_id')
                    if not request_id:
                        logging.warning(f"request_id 없음: {payload}")
                        continue
                    
                    # 채널별 상세 로그 및 transcript 저장
                    if channel == CLARIFICATION_REQUESTED:
                        msg = payload.get('message') or payload.get('question') or payload
                        logging.info(f"🟡 [{request_id}] 명료화 요청: {str(msg)[:120]}...")
                        self._add_transcript_entry(request_id, f"[명료화 요청] {msg}")
                    elif channel == CLARIFICATION_QUESTION:
                        q = payload.get('question') or payload
                        field = payload.get('field') or payload.get('clarification_field', '')
                        logging.info(f"❓ [{request_id}] 명료화 질문({field}): {str(q)[:120]}...")
                        self._add_transcript_entry(request_id, f"[명료화 질문:{field}] {q}")
                    elif channel == USER_CLARIFICATION:
                        resp = payload.get('message') or payload.get('response') or payload
                        field = payload.get('field', '')
                        logging.info(f"💬 [{request_id}] 학생 응답({field}): {str(resp)[:120]}...")
                        self._add_transcript_entry(request_id, f"[학생 응답:{field}] {resp}")
                    elif channel == CLARIFICATION_COMPLETED:
                        logging.info(f"✅ [{request_id}] 명료화 완료")
                        self._add_transcript_entry(request_id, "[명료화 완료]")
                    elif channel == ANSWER_REQUESTED:
                        logging.info(f"📝 [{request_id}] 답변 요청")
                        self._add_transcript_entry(request_id, "[답변 요청]")
                    elif channel == ANSWER_COMPLETED:
                        answer = payload.get('answer') or payload
                        logging.info(f"🟢 [{request_id}] 최종 답변 수신 (길이={len(answer) if isinstance(answer, str) else 'N/A'})")
                        self._add_transcript_entry(request_id, f"[최종 답변] {answer if isinstance(answer, str) else json.dumps(payload)[:400]}...")
                    elif channel == CONVERSATION_SUMMARY_UPDATED:
                        summary = payload.get('summary', '')
                        logging.info(f"🧾 [{request_id}] 대화 요약: {summary[:120]}...")
                        self._add_transcript_entry(request_id, f"[대화 요약] {summary}")
                    elif channel == STUDENT_STATUS_UPDATED:
                        logging.info(f"📊 [{request_id}] 학생 상태 업데이트 수신")
                        self._add_transcript_entry(request_id, f"[학생 상태] {json.dumps(payload, ensure_ascii=False)[:200]}...")
                    elif channel == SESSION_TITLE_UPDATED:
                        title = payload.get('session_title', '')
                        logging.info(f"🏷️ [{request_id}] 세션명 업데이트: {title}")
                        self._add_transcript_entry(request_id, f"[세션명] {title}")

                except Exception as e:
                    if self.receiver_running:
                        logging.error(f"메시지 수신 중 오류: {e}")
                        await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            logging.info("📡 메시지 수신 루프 취소됨")
        except Exception as e:
            logging.error(f"📡 메시지 수신 루프 오류: {e}")
        finally:
            self.receiver_running = False
            logging.info("📡 메시지 수신 루프 종료")

async def main():
    """메인 함수 - 테스트 모드와 질문 수를 외부에서 주입 가능"""
    import argparse
    
    # 명령행 인수 파싱
    parser = argparse.ArgumentParser(description='고급 테스트 에이전트 - 다양한 테스트 모드 지원')
    parser.add_argument('--mode', '-m', 
                       choices=['original', 'persona', 'combined'], 
                       default='combined',
                       help='테스트 모드 선택 (기본값: combined)')
    parser.add_argument('--questions', '-q', 
                       type=int, 
                       default=5,
                       help='질문 수 (기본값: 5)')
    parser.add_argument('--redis-url', '-r',
                       default='redis://localhost:6379',
                       help='Redis URL (기본값: redis://localhost:6379)')
    
    args = parser.parse_args()
    
    # 테스트 설정 출력
    print(f"\n🎯 테스트 설정:")
    print(f"   모드: {args.mode}")
    print(f"   질문 수: {args.questions}")
    print(f"   Redis URL: {args.redis_url}")
    
    tester = AdvancedTester(args.redis_url)
    
    try:
        await tester.connect()
        
        # 초기 세션 정보 표시
        initial_session = tester.get_current_session_info()
        logging.info(f"🎯 테스트 시작 - 초기 턴: {initial_session['turn_count']}")
        
        # 선택된 테스트 모드로 실행
        results = await tester.run_test(
            test_mode=args.mode, 
            num_questions=args.questions
        )
        
        # 세션 컨텍스트 테스트 추가
        logging.info("\n🔄 세션 컨텍스트 테스트 시작...")
        try:
            await tester.test_session_context("수열")
            logging.info("✅ 세션 컨텍스트 테스트 완료")
        except Exception as e:
            logging.error(f"❌ 세션 컨텍스트 테스트 실패: {e}")
        
        # 결과 출력
        logging.info("\n📊 테스트 결과 요약:")
        total_completed = 0
        total_failed = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logging.info(f"❌ 학생 {i+1}: 처리 실패 - {result}")
                total_failed += 1
            else:
                student_id = result.get('student_id', f'student_{i+1}')
                completed = result.get('completed', False)
                
                if completed:
                    total_completed += 1
                    status = "✅ 완료"
                else:
                    total_failed += 1
                    status = "⚠️ 미완료"
                
                if result.get('type') == 'original':
                    # 원문 질문 결과
                    logging.info(f"{status} {student_id}: 원문 질문 - 직접 답변")
                else:
                    # 페르소나 질문 결과
                    topic = result.get('topic', 'N/A')
                    persona = result.get('persona', 'N/A')
                    clarification_status = "명료화" if result.get('clarification') else "직접 답변"
                    logging.info(f"{status} {student_id}: {topic} - {persona} - {clarification_status}")
                    
                    if result.get('clarification'):
                        logging.info(f"   🔍 명료화 응답: {result.get('clarification_response', 'N/A')}")
                
                # 오류가 있는 경우 표시
                if result.get('error'):
                    logging.warning(f"   ⚠️ 오류: {result['error']}")
        
        # 최종 통계
        logging.info(f"\n📈 최종 통계:")
        logging.info(f"   총 질문: {len(results)}개")
        logging.info(f"   완료: {total_completed}개")
        logging.info(f"   미완료: {total_failed}개")
        logging.info(f"   완료율: {(total_completed/len(results)*100):.1f}%" if results else "0%")
        
        # 최종 세션 정보 표시
        final_session = tester.get_current_session_info()
        logging.info(f"\n🏁 테스트 완료 - 총 턴: {final_session['turn_count']}")
        
        # 새로운 세션 시작 옵션 (주석 처리)
        # tester.start_new_session()
        # logging.info("🔄 새로운 테스트 세션 준비 완료")
        
        # 모든 테스트 완료 후 연결 해제
        await tester.disconnect()
                
    except Exception as e:
        logging.error(f"❌ 테스트 실행 중 오류: {e}")
        # 오류 발생 시에도 연결 해제
        await tester.disconnect()
    finally:
        # finally 블록에서는 연결 해제하지 않음
        pass

if __name__ == "__main__":
    asyncio.run(main())
