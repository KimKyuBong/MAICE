"""
리팩토링된 답변 생성 에이전트 - LLM 툴 사용
"""

import logging
import asyncio
from typing import Dict, Any
from datetime import datetime

from agents.base_agent import BaseAgent
from agents.common.llm_tool import SpecializedLLMTool, PromptTemplate, LLMConfig
from agents.common.event_bus import (
    publish_event,
    subscribe_and_listen,
    AGENT_TO_AGENT
)
from utils.redis_streams_client import AgentRedisStreamsClient

logger = logging.getLogger(__name__)

class RefactoredAnswerGeneratorAgent(BaseAgent):
    """
    리팩토링된 답변 생성 에이전트 - LLM 툴 사용
    """
    
    def __init__(self):
        super().__init__(
            name="AnswerGeneratorAgent",
            role="수학 교육 답변 생성 전문가",
            system_prompt="수학 교육 전문가입니다."
        )
        
        # LLM 툴 초기화
        self.llm_tool = SpecializedLLMTool.create_answer_generator_tool()
        
        # Redis Streams 클라이언트
        self.streams_client = None
        
        # 프롬프트 템플릿
        self.answer_template = PromptTemplate(
            system_prompt=self._build_system_prompt(),
            user_template=self._build_user_template()
        )
    
    async def initialize(self):
        """에이전트 초기화"""
        try:
            # Redis Streams 클라이언트 초기화
            self.streams_client = AgentRedisStreamsClient(self.name)
            await self.streams_client.initialize()
            
            # pub/sub 구독 시작
            asyncio.create_task(self.run_pubsub_subscriber())
            
            self.logger.info("✅ AnswerGeneratorAgent 초기화 완료")
            
        except Exception as e:
            self.logger.error(f"❌ AnswerGeneratorAgent 초기화 실패: {e}")
            raise
    
    async def cleanup(self):
        """에이전트 정리"""
        if self.streams_client:
            await self.streams_client.cleanup()
        self.logger.info("✅ AnswerGeneratorAgent 정리 완료")
    
    async def run_subscriber(self):
        """Redis Streams 기반으로 백엔드 메시지 수신"""
        self.logger.info("🚀 AnswerGeneratorAgent Streams 구독 시작")
        
        try:
            while True:
                try:
                    # Streams에서 메시지 수신
                    messages = await self.streams_client.read_from_backend_stream(count=1, block=1000)
                    
                    if messages:
                        for msg_id, fields in messages:
                            await self._process_answer_request(msg_id, fields)
                    
                except Exception as e:
                    self.logger.error(f"❌ Streams 메시지 처리 오류: {e}")
                    await asyncio.sleep(1)
                    
        except Exception as e:
            self.logger.error(f"❌ Streams 구독 오류: {e}")
            raise
    
    async def run_pubsub_subscriber(self):
        """pub/sub 메시지 구독"""
        async def message_handler(channel: str, data: Dict[str, Any]):
            try:
                message_type = data.get("type", "")
                target_agent = data.get("target_agent", "")
                
                if target_agent not in ["AnswerGeneratorAgent", "AnswerGenerator"]:
                    return
                
                if message_type in ["READY_FOR_ANSWER", "ready_for_answer"]:
                    await self.process_answer_generation_request(data)
                elif message_type in ["GENERATE_ANSWER", "generate_answer"]:
                    await self.process_answer_generation_request(data)
                    
            except Exception as e:
                self.logger.error(f"pub/sub 메시지 처리 오류: {e}")
        
        # AGENT_TO_AGENT 채널 구독
        from agents.common.event_bus import AGENT_TO_AGENT
        await subscribe_and_listen([AGENT_TO_AGENT], message_handler, self)
        self.logger.info("✅ AnswerGeneratorAgent pub/sub 구독 시작")
    
    async def process_answer_generation_request(self, payload: Dict[str, Any]):
        """답변 생성 요청 처리"""
        try:
            session_id = payload.get("session_id")
            question = payload.get("question", "")
            context = payload.get("context", "")
            classification_result = payload.get("classification_result", {})
            
            self.logger.info(f"🔍 답변 생성 요청: 세션 {session_id}, 질문: {question}")
            
            # 답변 생성
            result = await self._generate_answer(
                question=question,
                context=context,
                evaluation=classification_result,
                session_id=session_id
            )
            
            if result and result.get("educational_answer"):
                # 답변 결과를 Streams로 백엔드에 전송
                await self._send_answer_to_backend(session_id, result)
                
                # ObserverAgent에게 요약 요청 전송
                await self._trigger_observer_summary(session_id, question, result["educational_answer"], result)
                
                self.logger.info(f"✅ 답변 생성 및 전송 완료: 세션 {session_id}")
            else:
                self.logger.error(f"❌ 답변 생성 실패: 세션 {session_id}")
                
        except Exception as e:
            self.logger.error(f"❌ 답변 생성 요청 처리 오류: {e}")
    
    async def _generate_answer(self, question: str, context: str, evaluation: Dict[str, Any], session_id: int) -> Dict[str, Any]:
        """답변 생성 - LLM 툴 사용"""
        try:
            self.logger.info(f"답변 생성 시작: {question}...")
            
            # 분류 결과 확인
            knowledge_code = evaluation.get("knowledge_code", "K1")
            quality = evaluation.get("quality", "answerable")
            
            if quality != "answerable":
                return {
                    "educational_answer": f"죄송합니다. 이 질문은 현재 답변하기 어려운 상태입니다. ({quality})",
                    "knowledge_code": knowledge_code,
                    "answerability": quality
                }
            
            # 프롬프트 변수 준비
            variables = {
                "question": question,
                "knowledge_code": knowledge_code,
                "answerability": quality,
                "context": context if context else "없음"
            }
            
            # 스트리밍 설정으로 LLM 호출
            streaming_config = LLMConfig(
                max_tokens=2000,
                stream=True,
                timeout=60
            )
            
            # LLM 툴로 답변 생성
            result = await self.llm_tool.execute(
                prompt=self.answer_template,
                variables=variables,
                config_override=streaming_config
            )
            
            if not result["success"]:
                return {
                    "educational_answer": f"답변 생성 중 오류가 발생했습니다: {result['error']}",
                    "knowledge_code": knowledge_code,
                    "answerability": quality
                }
            
            # 스트리밍 처리
            if result.get("stream"):
                return await self._handle_streaming_response(result, session_id, knowledge_code, quality)
            else:
                return {
                    "educational_answer": result["content"],
                    "knowledge_code": knowledge_code,
                    "answerability": quality
                }
            
        except Exception as e:
            self.logger.error(f"답변 생성 오류: {e}")
            return {
                "educational_answer": f"답변 생성 중 오류가 발생했습니다: {str(e)}",
                "knowledge_code": evaluation.get("knowledge_code", "K1"),
                "answerability": evaluation.get("quality", "answerable")
            }
    
    async def _handle_streaming_response(self, result: Dict[str, Any], session_id: int, knowledge_code: str, quality: str) -> Dict[str, Any]:
        """스트리밍 응답 처리"""
        try:
            full_answer = ""
            chunk_count = 0
            
            # 스트리밍 데이터 처리 (실제 구현에서는 result에서 스트림 데이터를 처리)
            # 여기서는 간단히 전체 응답을 반환
            full_answer = result["content"]
            
            # 스트리밍 완료 신호 전송
            await self._send_streaming_complete_signal(session_id, full_answer)
            
            return {
                "educational_answer": full_answer,
                "knowledge_code": knowledge_code,
                "answerability": quality
            }
            
        except Exception as e:
            self.logger.error(f"스트리밍 처리 오류: {e}")
            return {
                "educational_answer": f"스트리밍 처리 중 오류가 발생했습니다: {str(e)}",
                "knowledge_code": knowledge_code,
                "answerability": quality
            }
    
    def _build_system_prompt(self) -> str:
        """시스템 프롬프트 구성"""
        return """당신은 MAICE의 수학 교육 전문가입니다.

역할:
- 학생의 수학 질문에 대해 체계적이고 교육적인 답변을 생성합니다.
- 한국 고등학교 교육과정 수준에 맞춰 답변합니다.

답변 원칙:
- 단계별 설명으로 복잡한 개념을 단순화합니다.
- 실생활 예시와 시각적 설명을 활용합니다.
- 학생의 수준에 맞는 용어와 설명을 사용합니다.
- 한국어로 자연스럽게 표현합니다.

중요한 제약사항:
1. **한국 고등학교 교육과정 수준**에 맞춰 답변하세요
2. **한국 교과서에서 사용하는 표준 용어**만 사용하세요
3. **대학교 수준의 고급 개념은 제외**하세요
4. **한국어로 자연스럽게 표현**하세요

답변 톤:
고등학생이 이해하기 쉽고 친근한 톤으로 답변해주세요."""
    
    def _build_user_template(self) -> str:
        """사용자 프롬프트 템플릿"""
        return """## 📚 **학생 질문**
{question}

## 📋 **질문 정보**
- **질문 유형**: {knowledge_code}
- **분류 결과**: {answerability}
- **명료화 정보**: {context}"""
    
    async def _send_answer_to_backend(self, session_id: int, result: Dict[str, Any]):
        """백엔드에 답변 결과 전송"""
        try:
            await self.streams_client.send_to_backend_stream({
                "type": "answer_result",
                "session_id": session_id,
                "answer": result["educational_answer"],
                "knowledge_code": result.get("knowledge_code", "K1"),
                "answerability": result.get("answerability", "answerable"),
                "timestamp": datetime.now().isoformat()
            })
            
            self.logger.info(f"📤 백엔드에 답변 결과 전송: 세션 {session_id}")
            
        except Exception as e:
            self.logger.error(f"❌ 답변 결과 전송 오류: {e}")
    
    async def _send_streaming_complete_signal(self, session_id: int, full_answer: str):
        """스트리밍 완료 신호 전송"""
        try:
            await self.streams_client.send_to_backend_stream({
                "type": "streaming_complete",
                "session_id": session_id,
                "full_answer": full_answer,
                "timestamp": datetime.now().isoformat()
            })
            
            self.logger.info(f"📤 스트리밍 완료 신호 전송: 세션 {session_id}")
            
        except Exception as e:
            self.logger.error(f"❌ 스트리밍 완료 신호 전송 오류: {e}")
    
    async def _trigger_observer_summary(self, session_id: int, question: str, answer: str, result: Dict[str, Any]):
        """ObserverAgent에게 요약 요청 전송"""
        try:
            conversation_text = f"학생 질문: {question}\n\n에이전트 답변: {answer}"
            
            await publish_event(
                AGENT_TO_AGENT,
                {
                    "type": "generate_summary",
                    "target_agent": "ObserverAgent",
                    "session_id": session_id,
                    "conversation_text": conversation_text,
                    "question": question,
                    "answer": answer,
                    "context": {
                        "knowledge_code": result.get("knowledge_code", "K1"),
                        "answerability": result.get("answerability", "answerable"),
                        "clarification_used": False,
                        "context_used": 0
                    },
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            self.logger.info(f"📤 ObserverAgent에게 요약 요청 전송: 세션 {session_id}")
            
        except Exception as e:
            self.logger.error(f"❌ ObserverAgent 요약 요청 전송 오류: {e}")

