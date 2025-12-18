"""
답변 생성 전문 에이전트 - 새로운 3개 채널 구조 사용
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
    format_prompt_with_variables,
    extract_json_from_response
)
from agents.common.config_loader import PromptConfigLoader
from agents.common.prompt_builder import PromptBuilder
from agents.common.constants import AnswerabilityType
from agents.common.event_bus import (
    publish_event,
    subscribe_and_listen,
    AGENT_TO_AGENT,
    MessageType
)
from utils.redis_streams_client import AgentRedisStreamsClient
from agents.common.llm_tool import SpecializedLLMTool, LLMConfig

logger = logging.getLogger(__name__)

class AnswerGeneratorAgent(BaseAgent):
    """수학 교육 답변 생성 전문 에이전트 - 새로운 채널 구조"""
    
    def __init__(self):
        super().__init__(name="AnswerGeneratorAgent", role="answer_generator")  # BaseAgent 초기화 (logger 포함)
        
        # Redis Streams 클라이언트 초기화
        self.streams_client = AgentRedisStreamsClient("AnswerGeneratorAgent")
        
        # 프롬프트 설정 로더 초기화
        self.config_loader = PromptConfigLoader()
        
        # AnswerGenerator 에이전트 설정 로드
        yaml_data = self.config_loader.get_agent_config("answer_generator")
        if not yaml_data:
            self.logger.error("AnswerGenerator 설정을 로드할 수 없습니다")
            raise RuntimeError("AnswerGenerator 설정 로드 실패")
        
        # 프롬프트 빌더 초기화
        self.prompt_builder = PromptBuilder(yaml_data)
        
        # YAML 데이터를 인스턴스 변수로 저장
        self.prompt_config = yaml_data
        
        if yaml_data and "templates" in yaml_data:
            self.logger.info(f"🔍 templates 직접 접근 가능: {list(yaml_data['templates'].keys())}")
        elif yaml_data and "answer_generator" in yaml_data:
            answer_gen_config = yaml_data["answer_generator"]
            self.logger.info(f"🔍 answer_generator 키: {list(answer_gen_config.keys())}")
            if "templates" in answer_gen_config:
                self.logger.info(f"🔍 templates 키: {list(answer_gen_config['templates'].keys())}")
            else:
                self.logger.warning(f"⚠️ answer_generator 안에 templates 키가 없습니다!")
        else:
            self.logger.warning(f"⚠️ templates를 찾을 수 없습니다!")
        
        # LLM 툴 초기화
        self.llm_tool = SpecializedLLMTool.create_answer_generator_tool()
        
        # 시스템 프롬프트는 PromptBuilder를 통해 동적으로 생성
        
        # 툴 제거 - 함수로 대체
        super().__init__(
            name="AnswerGenerator",
            role="수학 교육 답변 생성",
            system_prompt="",  # PromptBuilder를 통해 동적으로 생성
            tools=[]  # 툴 없음
        )
    
    
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
        self.logger.info("🚀 AnswerGeneratorAgent Streams + pub/sub 구독 시작")
        
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
                            if target_agent not in ["AnswerGeneratorAgent", "AnswerGenerator"]:
                                tasks.append(self.streams_client.ack_stream_message(msg_id_str))
                                continue
                            
                            # 메시지 처리 태스크 생성
                            if message_type == "generate_answer":
                                tasks.append(self._handle_answer_generation_stream(fields, msg_id_str))
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
        """pub/sub 기반 메시지 수신 (AnswerGeneratorAgent 전용)"""
        self.logger.info("🚀 AnswerGeneratorAgent pub/sub 구독 시작")
        
        async def message_handler(channel: str, payload: Dict[str, Any]):
            try:
                target_agent = payload.get("target_agent")
                message_type = payload.get("type")
                
                # 자기 에이전트로 온 메시지가 아니면 즉시 리턴
                if target_agent not in ["AnswerGeneratorAgent", "AnswerGenerator"]:
                    return
                
                self.logger.info(f"📥 pub/sub 메시지 수신: channel={channel}, target_agent={target_agent}, type={message_type}")
                self.logger.info(f"🔍 payload 내용: {payload}")
                
                if message_type in ["READY_FOR_ANSWER", "ready_for_answer"]:
                    self.logger.info(f"🔄 READY_FOR_ANSWER 처리 시작 (병렬)")
                    # BaseAgent의 병렬 처리 메서드 사용 (await 없이)
                    asyncio.create_task(self.process_message_parallel(message_type, payload))
                elif message_type in ["GENERATE_ANSWER", "generate_answer"]:
                    self.logger.info(f"🔄 GENERATE_ANSWER 처리 시작 (병렬)")
                    # BaseAgent의 병렬 처리 메서드 사용 (await 없이)
                    asyncio.create_task(self.process_message_parallel(message_type, payload))
                else:
                    self.logger.warning(f"⚠️ 알 수 없는 pub/sub 메시지 타입: {message_type}")
                    
            except Exception as e:
                self.logger.error(f"pub/sub 메시지 처리 오류: {e}")
        
        # AGENT_TO_AGENT 채널 구독
        from agents.common.event_bus import subscribe_and_listen, AGENT_TO_AGENT
        await subscribe_and_listen([AGENT_TO_AGENT], message_handler, self)
        self.logger.info("✅ AnswerGeneratorAgent pub/sub 메시지 구독 시작")
    
    async def process_answer_generation_request(self, payload: Dict[str, Any]):
        """pub/sub으로 받은 답변 생성 요청 처리"""
        import time
        start_time = time.time()
        
        try:
            # 메트릭: 요청 시작
            if self.metrics:
                self.metrics.increment_counter("answer_requests_total")
                self.metrics.set_gauge("active_sessions", len(self.processed_sessions) + 1)
            
            self.logger.info(f"🔍 process_answer_generation_request 시작")
            self.logger.info(f"🔍 payload 타입: {type(payload)}")
            self.logger.info(f"🔍 payload 키들: {list(payload.keys()) if isinstance(payload, dict) else 'NOT_DICT'}")
            
            session_id = payload.get("session_id")
            question = payload.get("question", "")
            context = payload.get("context", "")
            
            self.logger.info(f"🔍 session_id: {session_id}")
            self.logger.info(f"🔍 question 길이: {len(question)}")
            self.logger.info(f"🔍 context 타입: {type(context)}")
            
            # QuestionImprovement에서 직접 보낸 메시지인지 확인
            from_agent = payload.get("from_agent")
            self.logger.info(f"🔍 from_agent 값: '{from_agent}'")
            self.logger.info(f"🔍 from_agent 타입: {type(from_agent)}")
            self.logger.info(f"🔍 payload 전체: {payload}")
            
            # evaluation_data 초기화
            evaluation_data = {}
            
            if from_agent == "QuestionImprovement":
                # QuestionImprovement에서 보낸 간소화된 메시지 구조 처리
                evaluation_data = {
                    "knowledge_code": payload.get("knowledge_code", "K1"),
                    "quality": payload.get("quality", "answerable"),
                    "unanswerable_reason": payload.get("unanswerable_reason", ""),
                    "clarification_attempts": payload.get("clarification_attempts", 0),
                    "original_question": payload.get("original_question", payload.get("question", ""))
                }
                self.logger.info(f"🔄 QuestionImprovement에서 온 답변 요청: 세션 {session_id}")
                self.logger.info(f"📝 질문: {question}")
                self.logger.info(f"🔍 knowledge_code: {evaluation_data['knowledge_code']}")
                self.logger.info(f"🔍 quality: {evaluation_data['quality']}")
            else:
                # 기존 백엔드에서 온 메시지 구조 처리
                classification_result = payload.get("classification_result", {})
                evaluation_data = classification_result if classification_result else payload.get("evaluation", {})
                
                self.logger.info(f"🔄 백엔드에서 온 답변 요청: 세션 {session_id}")
                self.logger.info(f"📝 질문: {question}")
                self.logger.info(f"🔍 classification_result: {classification_result}")
                self.logger.info(f"🔍 evaluation_data: {evaluation_data}")
                self.logger.info(f"🔍 evaluation_data['quality']: {evaluation_data.get('quality', 'NOT_FOUND')}")
            
            # 처리 로그 발행
            await self._publish_processing_log(session_id, "answer_start", "답변 생성 시작")
            
            # 답변 생성
            self.logger.info(f"🔍 _generate_answer 호출 전 evaluation_data: {evaluation_data}")
            result = await self._generate_answer(
                question=question,
                context=context,
                evaluation=evaluation_data,
                session_id=session_id
            )
            
            # 처리 시간 측정
            duration = time.time() - start_time
            
            if result:
                # 메트릭: 성공
                if self.metrics:
                    self.metrics.record_request("answer_generation", success=True, duration=duration)
                    self.metrics.increment_counter("answer_success_total")
                
                # result가 문자열인 경우 딕셔너리로 변환
                if isinstance(result, str):
                    result = {
                        "educational_answer": result,
                        "knowledge_code": evaluation_data.get("knowledge_code", "K1"),
                        "answerability": evaluation_data.get("quality", "answerable"),
                        "clarification_used": False,
                        "context_used": len(context) if context else 0
                    }
                
                # 답변 결과를 Streams로 백엔드에 전송
                await self._send_answer_to_backend(session_id, result)
                
                # ObserverAgent에게 요약 요청 전송
                await self._trigger_observer_summary(session_id, question, result["educational_answer"], result)
                
                # 처리 로그 발행
                await self._publish_processing_log(session_id, "answer_complete", "답변 생성 완료")
                
                self.logger.info(f"✅ 답변 생성 및 전송 완료: 세션 {session_id}")
            else:
                # 메트릭: 실패
                if self.metrics:
                    self.metrics.record_request("answer_generation", success=False, duration=duration)
                    self.metrics.increment_counter("answer_failed_total")
                    self.metrics.record_error("generation_failed", "answer_generation")
                
                # 처리 로그 발행
                await self._publish_processing_log(session_id, "answer_failed", "답변 생성 실패")
                
                self.logger.error(f"❌ 답변 생성 실패: 세션 {session_id}")
                
        except Exception as e:
            # 처리 시간 측정
            duration = time.time() - start_time
            
            # 메트릭: 에러
            if self.metrics:
                self.metrics.record_request("answer_generation", success=False, duration=duration)
                self.metrics.record_error("exception", "answer_generation")
            
            # 처리 로그 발행
            try:
                await self._publish_processing_log(session_id, "answer_error", f"오류 발생: {str(e)}")
            except:
                pass
            
            self.logger.error(f"❌ 답변 생성 요청 처리 오류: {e}")
        finally:
            # 메트릭: 활성 세션 감소
            if self.metrics:
                self.metrics.set_gauge("active_sessions", len(self.processed_sessions))
    
    async def _send_answer_to_backend(self, session_id: int, result: Dict[str, Any]):
        """Streams로 백엔드에 답변 결과 전송"""
        try:
            answer = result.get("educational_answer", "")
            knowledge_code = result.get("knowledge_code", "K1")
            answerability = result.get("answerability", "answerable")
            clarification_used = result.get("clarification_used", False)
            context_used = result.get("context_used", 0)
            
            # 디버깅: 실제 answer 길이 확인
            self.logger.info(f"🔍 전송할 answer 길이: {len(answer)}자")
            self.logger.info(f"🔍 answer 끝부분(마지막 100자): ...{answer[-100:] if len(answer) > 100 else answer}")
            
            # Streams로 답변 결과 전송
            await self.streams_client.send_to_backend_stream({
                "type": MessageType.ANSWER_RESULT,
                "session_id": session_id,
                "answer": answer,
                "knowledge_code": knowledge_code,
                "answerability": answerability,
                "clarification_used": clarification_used,
                "context_used": context_used,
                "timestamp": datetime.now().isoformat()
            })
            
            self.logger.info(f"📤 백엔드에 답변 결과 전송: 세션 {session_id}, 답변 길이 {len(answer)}자")
            
        except Exception as e:
            self.logger.error(f"❌ 백엔드 답변 전송 오류: {e}")
            raise
    
    async def _trigger_observer_summary(self, session_id: int, question: str, answer: str, result: Dict[str, Any]):
        """ObserverAgent에게 요약 요청 전송 (pub/sub)"""
        try:
            conversation_text = f"""학생 질문: {question}

에이전트 답변: {answer}

추가 정보:
- 지식 유형: {result.get('knowledge_code', 'K1')}
- 답변 가능성: {result.get('answerability', 'answerable')}
- 명료화 사용: {result.get('clarification_used', False)}
- 맥락 사용: {result.get('context_used', 0)}자"""
            
            from agents.common.event_bus import publish_event, AGENT_TO_AGENT
            
            # request_id 생성 (UUID 사용)
            import uuid
            request_id = str(uuid.uuid4())
            
            await publish_event(
                AGENT_TO_AGENT,
                {
                    "type": "generate_summary",
                    "target_agent": "ObserverAgent",
                    "session_id": session_id,
                    "request_id": request_id,
                    "conversation_text": conversation_text,
                    "question": question,
                    "answer": answer,
                    "context": {
                        "knowledge_code": result.get('knowledge_code', 'K1'),
                        "answerability": result.get('answerability', 'answerable'),
                        "clarification_used": result.get('clarification_used', False),
                        "context_used": result.get('context_used', 0)
                    },
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            self.logger.info(f"📤 ObserverAgent에게 요약 요청 전송: 세션 {session_id}")
            
        except Exception as e:
            self.logger.error(f"❌ ObserverAgent 요약 요청 전송 오류: {e}")
    
    
    
    
    
    async def _generate_answer(self, question: str, context: str, evaluation: dict, session_id: int = None) -> Dict[str, Any]:
        """답변 생성 - 기존 PromptGeneratorTool 로직을 함수로 변환"""
        try:
            self.logger.info(f"답변 생성 시작: {question[:50]}...")
            
            # 질문 유형과 답변 가능 여부 추출
            knowledge_code = evaluation.get("knowledge_code", "K1")
            quality = evaluation.get("quality", "")
            
            # 디버깅: evaluation 데이터 로그 출력
            self.logger.info(f"🔍 evaluation 전체 데이터: {evaluation}")
            self.logger.info(f"🔍 분류 결과 - knowledge_code: {knowledge_code}, quality: '{quality}'")
            
            # quality 값에 따른 처리 (AnswerGenerator는 answerable 질문만 처리)
            if quality == "" or quality == AnswerabilityType.UNANSWERABLE:
                answerability = AnswerabilityType.UNANSWERABLE
                self.logger.info(f"🚫 unanswerable로 판정: quality='{quality}'")
            elif quality == AnswerabilityType.NEEDS_CLARIFY:
                # AnswerGenerator는 needs_clarify를 처리하지 않음 - 이는 QuestionClassifier에서 처리되어야 함
                self.logger.error(f"❌ AnswerGenerator가 needs_clarify 질문을 받았습니다: quality='{quality}' - 이는 QuestionClassifier에서 처리되어야 합니다")
                return {"error": "needs_clarify 질문은 AnswerGenerator가 처리할 수 없습니다", "success": False}
            else:
                answerability = quality
                self.logger.info(f"✅ answerable로 판정: quality='{quality}'")
            
            # unanswerable 질문에 대한 고정된 응답 (LLM 호출 없음)
            if answerability == AnswerabilityType.UNANSWERABLE or quality == "unanswerable":
                self.logger.info("🚫 unanswerable 질문 - 고정된 거절 응답 반환")
                
                # 거절 이유에 따라 다른 메시지 반환
                unanswerable_reason = evaluation.get("unanswerable_reason", "")
                if unanswerable_reason == "clarification_failed":
                    actual_answer = self._get_clarification_failed_response(evaluation)
                else:
                    actual_answer = self._get_fixed_unanswerable_response()
                
                result = {
                    "educational_answer": actual_answer,
                    "prompt_used": "고정된 거절 응답",
                    "success": True,
                    "question": question,
                    "knowledge_code": knowledge_code,
                    "answerability": answerability,
                    "unanswerable": True
                }
                return result
            
            # 상황에 맞는 프롬프트 생성
            prompt = self._select_prompt_by_type(knowledge_code, answerability, question, context, evaluation)
            
            # 맥락 정보 추가
            enhanced_prompt = self._enhance_prompt_with_context(prompt, context, evaluation)
            
            # LLM을 통해 실제 교육적 답변 생성 (스트리밍)
            self.logger.info("LLM을 통해 실제 답변 생성 시작...")
            actual_answer = await self._generate_answer_with_llm(question, enhanced_prompt, context, session_id, knowledge_code, answerability)
            
            result = {
                "educational_answer": actual_answer,
                "prompt_used": enhanced_prompt,
                "success": True,
                "question": question,
                "context_used": len(context),
                "evaluation_used": evaluation is not None,
                "clarification_used": False,
                "knowledge_code": knowledge_code,
                "answerability": answerability
            }

            self.logger.info(f"답변 생성 완료: {len(actual_answer)}자")
            self.logger.info(f"🔍 actual_answer 끝부분(마지막 100자): ...{actual_answer[-100:] if len(actual_answer) > 100 else actual_answer}")
            return result

        except Exception as e:
            self.logger.error(f"답변 생성 오류: {e}")
            return {"error": str(e), "success": False}
    
    
    def _select_prompt_by_type(self, knowledge_code: str, answerability: str, question: str = "", context: str = "", evaluation: dict = None) -> str:
        """질문 유형별 프롬프트 선택 - YAML 기반"""
        self.logger.info(f"🔍 프롬프트 선택: knowledge_code={knowledge_code}, answerability={answerability}")
        
        # 답변 불가능한 질문에 대한 특별 처리
        if answerability == AnswerabilityType.UNANSWERABLE:
            self.logger.info(f"🚫 답변 불가능한 질문으로 분류됨 - 수학 외 영역 안내 메시지 생성")
            return self._get_unanswerable_prompt()
        
        # prompt_config 구조에 따라 접근 방식 결정
        if "templates" in self.prompt_config:
            # prompt_config가 직접 answer_generator 설정인 경우
            templates = self.prompt_config.get("templates", {})
        elif "answer_generator" in self.prompt_config:
            # prompt_config가 전체 설정이고 answer_generator 키가 있는 경우
            answer_generator_config = self.prompt_config.get("answer_generator", {})
            templates = answer_generator_config.get("templates", {})
        else:
            self.logger.error(f"❌ templates를 찾을 수 없습니다!")
            templates = {}
        
        # PromptBuilder를 사용하여 프롬프트 생성
        try:
            # 변수 준비
            variables = {
                "knowledge_type": knowledge_code,
                "original_question": question,
                "clarification_summary": evaluation.get("clarification_summary", "없음"),
                "answer_structure": self._get_answer_structure(knowledge_code),
                "tone_guide": self.prompt_builder.get_setting("answer_generator", "common.tone") or "친근하고 이해하기 쉬운 교사 톤",
                "language_guide": self.prompt_builder.get_setting("answer_generator", "common.language") or "한국어, 고등학생 수준에 맞는 표현",
                "structure_guide": self.prompt_builder.get_setting("answer_generator", "common.structure") or "체계적이고 논리적인 구성",
                "examples_guide": self.prompt_builder.get_setting("answer_generator", "common.examples") or "구체적이고 실제적인 예시 포함",
                "clarification_when_used": self.prompt_builder.get_setting("answer_generator", "clarification_integration.when_used") or "명료화 과정을 거친 질문에 대한 답변",
                "clarification_approach": self.prompt_builder.get_setting("answer_generator", "clarification_integration.approach") or "명료화 응답을 바탕으로 더 정확하고 맞춤형 답변 생성",
                "clarification_structure": self.prompt_builder.get_setting("answer_generator", "clarification_integration.structure") or "명료화 과정 요약, 수집된 정보를 바탕으로 한 답변, 추가 설명 및 예시",
                "formatting_rules": self.prompt_builder.get_setting("answer_generator", "formatting_rules") or "모든 수학 수식은 LaTeX 형식으로 작성하세요"
            }
            
            # PromptBuilder로 프롬프트 생성
            prompt = self.prompt_builder.build_prompt(
                template_name="answer_generation", 
                agent_name="answer_generator",
                variables=variables
            )
            template = prompt.get("system", "")
            
            self.logger.info(f"🔍 PromptBuilder로 생성된 템플릿 길이: {len(template)}")
            
            if not template:
                raise ValueError(f"PromptBuilder에서 프롬프트 생성 실패")
                
            return template
            
        except Exception as e:
            self.logger.error(f"❌ PromptBuilder 사용 중 오류: {e}")
            # 폴백: 기본 템플릿 사용
            answer_generation_template = templates.get("answer_generation", {})
            template = answer_generation_template.get("system", "")
            return template
    
    def _get_answer_structure(self, knowledge_code: str) -> str:
        """답변 유형별 구조 가져오기"""
        settings = self.prompt_config.get("settings", {})
        answer_types = settings.get("answer_types", {})
        answer_type_config = answer_types.get(knowledge_code.lower(), {})
        
        structure_list = answer_type_config.get("structure", [])
        if structure_list:
            return "\n".join([f"- {item}" for item in structure_list])
        else:
            return "기본 답변 구조"
    
    def _get_fixed_unanswerable_response(self) -> str:
        """unanswerable 질문에 대한 고정된 거절 응답"""
        return "안녕하세요! 😊 MAICE는 수학 학습을 도와주는 AI 튜터입니다. 현재는 수학 교과와 관련된 질문만 답변해드릴 수 있어요. 수학 문제나 개념에 대해 궁금한 것이 있으시면 언제든지 질문해주세요! 📚✨"
    
    def _get_clarification_failed_response(self, evaluation: dict) -> str:
        """명료화 실패로 인한 거절 응답 (정해진 메시지)"""
        original_question = evaluation.get("original_question", "질문")
        clarification_attempts = evaluation.get("clarification_attempts", 3)
        
        return f"""죄송합니다! 😅

**'{original_question}'** 질문에 대해 {clarification_attempts}번의 명료화를 시도했지만, 명확한 답변을 드리기 어려운 상황입니다.

## 🔄 **다시 질문해주세요**
더 구체적이고 명확한 질문으로 다시 물어보시면 정확한 답변을 드릴 수 있습니다.

### 💡 **좋은 질문 예시**:
- **"지수함수의 정의를 알려주세요"**
- **"로그의 성질을 설명해주세요"**  
- **"삼각함수 sin, cos, tan의 관계를 알려주세요"**
- **"등차수열의 일반항 구하는 방법을 알려주세요"**
- **"수학적 귀납법으로 증명하는 방법을 알려주세요"**

## 🎯 **질문 팁**
- 구체적인 수학 개념이나 문제를 명시해주세요
- "어떤 부분"이 궁금한지 구체적으로 말씀해주세요
- 예시나 구체적인 문제가 있으면 함께 알려주세요

새로운 질문을 기다리고 있겠습니다! 😊 함께 수학을 공부해봐요! 💪"""
    
    # def _get_unanswerable_prompt(self) -> str:
    #     """답변 불가능한 질문에 대한 프롬프트 생성 - DEPRECATED: 사용하지 않음"""
    #     return """당신은 수학 교육 전문 AI MAICE입니다. 
    # 
    # 학생이 수학 외의 영역에 대한 질문을 했습니다. 이 경우 다음과 같이 응답해야 합니다:
    # 
    # **응답 원칙:**
    # - 수학 교과와 관련된 질문만 답변 가능하다는 점을 친근하게 안내
    # - 수학 관련 질문을 요청하는 메시지 제공
    # - 친근하고 따뜻한 톤으로 응답
    # 
    # **응답 형식:**
    # 안녕하세요! 😊 MAICE는 수학 학습을 도와주는 AI 튜터입니다. 
    # 현재는 수학 교과와 관련된 질문만 답변해드릴 수 있어요. 
    # 수학 문제나 개념에 대해 궁금한 것이 있으시면 언제든지 질문해주세요! 📚✨
    # 
    # **응답 시 주의사항:**
    # - 수학 외 영역에 대한 직접적인 답변은 제공하지 않음
    # - 친근하고 따뜻한 톤 유지
    # - 이모지를 적절히 사용하여 친근감 표현
    # - 수학 관련 질문을 유도하는 메시지로 마무리
    # - 질문과 연관된 수학 개념들을 창의적으로 연결
    # - 구체적이고 실생활과 연관된 예시 제시
    # - 친근하고 격려하는 톤 유지
    # - 이모지 적절히 사용"""
    
    def _enhance_prompt_with_context(self, prompt: str, context: str, evaluation: dict) -> str:
        """프롬프트에 맥락 정보 추가"""
        try:
            # 기본 프롬프트에 맥락 정보 추가
            if context:
                context_section = f"\n\n## 맥락 정보:\n{context}\n"
                prompt = prompt + context_section
            
            # 평가 정보가 있으면 추가
            if evaluation:
                knowledge_code = evaluation.get("knowledge_code", "K1")
                quality = evaluation.get("quality", "answerable")
                
                evaluation_section = f"\n\n## 질문 분석 정보:\n- 질문 유형: {knowledge_code}\n- 답변 가능성: {quality}\n"
                prompt = prompt + evaluation_section
            
            return prompt
            
        except Exception as e:
            self.logger.error(f"프롬프트 맥락 추가 오류: {e}")
            return prompt  # 오류 시 원본 프롬프트 반환
    
    
    async def _generate_answer_with_llm(self, question: str, prompt: str, context: str = "", session_id: int = None, knowledge_code: str = "", answerability: str = "") -> str:
        """LLM을 통해 스트리밍 답변 생성 및 실시간 백엔드 전송 - LLM 툴 사용"""
        try:
            # 프롬프트 변수 준비
            variables = {
                "question": question,
                "knowledge_type": knowledge_code if knowledge_code else "미분류",
                "original_question": question,
                "clarification_summary": "명료화 과정을 거쳐 구체화된 질문",
                "answerability": answerability if answerability else "미분류",
                "context": context if context else "없음"
            }
            
            # 이미 _select_prompt_by_type에서 생성된 프롬프트 사용
            # prompt는 이미 변수 치환이 완료된 상태
            
            # PromptBuilder에서 생성된 전체 프롬프트 사용 (system + user 템플릿 모두 포함)
            full_prompt = self.prompt_builder.build_prompt(
                template_name="answer_generation", 
                agent_name="answer_generator",
                variables=variables
            )
            
            # LLM 툴로 답변 생성 - create_answer_generator_tool()의 기본 설정 사용 (max_tokens=4000, stream=True, timeout=60)
            result = await self.llm_tool.execute(
                prompt=full_prompt,
                variables=variables,
                session_id=session_id,
                streams_client=self.streams_client
            )
            
            if not result["success"]:
                return f"답변 생성 중 오류가 발생했습니다: {result['error']}"
            
            # LLM tools에서 스트리밍 처리가 완료되어 content 반환
            full_answer = result["content"] if isinstance(result, dict) else str(result)
            
            # 디버깅: LLM에서 받은 답변 길이 확인
            self.logger.info(f"🔍 LLM에서 받은 full_answer 길이: {len(full_answer)}자")
            self.logger.info(f"🔍 full_answer 끝부분(마지막 100자): ...{full_answer[-100:] if len(full_answer) > 100 else full_answer}")
            
            # 실시간 청크 전송은 LLM tools에서 이미 처리됨
            # 추가적인 청크 전송은 불필요
            
            return full_answer
            
        except Exception as e:
            self.logger.error(f"LLM 스트리밍 답변 생성 오류: {e}")
            return f"답변 생성 중 오류가 발생했습니다: {str(e)}"
    
    async def _send_answer_to_backend_realtime(self, session_id: int, full_answer: str):
        """실시간 답변 전송 (청크 단위로 분할)"""
        try:
            # 답변을 청크 단위로 분할 (15자씩)
            chunk_size = 15
            chunks = [full_answer[i:i+chunk_size] for i in range(0, len(full_answer), chunk_size)]
            
            self.logger.info(f"📤 실시간 답변 전송 시작: {len(chunks)}개 청크")
            
            # 각 청크를 순차적으로 전송
            for i, chunk in enumerate(chunks, 1):
                await self._send_answer_chunk_to_backend(session_id, chunk, i)
                # 실시간 느낌을 위해 약간의 지연
                await asyncio.sleep(0.05)
            
            # 최종 청크 전송
            await self._send_final_chunk(session_id, len(chunks))
            
            self.logger.info(f"✅ 실시간 답변 전송 완료: 세션 {session_id}")
            
        except Exception as e:
            self.logger.error(f"❌ 실시간 답변 전송 오류: {e}")
    
    
    async def _send_answer_chunk_to_backend(self, session_id: int, chunk: str, chunk_index: int):
        """답변 청크를 백엔드로 실시간 전송 (재시도 로직 포함)"""
        max_retries = 3
        retry_delay = 0.1  # 100ms
        
        for attempt in range(max_retries):
            try:
                await self.streams_client.send_to_backend_stream({
                    "type": MessageType.ANSWER_CHUNK,
                    "session_id": session_id,
                    "chunk": chunk,
                    "chunk_index": chunk_index,
                    "is_final": False,
                    "timestamp": datetime.now().isoformat()
                })
                # 청크 전송 성공 - 재시도한 경우에만 로깅
                if attempt > 0:
                    self.logger.info(f"✅ 청크 {chunk_index} 전송 성공 (재시도 {attempt}회 후)")
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))  # 지수 백오프
                else:
                    self.logger.error(f"❌ 청크 {chunk_index} 전송 최종 실패: {e}")
                    # 최종 실패 시에도 청크는 건너뛰지 않고 계속 진행
    
    async def _send_final_chunk(self, session_id: int, chunk_count: int):
        """마지막 청크 전송 (is_final: True)"""
        try:
            await self.streams_client.send_to_backend_stream({
                "type": "answer_chunk",
                "session_id": session_id,
                "chunk": "",  # 빈 청크로 완료 신호
                "chunk_index": chunk_count + 1,
                "is_final": True,
                "timestamp": datetime.now().isoformat()
            })
            self.logger.info(f"📤 최종 청크 전송 완료: 세션 {session_id}")
        except Exception as e:
            self.logger.error(f"❌ 최종 청크 전송 실패: {e}")
    
    
    async def process_message(self, message_type: str, payload: Dict[str, Any]):
        """메시지 처리 (BaseAgent 병렬 처리용)"""
        try:
            if message_type in ["READY_FOR_ANSWER", "ready_for_answer", "GENERATE_ANSWER", "generate_answer"]:
                await self.process_answer_generation_request(payload)
            else:
                self.logger.warning(f"알 수 없는 메시지 타입: {message_type}")
        except Exception as e:
            self.logger.error(f"메시지 처리 오류: {e}")
    
    async def _publish_processing_log(self, session_id: int, stage: str, message: str):
        """처리 로그를 Redis에 발행"""
        try:
            await self.streams_client.send_to_backend_stream({
                "type": "processing_log",
                "agent_name": "AnswerGenerator",
                "session_id": session_id,
                "stage": stage,
                "message": message,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            self.logger.debug(f"처리 로그 발행 실패 (무시): {e}")
    
    async def process_task(self, task: Task) -> Any:
        """작업 처리 (BaseAgent 호환성)"""
        try:
            # Task 객체를 payload로 변환
            payload = {
                "session_id": task.id,
                "question": task.description,
                "context": task.metadata.get("context", ""),
                "evaluation": task.metadata.get("evaluation", {})
            }
            
            # 기존 답변 생성 로직 사용
            await self.process_answer_generation_request(payload)
            
            return {"success": True, "task_id": task.id}
            
        except Exception as e:
            self.logger.error(f"Task 처리 오류: {e}")
            return {"success": False, "error": str(e), "task_id": task.id}
    
    