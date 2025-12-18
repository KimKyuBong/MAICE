"""
프리토커 에이전트 - 프리패스 모드 전담 에이전트
에이전트 없이 LLM과 직접 채팅하는 프리패스 모드를 에이전트 시스템으로 통합
"""

import logging
import json
import asyncio
import uuid
import os
from typing import Dict, Any, Optional
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

class FreeTalkerAgent(BaseAgent):
    """프리토커 에이전트 - 프리패스 모드 전담"""
    
    def __init__(self):
        # Redis Streams 클라이언트 초기화
        self.streams_client = AgentRedisStreamsClient("FreeTalkerAgent")
        
        # 프롬프트 설정 로더 초기화
        self.config_loader = PromptConfigLoader()
        self.prompt_config = self.config_loader.get_agent_config("freetalker")
        
        # 시스템 프롬프트 구성
        system_prompt = self._build_system_prompt()
        
        # LLM 툴 초기화
        self.llm_tool = SpecializedLLMTool.create_freetalker_tool()
        
        super().__init__(
            name="FreeTalker",
            role="프리패스 모드 전담 에이전트",
            system_prompt=system_prompt,
            tools=[self.llm_tool]
        )
        
        # 프리패스 세션 관리
        self.freepass_sessions = {}
    
    def _build_system_prompt(self) -> str:
        """설정 파일에서 시스템 프롬프트 구성"""
        try:
            if self.prompt_config and "system_prompt" in self.prompt_config:
                return self.prompt_config["system_prompt"]
            else:
                # 프리패스 모드용 간단한 시스템 프롬프트
                return """필요할 때만 수학 수식을 LaTeX 형식($수식$)으로 작성해주세요."""
        except Exception as e:
            logger.error(f"시스템 프롬프트 구성 실패: {e}")
            return "필요할 때만 수학 수식을 LaTeX 형식($수식$)으로 작성해주세요."
    
    async def initialize(self):
        """에이전트 초기화"""
        try:
            # 데이터베이스 연결 초기화
            await self.initialize_database()
            
            # Redis 클라이언트 초기화
            await self.streams_client.initialize()
            
            self.logger.info("✅ FreeTalker 에이전트 초기화 완료")
            
        except Exception as e:
            self.logger.error(f"❌ FreeTalker 에이전트 초기화 실패: {e}")
            raise
    
    async def run_subscriber(self):
        """Redis Streams 구독자 실행"""
        self.logger.info("🚀 FreeTalker 에이전트 구독자 시작")
        
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
                            
                            self.logger.info(f"🔍 메시지 분석: type={message_type}, target_agent={target_agent}")
                            
                            # msg_id가 bytes인 경우에만 decode, 이미 문자열이면 그대로 사용
                            msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
                            
                            # FreeTalker 에이전트를 대상으로 하는 메시지만 처리
                            if target_agent not in ["FreeTalkerAgent", "FreeTalker"]:
                                self.logger.info(f"📤 다른 에이전트용 메시지: {target_agent}")
                                # 메시지 ACK (다른 에이전트용이므로)
                                tasks.append(self.streams_client.ack_stream_message(msg_id_str))
                                continue
                            
                            # 프리패스 요청 처리 태스크 생성
                            if message_type == "freepass_request":
                                tasks.append(self._handle_freepass_request(msg_id_str, fields))
                            else:
                                self.logger.debug(f"알 수 없는 메시지 타입: {message_type}")
                                tasks.append(self.streams_client.ack_stream_message(msg_id_str))
                        
                        # 모든 태스크 동시 실행
                        if tasks:
                            await asyncio.gather(*tasks, return_exceptions=True)
                    
                except Exception as e:
                    self.logger.error(f"❌ Streams 메시지 처리 오류: {e}")
                    await asyncio.sleep(1)
                    
        except Exception as e:
            self.logger.error(f"❌ Streams 구독 오류: {e}")
            raise
    
    async def _handle_freepass_request(self, msg_id: str, fields: Dict[str, Any]):
        """프리패스 요청 처리"""
        try:
            # 메시지 ACK
            await self.streams_client.ack_stream_message(msg_id)
            
            # 프리패스 요청 처리
            await self._process_freepass_request(fields)
                
        except Exception as e:
            self.logger.error(f"❌ 프리패스 요청 처리 오류: {e}")
    
    async def _process_freepass_request(self, request_data: Dict[str, Any]):
        """프리패스 요청 처리 - 스트리밍 응답"""
        try:
            # 요청 데이터 추출
            question = request_data.get("question", "")
            conversation_history = request_data.get("conversation_history", [])
            user_id = request_data.get("user_id")
            session_id = request_data.get("session_id")
            request_id = request_data.get("request_id", str(uuid.uuid4()))
            message_id = request_data.get("message_id", request_id)  # 메시지 ID 추출 (프롬프트 추적용)
            
            self.logger.info(f"🚀 프리패스 요청 처리 시작: '{question[:50]}...' (요청 ID: {request_id}, 메시지 ID: {message_id})")
            
            # 실험 데이터 수집을 위한 고유 ID 생성
            experiment_id = str(uuid.uuid4())
            start_time = datetime.now()
            
            # 실험 데이터 로깅
            experiment_data = {
                "experiment_id": experiment_id,
                "mode": "freetalker_agent",
                "user_id": user_id,
                "session_id": session_id,
                "request_id": request_id,
                "message": question,
                "start_time": start_time.isoformat(),
                "conversation_history_length": len(conversation_history) if conversation_history else 0
            }
            self.logger.info(f"📊 실험 데이터: {json.dumps(experiment_data, ensure_ascii=False)}")
            
            # LLM 툴을 사용한 스트리밍 호출 - 실시간 스트리밍
            # 대화 히스토리가 있는 경우 전체 컨텍스트를 포함
            if conversation_history:
                # 대화 히스토리를 포함한 전체 메시지 구성
                full_context = ""
                for msg in conversation_history:
                    if isinstance(msg, dict) and "role" in msg and "content" in msg:
                        role = "사용자" if msg["role"] == "user" else "AI"
                        full_context += f"{role}: {msg['content']}\n\n"
                
                # 현재 질문 추가
                full_context += f"사용자: {question}"
                
                # LLM 툴 실행 - create_freetalker_tool()의 기본 설정 사용 (max_tokens=4000, stream=True, timeout=60)
                result = await self.llm_tool.execute(
                    prompt=full_context,
                    session_id=session_id,
                    streams_client=self.streams_client,
                    message_id=message_id,
                    request_id=request_id
                )
            else:
                # 대화 히스토리가 없는 경우 단순 호출
                # LLM 툴 실행 - create_freetalker_tool()의 기본 설정 사용 (max_tokens=4000, stream=True, timeout=60)
                result = await self.llm_tool.execute(
                    prompt=question,
                    session_id=session_id,
                    streams_client=self.streams_client,
                    message_id=message_id
                )
            
            # 결과 처리
            if not result["success"]:
                raise Exception(f"LLM 호출 실패: {result.get('error', 'Unknown error')}")
            
            # 전체 응답 내용 받기 - 이미 스트리밍이 완료된 상태
            full_response = result.get("content", "")
            if not full_response:
                raise Exception("빈 응답을 받았습니다.")
            
            # 이미 LLMTool에서 실시간 스트리밍을 처리했으므로 별도 청크 전송 불필요
            # 프리패스 모드에서는 프론트엔드로 직접 스트리밍 전달됨
            
            # chunk_count 대신 응답 길이를 청크 수로 추정 (실제 청크 수는 LLM 툴에서 전송됨)
            estimated_chunks = max(1, len(full_response) // 50)  # 대략적인 청크 수 추정
            
            # 완료 메시지 - AnswerGenerator 방식처럼
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # 통일된 streaming_complete로 전송
            await self.streams_client.send_to_backend_stream({
                "type": "streaming_complete",
                "request_id": request_id,
                "full_response": full_response,
                "total_chunks": estimated_chunks,
                "timestamp": end_time.isoformat(),
                "experiment_id": experiment_id,
                "processing_time_seconds": processing_time
            })
            
            # 실험 완료 데이터 로깅
            completion_data = {
                "experiment_id": experiment_id,
                "mode": "freetalker_agent",
                "end_time": end_time.isoformat(),
                "processing_time_seconds": processing_time,
                "response_length": len(full_response),
                "total_chunks": estimated_chunks,
                "success": True
            }
            self.logger.info(f"📊 실험 완료 데이터: {json.dumps(completion_data, ensure_ascii=False)}")
            
            self.logger.info(f"✅ 프리패스 요청 완료: 처리시간 {processing_time:.2f}초")
            
        except Exception as e:
            self.logger.error(f"❌ 프리패스 요청 처리 오류: {e}")
            
            # 오류 메시지를 백엔드로 전송
            await self.streams_client.send_to_backend_stream({
                "type": "freepass_error",
                "request_id": request_id,
                "error": str(e),
                "message": "프리토커 에이전트에서 오류가 발생했습니다.",
                "timestamp": datetime.now().isoformat()
            })
    
    async def process_task(self, task: Task) -> Dict[str, Any]:
        """작업 처리 - BaseAgent의 추상 메서드 구현"""
        # 프리토커 에이전트는 Redis Streams를 통해 직접 처리하므로
        # 이 메서드는 사용하지 않지만 추상 메서드이므로 구현 필요
        return {"success": True, "message": "FreeTalker는 Redis Streams를 통해 직접 처리됩니다"}
    
    async def cleanup(self):
        """에이전트 정리"""
        try:
            if self.streams_client:
                await self.streams_client.cleanup()
            
            self.logger.info("✅ FreeTalker 에이전트 정리 완료")
            
        except Exception as e:
            self.logger.error(f"❌ FreeTalker 에이전트 정리 실패: {e}")
