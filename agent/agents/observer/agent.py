"""
학습 관찰 에이전트 - 새로운 3개 채널 구조 사용
"""

import logging
import json
import asyncio
from typing import Dict, Any
from datetime import datetime
from agents.base_agent import BaseAgent, Task
from agents.common.prompt_utils import (
    sanitize_text,
    validate_prompt_content,
    format_prompt_with_variables
)
from agents.common.config_loader import PromptConfigLoader
from agents.common.event_bus import (
    publish_event,
    subscribe_and_listen,
    BACKEND_TO_AGENT,
    AGENT_TO_BACKEND,
    AGENT_STATUS,
    AGENT_TO_AGENT,
    MessageType
)
from utils.redis_streams_client import AgentRedisStreamsClient
from agents.common.llm_tool import SpecializedLLMTool, PromptTemplate, LLMConfig

logger = logging.getLogger(__name__)

class ObserverAgent(BaseAgent):
    """학습 관찰 및 분석 에이전트 - 새로운 채널 구조"""
    
    def __init__(self):
        super().__init__(name="ObserverAgent", role="observer")  # BaseAgent 초기화 (logger 포함)
        
        # Redis Streams 클라이언트 초기화
        self.streams_client = AgentRedisStreamsClient("ObserverAgent")
        
        # 프롬프트 설정 로더 초기화
        self.config_loader = PromptConfigLoader()
        self.prompt_config = self.config_loader.get_agent_config("observer")
        
        # 시스템 프롬프트 구성
        system_prompt = self._build_system_prompt()
        
        # LLM 툴 초기화
        self.llm_tool = SpecializedLLMTool.create_observer_tool()
        
        super().__init__(
            name="Observer",
            role="학습 관찰 및 분석",
            system_prompt=system_prompt,
            tools=[self.llm_tool]  # LLM 툴 추가
        )
        
        self.observation_sessions = {}
    
    def _build_system_prompt(self) -> str:
        """설정 파일에서 시스템 프롬프트 구성"""
        base_config = self.prompt_config.get("observer", {}).get("system_prompts", {}).get("base", "")
        
        if not base_config:
            return "당신은 MAICE의 학습 과정 요약 전문가입니다. 학생의 질문, 명료화 과정, 답변을 간결하고 명확하게 요약하여 백엔드 시스템에서 활용할 수 있도록 구조화된 정보를 제공합니다."
        
        return base_config
    
    async def initialize(self):
        """에이전트 초기화"""
        await super().initialize()
        await self.streams_client.initialize()
    
    async def cleanup(self):
        """에이전트 정리"""
        await self.streams_client.close()
        await super().cleanup()
    
    async def run_subscriber(self):
        """Streams와 pub/sub 기반 메시지 수신"""
        self.logger.info("🚀 ObserverAgent Streams + pub/sub 구독 시작")
        
        # pub/sub 구독 시작 (별도 태스크로 실행)
        pubsub_task = asyncio.create_task(self.run_pubsub_subscriber())
        
        try:
            while True:
                try:
                    # Streams에서 메시지 수신 - 대용량 동시 처리 (최대 50개)
                    messages = await self.streams_client.read_from_backend_stream(count=50, block=1000)
                    
                    if messages:
                        # 동시 처리할 메시지들 분류
                        tasks = []
                        for msg_id, fields in messages:
                            self.logger.info(f"📥 Streams에서 메시지 수신: {msg_id}")
                            
                            # 메시지 파싱 (이미 decode된 문자열)
                            message_type = fields.get('type', '')
                            target_agent = fields.get('target_agent', '')
                            
                            self.logger.info(f"🔍 메시지 분석: type={message_type}, target_agent={target_agent}")
                            
                            # msg_id가 bytes인 경우에만 decode, 이미 문자열이면 그대로 사용
                            msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
                            
                            # 자기 에이전트로 온 메시지가 아니면 ACK하고 건너뛰기
                            if target_agent not in ["ObserverAgent", "Observer"]:
                                tasks.append(self.streams_client.ack_stream_message(msg_id_str))
                                continue
                            
                            # 메시지 처리 태스크 생성
                            if message_type == "observe_learning":
                                tasks.append(self._handle_learning_observation_stream(fields, msg_id_str))
                            elif message_type == "generate_summary":
                                tasks.append(self._handle_summary_generation_stream(fields, msg_id_str))
                            else:
                                self.logger.warning(f"⚠️ 알 수 없는 메시지 타입: {message_type}")
                                tasks.append(self.streams_client.ack_stream_message(msg_id_str))
                        
                        # 모든 메시지 동시 처리
                        if tasks:
                            await asyncio.gather(*tasks, return_exceptions=True)
                    
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    self.logger.error(f"Streams 메시지 처리 오류: {e}")
                    await asyncio.sleep(0.1)
        
        finally:
            # pub/sub 태스크 정리
            pubsub_task.cancel()
            try:
                await pubsub_task
            except asyncio.CancelledError:
                pass
    
    async def run_pubsub_subscriber(self):
        """pub/sub 기반 메시지 수신 (ObserverAgent 전용)"""
        self.logger.info("🚀 ObserverAgent pub/sub 구독 시작")
        
        async def message_handler(channel: str, payload: Dict[str, Any]):
            try:
                target_agent = payload.get("target_agent")
                message_type = payload.get("type")
                
                # 자기 에이전트로 온 메시지가 아니면 즉시 리턴
                if target_agent not in ["ObserverAgent", "Observer"]:
                    return
                
                self.logger.info(f"📥 pub/sub 메시지 수신: channel={channel}, target_agent={target_agent}, type={message_type}")
                
                if message_type == "generate_summary":
                    await self.process_summary_generation_request(payload)
                else:
                    self.logger.warning(f"⚠️ 알 수 없는 pub/sub 메시지 타입: {message_type}")
                    
            except Exception as e:
                self.logger.error(f"pub/sub 메시지 처리 오류: {e}")
        
        # AGENT_TO_AGENT 채널 구독
        await subscribe_and_listen([AGENT_TO_AGENT], message_handler, self)
        self.logger.info("✅ ObserverAgent pub/sub 메시지 구독 시작")
    
    async def _handle_learning_observation_stream(self, fields: Dict[str, Any], msg_id: str):
        """Streams에서 받은 학습 관찰 요청 처리"""
        try:
            request_id = fields.get('request_id', '')
            session_id = int(fields.get('session_id', '0'))
            question = fields.get('question', '')
            answer = fields.get('answer', '')
            context_data = fields.get('context', '{}')
            
            try:
                context = json.loads(context_data) if context_data else {}
            except json.JSONDecodeError:
                context = {}
            
            self.logger.info(f"🔄 Streams 학습 관찰 요청: 세션 {session_id}")
            
            # 학습 관찰 수행
            observation_result = await self._observe_learning(question, answer, session_id, context)
            
            if observation_result.get("success"):
                await self._handle_successful_observation_stream(session_id, observation_result, request_id)
            else:
                await self._handle_observation_error_stream(session_id, observation_result, request_id)
            
            # 메시지 ACK
            await self.streams_client.ack_stream_message(msg_id)
            
        except Exception as e:
            self.logger.error(f"❌ Streams 학습 관찰 처리 오류: {e}")
            await self.streams_client.ack_stream_message(msg_id)
    
    async def _handle_summary_generation_stream(self, fields: Dict[str, Any], msg_id: str):
        """Streams에서 받은 요약 생성 요청 처리"""
        try:
            request_id = fields.get('request_id', '')
            session_id = int(fields.get('session_id', '0'))
            conversation_text = fields.get('conversation_text', '')
            
            self.logger.info(f"🔄 Streams 요약 생성 요청: 세션 {session_id}")
            
            # 요약 생성 수행
            summary_result = await self._generate_summary(conversation_text, session_id)
            
            if summary_result.get("success"):
                await self._handle_successful_summary_stream(session_id, summary_result, request_id)
            else:
                await self._handle_summary_error_stream(session_id, summary_result, request_id)
            
            # 메시지 ACK
            await self.streams_client.ack_stream_message(msg_id)
            
        except Exception as e:
            self.logger.error(f"❌ Streams 요약 생성 처리 오류: {e}")
            await self.streams_client.ack_stream_message(msg_id)
    
    async def _handle_successful_observation_stream(self, session_id: int, result: Dict[str, Any], request_id: str):
        """Streams로 성공적인 관찰 결과 전송"""
        try:
            # Streams로 관찰 결과 전송
            await self.streams_client.send_to_backend_stream({
                "type": MessageType.OBSERVATION_SUCCESS,
                "session_id": session_id,
                "result": result,
                "request_id": request_id
            })
            self.logger.info(f"✅ Streams로 관찰 결과 전송: 세션 {session_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Streams 관찰 결과 전송 오류: {e}")
    
    async def _handle_observation_error_stream(self, session_id: int, result: Dict[str, Any], request_id: str):
        """Streams로 관찰 오류 결과 전송"""
        try:
            error_message = result.get("error", "관찰 처리에 실패했습니다.")
            
            # Streams로 에러 결과 전송
            await self.streams_client.send_to_backend_stream({
                "type": MessageType.OBSERVATION_ERROR,
                "session_id": session_id,
                "error": error_message,
                "request_id": request_id
            })
            self.logger.info(f"❌ Streams로 관찰 오류 전송: 세션 {session_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Streams 관찰 오류 전송 오류: {e}")
    
    async def _handle_successful_summary_stream(self, session_id: int, result: Dict[str, Any], request_id: str):
        """Streams로 성공적인 요약 결과 전송"""
        try:
            summary = result.get("summary", "")
            
            # Streams로 요약 결과 전송
            await self.streams_client.send_to_backend_stream({
                "type": MessageType.SUMMARY_SUCCESS,
                "session_id": session_id,
                "summary": summary,
                "request_id": request_id
            })
            self.logger.info(f"✅ Streams로 요약 결과 전송: 세션 {session_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Streams 요약 결과 전송 오류: {e}")
    
    async def _handle_summary_error_stream(self, session_id: int, result: Dict[str, Any], request_id: str):
        """Streams로 요약 오류 결과 전송"""
        try:
            error_message = result.get("error", "요약 생성에 실패했습니다.")
            
            # Streams로 에러 결과 전송
            await self.streams_client.send_to_backend_stream({
                "type": MessageType.SUMMARY_ERROR,
                "session_id": session_id,
                "error": error_message,
                "request_id": request_id
            })
            self.logger.info(f"❌ Streams로 요약 오류 전송: 세션 {session_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Streams 요약 오류 전송 오류: {e}")
    
    async def process_message(self, message_type: str, payload: Dict[str, Any]):
        """메시지 처리 (BaseAgent 병렬 처리용)"""
        try:
            if message_type in ["GENERATE_SUMMARY", "generate_summary"]:
                await self.process_summary_generation_request(payload)
            elif message_type in ["LEARNING_OBSERVATION", "learning_observation"]:
                await self.process_learning_observation_request(payload)
            else:
                self.logger.warning(f"알 수 없는 메시지 타입: {message_type}")
        except Exception as e:
            self.logger.error(f"메시지 처리 오류: {e}")
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """BaseAgent 추상 메서드 구현 - 학습 관찰 태스크 처리"""
        try:
            self.logger.info(f"학습 관찰 태스크 시작: {task_data.get('task_type', 'unknown')}")
            
            # 태스크 타입에 따른 처리
            task_type = task_data.get("task_type", "observe_learning")
            
            if task_type == "observe_learning":
                return await self._observe_learning(
                    question=task_data.get("question", ""),
                    answer=task_data.get("answer", ""),
                    session_id=task_data.get("session_id", ""),
                    context=task_data.get("context", {})
                )
            else:
                return {"success": False, "error": f"지원하지 않는 태스크 타입: {task_type}"}
                
        except Exception as e:
            self.logger.error(f"태스크 처리 오류: {e}")
            return {"success": False, "error": str(e)}
    
    async def process_learning_observation_request(self, payload: dict):
        """백엔드로부터 받은 학습 관찰 요청"""
        request_id = payload.get("request_id")
        session_id = payload.get("session_id")
        question = payload.get("question")
        answer = payload.get("answer")
        context = payload.get("context", {})
        
        try:
            # 학습 관찰 수행 (기존 툴 로직을 함수로 변환)
            observation_result = await self._observe_learning(question, answer, session_id, context)
            
            if observation_result.get("success"):
                await self._handle_successful_observation(request_id, session_id, question, answer, observation_result)
            else:
                await self._handle_observation_error(request_id, session_id, question, answer, observation_result)
                
        except Exception as e:
            self.logger.error(f"학습 관찰 처리 오류: {e}")
            await self._handle_observation_error(request_id, session_id, question, answer, str(e))
    
    async def process_summary_generation_request(self, payload: dict):
        """백엔드로부터 받은 요약 생성 요청"""
        request_id = payload.get("request_id")
        session_id = payload.get("session_id")
        conversation_text = payload.get("conversation_text")
        
        try:
            self.logger.info(f"📝 요약 생성 요청 수신: 세션 {session_id}")
            
            # 요약 생성 수행
            summary_result = await self._generate_summary(conversation_text, session_id)
            
            if summary_result.get("success"):
                await self._handle_successful_summary(request_id, session_id, summary_result)
            else:
                await self._handle_summary_error(request_id, session_id, summary_result.get("error", "알 수 없는 오류"))
                
        except Exception as e:
            self.logger.error(f"요약 생성 처리 오류: {e}")
            await self._handle_summary_error(request_id, session_id, str(e))
    
    async def _observe_learning(self, question: str, answer: str, session_id: str, context: dict) -> Dict[str, Any]:
        """학습 과정 요약 - YAML 프롬프트 기반 LLM 요약 (최적화된 비동기 처리)"""
        try:
            self.logger.info(f"학습 과정 요약 시작: 세션 {session_id}")
            
            # 학습 맥락 정보 추출 (빠른 처리)
            learning_context = self._extract_learning_context(context)
            
            # 기본 요약 생성 (빠른 처리)
            question_summary = self._summarize_question(question)
            clarification_summary = self._summarize_clarification(context)
            answer_summary = self._summarize_answer(answer)
            
            # 기본 요약 데이터 구성
            summary_data = {
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "question_summary": question_summary,
                "clarification_summary": clarification_summary,
                "answer_summary": answer_summary,
                "conversation_summary": answer_summary,
                "learning_context": learning_context,
                "title": question_summary[:50] + "...",  # 기본 제목
                "summary": answer_summary,
                "key_concepts": [],
                "student_progress": "학습 진행 중"
            }
            
            # 백엔드로 즉시 전송 (기본 요약)
            await self._send_summary_to_backend(summary_data)
            
            # LLM 요약은 백그라운드에서 비동기 처리 (타임아웃 없이)
            asyncio.create_task(self._enhance_summary_with_llm_async(question, answer, session_id, summary_data))
            
            result = {
                "success": True,
                "session_id": session_id,
                "summary_sent": True,
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f"학습 과정 요약 완료: 세션 {session_id}, 백엔드 전송 완료")
            return result
            
        except Exception as e:
            self.logger.error(f"학습 과정 요약 오류: {e}")
            return {"success": False, "error": str(e)}
    
    async def _enhance_summary_with_llm_async(self, question: str, answer: str, session_id: str, summary_data: dict):
        """백그라운드에서 LLM을 사용한 요약 향상 (비동기 처리)"""
        try:
            self.logger.info(f"🔧 LLM 요약 향상 시작: 세션 {session_id}")
            
            # 타임아웃 설정 (30초)
            enhanced_summary = await asyncio.wait_for(
                self._generate_summary_with_llm(f"학생 질문: {question}\n\n에이전트 답변: {answer}", session_id),
                timeout=30.0
            )
            
            # 향상된 요약 데이터 업데이트
            enhanced_data = {
                **summary_data,
                "title": enhanced_summary.get("session_title", summary_data.get("title", "")),
                "summary": enhanced_summary.get("learning_summary", summary_data.get("summary", "")),
                "key_concepts": enhanced_summary.get("key_concepts", []),
                "student_progress": enhanced_summary.get("student_progress", summary_data.get("student_progress", "")),
                "enhanced": True,
                "enhanced_timestamp": datetime.now().isoformat()
            }
            
            # 향상된 요약을 백엔드로 전송
            await self._send_summary_to_backend(enhanced_data)
            
            self.logger.info(f"✅ LLM 요약 향상 완료: 세션 {session_id}")
            
        except asyncio.TimeoutError:
            self.logger.warning(f"⏰ LLM 요약 향상 타임아웃: 세션 {session_id} (30초 초과)")
        except Exception as e:
            self.logger.error(f"❌ LLM 요약 향상 실패: 세션 {session_id}, 오류: {e}")
    
    def _summarize_question(self, question: str) -> str:
        """질문 요약 - 핵심 내용만 추출"""
        try:
            if len(question) <= 100:
                return question
            
            # 긴 질문은 앞부분과 핵심 키워드로 요약
            words = question.split()
            if len(words) > 20:
                return f"{' '.join(words[:15])}... (총 {len(words)}단어)"
            
            return question
            
        except Exception as e:
            self.logger.error(f"질문 요약 오류: {e}")
            return question[:100] + "..."
    
    def _summarize_clarification(self, context: dict) -> str:
        """명료화 과정 요약 - 기본 처리"""
        try:
            clarification_turns = context.get("clarification_turns", [])
            if not clarification_turns:
                return "명료화 과정 없음"
            
            return f"명료화 {len(clarification_turns)}회 진행"
            
        except Exception as e:
            self.logger.error(f"명료화 요약 오류: {e}")
            return "명료화 과정 요약 실패"
    
    def _summarize_answer(self, answer: str) -> str:
        """답변 요약 - 기본 처리"""
        try:
            if len(answer) <= 200:
                return answer
            
            # 답변의 앞부분과 핵심 키워드로 요약
            words = answer.split()
            if len(words) > 50:
                return f"{' '.join(words[:40])}... (총 {len(words)}단어)"
            
            return answer
            
        except Exception as e:
            self.logger.error(f"답변 요약 오류: {e}")
            return answer[:200] + "..." if len(answer) > 200 else answer
    
    def _summarize_clarification_process(self, context: dict) -> Dict[str, Any]:
        """명료화 과정 요약"""
        try:
            clarification_info = context.get("clarification_responses", {})
            
            if not clarification_info:
                return {"has_clarification": False, "summary": "명료화 과정 없음"}
            
            # 명료화 질문과 답변 요약
            clarification_summary = []
            for key, value in clarification_info.items():
                if isinstance(value, str) and len(value) > 50:
                    summary = value[:50] + "..."
                else:
                    summary = str(value)
                clarification_summary.append(f"{key}: {summary}")
            
            return {
                "has_clarification": True,
                "total_clarifications": len(clarification_info),
                "summary": "; ".join(clarification_summary),
                "detailed_responses": clarification_info
            }
            
        except Exception as e:
            self.logger.error(f"명료화 과정 요약 오류: {e}")
            return {"has_clarification": False, "summary": "요약 실패"}
    
    def _summarize_answer(self, answer: str) -> str:
        """답변 요약 - 핵심 내용만 추출"""
        try:
            # 간단한 요약 (실제로는 LLM을 사용할 수 있음)
            if len(answer) <= 200:
                return answer
            
            # 긴 답변은 구조별로 요약
            lines = answer.split('\n')
            summary_parts = []
            
            for line in lines:
                if line.strip() and len(line.strip()) > 10:
                    # 제목이나 중요한 내용만 추출
                    if line.startswith('##') or line.startswith('**'):
                        summary_parts.append(line.strip())
                    elif len(summary_parts) < 5:  # 최대 5개 라인만
                        summary_parts.append(line.strip())
            
            if summary_parts:
                return "\n".join(summary_parts) + f"\n... (총 {len(answer)}자)"
            
            return answer[:200] + "..."
            
        except Exception as e:
            self.logger.error(f"답변 요약 오류: {e}")
            return answer[:200] + "..." if len(answer) > 200 else answer
    
    def _extract_learning_context(self, context: dict) -> Dict[str, Any]:
        """학습 맥락 정보 추출"""
        try:
            return {
                "unit": context.get("unit", ""),
                "learning_objective": context.get("learning_objective", ""),
                "knowledge_type": context.get("knowledge_type", ""),
                "difficulty": context.get("difficulty", ""),
                "student_id": context.get("student_id", "")
            }
        except Exception as e:
            self.logger.error(f"학습 맥락 추출 오류: {e}")
            return {}
    
    async def _send_summary_to_backend(self, summary_data: dict):
        """요약된 정보를 백엔드로 전송 - 스트리밍 방식"""
        try:
            session_id = summary_data.get("session_id")
            
            # 1. 요약 시작 알림
            await self.streams_client.send_to_backend_stream({
                "type": MessageType.SUMMARY_START,
                "session_id": session_id,
                "message": "학습 과정을 분석하고 요약을 생성하고 있습니다...",
                "timestamp": datetime.now().isoformat()
            })
            
            # 2. 요약 진행 상황 스트리밍
            await self.streams_client.send_to_backend_stream({
                "type": MessageType.SUMMARY_PROGRESS,
                "session_id": session_id,
                "message": "질문과 답변을 분석하여 학습 포인트를 추출하고 있습니다...",
                "progress": 60,
                "timestamp": datetime.now().isoformat()
            })
            
            # 3. 최종 요약 전송
            await self.streams_client.send_to_backend_stream({
                "type": MessageType.SUMMARY_COMPLETE,
                "session_id": session_id,
                "message": f"학습 요약 완료: {summary_data.get('summary_title', '학습 과정 요약')}",
                "data": summary_data,
                "timestamp": datetime.now().isoformat()
            })
            
            self.logger.info(f"✅ 스트리밍으로 학습 요약 백엔드 전송 완료: 세션 {session_id}")
            
        except Exception as e:
            self.logger.error(f"❌ 백엔드 전송 오류: {e}")
            raise
    
    async def _handle_successful_observation(self, request_id: str, session_id: str, question: str, answer: str, result: Dict[str, Any]):
        """성공적인 관찰 처리"""
        try:
            # Streams로 성공 신호 전송
            success_message = {
                "type": MessageType.OBSERVATION_SUCCESS,
                "request_id": request_id,
                "session_id": session_id,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.streams_client.send_to_backend_stream(success_message)
            
            self.logger.info(f"관찰 성공 처리 완료: 세션 {session_id}")
            
        except Exception as e:
            self.logger.error(f"관찰 성공 처리 오류: {e}")
    
    async def _handle_observation_error(self, request_id: str, session_id: str, error: str):
        """관찰 오류 처리"""
        try:
            # Streams로 오류 신호 전송
            error_message = {
                "type": MessageType.OBSERVATION_ERROR,
                "request_id": request_id,
                "session_id": session_id,
                "error": error,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.streams_client.send_to_backend_stream(error_message)
            
            self.logger.error(f"관찰 오류 처리 완료: 세션 {session_id}, 오류: {error}")
            
        except Exception as e:
            self.logger.error(f"관찰 오류 처리 중 추가 오류 발생: {e}")

    async def _summarize_question_with_llm(self, question: str, session_id: int = None) -> str:
        """LLM을 통한 질문 요약"""
        try:
            # YAML에서 질문 요약 프롬프트 템플릿 가져오기
            template = self.prompt_config.get("observer", {}).get("system_prompts", {}).get("question_summary_template", "")
            if not template:
                self.logger.warning("YAML에서 question_summary_template을 찾을 수 없습니다. 기본 요약 사용")
                return self._fallback_question_summary(question)
            
            # 프롬프트 구성
            prompt = template.format(
                question=question,
                summary=""
            )
            
            # LLM 호출
            response = await self._call_llm_for_summary(prompt, "질문 요약", session_id=None)
            
            # 응답 검증 및 길이 제한
            max_length = self.prompt_config.get("observer", {}).get("summary_guidelines", {}).get("question_summary", {}).get("max_length", 100)
            if len(response) > max_length:
                response = response[:max_length] + "..."
            
            return response
            
        except Exception as e:
            self.logger.error(f"LLM 질문 요약 오류: {e}")
            return self._fallback_question_summary(question)
    
    async def _summarize_clarification_with_llm(self, context: dict, session_id: int = None) -> Dict[str, Any]:
        """LLM을 통한 명료화 과정 요약"""
        try:
            clarification_info = context.get("clarification_responses", {})
            
            if not clarification_info:
                return {"has_clarification": False, "summary": "명료화 과정 없음"}
            
            # YAML에서 명료화 요약 프롬프트 템플릿 가져오기
            template = self.prompt_config.get("observer", {}).get("system_prompts", {}).get("clarification_summary_template", "")
            if not template:
                self.logger.warning("YAML에서 clarification_summary_template을 찾을 수 없습니다. 기본 요약 사용")
                return self._fallback_clarification_summary(context)
            
            # 명료화 데이터 준비
            clarification_data = self._format_clarification_data(clarification_info)
            
            # 프롬프트 구성
            prompt = template.format(
                clarification_data=clarification_data,
                summary=""
            )
            
            # LLM 호출
            response = await self._call_llm_for_summary(prompt, "명료화 과정 요약", session_id=None)
            
            return {
                "has_clarification": True,
                "total_clarifications": len(clarification_info),
                "summary": response,
                "detailed_responses": clarification_info
            }
            
        except Exception as e:
            self.logger.error(f"LLM 명료화 요약 오류: {e}")
            return self._fallback_clarification_summary(context)
    
    async def _summarize_answer_with_llm(self, answer: str, session_id: int = None) -> str:
        """LLM을 통한 답변 요약"""
        try:
            # YAML에서 답변 요약 프롬프트 템플릿 가져오기
            template = self.prompt_config.get("observer", {}).get("system_prompts", {}).get("answer_summary_template", "")
            if not template:
                self.logger.warning("YAML에서 answer_summary_template을 찾을 수 없습니다. 기본 요약 사용")
                return await self._fallback_answer_summary(answer)
            
            # 프롬프트 구성
            prompt = template.format(
                answer=answer,
                summary=""
            )
            
            # LLM 호출
            response = await self._call_llm_for_summary(prompt, "답변 요약", session_id=None)
            
            # 응답 검증 및 길이 제한
            max_length = self.prompt_config.get("observer", {}).get("summary_guidelines", {}).get("answer_summary", {}).get("max_length", 200)
            if len(response) > max_length:
                response = response[:max_length] + "..."
            
            return response
            
        except Exception as e:
            self.logger.error(f"LLM 답변 요약 오류: {e}")
            return await self._fallback_answer_summary(answer)
    
    async def _call_llm_for_summary(self, prompt: str, summary_type: str, session_id: int = None) -> str:
        """요약을 위한 LLM 호출 - 새로운 LLM 툴 사용"""
        try:
            # 딕셔너리 형태로 프롬프트 구성
            prompt_dict = {
                "system": self._build_system_prompt(),
                "user": prompt
            }
            
            # LLM 툴 실행 (session_id 전달)
            result = await self.llm_tool.execute(
                prompt_dict,
                session_id=session_id
            )
            
            # LLM 툴 응답 처리 (딕셔너리 형태)
            if isinstance(result, dict) and result.get("success"):
                response = result.get("content", "")
            else:
                self.logger.error(f"LLM {summary_type} 호출 실패: {result.get('error', 'Unknown error')}")
                return ""
            
            self.logger.info(f"LLM {summary_type} 응답: {response[:100]}...")
            return response
            
        except Exception as e:
            self.logger.error(f"LLM {summary_type} 호출 실패: {e}")
            return ""
    
    def _format_clarification_data(self, clarification_info: dict) -> str:
        """명료화 데이터를 프롬프트용으로 포맷팅"""
        formatted_parts = []
        
        for key, value in clarification_info.items():
            if isinstance(value, str):
                formatted_parts.append(f"**{key}**: {value}")
            else:
                formatted_parts.append(f"**{key}**: {str(value)}")
        
        return "\n".join(formatted_parts)
    
    def _fallback_question_summary(self, question: str) -> str:
        """LLM 실패 시 기본 질문 요약"""
        if len(question) <= 100:
            return question
        return question[:100] + "..."
    
    def _fallback_clarification_summary(self, context: dict) -> Dict[str, Any]:
        """LLM 실패 시 기본 명료화 요약"""
        clarification_info = context.get("clarification_responses", {})
        if not clarification_info:
            return {"has_clarification": False, "summary": "명료화 과정 없음"}
        
        summary_parts = []
        for key, value in clarification_info.items():
            if isinstance(value, str) and len(value) > 50:
                summary = value[:50] + "..."
            else:
                summary = str(value)
            summary_parts.append(f"{key}: {summary}")
        
        return {
            "has_clarification": True,
            "total_clarifications": len(clarification_info),
            "summary": "; ".join(summary_parts),
            "detailed_responses": clarification_info
        }
    
    async def _fallback_answer_summary(self, answer: str, session_id: int = None) -> str:
        """LLM 실패 시 기본 답변 요약 - LLM을 사용한 간단한 요약 시도"""
        if len(answer) <= 200:
            return answer
        
        try:
            # 간단한 LLM 요약 시도
            summary_prompt = f"""다음 수학 교육 답변을 핵심 내용 위주로 200자 이내로 요약해주세요:

## 답변:
{answer}

## 요약 기준:
- 주요 개념과 설명 중심
- 핵심 예시나 방법론 포함
- 학습 포인트와 중요사항 강조
- 간결하고 이해하기 쉽게 정리

## 요약:"""

            response = await self._call_llm_for_summary(summary_prompt, "답변 요약 (fallback)", session_id=session_id)
            if response and len(response.strip()) > 0:
                return response.strip()[:200]
            else:
                # LLM 응답이 비어있으면 기본 처리
                return answer[:200] + "..."
                
        except Exception as e:
            self.logger.warning(f"⚠️ Fallback 요약 LLM 호출 실패: {e}")
            # LLM 실패 시 기본 처리
            return answer[:200] + "..."
    
    async def _generate_summary_with_llm(self, conversation_text: str, session_id: str) -> Dict[str, str]:
        """LLM을 사용한 대화 요약 및 제목 생성"""
        try:
            # YAML에서 요약 프롬프트 템플릿 가져오기
            template = self.prompt_config.get("observer", {}).get("system_prompts", {}).get("conversation_summary_template", "")
            if not template:
                self.logger.error("❌ YAML에서 conversation_summary_template을 찾을 수 없습니다.")
                return {
                    "title": "",
                    "summary": "요약 템플릿을 찾을 수 없습니다.",
                    "key_concepts": [],
                    "student_progress": ""
                }
            
            # self.logger.info(f"✅ YAML에서 conversation_summary_template 로드 성공")
            
            # 프롬프트 구성
            prompt = template.format(conversation_text=conversation_text)
            
            # LLM 호출 (session_id 전달)
            response = await self._call_llm_for_summary(prompt, "대화 요약 및 제목 생성", session_id=session_id)
            self.logger.info(f"🔍 LLM 응답 수신: {response[:200]}..." if len(response) > 200 else f"🔍 LLM 응답 수신: {response}")
            
            # JSON 응답 파싱
            try:
                import re
                import json
                
                # JSON 블록 추출 (```json ... ``` 형태)
                json_match = re.search(r'```json\s*\n(.*?)\n```', response, re.DOTALL | re.IGNORECASE)
                if json_match:
                    json_str = json_match.group(1).strip()
                    json_data = json.loads(json_str)
                    # self.logger.info(f"✅ JSON 블록에서 파싱 성공")
                else:
                    # JSON 블록이 없으면 중괄호로 감싸진 JSON 객체 찾기
                    start_idx = response.find('{')
                    if start_idx != -1:
                        # 중괄호 개수를 세어서 JSON 객체 끝 찾기
                        brace_count = 0
                        end_idx = start_idx
                        for i, char in enumerate(response[start_idx:], start_idx):
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end_idx = i + 1
                                    break
                        
                        json_str = response[start_idx:end_idx]
                        json_data = json.loads(json_str)
                        self.logger.info(f"✅ 응답에서 JSON 파싱 성공")
                    else:
                        raise ValueError("JSON 형식의 응답을 찾을 수 없습니다")
                
                # JSON 데이터에서 정보 추출
                title = json_data.get("session_title", "").strip()
                summary = json_data.get("learning_summary", "").strip()
                key_concepts = json_data.get("key_concepts", [])
                progress = json_data.get("student_progress", "").strip()
                
                # 제목에서 불필요한 접두사 제거
                if title and (title.startswith("세션") or title.startswith("학습")):
                    title = re.sub(r'^세션\s*\d*\s*[의의]\s*학습\s*요약\s*:\s*', '', title)
                
                # key_concepts가 문자열인 경우 배열로 변환
                if isinstance(key_concepts, str):
                    concepts_list = re.split(r'[,，\n]', key_concepts)
                    key_concepts = [c.strip().strip('"\'') for c in concepts_list if c.strip()]
                
                self.logger.info(f"✅ 요약 정보 추출 성공 - 제목: {title}, 요약 길이: {len(summary)}")
                return {
                    "title": title[:50] if title else "",  # 최대 50자
                    "summary": summary,
                    "key_concepts": key_concepts if isinstance(key_concepts, list) else [],
                    "student_progress": progress
                }
                
            except (json.JSONDecodeError, ValueError) as parse_error:
                self.logger.error(f"❌ JSON 파싱 실패: {parse_error}")
                self.logger.error(f"❌ 파싱 실패한 응답: {response[:500]}")
                
                # JSON 파싱 실패 시 기본 처리
                lines = conversation_text.split('\n')
                question_line = ""
                for line in lines:
                    if "학생 질문:" in line or "질문:" in line:
                        question_line = line
                        break
                
                return {
                    "title": "",
                    "summary": f"요약 생성 실패: {question_line[:100]}..." if question_line else "요약 생성 실패",
                    "key_concepts": [],
                    "student_progress": ""
                }
            
        except Exception as e:
            self.logger.error(f"LLM 대화 요약 생성 오류: {e}")
            return {
                "title": "",
                "summary": "",
                "key_concepts": [],
                "student_progress": ""
            }
    
    async def _generate_summary(self, conversation_text: str, session_id: str) -> Dict[str, Any]:
        """LLM을 사용한 대화 요약 생성"""
        try:
            # self.logger.info(f"📝 LLM 기반 대화 요약 생성 시작: 세션 {session_id}")
            
            # LLM을 사용한 요약 및 제목 생성
            summary_data = await self._generate_summary_with_llm(conversation_text, session_id)
            
            if not summary_data.get("summary"):
                # LLM 실패 시 기본 요약 생성
                summary_data = {
                    "title": "수학 학습",
                    "summary": f"세션 {session_id}의 학습 요약: {conversation_text[:200]}...",
                    "key_concepts": [],
                    "student_progress": ""
                }
                self.logger.warning(f"⚠️ LLM 요약 실패, 기본 요약 사용: 세션 {session_id}")
            
            return {
                "success": True,
                "summary": summary_data.get("summary", ""),
                "title": summary_data.get("title", ""),
                "key_concepts": summary_data.get("key_concepts", []),
                "student_progress": summary_data.get("student_progress", ""),
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"요약 생성 오류: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _handle_successful_summary(self, request_id: str, session_id: str, result: Dict[str, Any]):
        """성공적인 요약 처리"""
        try:
            summary_content = result.get('summary', '')
            
            # Streams로 성공 신호 전송
            success_message = {
                "type": MessageType.SUMMARY_COMPLETE,
                "request_id": request_id,
                "session_id": session_id,
                "summary": summary_content,
                "data": result,
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f"📤 백엔드에 요약 전송: 세션 {session_id}, request_id={request_id}, 요약길이={len(summary_content)}")
            self.logger.info(f"📤 요약 내용: {summary_content[:100]}...")
            
            await self.streams_client.send_to_backend_stream(success_message)
            
            self.logger.info(f"✅ 요약 성공 처리 완료: 세션 {session_id}")
            
        except Exception as e:
            self.logger.error(f"❌ 요약 성공 처리 오류: {e}")
    
    async def _handle_summary_error(self, request_id: str, session_id: str, error: str):
        """요약 오류 처리"""
        try:
            # Streams로 오류 신호 전송
            error_message = {
                "type": MessageType.SUMMARY_ERROR,
                "request_id": request_id,
                "session_id": session_id,
                "error": error,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.streams_client.send_to_backend_stream(error_message)
            
            self.logger.error(f"요약 오류 처리 완료: 세션 {session_id} - {error}")
            
        except Exception as e:
            self.logger.error(f"요약 오류 처리 중 오류: {e}")
