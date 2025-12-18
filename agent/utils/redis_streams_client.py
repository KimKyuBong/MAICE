"""
에이전트용 Redis Streams 클라이언트
MAICE 시스템의 에이전트들이 Redis Streams를 통해 백엔드와 통신하기 위한 클라이언트
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)

class AgentRedisStreamsClient:
    """에이전트용 Redis Streams 클라이언트"""
    
    # Streams 채널 정의
    BACKEND_TO_AGENT_STREAM = "maice:backend_to_agent_stream"    # 백엔드 → 에이전트
    AGENT_TO_BACKEND_STREAM = "maice:agent_to_backend_stream"    # 에이전트 → 백엔드 (기본)
    
    # 세션별 독립 Stream 채널 생성 함수 - 강화된 세션 격리
    @staticmethod
    def get_session_stream(session_id: int) -> str:
        """세션별 완전 독립 Stream 채널 이름 생성"""
        return f"maice:agent_to_backend_stream_session_{session_id}"
    
    @staticmethod 
    def get_backend_to_agent_session_stream(session_id: int) -> str:
        """백엔드 → 에이전트 세션별 독립 Stream 채널"""
        return f"maice:backend_to_agent_stream_session_{session_id}"
    
    # Consumer Groups
    BACKEND_CONSUMER_GROUP = "backend_consumers"   # 백엔드용 Consumer Group
    AGENT_CONSUMER_GROUP = "agent_consumers"       # 에이전트용 Consumer Group
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.redis_client: Optional[redis.Redis] = None
        self._streams_initialized = False
        self._consumer_name = f"{agent_name}_consumer_{id(self)}"
        # 각 에이전트별 고유 Consumer Group
        self.agent_consumer_group = f"{agent_name.lower()}_consumers"
        self._is_initialized = False
    
    async def initialize(self):
        """Redis 클라이언트 초기화"""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis_client = redis.from_url(redis_url)
            
            logger.info(f"📡 {self.agent_name} Redis 클라이언트 생성 완료, 연결 테스트 중...")
            await self.redis_client.ping()
            logger.info(f"✅ {self.agent_name} Redis 연결 성공! 클라이언트 초기화 완료")
            
            self._is_initialized = True
            
            # Streams 초기화
            await self._initialize_streams()
            
        except Exception as e:
            logger.error(f"❌ {self.agent_name} Redis 클라이언트 초기화 실패: {e}")
            raise
    
    async def _initialize_streams(self):
        """Redis Streams 초기화"""
        try:
            # Consumer Groups 생성
            await self._create_consumer_groups()
            self._streams_initialized = True
            logger.info(f"✅ {self.agent_name} Redis Streams 초기화 완료")
            
        except Exception as e:
            logger.error(f"❌ {self.agent_name} Redis Streams 초기화 실패: {e}")
            raise
    
    async def _create_consumer_groups(self):
        """Consumer Groups 생성"""
        try:
            # 에이전트용 Consumer Group 생성 (백엔드로부터 메시지 수신) - 각 에이전트별 고유 그룹
            await self.redis_client.xgroup_create(
                self.BACKEND_TO_AGENT_STREAM,
                self.agent_consumer_group,
                id="0",
                mkstream=True
            )
            logger.info(f"✅ {self.agent_name} Consumer Group 생성: {self.agent_consumer_group}")
            
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.info(f"ℹ️ {self.agent_name} Consumer Group 이미 존재: {self.agent_consumer_group}")
            else:
                raise
    
    async def close(self):
        """Redis 연결 종료"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info(f"🔒 {self.agent_name} Redis 연결 종료")
    
    # Streams 메서드들
    async def send_to_backend_stream(self, message: Dict[str, Any]) -> str:
        """백엔드로 메시지 전송 (Streams) - 세션별 독립 채널 사용"""
        if not self._streams_initialized:
            raise RuntimeError("Streams가 초기화되지 않았습니다")
        
        try:
            # 메시지에 에이전트 정보 추가
            message["agent_name"] = self.agent_name
            message["timestamp"] = datetime.utcnow().isoformat()
            
            # 세션별 독립 채널 사용
            session_id = message.get("session_id")
            if session_id:
                stream_name = self.get_session_stream(session_id)
            else:
                stream_name = self.AGENT_TO_BACKEND_STREAM
            
            # 모든 값을 문자열로 변환 (Redis Streams 요구사항)
            stream_message = {}
            for key, value in message.items():
                if isinstance(value, (dict, list)):
                    stream_message[key] = json.dumps(value, ensure_ascii=False)
                else:
                    stream_message[key] = str(value)
            
            message_id = await self.redis_client.xadd(
                stream_name,
                stream_message
            )
            # 추가 명료화 질문 전송 시에만 로그 출력
            if message.get("type") == "clarification_question":
                logger.info(f"📤 {self.agent_name} Streams로 백엔드에 명료화 질문 전송: {message_id}, 세션: {message.get('session_id')}")
            # logger.info(f"📤 {self.agent_name} Streams로 백엔드에 메시지 전송: {message_id}")
            return message_id.decode() if isinstance(message_id, bytes) else str(message_id)
            
        except Exception as e:
            logger.error(f"❌ {self.agent_name} Streams 메시지 전송 실패: {e}")
            raise
    
    async def read_from_backend_stream(self, count: int = 1, block: int = 1000) -> List[Dict[str, Any]]:
        """백엔드로부터 메시지 수신 (Streams) - 개선된 에러 핸들링"""
        if not self._streams_initialized:
            raise RuntimeError("Streams가 초기화되지 않았습니다")
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                messages = await self.redis_client.xreadgroup(
                    self.agent_consumer_group,
                    self._consumer_name,
                    {self.BACKEND_TO_AGENT_STREAM: ">"},
                    count=count,
                    block=block
                )
                
                if messages:
                    # Redis에서 받은 메시지 값들을 다시 파싱
                    parsed_messages = []
                    for msg_id, msg_data in messages[0][1]:
                        try:
                            parsed_data = {}
                            for key, value in msg_data.items():
                                try:
                                    # JSON 문자열인 경우 파싱 시도
                                    parsed_data[key.decode()] = json.loads(value.decode())
                                except (json.JSONDecodeError, UnicodeDecodeError):
                                    # JSON이 아니거나 디코딩 실패 시 일반 문자열로 처리
                                    parsed_data[key.decode()] = value.decode()
                            msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
                            parsed_messages.append((msg_id_str, parsed_data))
                        except Exception as parse_error:
                            logger.error(f"❌ {self.agent_name} 메시지 파싱 오류: {parse_error}")
                            continue
                    
                    logger.info(f"📥 {self.agent_name} Streams에서 백엔드 메시지 수신: {len(parsed_messages)}개")
                    return parsed_messages
                else:
                    return []
                    
            except redis.ConnectionError as e:
                retry_count += 1
                logger.error(f"❌ {self.agent_name} Redis 연결 오류 (시도 {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    await asyncio.sleep(1.0 * retry_count)  # 점진적 백오프
                else:
                    raise
            except Exception as e:
                logger.error(f"❌ {self.agent_name} Streams 메시지 수신 실패: {e}")
                raise
    
    async def ack_stream_message(self, message_id: str):
        """Streams 메시지 처리 완료 확인"""
        if not self._streams_initialized:
            raise RuntimeError("Streams가 초기화되지 않았습니다")
        
        try:
            await self.redis_client.xack(
                self.BACKEND_TO_AGENT_STREAM,
                self.agent_consumer_group,
                message_id
            )
            logger.info(f"✅ {self.agent_name} Streams 메시지 ACK: {message_id}")
            
        except Exception as e:
            logger.error(f"❌ {self.agent_name} Streams ACK 실패: {e}")
            raise
    
    async def get_stream_info(self, stream: str) -> Dict[str, Any]:
        """스트림 정보 조회"""
        try:
            info = await self.redis_client.xinfo_stream(stream)
            return info
            
        except Exception as e:
            logger.error(f"❌ {self.agent_name} 스트림 정보 조회 실패: {e}")
            return {}
    
    async def get_pending_messages(self) -> List[Dict[str, Any]]:
        """처리되지 않은 메시지 조회"""
        try:
            pending = await self.redis_client.xpending(
                self.BACKEND_TO_AGENT_STREAM,
                self.agent_consumer_group
            )
            return pending
            
        except Exception as e:
            logger.error(f"❌ {self.agent_name} Pending 메시지 조회 실패: {e}")
            return []
    
    async def read_pending_messages(self, count: int = 10) -> List[Dict[str, Any]]:
        """기존 pending 메시지들을 읽어서 처리"""
        if not self._streams_initialized:
            raise RuntimeError("Streams가 초기화되지 않았습니다")
        
        try:
            # Pending 메시지들을 읽어옴 (ID 0부터 시작)
            messages = await self.redis_client.xreadgroup(
                self.agent_consumer_group,
                self._consumer_name,
                {self.BACKEND_TO_AGENT_STREAM: "0"},
                count=count
            )
            
            if messages:
                # Redis에서 받은 메시지 값들을 다시 파싱
                parsed_messages = []
                for msg_id, msg_data in messages[0][1]:
                    try:
                        parsed_data = {}
                        for key, value in msg_data.items():
                            try:
                                # JSON 문자열인 경우 파싱 시도
                                parsed_data[key.decode()] = json.loads(value.decode())
                            except (json.JSONDecodeError, UnicodeDecodeError):
                                # JSON이 아니거나 디코딩 실패 시 일반 문자열로 처리
                                parsed_data[key.decode()] = value.decode()
                        msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
                        parsed_messages.append((msg_id_str, parsed_data))
                    except Exception as parse_error:
                        logger.error(f"❌ {self.agent_name} Pending 메시지 파싱 오류: {parse_error}")
                        continue
                
                logger.info(f"📥 {self.agent_name} Pending 메시지 수신: {len(parsed_messages)}개")
                return parsed_messages
            else:
                return []
                
        except Exception as e:
            logger.error(f"❌ {self.agent_name} Pending 메시지 수신 실패: {e}")
            return []
    
    async def read_from_backend_stream_with_pending(self, count: int = 1, block: int = 1000) -> List[Dict[str, Any]]:
        """백엔드로부터 메시지 수신 (Streams) - pending 메시지 포함"""
        if not self._streams_initialized:
            raise RuntimeError("Streams가 초기화되지 않았습니다")
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # 먼저 pending 메시지들을 읽어옴 (ID 0부터 시작)
                pending_messages = await self.redis_client.xreadgroup(
                    self.agent_consumer_group,
                    self._consumer_name,
                    {self.BACKEND_TO_AGENT_STREAM: "0"},
                    count=count,
                    block=block
                )
                
                if pending_messages:
                    # Redis에서 받은 메시지 값들을 다시 파싱
                    parsed_messages = []
                    for msg_id, msg_data in pending_messages[0][1]:
                        try:
                            parsed_data = {}
                            for key, value in msg_data.items():
                                try:
                                    # JSON 문자열인 경우 파싱 시도
                                    parsed_data[key.decode()] = json.loads(value.decode())
                                except (json.JSONDecodeError, UnicodeDecodeError):
                                    # JSON이 아니거나 디코딩 실패 시 일반 문자열로 처리
                                    parsed_data[key.decode()] = value.decode()
                            msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
                            parsed_messages.append((msg_id_str, parsed_data))
                        except Exception as parse_error:
                            logger.error(f"❌ {self.agent_name} 메시지 파싱 오류: {parse_error}")
                            continue
                    
                    logger.info(f"📥 {self.agent_name} Streams에서 백엔드 메시지 수신 (pending 포함): {len(parsed_messages)}개")
                    return parsed_messages
                
                # pending 메시지가 없으면 새로운 메시지 읽기
                messages = await self.redis_client.xreadgroup(
                    self.agent_consumer_group,
                    self._consumer_name,
                    {self.BACKEND_TO_AGENT_STREAM: ">"},
                    count=count,
                    block=block
                )
                
                if messages:
                    # Redis에서 받은 메시지 값들을 다시 파싱
                    parsed_messages = []
                    for msg_id, msg_data in messages[0][1]:
                        try:
                            parsed_data = {}
                            for key, value in msg_data.items():
                                try:
                                    # JSON 문자열인 경우 파싱 시도
                                    parsed_data[key.decode()] = json.loads(value.decode())
                                except (json.JSONDecodeError, UnicodeDecodeError):
                                    # JSON이 아니거나 디코딩 실패 시 일반 문자열로 처리
                                    parsed_data[key.decode()] = value.decode()
                            msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
                            parsed_messages.append((msg_id_str, parsed_data))
                        except Exception as parse_error:
                            logger.error(f"❌ {self.agent_name} 메시지 파싱 오류: {parse_error}")
                            continue
                    
                    logger.info(f"📥 {self.agent_name} Streams에서 백엔드 메시지 수신 (새 메시지): {len(parsed_messages)}개")
                    return parsed_messages
                else:
                    return []
                    
            except redis.ConnectionError as e:
                retry_count += 1
                logger.error(f"❌ {self.agent_name} Redis 연결 오류 (시도 {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    await asyncio.sleep(1.0 * retry_count)  # 점진적 백오프
                else:
                    raise
            except Exception as e:
                logger.error(f"❌ {self.agent_name} Streams 메시지 수신 실패: {e}")
                raise
    
    # 편의 메서드들
    async def send_classification_result(self, session_id: int, question: str, result: Dict[str, Any]) -> str:
        """분류 결과 전송"""
        message = {
            "type": "classification_complete",
            "session_id": session_id,
            "question": question,
            "result": result
        }
        return await self.send_to_backend_stream(message)
    
    async def send_clarification_question(self, session_id: int, question: str, original_question: str, 
                                        question_index: int, total_questions: int, missing_fields: List[str]) -> str:
        """명료화 질문 전송"""
        message = {
            "type": "clarification_question",
            "session_id": session_id,
            "question": question,
            "original_question": original_question,
            "question_index": question_index,
            "total_questions": total_questions,
            "missing_fields": missing_fields
        }
        return await self.send_to_backend_stream(message)
    
    async def send_clarification_complete(self, session_id: int, improved_question: str, 
                                        user_responses: List[str]) -> str:
        """명료화 완료 전송"""
        message = {
            "type": "clarification_complete",
            "session_id": session_id,
            "improved_question": improved_question,
            "user_responses": user_responses
        }
        return await self.send_to_backend_stream(message)
    
    async def send_answer_result(self, session_id: int, answer: str, request_id: str) -> str:
        """답변 결과 전송"""
        message = {
            "type": "answer_result",
            "session_id": session_id,
            "answer": answer,
            "request_id": request_id
        }
        return await self.send_to_backend_stream(message)
    
    async def send_answer_error(self, session_id: int, error_message: str, request_id: str) -> str:
        """답변 에러 전송"""
        message = {
            "type": "answer_error",
            "session_id": session_id,
            "error": error_message,
            "request_id": request_id
        }
        return await self.send_to_backend_stream(message)
    
    async def send_summary_result(self, session_id: int, summary: str) -> str:
        """요약 결과 전송"""
        message = {
            "type": "summary_result",
            "session_id": session_id,
            "summary": summary
        }
        return await self.send_to_backend_stream(message)
    
    # 헬스 체크
    async def health_check(self) -> bool:
        """Redis 연결 상태 확인"""
        try:
            if not self._is_initialized:
                return False
            
            await self.redis_client.ping()
            return True
            
        except Exception as e:
            logger.error(f"❌ {self.agent_name} 헬스 체크 실패: {e}")
            return False
