"""
페르소나 관리 클래스 - 학생 페르소나 관리 및 스타일 적용
"""

import random
import logging
from typing import Dict, Any, List, Optional
from tester.personas.student_personas import STUDENT_PERSONAS, MATH_TOPICS

logger = logging.getLogger(__name__)

class PersonaManager:
    """학생 페르소나 관리"""
    
    def __init__(self):
        self.personas = STUDENT_PERSONAS
        self.math_topics = MATH_TOPICS
        self.current_persona: Optional[Dict[str, Any]] = None
        
    def get_random_persona(self) -> Dict[str, Any]:
        """랜덤 페르소나 선택"""
        persona = random.choice(self.personas)
        self.current_persona = persona
        logger.info(f"🎭 페르소나 선택: {persona['name']} ({persona['style']})")
        return persona
        
    def get_persona_by_id(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """ID로 페르소나 찾기"""
        for persona in self.personas:
            if persona['id'] == persona_id:
                self.current_persona = persona
                return persona
        return None
        
    def get_persona_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """이름으로 페르소나 찾기"""
        for persona in self.personas:
            if persona['name'] == name:
                self.current_persona = persona
                return persona
        return None
        
    def apply_persona_style(self, question: str, persona: Dict[str, Any]) -> str:
        """페르소나 스타일을 질문에 적용"""
        style = persona.get('style', '')
        name = persona.get('name', '')
        
        # 페르소나별 스타일 적용
        if '모범학생' in name:
            return self._apply_model_student_style(question)
        elif '소심한 학생' in name:
            return self._apply_shy_student_style(question)
        elif '불안한 학생' in name:
            return self._apply_anxious_student_style(question)
        elif '자신감 있는 학생' in name:
            return self._apply_confident_student_style(question)
        elif '완벽주의자' in name:
            return self._apply_perfectionist_style(question)
        elif '호기심 많은 학생' in name:
            return self._apply_curious_student_style(question)
        elif '냉소적인 학생' in name:
            return self._apply_cynical_student_style(question)
        elif '비꼬는 학생' in name:
            return self._apply_sarcastic_student_style(question)
        else:
            return question
            
    def _apply_model_student_style(self, question: str) -> str:
        """모범학생 스타일 적용"""
        if not question.endswith('요'):
            question += '요'
        return question
        
    def _apply_shy_student_style(self, question: str) -> str:
        """소심한 학생 스타일 적용"""
        if not question.endswith('요'):
            question += '요'
        # 말끝 흐림 효과
        if random.random() < 0.3:
            question = question.rstrip('요') + '...요?'
        return question
        
    def _apply_anxious_student_style(self, question: str) -> str:
        """불안한 학생 스타일 적용"""
        if not question.endswith('요'):
            question += '요'
        # 확인성 질문 추가
        if random.random() < 0.4:
            question += ' 맞나요?'
        return question
        
    def _apply_confident_student_style(self, question: str) -> str:
        """자신감 있는 학생 스타일 적용"""
        # 확신에 찬 톤
        if random.random() < 0.3:
            question = question.replace('요', '요!')
        return question
        
    def _apply_perfectionist_style(self, question: str) -> str:
        """완벽주의자 스타일 적용"""
        if not question.endswith('요'):
            question += '요'
        # 정확성 강조
        if random.random() < 0.4:
            question = question.replace('뭔가요', '정확히 무엇인가요')
        return question
        
    def _apply_curious_student_style(self, question: str) -> str:
        """호기심 많은 학생 스타일 적용"""
        if not question.endswith('요'):
            question += '요'
        # 추가 궁금증
        if random.random() < 0.3:
            question += ' 그리고 어떻게 해요?'
        return question
        
    def _apply_cynical_student_style(self, question: str) -> str:
        """냉소적인 학생 스타일 적용"""
        # 냉소적 톤
        if random.random() < 0.4:
            question = question.replace('요', '요...')
        return question
        
    def _apply_sarcastic_student_style(self, question: str) -> str:
        """비꼬는 학생 스타일 적용"""
        # 비꼬는 톤
        if random.random() < 0.3:
            question = question.replace('요', '요?')
        return question
        
    def get_math_topic(self) -> str:
        """수학 주제 랜덤 선택"""
        return random.choice(self.math_topics)
        
    def get_difficulty_level(self) -> str:
        """난이도 레벨 랜덤 선택"""
        levels = ['naive', 'basic', 'intermediate', 'advanced', 'olympiad']
        return random.choice(levels)
        
    def get_persona_combination(self) -> Dict[str, Any]:
        """페르소나와 수학 주제 조합 반환"""
        persona = self.get_random_persona()
        topic = random.choice(self.math_topics)
        difficulties = ["naive", "basic", "intermediate", "advanced", "olympiad"]
        difficulty = random.choice(difficulties)
        
        return {
            "persona": persona,
            "topic": topic,
            "difficulty": difficulty
        }
        
    def get_all_personas(self) -> List[Dict[str, Any]]:
        """모든 페르소나 반환"""
        return self.personas.copy()
        
    def get_personas_by_category(self, category: str) -> List[Dict[str, Any]]:
        """카테고리별 페르소나 반환"""
        # 카테고리별 분류 (간단한 키워드 매칭)
        if '학습' in category:
            return [p for p in self.personas if '학습' in p.get('style', '')]
        elif '감정' in category:
            return [p for p in self.personas if any(word in p.get('style', '') for word in ['확신', '불안', '좌절', '흥미'])]
        elif '수준' in category:
            return [p for p in self.personas if any(word in p.get('style', '') for word in ['초보', '중급', '고급', '영재'])]
        else:
            return self.personas
