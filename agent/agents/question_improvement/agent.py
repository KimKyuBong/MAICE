"""
명료화 에이전트 - 새로운 3개 채널 구조 사용
"""

import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, List
from agents.base_agent import BaseAgent, Task
from agents.common.prompt_utils import (
    sanitize_text,
    validate_prompt_content,
    generate_safe_separators,
    create_separator_hash,
    extract_json_from_response,
    validate_json_structure
)
from agents.common.config_loader import PromptConfigLoader
from agents.common.prompt_builder import PromptBuilder
from agents.common.constants import AnswerabilityType
from agents.common.event_bus import (
    subscribe_and_listen,
    publish_event,
    BACKEND_TO_AGENT,
    AGENT_TO_BACKEND,
    AGENT_STATUS,
    AGENT_TO_AGENT,
    MessageType
)
from utils.redis_streams_client import AgentRedisStreamsClient
from agents.common.llm_tool import SpecializedLLMTool, PromptTemplate, LLMConfig

logger = logging.getLogger(__name__)

class QuestionImprovementAgent(BaseAgent):
    """명료화 에이전트 - 새로운 채널 구조"""
    
    def __init__(self):
        # 프롬프트 설정 로더 초기화
        self.config_loader = PromptConfigLoader()
        
        # QuestionImprovement 에이전트 설정 로드
        yaml_data = self.config_loader.get_agent_config("question_improvement")
        if not yaml_data:
            self.logger.error("QuestionImprovement 설정을 로드할 수 없습니다")
            raise RuntimeError("QuestionImprovement 설정 로드 실패")
        
        # 프롬프트 빌더 초기화
        self.prompt_builder = PromptBuilder(yaml_data)
        
        # YAML 데이터를 인스턴스 변수로 저장
        self.prompt_config = yaml_data
        
        # 시스템 프롬프트는 PromptBuilder를 통해 동적으로 생성
        
        super().__init__(
            name="QuestionImprovement",
            role="명료화 질문 전달 및 답변 수집", 
            system_prompt="",  # PromptBuilder를 통해 동적으로 생성
            tools=[]
        )
        
        # 히스토리는 백엔드에서 관리하므로 제거
        
        self.clarification_sessions = {}  # session_id 기반 명료화 세션 저장소
        
        # Redis Streams 클라이언트 초기화
        self.streams_client = AgentRedisStreamsClient("QuestionImprovementAgent")
        
        # LLM 툴 초기화
        self.llm_tool = SpecializedLLMTool.create_question_improvement_tool()
        
        # 안전한 구분자 설정
        self.separators = generate_safe_separators()
        self.separator_hash = create_separator_hash(self.separators)
        
        # 프롬프트 템플릿은 PromptBuilder를 통해 동적으로 생성
    
        
    async def initialize(self):
        """에이전트 초기화"""
        await super().initialize()
        # Redis Streams 클라이언트 초기화
        await self.streams_client.initialize()
        self.logger.info("✅ QuestionImprovementAgent Streams 클라이언트 초기화 완료")
    
    async def cleanup(self):
        """에이전트 정리"""
        await super().cleanup()
        # Redis Streams 클라이언트 정리
        await self.streams_client.close()
        self.logger.info("✅ QuestionImprovementAgent Streams 클라이언트 정리 완료")

    async def run_subscriber(self):
        """Redis Streams 기반으로 메시지 수신"""
        self.logger.info("🚀 QuestionImprovementAgent Streams + pub/sub 구독 시작")
        
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
                            
                            # 메시지 파싱
                            message_type = fields.get('type', '')
                            target_agent = fields.get('target_agent', '')
                            
                            # 이 에이전트를 대상으로 하는 메시지만 처리
                            if target_agent not in ["QuestionImprovementAgent", "QuestionImprovement"]:
                                # 메시지 ACK (다른 에이전트용이므로)
                                tasks.append(self.streams_client.ack_stream_message(msg_id))
                                continue
                            
                            self.logger.info(f"📥 백엔드 메시지 수신: {message_type}")
                            
                            # 메시지 처리 태스크 생성
                            if message_type == "clarification_response":
                                tasks.append(self._handle_clarification_response_stream(fields, msg_id))
                            elif message_type == "process_clarification":
                                tasks.append(self._handle_process_clarification_stream(fields, msg_id))
                            else:
                                self.logger.warning(f"⚠️ 알 수 없는 메시지 타입: {message_type}")
                                # 알 수 없는 메시지도 ACK
                                tasks.append(self.streams_client.ack_stream_message(msg_id))
                        
                        # 모든 메시지 동시 처리
                        if tasks:
                            await asyncio.gather(*tasks, return_exceptions=True)
                    

                    
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    self.logger.error(f"❌ Streams 메시지 처리 오류: {e}")
                    await asyncio.sleep(1)  # 오류 시 잠시 대기
                    
        except Exception as e:
            self.logger.error(f"❌ Streams 구독 오류: {e}")
            raise
        finally:
            # pub/sub 태스크 정리
            pubsub_task.cancel()
            try:
                await pubsub_task
            except asyncio.CancelledError:
                pass
    
    async def run_pubsub_subscriber(self):
        """pub/sub 메시지 구독"""
        self.logger.info("🚀 QuestionImprovementAgent pub/sub 구독 시작")
        
        try:
            from agents.common.event_bus import subscribe_and_listen
            
            async def message_handler(channel: str, message: Dict[str, Any]):
                try:
                    self.logger.info(f"📥 pub/sub 메시지 수신: {message}")
                    
                    # 메시지 타입 확인
                    message_type = message.get("type", "")
                    target_agent = message.get("target_agent", "")
                    
                    # 이 에이전트를 대상으로 하는 메시지만 처리
                    if target_agent in ["QuestionImprovementAgent", "QuestionImprovement"]:
                        if message_type in ["NEED_CLARIFICATION", "need_clarification"]:
                            await self._handle_need_clarification_message(message)
                        else:
                            self.logger.warning(f"⚠️ 알 수 없는 pub/sub 메시지 타입: {message_type}")
                    else:
                        self.logger.debug(f"🔍 다른 에이전트용 메시지: {target_agent}")
                        
                except Exception as e:
                    self.logger.error(f"❌ pub/sub 메시지 처리 오류: {e}")
            
            await subscribe_and_listen([AGENT_TO_AGENT], message_handler, self)
                    
        except Exception as e:
            self.logger.error(f"❌ pub/sub 구독 오류: {e}")
    
    async def _handle_clarification_response_stream(self, fields: Dict[str, Any], msg_id: str):
        """Streams 기반 명료화 응답 처리"""
        try:
            # 메시지 파싱
            session_id = int(fields.get('session_id', '0'))
            clarification_answer = fields.get('clarification_answer', '')
            user_id = int(fields.get('user_id', '0'))
            
            self.logger.info(f"🔄 Streams로 명료화 답변 수신: 세션 {session_id}")
            
            # 명료화 답변 처리 - process_user_clarification_response 호출
            await self.process_user_clarification_response(session_id, clarification_answer)
            
            # 메시지 ACK
            await self.streams_client.ack_stream_message(msg_id)
            
        except Exception as e:
            self.logger.error(f"❌ Streams 명료화 응답 처리 오류: {e}")
            # 오류 시에도 ACK
            await self.streams_client.ack_stream_message(msg_id)
    
    async def _handle_process_clarification_stream(self, fields: Dict[str, Any], msg_id: str):
        """Streams 기반 명료화 처리 요청 처리"""
        try:
            # 메시지 파싱
            session_id = int(fields.get('session_id', '0'))
            request_id = fields.get('request_id', '')
            clarification_data = fields.get('clarification', {})
            
            self.logger.info(f"🔄 Streams로 명료화 처리 요청 수신: 세션 {session_id}, 요청 {request_id}")
            
            # 명료화 처리 요청 처리
            payload = {
                "session_id": session_id,
                "request_id": request_id,
                "clarification": clarification_data
            }
            await self.process_clarification_request(payload)
            
            # 메시지 ACK
            await self.streams_client.ack_stream_message(msg_id)
            
        except Exception as e:
            self.logger.error(f"❌ Streams 명료화 처리 요청 처리 오류: {e}")
            # 오류 시에도 ACK
            await self.streams_client.ack_stream_message(msg_id)
    

    async def _handle_need_clarification_message(self, message: Dict[str, Any]):
        """NEED_CLARIFICATION 메시지 처리"""
        try:
            session_id = message.get("session_id")
            question = message.get("question", "")
            context = message.get("context", "")
            classification_result = message.get("classification_result", {})
            
            self.logger.info(f"🔄 NEED_CLARIFICATION 메시지 처리: 세션 {session_id}")
            
            # 명료화 요청 처리
            await self.process_agent_clarification_request({
                "session_id": session_id,
                "question": question,
                "context": context,
                "classification_result": classification_result
            })
            
        except Exception as e:
            self.logger.error(f"❌ NEED_CLARIFICATION 메시지 처리 오류: {e}")
    
    async def process_clarification_request(self, payload: dict):
        """백엔드로부터 받은 명료화 처리 요청"""
        session_id = payload.get("session_id")
        clarification_data = payload.get("clarification", {})
        
        try:
            self.logger.info(f"🚀 백엔드 명료화 처리 요청: 세션 {session_id}")
            
            # clarification_data에서 명료화 답변 및 히스토리, 원본 질문 추출
            clarification_answer = clarification_data.get("answer", "") or clarification_data.get("clarification_answer", "")
            user_id = clarification_data.get("user_id", 0)
            clarification_history = clarification_data.get("clarification_history", [])
            original_question = clarification_data.get("original_question")
            
            if clarification_answer:
                # 명료화 답변 처리 - 히스토리 + 원본 질문도 함께 전달
                self.logger.info(f"🔄 명료화 답변 처리: 세션 {session_id} - {clarification_answer}, 히스토리 {len(clarification_history)}개, 원본: {original_question[:50] if original_question else 'None'}...")
                
                # 세션에 히스토리와 원본 질문 업데이트 (백엔드에서 받은 것으로 대체)
                if session_id in self.clarification_sessions:
                    self.clarification_sessions[session_id]["clarification_history"] = clarification_history
                    if original_question:
                        self.clarification_sessions[session_id]["original_question"] = original_question
                        self.logger.info(f"📚 세션 {session_id} 원본 질문 업데이트: {original_question[:50]}...")
                    self.logger.info(f"📚 세션 {session_id} 히스토리 업데이트: {len(clarification_history)}개 항목")
                
                await self.process_user_clarification_response(session_id, clarification_answer)
            else:
                # 명료화 세션 생성 (컨텍스트 포함)
                context = payload.get("context", "") or clarification_data.get("context", "")
                session = await self._create_clarification_session(
                    session_id, 
                    payload.get("question", ""), 
                    clarification_data.get("missing_fields", []),
                    clarification_data.get("unit_tags", []),
                    clarification_data,
                    context  # 컨텍스트 전달
                )
                
                # 첫 번째 명료화 질문 전송
                await self._generate_and_send_first_clarification(session_id, session)
            
            self.logger.info(f"✅ 명료화 처리 완료: 세션 {session_id}")
            
        except Exception as e:
            self.logger.error(f"백엔드 명료화 처리 요청 오류: {e}")
    
    async def process_agent_clarification_request(self, payload: dict):
        """다른 에이전트로부터 받은 명료화 요청 처리 - LLM 기반"""
        session_id = payload.get("session_id")
        question = payload.get("question", "")
        context = payload.get("context", "")
        classification_result = payload.get("classification_result", {})
        
        try:
            await self._send_status_update(session_id, "processing_clarification", 30)
            
            # 분류 결과에서 필요한 정보 추출
            missing_fields = classification_result.get("missing_fields", [])
            unit_tags = classification_result.get("unit_tags", [])
            
            # LLM 기반 명료화 세션 생성 (context 포함)
            session = await self._create_clarification_session(
                session_id, question, missing_fields, unit_tags, 
                classification_result, context
            )
            
            # LLM으로 첫 번째 명료화 질문 생성 및 전송
            await self._generate_and_send_first_clarification(session_id, session)
            
            await self._send_status_update(session_id, "clarification_started", 60)
                
        except Exception as e:
            await self._send_status_update(session_id, "error", 0, str(e))
            self.logger.error(f"에이전트 명료화 요청 처리 오류: {e}")

    async def _create_clarification_session(self, session_id: int, question: str, 
                                          missing_fields: List[str], unit_tags: List[str], 
                                          clarification_data: dict, context: str = "") -> Dict[str, Any]:
        """명료화 세션 생성 - LLM 기반 (배열 기반 로직 제거)"""
        # clarification_data에 questions 배열 추가 (평가 시 필요)
        clarification_data_with_questions = {
            **clarification_data,
            "questions": clarification_data.get("clarification_questions", [])
        }
        
        session_data = {
            "session_id": session_id,
            "original_question": question,
            "context": context,  # 이전 대화 맥락 저장
            "missing_fields": missing_fields,
            "unit_tags": unit_tags,
            "clarification_data": clarification_data_with_questions,
            "classification_result": clarification_data,  # 분류 결과 저장
            "status": "active",
            "clarification_count": 0,  # 명료화 횟수 카운터 추가
            "max_clarifications": 3,   # 최대 명료화 횟수 설정
            "created_at": datetime.utcnow().isoformat()
        }
        
        self.clarification_sessions[session_id] = session_data
        self.logger.info(f"📝 LLM 기반 명료화 세션 생성: 세션 {session_id}")
        
        return session_data

    async def _generate_and_send_first_clarification(self, session_id: int, session: dict):
        """분류 에이전트 제안 질문 우선 사용, 없으면 LLM으로 생성 - 스트리밍 방식"""
        try:
            # 1. 명료화 시작 알림
            await self.streams_client.send_to_backend_stream({
                "type": MessageType.CLARIFICATION_START,
                "session_id": session_id,
                "message": "명료화 질문을 준비하고 있습니다...",
                "timestamp": datetime.now().isoformat()
            })
            
            # 2. 분류 에이전트가 제안한 명료화 질문 우선 사용
            classification_result = session.get("classification_result", {})
            self.logger.info(f"🔍 classification_result: {classification_result}")
            suggested_questions = classification_result.get("clarification_questions", [])
            self.logger.info(f"🔍 suggested_questions: {suggested_questions}")
            
            clarification_question = None
            if suggested_questions and len(suggested_questions) > 0:
                # 진행 상황 스트리밍
                await self.streams_client.send_to_backend_stream({
                    "type": MessageType.CLARIFICATION_PROGRESS,
                    "session_id": session_id,
                    "message": "분류 결과를 바탕으로 명료화 질문을 선택하고 있습니다...",
                    "progress": 50,
                    "timestamp": datetime.now().isoformat()
                })
                
                clarification_question = suggested_questions[0]  # 첫 번째 제안 질문 사용
                self.logger.info(f"✅ 분류 에이전트 제안 질문 사용: {clarification_question[:50]}...")
            else:
                # 진행 상황 스트리밍
                await self.streams_client.send_to_backend_stream({
                    "type": MessageType.CLARIFICATION_PROGRESS,
                    "session_id": session_id,
                    "message": "AI가 명료화 질문을 생성하고 있습니다...",
                    "progress": 30,
                    "timestamp": datetime.now().isoformat()
                })
                
                # 2. 분류 에이전트 제안이 없으면 LLM으로 생성
                clarification_question = await self._generate_clarification_question_with_llm(session)
                self.logger.info(f"🤖 LLM으로 명료화 질문 생성: {clarification_question[:50]}...")
            
            # 3. 명료화 질문 전송 (스트리밍) - 카운트 증가
            # 첫 번째 명료화 질문을 보낼 때 카운트 증가
            session["clarification_count"] = session.get("clarification_count", 0) + 1
            self.logger.info(f"📊 명료화 질문 전송 - 횟수 증가: {session['clarification_count']}")
            
            self.logger.info(f"🔄 명료화 질문 전송 준비: 세션 {session_id}, 질문: {clarification_question}")
            
            message_data = {
                "type": MessageType.CLARIFICATION_QUESTION,
                "session_id": session_id,
                "message": clarification_question,
                "original_question": session.get("original_question", ""),
                "question_index": session["clarification_count"],
                "total_questions": session.get("max_clarifications", 3),
                "missing_fields": session.get("missing_fields", []),
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f"🔍 전송할 메시지 데이터: {message_data}")
            
            await self.streams_client.send_to_backend_stream(message_data)
            
            self.logger.info(f"📤 스트리밍으로 첫 번째 명료화 질문 전송 완료: 세션 {session_id} - {clarification_question[:50]}...")
            
        except Exception as e:
            self.logger.error(f"❌ 첫 번째 명료화 질문 생성/전송 오류: {e}")
            # 폴백 질문 전송 (스트리밍)
            fallback_question = "어떤 부분이 궁금하신가요?"
            await self.streams_client.send_to_backend_stream({
                "type": MessageType.CLARIFICATION_QUESTION,
                "session_id": session_id,
                "message": fallback_question,
                "original_question": session.get("original_question", ""),
                "question_index": 1,
                "total_questions": 1,
                "missing_fields": session.get("missing_fields", []),
                "timestamp": datetime.now().isoformat()
            })

    async def _generate_clarification_question_with_llm(self, session: dict) -> str:
        """LLM으로 명료화 질문 생성 - LLM 툴 사용"""
        try:
            original_question = session.get("original_question", "")
            missing_fields = session.get("missing_fields", [])
            knowledge_code = session.get("clarification_data", {}).get("knowledge_code", "K1")
            context = session.get("context", "")  # 이전 대화 맥락 가져오기
            
            # 프롬프트 변수 준비
            context_section = f"\n**이전 대화 맥락**: {context}\n" if context and context.strip() else ""
            
            variables = {
                "original_question": original_question,
                "knowledge_code": knowledge_code,
                "missing_fields": ', '.join(missing_fields),
                "context": context
            }
            
            # PromptBuilder를 사용하여 프롬프트 생성
            prompt = self.prompt_builder.build_prompt(
                template_name="clarification_question_generation",
                agent_name="question_improvement",
                variables=variables
            )
            
            # LLM 툴로 명료화 질문 생성
            result = await self.llm_tool.execute(
                prompt=prompt,
                variables=variables
            )
            
            if result["success"] and result["content"]:
                return result["content"].strip()
            
            # 폴백
            return "어떤 부분이 궁금하신가요?"
            
        except Exception as e:
            self.logger.error(f"❌ LLM 명료화 질문 생성 오류: {e}")
            return "어떤 부분이 궁금하신가요?"


    
    async def _send_status_update(self, session_id: int, status: str, progress: int, error: str = None):
        """상태 업데이트 전송"""
        status_data = {
            "session_id": session_id,  # session_id 사용
            "agent_name": self.name,
            "type": MessageType.STATUS_UPDATE,
            "status": status,
            "progress": progress,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if error:
            status_data["error"] = error
            status_data["type"] = MessageType.ERROR_REPORT
        
        await publish_event(AGENT_STATUS, status_data)
        self.logger.info(f"📊 상태 업데이트 전송: {status} ({progress}%)")
    
    async def _send_to_answer_agent(self, session_id: int, improved_question: str, context: str, clarification_data: dict):
        """명료화 완료 후 답변생성 에이전트로 직접 메시지 전송"""
        # 세션에서 재분류된 값 가져오기
        session = self.clarification_sessions.get(session_id, {})
        
        # 재분류된 값으로 clarification_result 업데이트
        updated_clarification_data = clarification_data.copy()
        updated_clarification_data["knowledge_code"] = session.get("reclassified_knowledge_code", "K1")
        updated_clarification_data["quality"] = AnswerabilityType.ANSWERABLE
        
        # 간소화된 메시지 구성
        message_data = {
            "session_id": session_id,
            "from_agent": self.name,
            "target_agent": "AnswerGeneratorAgent",
            "type": "GENERATE_ANSWER",
            "question": improved_question,
            "original_question": clarification_data.get("original_question", ""),
            "context": context,
            "knowledge_code": session.get("reclassified_knowledge_code", "K1"),
            "quality": AnswerabilityType.ANSWERABLE,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await publish_event(AGENT_TO_AGENT, message_data)
        self.logger.info(f"🔄 답변생성 에이전트로 명료화 완료 메시지 전송: 세션 {session_id}")
    
    async def process_user_clarification_response(self, session_id: int, user_response: str):
        """사용자 명료화 응답 처리 - LLM 기반 평가로 변경"""
        if session_id not in self.clarification_sessions:
            self.logger.warning(f"⚠️ 세션 {session_id}이 없음 - 임시 세션 생성")
            # 임시 세션 생성
            self.clarification_sessions[session_id] = {
                "session_id": session_id,
                "current_question_index": 0,
                "clarification_data": {
                    "questions": ["어떤 부분이 궁금하신가요?"]
                },
                "classification_result": {
                    "knowledge_code": "K1",
                    "missing_fields": ["정확한 용어", "단원 정보", "맥락 정보"]
                },
                "clarification_count": 0,  # 명료화 횟수 카운터 추가
                "max_clarifications": 3,   # 최대 명료화 횟수 설정
            }
        
        session = self.clarification_sessions[session_id]
        current_index = session.get("current_question_index", 0)
        clarification_data = session.get("clarification_data", {})
        questions = clarification_data.get("questions", [])
        
        try:
            # 명료화 횟수는 사용자 응답을 받을 때가 아니라 질문을 보낼 때 증가해야 함
            # 현재 명료화 횟수 확인 (증가시키지 않음)
            clarification_count = session.get("clarification_count", 0)
            max_clarifications = session.get("max_clarifications", 3)
            
            self.logger.info(f"📊 현재 명료화 횟수: {clarification_count}/{max_clarifications} (응답 처리 중)")
            
            # 현재 답변 저장
            if "user_responses" not in session:
                session["user_responses"] = {}
            session["user_responses"][str(current_index)] = user_response
            
            # 명료화 히스토리는 백엔드에서 받아온 것을 사용
            # 에이전트는 DB를 직접 조회하지 않으므로 백엔드가 보내준 히스토리를 신뢰
            # (이미 process_clarification_request에서 백엔드 히스토리로 업데이트됨)
            clarification_history = session.get("clarification_history", [])
            
            self.logger.info(f"📝 백엔드에서 받은 명료화 히스토리 사용: {len(clarification_history)}개 항목")
            if clarification_history:
                for i, item in enumerate(clarification_history, 1):
                    self.logger.info(f"  📚 히스토리 {i}: Q: {item.get('question', '')[:50]}... A: {item.get('answer', '')[:30]}...")
            
            # LLM으로 현재 답변 평가
            evaluation_result = await self._evaluate_clarification_response(
                session, current_index, user_response
            )
            
            if evaluation_result.get("evaluation") == "PASS":
                # 충분히 명료함 - 다음 missing_field로 진행 또는 완료
                await self._handle_sufficient_clarification(session_id, session, evaluation_result)
            else:
                # 추가 명료화 필요 - 다음 질문 전송 (최대 횟수 체크는 _handle_insufficient_clarification에서 수행)
                await self._handle_insufficient_clarification(session_id, session, evaluation_result)
                
        except Exception as e:
            await self._send_status_update(session_id, "error", 0, str(e))
            self.logger.error(f"명료화 응답 처리 오류: {e}")
    
    async def _handle_sufficient_clarification(self, session_id: int, session: dict, evaluation_result: Dict[str, Any]):
        """충분히 명료함을 확인했을 때 처리"""
        self.logger.info(f"✅ 충분히 명료함: {evaluation_result.get('reasoning')}")
        
        # 명료화 완료 알림 전송
        await self.streams_client.send_to_backend_stream({
            "type": MessageType.CLARIFICATION_SUFFICIENT,
            "session_id": session_id,
            "message": "충분한 정보를 수집했습니다. 답변을 생성하고 있습니다...",
            "timestamp": datetime.now().isoformat()
        })
        
        # 명료화가 완료되었으므로 바로 답변 생성으로 진행
        await self._complete_clarification(session_id, session)
    
    async def _handle_insufficient_clarification(self, session_id: int, session: dict, evaluation_result: Dict[str, Any]):
        """추가 명료화가 필요함을 확인했을 때 처리"""
        self.logger.info(f"❌ 추가 명료화 필요: {evaluation_result.get('reasoning')}")
        
        # 최대 횟수 체크 - 이미 최대치면 포기
        clarification_count = session.get("clarification_count", 0)
        max_clarifications = session.get("max_clarifications", 3)
        
        if clarification_count >= max_clarifications:
            self.logger.warning(f"⚠️ 최대 명료화 횟수({max_clarifications}) 도달 - 추가 질문 없이 unanswerable 처리")
            await self._send_unanswerable_to_answer_agent(session_id, session)
            return
        
        # LLM이 제안한 추가 명료화 질문 사용
        next_clarification = evaluation_result.get("next_clarification")
        if next_clarification:
            await self._send_additional_clarification(session_id, session, next_clarification)
        else:
            # LLM이 명료화 질문을 생성하지 못한 경우 기본 질문 사용
            default_question = "더 구체적으로 설명해주세요."
            await self._send_additional_clarification(session_id, session, default_question)
    
    async def _send_additional_clarification(self, session_id: int, session: dict, additional_question: str):
        """LLM이 제안한 추가 명료화 질문 전송"""
        self.logger.info(f"🔍 _send_additional_clarification 호출됨: 세션 {session_id}")
        
        # 추가 명료화 질문을 보낼 때도 카운트 증가
        session["clarification_count"] = session.get("clarification_count", 0) + 1
        max_clarifications = session.get("max_clarifications", 3)
        self.logger.info(f"📊 추가 명료화 질문 전송 - 횟수 증가: {session['clarification_count']}/{max_clarifications}")
        
        response_data = {
            "type": "clarification_question",  # 추가 명료화도 똑같은 명료화 질문
            "session_id": session_id,
            "message": additional_question,
            "original_question": session.get("original_question", ""),
            "question_index": session["clarification_count"],
            "total_questions": max_clarifications,
            "missing_fields": session.get("missing_fields", []),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.info(f"🔍 전송할 데이터: {response_data}")
        
        # Streams로 전송
        await self.streams_client.send_to_backend_stream(response_data)
        self.logger.info(f"📤 추가 명료화 질문 전송 완료: 세션 {session_id} - {additional_question[:50]}...")

    async def _force_clarification_completion(self, session_id: int, session: dict):
        """최대 횟수 도달 시 강제로 명료화 완료 처리"""
        try:
            self.logger.info(f"🔄 강제 명료화 완료 처리: 세션 {session_id}")
            
            # 마지막 사용자 응답을 바탕으로 최종 질문 생성
            user_responses = session.get("user_responses", {})
            last_response = ""
            if user_responses:
                last_response = list(user_responses.values())[-1]
            
            original_question = session.get("original_question", "")
            
            # 마지막 답변이 구체적인 수학 주제를 언급했다면 이를 활용
            if last_response and any(keyword in last_response for keyword in ['수열', '함수', '미분', '적분', '확률', '통계', '기하', '방정식', '그래프', '공식']):
                final_question = f"{original_question} - {last_response}"
                self.logger.info(f"📝 마지막 답변 기반 최종 질문 생성: {final_question}")
            else:
                final_question = original_question
                self.logger.info(f"📝 원본 질문 사용: {final_question}")
            
            # 강제 완료 처리
            session["final_question"] = final_question
            session["reclassified_knowledge_code"] = session.get("clarification_data", {}).get("knowledge_code", "K1")
            
            await self._complete_clarification(session_id, session)
            
        except Exception as e:
            self.logger.error(f"❌ 강제 명료화 완료 처리 오류: {e}")
            # 오류 시 unanswerable로 처리
            await self._send_unanswerable_to_answer_agent(session_id, session)

    async def _send_unanswerable_to_answer_agent(self, session_id: int, session: dict):
        """최대 명료화 횟수 초과 시 unanswerable로 분류하여 답변 에이전트에 전달"""
        self.logger.info(f"❌ 명료화 실패 - unanswerable로 답변 에이전트에 전달: 세션 {session_id}")
        
        try:
            # 상태 업데이트
            await self._send_status_update(session_id, "clarification_failed", 100)
            
            original_question = session.get("original_question", "")
            clarification_count = session.get("clarification_count", 0)
            clarification_history = session.get("clarification_history", [])
            
            # unanswerable 분류 결과를 답변 에이전트에 전달
            message_data = {
                "session_id": session_id,
                "from_agent": self.name,
                "target_agent": "AnswerGeneratorAgent",
                "type": "GENERATE_ANSWER",
                "question": original_question,
                "original_question": original_question,
                "context": session.get("context", ""),
                "knowledge_code": session.get("clarification_data", {}).get("knowledge_code", "K1"),
                "quality": "unanswerable",  # 명료화 실패로 인한 unanswerable
                "unanswerable_reason": "clarification_failed",
                "clarification_attempts": clarification_count,
                "clarification_history": clarification_history,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await publish_event(AGENT_TO_AGENT, message_data)
            self.logger.info(f"📤 unanswerable 분류 결과를 답변 에이전트에 전달: 세션 {session_id}")
            
            # 세션 정리
            if session_id in self.clarification_sessions:
                del self.clarification_sessions[session_id]
                
        except Exception as e:
            self.logger.error(f"❌ unanswerable 전달 실패: {e}")
            await self._send_status_update(session_id, "error", 0, str(e))
    
    # 키워드 매칭 기반 재분류 로직 제거됨 - LLM 기반 재분류로 대체
    
    async def _evaluate_clarification_response(self, session: dict, question_index: int, user_response: str) -> Dict[str, Any]:
        """LLM으로 명료화 답변 평가, 재분류, 최종 질문 생성 - LLM 툴 사용"""
        try:
            # 분류 결과에서 필요한 정보 가져오기
            classification_result = session.get("classification_result", {})
            original_knowledge_code = classification_result.get("knowledge_code", "K1")
            missing_fields = classification_result.get("missing_fields", [])
            
            # questions 배열 안전하게 접근
            questions = session.get("clarification_data", {}).get("questions", [])
            if question_index < len(questions) and questions:
                current_question = questions[question_index]
            else:
                # question_index가 범위를 벗어나면 에러 발생
                raise IndexError(f"question_index {question_index}가 questions 배열 범위를 벗어남. 배열 길이: {len(questions)}")
            
            # 히스토리 정보 포맷팅
            clarification_history = session.get("clarification_history", [])
            if clarification_history:
                history_items = []
                for i, item in enumerate(clarification_history, 1):
                    history_items.append(f"  {i}. 질문: {item.get('question', '')} → 답변: {item.get('answer', '')}")
                history_text = f"**명료화 대화 히스토리**:\n" + "\n".join(history_items)
            else:
                history_text = "**명료화 대화 히스토리**: 없음"
            
            # 프롬프트 변수 준비
            variables = {
                "separator_start": self.separators["start"],
                "separator_end": self.separators["end"],
                "separator_content": self.separators["content"],
                "separator_hash": self.separator_hash,
                "original_question": session.get("original_question", ""),
                "knowledge_code": original_knowledge_code,
                "missing_fields": ', '.join(missing_fields),
                "original_clarification_question": current_question,
                "user_response": user_response,
                "clarification_count": session.get("clarification_count", 0),
                "clarification_history": history_text
            }
            
            # PromptBuilder로 평가 프롬프트 생성
            evaluation_prompt = self.prompt_builder.build_prompt(
                template_name="clarification_evaluation",
                variables=variables,
                agent_name="question_improvement"
            )
            
            # LLM 툴로 평가 수행
            result = await self.llm_tool.execute(
                prompt=evaluation_prompt,
                variables=variables
            )
            
            if not result["success"]:
                return {
                    "evaluation": "NEED_MORE",
                    "confidence": 0.0,
                    "reasoning": f"LLM 평가 실패: {result['error']}",
                    "missing_field_coverage": 0.0,
                    "next_clarification": "평가 오류로 인해 추가 명료화 필요",
                    "reclassified_knowledge_code": None,
                    "final_question": None
                }
            
            # 응답 파싱 및 검증
            evaluation_result = await self._parse_evaluation_response(result["content"])
            
            # 재분류된 유형과 최종 질문을 세션에 저장
            if evaluation_result.get("reclassified_knowledge_code"):
                session["reclassified_knowledge_code"] = evaluation_result["reclassified_knowledge_code"]
                self.logger.info(f"🔄 유형 재분류: {original_knowledge_code} → {evaluation_result['reclassified_knowledge_code']}")
            
            if evaluation_result.get("final_question"):
                session["final_question"] = evaluation_result["final_question"]
                self.logger.info(f"📝 최종 질문 생성: {evaluation_result['final_question']}")
            
            self.logger.info(f"명료화 평가 결과: {evaluation_result}")
            return evaluation_result
            
        except Exception as e:
            self.logger.error(f"명료화 평가 오류: {e}")
            return {
                "evaluation": "NEED_MORE",
                "confidence": 0.0,
                "reasoning": f"평가 중 오류 발생: {e}",
                "missing_field_coverage": 0.0,
                "next_clarification": "평가 오류로 인해 추가 명료화 필요",
                "reclassified_knowledge_code": None,
                "final_question": None
            }
    
    
    async def _parse_evaluation_response(self, content: str) -> Dict[str, Any]:
        """LLM 평가 응답 파싱 및 검증 (재분류, 최종 질문 포함)"""
        try:
            self.logger.info(f"LLM 평가 원본 응답: {content}")
            
            # 보안 검증 - 구분자가 포함되어 있으면 안됨
            if any(separator in content for separator in self.separators.values()):
                self.logger.warning("LLM 응답에 구분자가 포함되어 있어 보안 위험")
                return {
                    "evaluation": "NEED_MORE",
                    "confidence": 0.0,
                    "reasoning": "보안 위험이 감지되었습니다",
                    "missing_field_coverage": 0.0,
                    "next_clarification": "보안 문제로 추가 명료화 필요",
                    "reclassified_knowledge_code": None,
                    "final_question": None
                }
            
            # JSON 추출
            json_str = extract_json_from_response(content)
            if not json_str:
                return {
                    "evaluation": "NEED_MORE", 
                    "confidence": 0.0, 
                    "reasoning": "JSON 파싱 실패",
                    "reclassified_knowledge_code": None,
                    "final_question": None
                }
            
            # JSON 파싱
            data = json.loads(json_str)
            self.logger.info(f"LLM 평가 결과: {data}")
            
            # 필수 필드 검증 및 기본값 설정
            required_fields = ["evaluation", "confidence", "reasoning", "missing_field_coverage", "reclassified_knowledge_code", "final_question"]
            data = validate_json_structure(data, required_fields)
            
            return data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 파싱 오류: {e}")
            return {
                "evaluation": "NEED_MORE", 
                "confidence": 0.0, 
                "reasoning": f"JSON 파싱 실패: {e}",
                "reclassified_knowledge_code": None,
                "final_question": None
            }
        except Exception as e:
            self.logger.error(f"응답 파싱 오류: {e}")
            return {
                "evaluation": "NEED_MORE",
                "confidence": 0.0,
                "reasoning": f"응답 파싱 오류: {e}",
                "reclassified_knowledge_code": None,
                "final_question": None
            }
    
    
    async def _complete_clarification(self, session_id: int, session: dict):
        """모든 명료화 질문 완료 처리"""
        try:
            await self._send_status_update(session_id, "processing_responses", 80)
            
            # 수집된 모든 명료화 답변들을 종합
            user_responses = session.get("user_responses", {})
            classification_result = session.get("classification_result", {})
            
            # 최종 질문이 이미 생성되어 있다면 사용, 없으면 원본 질문 사용
            final_question = session.get("final_question")
            if not final_question:
                # 간단한 폴백: 원본 질문 사용
                final_question = session.get("original_question", "질문을 이해할 수 없습니다.")
                self.logger.info(f"📝 폴백으로 원본 질문 사용: {final_question}")
            else:
                self.logger.info(f"📝 평가에서 생성된 최종 질문 사용: {final_question}")
            
            # 명료화 컨텍스트 구성
            clarification_context = await self._build_clarification_context_for_answer_generator(
                session, user_responses, classification_result
            )
            
            # 백엔드로 명료화 완료 메시지 전송 (final_question 포함)
            completion_message = {
                "session_id": session_id,
                "agent_name": self.name,
                "type": MessageType.CLARIFICATION_COMPLETE,
                "status": "clarification_complete",
                "improved_question": final_question,
                "user_responses": user_responses,
                "timestamp": datetime.utcnow().isoformat()
            }
            # Streams로 명료화 완료 메시지 전송
            await self.streams_client.send_clarification_complete(
                session_id=session_id,
                improved_question=final_question,
                user_responses=list(user_responses.values()) if user_responses else []
            )
            
            # 답변생성 에이전트로 전송 (상세한 컨텍스트 포함)
            # 재분류된 knowledge_code 사용
            reclassified_knowledge_code = session.get("reclassified_knowledge_code", classification_result.get("knowledge_code", "K1"))
            
            await self._send_to_answer_agent(
                session_id, 
                final_question, 
                clarification_context,
                {
                    **session,
                    "user_responses": user_responses,
                    "improved_question": final_question,
                    "clarification_context": clarification_context,
                    "knowledge_code": reclassified_knowledge_code  # 재분류된 유형 포함
                }
            )
            
            await self._send_status_update(session_id, "clarification_complete", 100)
            self.logger.info(f"✅ 명료화 처리 완료: 세션 {session_id}")
            
            # 세션 정리
            del self.clarification_sessions[session_id]
                
        except Exception as e:
            await self._send_status_update(session_id, "error", 0, str(e))
            self.logger.error(f"명료화 완료 처리 오류: {e}")
    
    
    async def _reclassify_knowledge_type(self, original_knowledge_code: str, user_response: str, context: str) -> str:
        """명료화 답변을 기반으로 지식 유형 재분류 - LLM 기반"""
        try:
            # LLM으로 재분류 수행
            variables = {
                "original_knowledge_code": original_knowledge_code,
                "user_response": user_response,
                "context": context
            }
            
            # 재분류 프롬프트 생성
            prompt = self.prompt_builder.build_prompt(
                template_name="knowledge_type_reclassification",
                agent_name="question_improvement",
                variables=variables
            )
            
            # LLM 툴로 재분류 수행
            result = await self.llm_tool.execute(
                prompt=prompt,
                variables=variables
            )
            
            if result["success"] and result["content"]:
                # JSON 응답에서 knowledge_code 추출
                try:
                    import json
                    reclassification_data = json.loads(result["content"])
                    new_knowledge_code = reclassification_data.get("knowledge_code", original_knowledge_code)
                    self.logger.info(f"🔄 LLM 재분류 결과: {original_knowledge_code} → {new_knowledge_code}")
                    return new_knowledge_code
                except (json.JSONDecodeError, KeyError) as e:
                    self.logger.warning(f"재분류 응답 파싱 실패: {e}, 원본 유지")
                    return original_knowledge_code
            else:
                self.logger.warning(f"LLM 재분류 실패: {result.get('error', 'Unknown error')}, 원본 유지")
                return original_knowledge_code
                
        except Exception as e:
            self.logger.error(f"지식 유형 재분류 오류: {e}")
            return original_knowledge_code

    async def _build_clarification_context_for_answer_generator(self, session: dict, user_responses: Dict[str, str], 
                                         classification_result: dict) -> Dict[str, Any]:
        """명료화 컨텍스트 구성 - 답변 생성기용"""
        try:
            original_knowledge_code = classification_result.get("knowledge_code", "K1")
            missing_fields = classification_result.get("missing_fields", [])
            
            # 명료화 답변을 기반으로 유형 재분류 시도 (첫 번째 답변 사용)
            first_response = list(user_responses.values())[0] if user_responses else ""
            knowledge_code = await self._reclassify_knowledge_type(original_knowledge_code, first_response, "명료화 답변")
            
            # 각 missing_field별로 수집된 정보 매핑
            field_mapping = {}
            for field in missing_fields:
                field_mapping[field] = "정보 없음"
            
            # 사용자 응답을 missing_field와 연결
            clarification_questions = session.get("clarification_data", {}).get("questions", [])
            for question_idx, response in user_responses.items():
                if question_idx.isdigit() and int(question_idx) < len(clarification_questions):
                    question = clarification_questions[int(question_idx)]
                    # 질문과 missing_field 연결 (간단한 매핑)
                    for field in missing_fields:
                        if field.lower() in question.lower():
                            field_mapping[field] = response
                            break
            
            context = {
                "knowledge_type": knowledge_code,
                "original_question": session.get("original_question", ""),
                "missing_fields_covered": field_mapping,
                "clarification_summary": {
                    "total_questions": len(clarification_questions),
                    "answered_questions": len(user_responses),
                    "coverage_rate": len([v for v in field_mapping.values() if v != "정보 없음"]) / len(missing_fields) if missing_fields else 0
                },
                "user_responses_detail": user_responses,
                "unit_tags": classification_result.get("unit_tags", []),
                "policy_flags": classification_result.get("policy_flags", {})
            }
            
            self.logger.info(f"📋 명료화 컨텍스트 구성: {context}")
            return context
            
        except Exception as e:
            self.logger.error(f"명료화 컨텍스트 구성 오류: {e}")
            return {
                "knowledge_type": "K1",
                "original_question": session.get("original_question", ""),
                "error": f"컨텍스트 구성 실패: {e}"
            }
    
    
    
    
    async def process_message(self, message_type: str, payload: Dict[str, Any]):
        """메시지 처리 (BaseAgent 병렬 처리용)"""
        try:
            if message_type in ["CLARIFICATION_REQUEST", "clarification_request"]:
                await self.process_clarification_request(payload)
            elif message_type in ["NEED_CLARIFICATION", "need_clarification"]:
                await self.process_agent_clarification_request(payload)
            else:
                self.logger.warning(f"알 수 없는 메시지 타입: {message_type}")
        except Exception as e:
            self.logger.error(f"메시지 처리 오류: {e}")
    
    async def process_task(self, task: Task) -> Dict[str, Any]:
        """기존 Task 처리 메서드 (호환성 유지)"""
        # 새로운 채널 구조에서는 사용되지 않음
        return {
            "error": "새로운 채널 구조에서는 process_task 대신 process_clarification_request를 사용합니다.",
            "success": False,
            "agent": self.name
        }

 