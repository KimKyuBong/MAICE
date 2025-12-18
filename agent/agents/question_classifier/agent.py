"""
질문 분류 전문 에이전트 - 새로운 3개 채널 구조 사용
"""

import logging
import os
import json
import asyncio
from typing import Dict, Any, List
from datetime import datetime
from agents.base_agent import BaseAgent, Task
from agents.common.prompt_utils import (
    sanitize_text,
    validate_prompt_content,
    generate_safe_separators,
    create_separator_hash,
    extract_json_from_response,
    validate_json_structure,
)
from agents.common.prompt_builder import PromptBuilder
from agents.common.config_loader import PromptConfigLoader
from agents.common.constants import AnswerabilityType
from agents.common.event_bus import (
    publish_event,
    subscribe_and_listen,
    BACKEND_TO_AGENT,
    AGENT_TO_BACKEND,
    AGENT_STATUS,
    AGENT_TO_AGENT,
    MessageType,
)
from utils.redis_streams_client import AgentRedisStreamsClient
from agents.common.llm_tool import SpecializedLLMTool, PromptTemplate, LLMConfig
from database.repository import QuestionClassificationRepository
from database.postgres_db import get_db
from database.models import QuestionClassificationData

logger = logging.getLogger(__name__)


class QuestionClassifierAgent(BaseAgent):
    """질문 분류 및 게이팅 판정 에이전트 - 새로운 채널 구조"""

    def __init__(self):
        # 프롬프트 설정 로더 초기화
        self.logger = logging.getLogger(__name__)
        self.config_loader = PromptConfigLoader()

        # QuestionClassifier 에이전트 설정 로드
        yaml_data = self.config_loader.get_agent_config("question_classifier")
        if not yaml_data:
            self.logger.error("QuestionClassifier 설정을 로드할 수 없습니다")
            raise RuntimeError("QuestionClassifier 설정 로드 실패")

        # 프롬프트 빌더 초기화
        self.prompt_builder = PromptBuilder(yaml_data)

        # YAML 데이터를 인스턴스 변수로 저장
        self.prompt_config = yaml_data

        # 시스템 프롬프트는 PromptBuilder를 통해 동적으로 생성

        # 툴 제거 - 함수로 대체
        super().__init__(
            name="QuestionClassifier",
            role="질문 분류 및 게이팅 판정",
            system_prompt="",  # PromptBuilder를 통해 동적으로 생성
            tools=[],  # 툴 없음
        )

        self.logger = logging.getLogger(__name__)
        self.db = None
        self.processed_sessions = set()
        self.sessions_lock = asyncio.Lock()

        # Redis Streams 클라이언트 초기화
        self.streams_client = AgentRedisStreamsClient("QuestionClassifierAgent")

        # LLM 툴 초기화
        self.llm_tool = SpecializedLLMTool.create_classifier_tool()

        # 안전한 구분자 설정
        # YAML 설정에서 separators 가져오기
        separators_config = (
            self.prompt_config.get("question_classifier", {})
            .get("security_settings", {})
            .get("safe_separators", {})
        )
        self.separators = (
            separators_config if separators_config else generate_safe_separators()
        )
        self.separator_hash = create_separator_hash(self.separators)

        # 프롬프트 템플릿은 PromptBuilder를 통해 동적으로 생성

    # _build_system_prompt 메서드는 PromptBuilder 사용으로 인해 더 이상 필요하지 않음

    async def initialize(self):
        """에이전트 초기화"""
        await super().initialize()
        # Redis Streams 클라이언트 초기화
        await self.streams_client.initialize()
        self.logger.info("✅ QuestionClassifierAgent Streams 클라이언트 초기화 완료")

    async def cleanup(self):
        """에이전트 정리"""
        await super().cleanup()
        # Redis Streams 클라이언트 정리
        await self.streams_client.close()
        self.logger.info("✅ QuestionClassifierAgent Streams 클라이언트 정리 완료")

    async def run_subscriber(self):
        """Redis Streams 기반으로 백엔드 메시지 수신"""
        self.logger.info("🚀 QuestionClassifierAgent Streams 구독 시작")

        try:
            while True:
                try:
                    # Streams에서 메시지 수신 - 대용량 동시 처리 (최대 50개)
                    messages = await self.streams_client.read_from_backend_stream(
                        count=50, block=1000
                    )

                    if messages:
                        # 동시 처리할 메시지들 분류
                        tasks = []
                        for msg_id, fields in messages:
                            self.logger.info(f"📥 Streams에서 메시지 수신: {msg_id}")

                            # 메시지 파싱
                            message_type = fields.get("type", "")
                            target_agent = fields.get("target_agent", "")

                            self.logger.info(
                                f"🔍 메시지 분석: type={message_type}, target_agent={target_agent}"
                            )

                            # 이 에이전트를 대상으로 하는 메시지만 처리
                            if target_agent not in [
                                "QuestionClassifierAgent",
                                "QuestionClassifier",
                            ]:
                                self.logger.info(
                                    f"📤 다른 에이전트용 메시지: {target_agent}"
                                )
                                # 메시지 ACK (다른 에이전트용이므로)
                                tasks.append(
                                    self.streams_client.ack_stream_message(msg_id)
                                )
                                continue

                            self.logger.info(f"📥 백엔드 메시지 수신: {message_type}")

                            # 메시지 처리 태스크 생성
                            if message_type == "classify_question":
                                tasks.append(
                                    self._handle_classify_question_stream(
                                        fields, msg_id
                                    )
                                )
                            else:
                                self.logger.warning(
                                    f"⚠️ 알 수 없는 메시지 타입: {message_type}"
                                )
                                # 알 수 없는 메시지도 ACK
                                tasks.append(
                                    self.streams_client.ack_stream_message(msg_id)
                                )

                        # 모든 메시지 동시 처리
                        if tasks:
                            await asyncio.gather(*tasks, return_exceptions=True)

                except Exception as e:
                    self.logger.error(f"❌ Streams 메시지 처리 오류: {e}")
                    await asyncio.sleep(1)  # 오류 시 잠시 대기

        except Exception as e:
            self.logger.error(f"❌ Streams 구독 오류: {e}")
            raise

    async def _handle_classify_question_stream(
        self, fields: Dict[str, Any], msg_id: str
    ):
        """Streams 기반 질문 분류 요청 처리"""
        import time

        start_time = time.time()

        try:
            # 메트릭: 요청 시작
            if self.metrics:
                self.metrics.increment_counter("classification_requests_total")
                self.metrics.set_gauge(
                    "active_sessions", len(self.processed_sessions) + 1
                )

            # 메시지 파싱
            session_id = int(fields.get("session_id", "0"))
            question = fields.get("question", "")
            context = fields.get("context", "")
            request_id = fields.get("request_id", "")
            is_new_question = fields.get("is_new_question", False)

            self.logger.info(
                f"🔍 질문 분류 요청 처리: 세션 {session_id}, 질문: {question}, 새로운 질문: {is_new_question}"
            )
            if context:
                self.logger.info(f"🔍 이전 대화 맥락: {context}")

            # 처리 로그 발행
            await self._publish_processing_log(
                session_id, "classification_start", "질문 분류 시작"
            )

            # 질문 분류 수행 (context, session_id 포함)
            classification_result = await self._classify_question(
                question, "고등학교", context, session_id
            )

            # 처리 시간 측정
            duration = time.time() - start_time

            if classification_result.get("success"):
                # 메트릭: 성공
                if self.metrics:
                    self.metrics.record_request(
                        "classification", success=True, duration=duration
                    )
                    self.metrics.increment_counter("classification_success_total")

                # 성공적인 분류 결과 처리 (새로운 질문 플래그 포함)
                await self._handle_successful_classification_stream(
                    session_id,
                    question,
                    classification_result,
                    request_id,
                    context,
                    is_new_question,
                )

                # 처리 로그 발행
                await self._publish_processing_log(
                    session_id,
                    "classification_complete",
                    f"분류 완료: {classification_result.get('knowledge_code')} - {classification_result.get('quality')}",
                )
            else:
                # 메트릭: 실패
                if self.metrics:
                    self.metrics.record_request(
                        "classification", success=False, duration=duration
                    )
                    self.metrics.increment_counter("classification_failed_total")
                    self.metrics.record_error("classification_failed", "classification")

                # 분류 실패 처리
                await self._handle_classification_failure_stream(
                    session_id, question, classification_result, request_id
                )

                # 처리 로그 발행
                await self._publish_processing_log(
                    session_id,
                    "classification_failed",
                    f"분류 실패: {classification_result.get('error', '알 수 없는 오류')}",
                )

            # 메시지 ACK
            await self.streams_client.ack_stream_message(msg_id)

        except Exception as e:
            # 처리 시간 측정
            duration = time.time() - start_time

            # 메트릭: 에러
            if self.metrics:
                self.metrics.record_request(
                    "classification", success=False, duration=duration
                )
                self.metrics.record_error("exception", "classification")

            self.logger.error(f"❌ Streams 질문 분류 처리 오류: {e}")

            # 처리 로그 발행
            try:
                session_id = int(fields.get("session_id", "0"))
                await self._publish_processing_log(
                    session_id, "classification_error", f"오류 발생: {str(e)}"
                )
            except:
                pass

            # 오류 시에도 ACK
            await self.streams_client.ack_stream_message(msg_id)
        finally:
            # 메트릭: 활성 세션 감소
            if self.metrics:
                self.metrics.set_gauge("active_sessions", len(self.processed_sessions))

    async def process_classification_request(self, payload: dict):
        """백엔드로부터 받은 질문 분류 요청 처리"""
        session_id = payload.get("session_id")
        question = payload.get("question")
        grade_hint = payload.get("grade_hint", "고등학교")

        try:
            # 질문 분류 수행 (기존 툴 로직을 함수로 변환)
            classification_result = await self._classify_question(question, grade_hint)

            if classification_result.get("success"):
                # 성공적인 분류 결과 처리
                await self._handle_successful_classification(
                    session_id, question, classification_result, ""
                )
            else:
                # 분류 실패 처리
                await self._handle_classification_failure(
                    session_id, question, classification_result
                )

        except Exception as e:
            self.logger.error(f"질문 분류 처리 오류: {e}")
            await self._handle_classification_error(session_id, question, str(e))

    async def _classify_question(
        self,
        question: str,
        grade_hint: str = None,
        context: str = "",
        session_id: int = None,
    ) -> Dict[str, Any]:
        """질문 분류 - LLM 툴 사용"""
        try:
            # 1. 질문 검증
            validation_result = await self._validate_question(question)
            if not validation_result["is_valid"]:
                return validation_result

            # 2. 프롬프트 빌더로 변수 준비
            user_variables = {
                "question": question,
                "context": context if context else "없음",
                "separator_start": self.separators["start"],
                "separator_end": self.separators["end"],
                "separator_content": self.separators["content"],
                "separator_hash": self.separator_hash,
                # settings에서 변수들 추가
                "k1_definition": self.prompt_builder.get_setting(
                    "question_classifier", "k1_definition"
                ),
                "k2_definition": self.prompt_builder.get_setting(
                    "question_classifier", "k2_definition"
                ),
                "k3_definition": self.prompt_builder.get_setting(
                    "question_classifier", "k3_definition"
                ),
                "k4_definition": self.prompt_builder.get_setting(
                    "question_classifier", "k4_definition"
                ),
                "answerable_criteria": self.prompt_builder.get_setting(
                    "question_classifier", "answerable_criteria"
                ),
                "needs_clarify_criteria": self.prompt_builder.get_setting(
                    "question_classifier", "needs_clarify_criteria"
                ),
                "unanswerable_criteria": self.prompt_builder.get_setting(
                    "question_classifier", "unanswerable_criteria"
                ),
                "k1_missing_fields": self.prompt_builder.get_setting(
                    "question_classifier", "k1_missing_fields"
                ),
                "k2_missing_fields": self.prompt_builder.get_setting(
                    "question_classifier", "k2_missing_fields"
                ),
                "k3_missing_fields": self.prompt_builder.get_setting(
                    "question_classifier", "k3_missing_fields"
                ),
                "k4_missing_fields": self.prompt_builder.get_setting(
                    "question_classifier", "k4_missing_fields"
                ),
                "tone_guide": self.prompt_builder.get_setting(
                    "question_classifier", "tone_guide"
                ),
                "clarification_open_questions": self.prompt_builder.get_setting(
                    "question_classifier", "clarification_open_questions"
                ),
                "clarification_natural_conversation": self.prompt_builder.get_setting(
                    "question_classifier", "clarification_natural_conversation"
                ),
                "clarification_friendly_approach": self.prompt_builder.get_setting(
                    "question_classifier", "clarification_friendly_approach"
                ),
                "clarification_no_specific_examples": self.prompt_builder.get_setting(
                    "question_classifier", "clarification_no_specific_examples"
                ),
            }

            # 프롬프트 빌드
            prompt_data = self.prompt_builder.build_prompt(
                template_name="classification",
                variables=user_variables,
                agent_name="question_classifier",
            )

            # 프롬프트 로깅 (환경변수로 제어, 기본 비활성화) - 프로덕션에서는 강제 비활성화
            _env = os.getenv("ENVIRONMENT", "development").lower()
            _log_prompts = os.getenv("MAICE_LOG_LLM_PROMPTS", "false").lower() in (
                "1",
                "true",
                "yes",
            )
            if _env in ("production", "prod"):
                _log_prompts = False
            if _log_prompts:
                self.logger.debug(
                    f"🔍 사용된 프롬프트 - System: {prompt_data.get('system', '')}"
                )
                self.logger.debug(
                    f"🔍 사용된 프롬프트 - User: {prompt_data.get('user', '')}"
                )
                self.logger.debug(f"🔍 프롬프트 변수: {user_variables}")

            # 3. LLM 툴로 분류 수행 (session_id 전달, JSON 응답 요청)
            result = await self.llm_tool.execute(
                prompt=prompt_data,
                variables={},
                session_id=session_id,
                json_response=True,
            )

            if not result["success"]:
                return {"success": False, "error": result["error"]}

            # 4. MCP 스트리밍 응답 처리
            if result.get("content") and isinstance(result["content"], list):
                # MCP 스트리밍 응답인 경우 모든 청크를 수집
                content = ""
                for chunk in result["content"]:
                    if chunk.get("type") == "text" and chunk.get("text"):
                        content += chunk["text"]

                self.logger.debug(f"🔍 MCP 스트리밍 응답 수집 완료: {len(content)}자")
                self.logger.debug(f"🔍 수집된 내용 미리보기: {content[:200]}...")

                # 수집된 전체 내용으로 파싱
                return await self._parse_and_validate_response(content)
            elif result.get("stream"):
                # 일반 스트리밍 응답인 경우 모든 청크를 수집
                content = ""
                async for chunk in result["stream"]:
                    if hasattr(chunk, "choices") and chunk.choices:
                        chunk_content = chunk.choices[0].message.content
                        if chunk_content:
                            content += chunk_content

                # 수집된 전체 내용으로 파싱
                return await self._parse_and_validate_response(content)
            else:
                # 일반 응답인 경우
                return await self._parse_and_validate_response(result["content"])

        except Exception as e:
            self.logger.error(f"질문 분류 오류: {e}")
            return {"success": False, "error": str(e)}

    async def _validate_question(self, question: str) -> Dict[str, Any]:
        """질문 검증 - 기존 검증 로직을 함수로 변환"""
        # 설정에서 위험 패턴 가져오기
        dangerous_patterns = (
            self.prompt_config.get("question_classifier", {})
            .get("security_settings", {})
            .get("validation_patterns", [])
        )

        is_safe, error_msg = validate_prompt_content(question, dangerous_patterns)
        if not is_safe:
            return {
                "success": False,
                "is_valid": False,
                "error": f"안전하지 않은 질문입니다: {error_msg}",
                "security_flag": True,
            }

        # 질문 내용 정제
        sanitized_question = sanitize_text(question)
        if not sanitized_question:
            return {
                "success": False,
                "is_valid": False,
                "error": "질문 내용을 정제할 수 없습니다",
                "security_flag": True,
            }

        return {
            "success": True,
            "is_valid": True,
            "sanitized_question": sanitized_question,
        }

    async def _parse_and_validate_response(self, content: str) -> Dict[str, Any]:
        """LLM 응답 파싱 및 검증"""
        try:
            # LLM 원본 응답 로깅 (환경변수로 제어, 기본 비활성화) - 프로덕션 강제 비활성화
            _env = os.getenv("ENVIRONMENT", "development").lower()
            _log_responses = os.getenv("MAICE_LOG_LLM_RESPONSES", "false").lower() in (
                "1",
                "true",
                "yes",
            )
            if _env in ("production", "prod"):
                _log_responses = False
            if _log_responses:
                self.logger.debug(f"LLM 원본 응답: {content}")

            # 보안 검증 - 구분자가 포함되어 있으면 안됨
            if any(separator in content for separator in self.separators.values()):
                self.logger.warning("LLM 응답에 구분자가 포함되어 있어 보안 위험")
                return {
                    "success": False,
                    "error": "보안 위험이 감지되었습니다",
                    "security_flag": True,
                }

            # JSON 추출
            _env = os.getenv("ENVIRONMENT", "development").lower()
            _log_responses = os.getenv("MAICE_LOG_LLM_RESPONSES", "false").lower() in (
                "1",
                "true",
                "yes",
            )
            if _env in ("production", "prod"):
                _log_responses = False
            if _log_responses:
                self.logger.debug(f"JSON 추출 전 원본 내용: {repr(content)}")
            json_str = extract_json_from_response(content)
            _env = os.getenv("ENVIRONMENT", "development").lower()
            _log_responses = os.getenv("MAICE_LOG_LLM_RESPONSES", "false").lower() in (
                "1",
                "true",
                "yes",
            )
            if _env in ("production", "prod"):
                _log_responses = False
            if _log_responses:
                self.logger.debug(f"추출된 JSON 문자열: {repr(json_str)}")

            if not json_str:
                self.logger.error("JSON 문자열 추출 실패")
                return {"success": False, "error": "JSON 파싱 실패"}

            # JSON 파싱
            try:
                data = json.loads(json_str)
                self.logger.debug(f"JSON 파싱 성공: {data}")
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON 파싱 실패: {e}")
                self.logger.error(f"파싱 시도한 문자열: {repr(json_str)}")
                return {"success": False, "error": f"JSON 파싱 실패: {e}"}
            self.logger.info(f"LLM 분류 결과: {data}")

            # 빈 JSON 체크 - LLM이 제대로 분류하지 못한 경우
            if not data or data == {}:
                self.logger.error(
                    "LLM이 빈 JSON을 반환했습니다. 분류 실패로 처리합니다."
                )
                return {"success": False, "error": "LLM 분류 실패 - 빈 응답"}

            # 필수 필드 검증 및 기본값 설정 (gating 변환 전에 먼저 실행)
            required_fields = [
                "knowledge_code",
                "quality",
                "missing_fields",
                "unit_tags",
                "policy_flags",
                "reasoning",
            ]
            data = validate_json_structure(data, required_fields)

            # gating을 quality로 변환 (LLM이 gating으로 응답하는 경우)
            if "gating" in data and data.get("gating") != data.get("quality"):
                data["quality"] = data["gating"]
                self.logger.info(
                    f"🔄 gating을 quality로 변환: {data['gating']} → {data['quality']}"
                )

            return {"success": True, **data}

        except Exception as e:
            self.logger.error(f"응답 파싱 오류: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_successful_classification(
        self, session_id: str, question: str, result: Dict[str, Any], context: str = ""
    ):
        """성공적인 분류 결과 처리"""
        # 백엔드로 결과 전송
        await publish_event(
            AGENT_TO_BACKEND,
            {
                "type": MessageType.CLASSIFICATION_COMPLETE,
                "session_id": session_id,
                "question": question,
                "original_question": question,  # 원본 질문을 명시적으로 포함
                "result": result,
                "session_type": "classification",  # 세션 타입 명시
                "timestamp": datetime.now().isoformat(),
            },
        )

        self.logger.info(f"✅ 질문 분류 완료: {session_id}")

        # 분류 결과에 따라 직접 라우팅
        if result.get("quality") == AnswerabilityType.NEEDS_CLARIFY:
            # 명료화 필요한 경우 - QuestionImprovementAgent로 직접 전송
            await publish_event(
                AGENT_TO_AGENT,
                {
                    "type": MessageType.NEED_CLARIFICATION,
                    "target_agent": "QuestionImprovement",
                    "session_id": session_id,
                    "question": question,
                    "context": context,
                    "classification_result": result,
                    "timestamp": datetime.now().isoformat(),
                },
            )
            self.logger.info(f"🔄 명료화 요청 전송: {session_id}")
        else:
            # 즉시 답변 가능한 경우 - AnswerGenerator로 직접 전송
            self.logger.info(f"🔍 AnswerGenerator로 전달할 result: {result}")
            await publish_event(
                AGENT_TO_AGENT,
                {
                    "type": MessageType.READY_FOR_ANSWER,
                    "target_agent": "AnswerGenerator",
                    "session_id": session_id,
                    "question": question,
                    "classification_result": result,
                    "timestamp": datetime.now().isoformat(),
                },
            )
            self.logger.info(f"🔄 답변 생성 요청 전송: {session_id}")

    async def _handle_successful_classification_stream(
        self,
        session_id: int,
        question: str,
        result: Dict[str, Any],
        request_id: str,
        context: str = "",
        is_new_question: bool = False,
    ):
        """Streams 기반 성공적인 분류 결과 처리 - 스트리밍 방식"""
        try:
            # 0. 분류 결과를 DB에 저장
            await self._save_classification_to_db(
                question, result, request_id, session_id
            )

            # 1. 분류 시작 알림
            await self.streams_client.send_to_backend_stream(
                {
                    "type": "classification_start",
                    "session_id": session_id,
                    "message": "질문을 분석하고 있습니다...",
                    "timestamp": datetime.now().isoformat(),
                }
            )

            # 2. 분류 진행 상황 스트리밍
            await self.streams_client.send_to_backend_stream(
                {
                    "type": "classification_progress",
                    "session_id": session_id,
                    "message": "질문의 난이도와 주제를 파악하고 있습니다...",
                    "progress": 50,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            # 3. 최종 분류 결과 전송 (새로운 질문 플래그 포함)
            await self.streams_client.send_to_backend_stream(
                {
                    "type": "classification_complete",
                    "session_id": session_id,
                    "question": question,
                    "original_question": question,
                    "result": result,
                    "session_type": "classification",
                    "request_id": request_id,
                    "is_new_question": is_new_question,
                    "message": f"분류 완료: {result.get('knowledge_code', 'K1')} - {result.get('quality', 'answerable')}",
                    "timestamp": datetime.now().isoformat(),
                }
            )

            self.logger.info(
                f"✅ 스트리밍으로 질문 분류 완료 전송: {session_id}, 새로운 질문: {is_new_question}"
            )

        except Exception as e:
            self.logger.error(f"❌ 분류 결과 스트리밍 전송 오류: {e}")
            # 오류 발생 시 기본 전송
            await self.streams_client.send_classification_result(
                session_id=session_id,
                question=question,
                result={
                    "type": "classification_complete",
                    "session_id": session_id,
                    "question": question,
                    "original_question": question,
                    "result": result,
                    "session_type": "classification",
                    "request_id": request_id,
                    "is_new_question": is_new_question,
                    "timestamp": datetime.now().isoformat(),
                },
            )

        # 명료화가 필요한 경우 QuestionImprovementAgent로 전송
        if result.get("quality") == AnswerabilityType.NEEDS_CLARIFY:
            # QuestionImprovementAgent로만 전송 (중복 제거)
            await publish_event(
                AGENT_TO_AGENT,
                {
                    "type": MessageType.NEED_CLARIFICATION,
                    "target_agent": "QuestionImprovement",
                    "session_id": session_id,
                    "question": question,
                    "context": context,  # 이전 대화 맥락 추가
                    "classification_result": result,
                    "is_new_question": is_new_question,
                    "timestamp": datetime.now().isoformat(),
                },
            )
            self.logger.info(
                f"🔄 명료화 요청 전송: {session_id}, 새로운 질문: {is_new_question}"
            )
        else:
            # 즉시 답변 가능한 경우 answer_generator로 전송 (pub/sub 유지)
            await publish_event(
                AGENT_TO_AGENT,
                {
                    "type": MessageType.READY_FOR_ANSWER,
                    "target_agent": "AnswerGenerator",
                    "session_id": session_id,
                    "question": question,
                    "context": context,  # 이전 대화 맥락 추가
                    "classification_result": result,
                    "is_new_question": is_new_question,
                    "timestamp": datetime.now().isoformat(),
                },
            )
            self.logger.info(
                f"🔄 답변 생성 요청 전송: {session_id}, 새로운 질문: {is_new_question}"
            )

    async def _save_classification_to_db(
        self,
        question: str,
        result: Dict[str, Any],
        request_id: str,
        session_id: int = None,
    ):
        """분류 결과를 DB에 저장"""
        try:
            db_pool = await get_db()
            repo = QuestionClassificationRepository(db_pool)
            classification_data = QuestionClassificationData(
                request_id=request_id,
                original_question=question,
                knowledge_code=result.get("knowledge_code", "K1"),
                quality=result.get("quality", "answerable"),
                missing_fields=result.get("missing_fields", []),
                unit_tags=result.get("unit_tags", []),
                reasoning=result.get("reasoning", ""),
                created_at=datetime.now(),
            )

            success = await repo.save(classification_data)
            if success:
                self.logger.info(
                    f"✅ 분류 결과 DB 저장 완료: 세션 {session_id}, {request_id}"
                )
            else:
                self.logger.error(f"❌ 분류 결과 DB 저장 실패: {request_id}")

        except Exception as e:
            self.logger.error(f"❌ 분류 결과 DB 저장 오류: {e}")
            # DB 저장 실패해도 계속 진행

    async def _handle_classification_failure_stream(
        self, session_id: int, question: str, result: Dict[str, Any], request_id: str
    ):
        """Streams 기반 분류 실패 처리"""
        await self.streams_client.send_classification_result(
            session_id=session_id,
            question=question,
            result={
                "type": "classification_failed",
                "session_id": session_id,
                "question": question,
                "error": result.get("error", "분류 실패"),
                "request_id": request_id,
                "timestamp": datetime.now().isoformat(),
            },
        )
        self.logger.error(f"❌ Streams로 분류 실패 전송: {session_id}")

    async def _handle_classification_failure(
        self, session_id: str, question: str, result: Dict[str, Any]
    ):
        """분류 실패 처리"""
        await publish_event(
            AGENT_TO_BACKEND,
            {
                "type": MessageType.CLASSIFICATION_FAILED,
                "session_id": session_id,
                "question": question,
                "error": result.get("error", "알 수 없는 오류"),
                "timestamp": datetime.now().isoformat(),
            },
        )

        self.logger.warning(f"⚠️ 질문 분류 실패: {session_id} - {result.get('error')}")

    async def _handle_classification_error(
        self, session_id: str, question: str, error: str
    ):
        """분류 오류 처리"""
        await publish_event(
            AGENT_TO_BACKEND,
            {
                "type": MessageType.CLASSIFICATION_ERROR,
                "session_id": session_id,
                "question": question,
                "error": error,
                "timestamp": datetime.now().isoformat(),
            },
        )

        self.logger.error(f"❌ 질문 분류 오류: {session_id} - {error}")

    async def _publish_processing_log(self, session_id: int, stage: str, message: str):
        """처리 로그를 Redis에 발행"""
        try:
            await self.streams_client.send_to_backend_stream(
                {
                    "type": "processing_log",
                    "agent_name": "QuestionClassifier",
                    "session_id": session_id,
                    "stage": stage,
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        except Exception as e:
            self.logger.debug(f"처리 로그 발행 실패 (무시): {e}")

    async def process_task(self, task: Task) -> Any:
        """작업 처리 (BaseAgent 호환성)"""
        try:
            # Task 객체를 payload로 변환
            payload = {
                "session_id": task.id,
                "question": task.description,
                "grade_hint": task.metadata.get("grade_hint", "고등학교"),
                "context": task.metadata.get("context", ""),
            }

            # 기존 분류 로직 사용
            await self.process_classification_request(payload)

            return {"success": True, "task_id": task.id}

        except Exception as e:
            self.logger.error(f"Task 처리 오류: {e}")
            return {"success": False, "error": str(e), "task_id": task.id}

    async def test_classification(
        self, question: str, session_id: int = None
    ) -> Dict[str, Any]:
        """테스트용 분류 메서드"""
        try:
            self.logger.info(f"🧪 테스트 분류 시작: {question}")

            # 직접 분류 수행
            result = await self._classify_question(question, "고등학교", "", session_id)

            self.logger.info(f"🧪 테스트 분류 결과: {result}")
            return result

        except Exception as e:
            self.logger.error(f"🧪 테스트 분류 오류: {e}")
            return {"success": False, "error": str(e)}
