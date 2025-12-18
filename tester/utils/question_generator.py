"""
질문 생성 유틸리티 - 수학 주제별 질문 생성
"""

import random
import logging
from typing import Dict, Any, List, Optional
from tester.personas.student_personas import MATH_TOPICS

logger = logging.getLogger(__name__)

class QuestionGenerator:
    """수학 질문 생성기"""
    
    def __init__(self):
        self.math_topics = MATH_TOPICS
        self.question_templates = self._init_question_templates()
        
    def _init_question_templates(self) -> Dict[str, List[str]]:
        """질문 템플릿 초기화"""
        return {
            "수열": [
                "등차수열의 일반항을 구하는 방법이 뭔가요?",
                "등비수열의 합을 구하는 공식이 뭔가요?",
                "수열의 극한값을 어떻게 구하나요?",
                "피보나치 수열의 일반항을 구할 수 있나요?",
                "수열의 수렴성을 판단하는 방법이 뭔가요?",
                "등차수열과 등비수열의 차이점이 뭔가요?",
                "수열의 일반항을 구하는 과정을 설명해주세요",
                "수열의 합을 구할 때 주의할 점이 뭔가요?"
            ],
            "수열의합": [
                "등차수열의 합을 구하는 공식이 뭔가요?",
                "등비수열의 합을 구하는 방법을 알려주세요",
                "시그마 기호를 사용해서 합을 구하는 방법이 뭔가요?",
                "무한급수의 합을 구할 수 있나요?",
                "부분합을 이용해서 합을 구하는 방법이 뭔가요?",
                "수열의 합을 구할 때 공차나 공비를 어떻게 찾나요?",
                "복잡한 수열의 합을 구하는 전략이 뭔가요?",
                "수열의 합과 일반항의 관계를 설명해주세요"
            ],
            "점화식": [
                "점화식을 일반항으로 바꾸는 방법이 뭔가요?",
                "선형점화식과 비선형점화식의 차이가 뭔가요?",
                "점화식의 초기값을 어떻게 설정하나요?",
                "점화식을 푸는 여러 방법이 있나요?",
                "점화식의 해가 유일한지 어떻게 확인하나요?",
                "점화식을 이용해서 수열을 정의하는 방법이 뭔가요?",
                "복잡한 점화식을 단순화하는 방법이 있나요?",
                "점화식의 안정성을 판단하는 기준이 뭔가요?"
            ],
            "수학적귀납법": [
                "수학적 귀납법의 원리를 설명해주세요",
                "귀납 가정을 어떻게 설정하나요?",
                "기초 단계와 귀납 단계를 구분하는 방법이 뭔가요?",
                "강한 귀납법과 약한 귀납법의 차이가 뭔가요?",
                "귀납법을 사용할 때 주의할 점이 뭔가요?",
                "귀납법으로 증명할 수 있는 문제의 특징이 뭔가요?",
                "귀납법과 다른 증명 방법의 차이점이 뭔가요?",
                "귀납법을 이용해서 공식을 유도하는 과정을 보여주세요"
            ]
        }
        
    def get_random_topic_and_difficulty(self) -> tuple[str, str]:
        """랜덤 주제와 난이도 반환"""
        topic = random.choice(self.math_topics)
        difficulties = ["naive", "basic", "intermediate", "advanced", "olympiad"]
        difficulty = random.choice(difficulties)
        return topic, difficulty
        
    def generate_question(self, topic: str, difficulty: str = "basic") -> str:
        """주제와 난이도에 따른 질문 생성"""
        if topic not in self.question_templates:
            topic = random.choice(self.math_topics)
            
        base_questions = self.question_templates[topic]
        question = random.choice(base_questions)
        
        # 난이도에 따른 질문 수정
        modified_question = self._modify_by_difficulty(question, difficulty)
        
        logger.info(f"📝 질문 생성: {topic} ({difficulty}) - {modified_question}")
        return modified_question
        
    def _modify_by_difficulty(self, question: str, difficulty: str) -> str:
        """난이도에 따른 질문 수정"""
        if difficulty == "naive":
            # 기초 개념 질문
            question = question.replace("방법이 뭔가요?", "개념을 설명해주세요")
            question = question.replace("공식이 뭔가요?", "정의를 알려주세요")
        elif difficulty == "basic":
            # 기본 응용 질문 (변경 없음)
            pass
        elif difficulty == "intermediate":
            # 핵심 원리 질문
            question = question.replace("방법이 뭔가요?", "원리를 설명해주세요")
            question = question.replace("공식이 뭔가요?", "증명 과정을 보여주세요")
        elif difficulty == "advanced":
            # 조건/예외 질문
            question = question.replace("방법이 뭔가요?", "모든 경우에 적용되는 방법인가요?")
            question = question.replace("공식이 뭔가요?", "이 공식이 성립하지 않는 경우가 있나요?")
        elif difficulty == "olympiad":
            # 증명 관점 질문
            question = question.replace("방법이 뭔가요?", "엄밀하게 증명해주세요")
            question = question.replace("공식이 뭔가요?", "이 공식의 최적성을 증명해주세요")
            
        return question
        
    def generate_question_by_method(self, topic: str, method: str) -> str:
        """특정 방법에 따른 질문 생성"""
        method_templates = {
            "개념이해": [
                f"{topic}의 정의가 뭔가요?",
                f"{topic}의 핵심 아이디어를 설명해주세요",
                f"{topic}를 이해하는데 중요한 점이 뭔가요?"
            ],
            "비교질문": [
                f"{topic}와 다른 개념의 차이점이 뭔가요?",
                f"{topic}와 유사한 개념이 있나요?",
                f"{topic}를 다른 방법으로 설명할 수 있나요?"
            ],
            "응용질문": [
                f"{topic}를 실제로 어떻게 사용하나요?",
                f"{topic}의 활용 예시를 들어주세요",
                f"{topic}를 다른 문제에 적용하는 방법이 뭔가요?"
            ],
            "증명질문": [
                f"{topic}의 증명 과정을 보여주세요",
                f"{topic}가 성립하는 이유가 뭔가요?",
                f"{topic}의 증명에서 핵심 아이디어가 뭔가요?"
            ]
        }
        
        if method in method_templates:
            return random.choice(method_templates[method])
        else:
            return self.generate_question(topic)
            
    def generate_situation_based_question(self, topic: str, situation: str) -> str:
        """상황 기반 질문 생성"""
        situation_templates = {
            "시험": [
                f"시험에서 {topic} 문제를 풀 때 주의할 점이 뭔가요?",
                f"시험 시간이 부족할 때 {topic} 문제를 어떻게 빠르게 풀 수 있나요?",
                f"시험에서 {topic} 문제를 틀리지 않는 팁이 있나요?"
            ],
            "숙제": [
                f"숙제로 {topic} 문제를 풀 때 도움이 되는 방법이 뭔가요?",
                f"{topic} 숙제를 효율적으로 풀 수 있는 전략이 뭔가요?",
                f"숙제에서 {topic} 문제를 틀렸을 때 어떻게 복습하나요?"
            ],
            "실생활": [
                f"실생활에서 {topic}가 어떻게 사용되나요?",
                f"{topic}를 이용해서 실생활 문제를 푸는 예시가 있나요?",
                f"일상생활에서 {topic}의 원리를 발견할 수 있나요?"
            ]
        }
        
        if situation in situation_templates:
            return random.choice(situation_templates[situation])
        else:
            return self.generate_question(topic)
            
    def generate_connection_question(self, topic1: str, topic2: str) -> str:
        """두 주제 간의 연결 질문 생성"""
        connection_templates = [
            f"{topic1}와 {topic2}의 관계를 설명해주세요",
            f"{topic1}를 이용해서 {topic2}를 이해할 수 있나요?",
            f"{topic1}와 {topic2}를 함께 사용하는 문제가 있나요?",
            f"{topic1}에서 배운 내용이 {topic2}에 어떻게 도움이 되나요?"
        ]
        
        return random.choice(connection_templates)
        
    def get_available_topics(self) -> List[str]:
        """사용 가능한 수학 주제 반환"""
        return self.math_topics.copy()
        
    def get_available_methods(self) -> List[str]:
        """사용 가능한 질문 방법 반환"""
        return ["개념이해", "비교질문", "응용질문", "증명질문"]
        
    def get_available_situations(self) -> List[str]:
        """사용 가능한 상황 반환"""
        return ["시험", "숙제", "실생활"]
