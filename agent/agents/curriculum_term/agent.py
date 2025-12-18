"""
교과과정 용어 에이전트
질문을 분석하여 교과과정에 맞는 적절한 용어를 제안하고, 최종 응답을 검증합니다.
"""

import asyncio
import logging
from typing import Dict, Any, List

from ..base_agent import BaseAgent, Task
from .tools.curriculum_term_tool import CurriculumTermTool
from ..common.event_bus import (
    subscribe_and_listen,
    QUESTION_SUBMITTED,
    CURRICULUM_TERMS_SUGGESTED,
    publish_event,
)


class CurriculumTermAgent(BaseAgent):
    """교과과정 용어 분석 및 제안 에이전트"""
    
    def __init__(self):
        super().__init__(
            name="curriculum_term",
            role="교과과정 용어 분석 및 제안",
            system_prompt="""당신은 한국 고등학교 수학 교과과정 전문가입니다.

역할:
1. 질문을 분석하여 필요한 수학 개념 파악
2. 교과과정에 맞는 적절한 용어 제안
3. 고급 용어를 교과과정 수준으로 변환
4. 최종 응답의 용어 검증

교과과정 수준:
- 고등학교 1학년: 수와 연산, 방정식과 부등식, 도형의 방정식
- 고등학교 2학년: 집합과 명제, 함수, 수열, 확률과 통계
- 고등학교 3학년: 미적분, 기하, 확률과 통계 심화

용어 제안 원칙:
- 학생이 이해할 수 있는 수준
- 교과서에서 사용하는 표준 용어
- 복잡한 개념은 단계별로 분해

수식 표기 규칙:
- 모든 수학 수식은 LaTeX 형식으로 작성합니다.
- 인라인 수식: $x^2 + 2x + 1 = 0$
- 블록 수식: $$f(x) = ax^2 + bx + c$$
- 용어 제안이나 분석 결과에 수식이 포함될 경우 반드시 LaTeX로 작성합니다.
- 예시: "이차함수 $f(x) = x^2 + 2x + 1$의 꼭짓점 공식 $x = -\\frac{b}{2a}$를 사용합니다" """
        )
        self.curriculum_tool = CurriculumTermTool()
        self.logger = logging.getLogger(__name__)
        
    async def analyze_question_and_suggest_terms(self, question: str, context: str = "") -> Dict[str, Any]:
        """질문 분석 및 용어 제안"""
        try:
            self.logger.info("질문 분석 및 용어 제안 시작")
            
            # RAG 검색으로 교과과정 용어 분석
            analysis_result = await self.curriculum_tool.analyze_question(question)
            
            if analysis_result.get("success"):
                suggested_terms = analysis_result.get("suggested_terms", [])
                concept_level = analysis_result.get("concept_level", "고등학교 1학년")
                avoid_terms = analysis_result.get("avoid_terms", [])
                
                # 교과과정 관련 정보 추가
                curriculum_info = analysis_result.get("curriculum_info", {})
                achievement_standards = curriculum_info.get("achievement_standards", [])
                textbook_content = curriculum_info.get("textbook_content", [])
                learning_notes = curriculum_info.get("learning_notes", [])
                
                self.logger.info(f"용어 제안 완료: {len(suggested_terms)}개 용어, 수준: {concept_level}")
                
                return {
                    "success": True,
                    "suggested_terms": suggested_terms,
                    "concept_level": concept_level,
                    "avoid_terms": avoid_terms,
                    "analysis": analysis_result.get("analysis", ""),
                    "recommendations": analysis_result.get("recommendations", []),
                    # 교과과정 정보 추가
                    "achievement_standards": achievement_standards,  # 성취기준
                    "textbook_content": textbook_content,          # 교과서 내용
                    "learning_notes": learning_notes,             # 유의점
                    "curriculum_context": {
                        "subject": curriculum_info.get("subject", ""),
                        "grade_level": curriculum_info.get("grade_level", ""),
                        "domain": curriculum_info.get("domain", ""),
                        "achievement_code": curriculum_info.get("achievement_code", "")
                    }
                }
            else:
                self.logger.warning("질문 분석 실패")
                return {
                    "success": False,
                    "error": analysis_result.get("error", "알 수 없는 오류")
                }
                
        except Exception as e:
            self.logger.error(f"질문 분석 오류: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # 용어 검증 기능 제거(요청에 따라 비활성화)
        
    async def run_subscriber(self):
        """이벤트 구독 및 처리 (비활성화)"""
        # 교과과정 용어 에이전트가 비활성화되어 있음
        self.logger.info("교과과정 용어 에이전트 비활성화됨")
        # 무한 대기로 에이전트 유지
        while True:
            await asyncio.sleep(3600)  # 1시간마다 체크
        
    async def process_task(self, task: Task) -> Dict[str, Any]:
        """작업 처리 (BaseAgent 요구사항 충족용)"""
        try:
            self.logger.info(f"교과과정 용어 에이전트 작업 처리: {task.description}")
            
            if task.description == "analyze_question":
                return await self.analyze_question_and_suggest_terms(
                    task.metadata.get("question", ""),
                    task.metadata.get("context", "")
                )
            
            else:
                self.logger.warning(f"알 수 없는 작업 설명: {task.description}")
                return {"success": False, "error": f"Unknown task description: {task.description}"}
                
        except Exception as e:
            self.logger.error(f"교과과정 용어 에이전트 작업 처리 오류: {e}")
            return {"success": False, "error": str(e)}
            
    async def execute(self, task: Task) -> Dict[str, Any]:
        """에이전트 실행 (이벤트 기반)"""
        return await self.process_task(task)
