#!/usr/bin/env python3
"""
명료화 질문 처리 핸들러
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ClarificationHandler:
    """명료화 질문 처리 핸들러"""
    
    def __init__(self, persona_manager):
        """초기화"""
        self.persona_manager = persona_manager
        self.current_persona = None
        logger.info("🔧 ClarificationHandler 초기화 완료")
    
    def set_current_persona(self, persona: Dict[str, Any]):
        """현재 페르소나 설정"""
        self.current_persona = persona
        logger.info(f"🎭 현재 페르소나 설정: {persona.get('name', 'Unknown')}")
    
    async def handle_clarification_question(self, data: Dict[str, Any]) -> str:
        """명료화 질문에 대한 응답 생성"""
        try:
            field = data.get('field', '')
            question = data.get('question', '')
            
            logger.info(f"❓ 명료화 질문 처리: {field} - {question[:50]}...")
            
            # 기본 응답 생성
            response = self._generate_basic_response(field)
            
            logger.info(f"✅ 명료화 응답 생성 완료: {response[:50]}...")
            return response
            
        except Exception as e:
            logger.error(f"❌ 명료화 응답 생성 실패: {e}")
            return "죄송합니다. 잘 모르겠어요."
    
    def _generate_basic_response(self, field: str) -> str:
        """필드별 기본 응답 생성"""
        field_responses = {
            '질문_1': [
                "아, 그런 거였군요! 제가 잘못 이해했네요.",
                "아, 맞습니다! 그 부분을 놓쳤어요.",
                "아, 그렇구나! 이제 이해했어요."
            ],
            '질문_2': [
                "그 부분은 아직 제대로 모르겠어요.",
                "그건 좀 어려워서 잘 모르겠어요.",
                "그 부분은 배우지 못했어요."
            ],
            '질문_3': [
                "결과는 공식 형태로 알고 싶어요.",
                "단계별로 설명해주시면 좋겠어요.",
                "예시와 함께 설명해주세요."
            ]
        }
        
        import random
        responses = field_responses.get(field, ["더 자세히 설명해주세요."])
        return random.choice(responses)
        
    def generate_clarification_response(self, clarification_data: Dict[str, Any], persona: Dict[str, Any]) -> str:
        """페르소나 기반 명료화 응답 생성 - 성공한 심플 테스터 로직"""
        try:
            field = clarification_data.get('field', '')
            question = clarification_data.get('question', '')
            
            logger.info(f"🎭 페르소나 기반 명료화 응답 생성: {persona.get('name', 'Unknown')}")
            logger.info(f"   필드: {field}")
            logger.info(f"   질문: {question[:50]}...")
            
            # 페르소나별 응답 스타일 적용
            if persona.get('style') == 'formal':
                response = f"네, {field}에 대해 더 자세히 알고 싶습니다. {question}"
            elif persona.get('style') == 'casual':
                response = f"아, 그 부분이 궁금해요! {question}"
            elif persona.get('style') == 'enthusiastic':
                response = f"와! 그거 정말 궁금했어요! {question}"
            else:
                # 기본 응답
                response = self._generate_basic_response(field)
            
            logger.info(f"✅ 페르소나 응답 생성 완료: {response[:50]}...")
            return response
            
        except Exception as e:
            logger.error(f"❌ 페르소나 기반 응답 생성 실패: {e}")
            return self._generate_basic_response(field)
