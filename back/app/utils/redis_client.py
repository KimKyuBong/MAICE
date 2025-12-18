"""
Redis 클라이언트 유틸리티 - 새로운 3개 채널 구조 사용
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional, Callable, Awaitable, List
from datetime import datetime

import redis.asyncio as redis

logger = logging.getLogger(__name__)

class RedisAgentClient:
    """MAICE 에이전트와의 통신을 위한 Redis 클라이언트 - Redis Streams 활용"""
    
    # 기존 pub/sub 채널
    BACKEND_TO_AGENT = "maice.backend_to_agent"    # 백엔드 → 에이전트
    AGENT_TO_BACKEND = "maice.agent_to_backend"    # 에이전트 → 백엔드
    AGENT_STATUS = "maice.agent_status"            # 에이전트 상태
    AGENT_TO_AGENT = "maice.agent_to_agent"       # 에이전트 → 에이전트
    
    # Redis Streams 채널 (세션별 독립)
    BACKEND_TO_AGENT_STREAM = "maice:backend_to_agent_stream"    # 백엔드 → 에이전트
    AGENT_TO_BACKEND_STREAM = "maice:agent_to_backend_stream"    # 에이전트 → 백엔드 (기본)
    
    # 세션별 독립 Stream 채널 생성 함수
    @staticmethod
    def get_session_stream(session_id: int) -> str:
        """세션별 독립 Stream 채널 이름 생성"""
        return f"maice:agent_to_backend_stream_session_{session_id}"
    
    # Consumer Groups
    BACKEND_CONSUMER_GROUP = "backend_consumers"   # 백엔드용 Consumer Group
    AGENT_CONSUMER_GROUP = "agent_consumers"       # 에이전트용 Consumer Group
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.timeout = 120
        self._status_subscribers: List[Callable] = []
        self._response_subscribers: Dict[str, Callable] = {}
        self._session_subscribers: Dict[str, Callable] = {}  # session_id 기반 구독
        self._is_initialized = False
        self._status_subscribed = False
        self._agent_to_agent_subscribed = False
        self._status_monitor_task: Optional[asyncio.Task] = None
        self._agent_to_agent_monitor_task: Optional[asyncio.Task] = None
        
        # Streams 관련 변수
        self._streams_initialized = False
        self._consumer_name = "backend_consumer_main"  # 고정된 Consumer Name 사용
        
    async def initialize(self):
        """Redis 클라이언트 초기화"""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            logger.info(f"🔄 Redis 연결 시도: {redis_url}")
            self.redis_client = redis.from_url(redis_url)
            logger.info("📡 Redis 클라이언트 생성 완료, 연결 테스트 중...")
            await self.redis_client.ping()
            logger.info("✅ Redis 연결 성공! 클라이언트 초기화 완료")
            
            self._is_initialized = True
            
            # Streams 초기화
            await self._initialize_streams()
            
        except Exception as e:
            logger.error(f"❌ Redis 클라이언트 초기화 실패: {e}")
            raise
    
    async def _initialize_streams(self):
        """Redis Streams 초기화"""
        try:
            # Consumer Groups 생성
            await self._create_consumer_groups()
            self._streams_initialized = True
            logger.info("✅ Redis Streams 초기화 완료")
            
        except Exception as e:
            logger.error(f"❌ Redis Streams 초기화 실패: {e}")
            raise
    
    async def _create_consumer_groups(self):
        """Consumer Groups 생성"""
        try:
            # 백엔드용 Consumer Group 생성 (에이전트로부터 메시지 수신)
            await self.redis_client.xgroup_create(
                self.AGENT_TO_BACKEND_STREAM,
                self.BACKEND_CONSUMER_GROUP,
                id="0",
                mkstream=True
            )
            logger.info(f"✅ Consumer Group 생성: {self.BACKEND_CONSUMER_GROUP}")
            
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.info(f"ℹ️ Consumer Group 이미 존재: {self.BACKEND_CONSUMER_GROUP}")
            else:
                raise
    
    async def close(self):
        """Redis 연결 종료"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis 연결 종료")
    
    async def _ensure_connection(self):
        """Redis 연결 상태 확인 및 재연결"""
        if not self._is_initialized or not self.redis_client:
            await self.initialize()
    
    # 백엔드 → 에이전트 메시지 전송
    async def send_to_agent(self, agent_name: str, message: dict):
        """백엔드에서 특정 에이전트로 메시지 전송"""
        await self._ensure_connection()
        
        message_data = {
            "target_agent": agent_name,
            "timestamp": datetime.utcnow().isoformat(),
            **message
        }
        
        await self.redis_client.publish(
            self.BACKEND_TO_AGENT, 
            json.dumps(message_data)
        )
        logger.info(f"📤 에이전트로 메시지 전송: {agent_name}")
    
    # 에이전트 응답 구독
    async def subscribe_to_agent_responses(self, request_id: str, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """특정 요청에 대한 에이전트 응답 구독"""
        await self._ensure_connection()
        
        # 콜백 유효성 검사
        if callback is None:
            logger.warning("⚠️ None 콜백은 등록할 수 없습니다")
            return
        
        if not callable(callback):
            logger.warning(f"⚠️ 콜백이 callable이 아닙니다: {type(callback)}")
            return
        
        # 콜백 등록
        self._response_subscribers[request_id] = callback
        
        # 백그라운드에서 응답 모니터링 시작
        asyncio.create_task(self._monitor_agent_responses(request_id))
        
        logger.info(f"🔍 에이전트 응답 구독 시작: {request_id}")
    
    async def subscribe_to_session_responses(self, session_id: int, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """특정 세션에 대한 에이전트 응답 구독 (명료화 질문 등)"""
        await self._ensure_connection()
        
        # 콜백 유효성 검사
        if callback is None:
            logger.warning("⚠️ None 콜백은 등록할 수 없습니다")
            return
        
        if not callable(callback):
            logger.warning(f"⚠️ 콜백이 callable이 아닙니다: {type(callback)}")
            return
        
        # 콜백 등록
        self._session_subscribers[str(session_id)] = callback
        
        # 백그라운드에서 응답 모니터링 시작 (이미 시작된 경우 중복 방지)
        if not hasattr(self, '_session_monitor_started'):
            asyncio.create_task(self._monitor_session_responses())
            self._session_monitor_started = True
        
        logger.info(f"🔍 세션 응답 구독 시작: {session_id}")
    
    async def _monitor_agent_responses(self, request_id: str):
        """에이전트 응답 모니터링"""
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(self.AGENT_TO_BACKEND)
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        
                        # request_id 또는 session_id가 일치하는 응답 처리
                        message_request_id = data.get("request_id")
                        message_session_id = data.get("session_id")
                        
                        # request_id 매칭 (기존 로직)
                        if message_request_id == request_id:
                            callback = self._response_subscribers.get(request_id)
                            if callback is not None and callable(callback):
                                try:
                                    await callback(data)
                                    # 응답 받으면 구독 해제
                                    del self._response_subscribers[request_id]
                                    break
                                except Exception as e:
                                    logger.error(f"응답 콜백 실행 오류: {e}")
                                    # 오류 발생 시에도 구독 해제
                                    del self._response_subscribers[request_id]
                                    break
                            else:
                                logger.warning(f"⚠️ 응답 콜백이 None이거나 callable이 아닙니다: {type(callback)}")
                                # 잘못된 콜백 제거
                                del self._response_subscribers[request_id]
                                break
                        
                        # session_id 매칭 (새로운 로직) - 명료화 질문 등
                        elif message_session_id and hasattr(self, '_session_subscribers'):
                            session_callback = self._session_subscribers.get(str(message_session_id))
                            if session_callback is not None and callable(session_callback):
                                try:
                                    await session_callback(data)
                                    logger.info(f"✅ session_id 기반 응답 처리 완료: {message_session_id}")
                                except Exception as e:
                                    logger.error(f"세션 응답 콜백 실행 오류: {e}")
                                
                    except json.JSONDecodeError as e:
                        logger.error(f"메시지 파싱 오류: {e}")
                        
        finally:
            await pubsub.close()
    
    async def _monitor_session_responses(self):
        """세션 기반 에이전트 응답 모니터링"""
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(self.AGENT_TO_BACKEND)
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        session_id = data.get("session_id")
                        
                        if session_id and str(session_id) in self._session_subscribers:
                            callback = self._session_subscribers[str(session_id)]
                            if callback is not None and callable(callback):
                                try:
                                    await callback(data)
                                    logger.info(f"✅ 세션 응답 처리 완료: {session_id}")
                                except Exception as e:
                                    logger.error(f"세션 응답 콜백 실행 오류: {e}")
                                    
                    except json.JSONDecodeError as e:
                        logger.error(f"세션 메시지 파싱 오류: {e}")
                        
        finally:
            await pubsub.close()
    
    # 전체 에이전트 응답 구독 (명료화 질문 등)
    async def subscribe_to_all_agent_responses(self, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """모든 에이전트 응답을 구독 (명료화 질문, 답변 결과 등)"""
        await self._ensure_connection()
        
        # 중복 구독 방지: 이미 구독 중이면 무시
        if hasattr(self, '_all_responses_subscribed') and self._all_responses_subscribed:
            logger.info("🔄 이미 전체 응답 구독 중 - 중복 구독 방지")
            return
        
        # 콜백 유효성 검사
        if callback is None:
            logger.warning("⚠️ None 콜백은 등록할 수 없습니다")
            return
        
        if not callable(callback):
            logger.warning(f"⚠️ 콜백이 callable이 아닙니다: {type(callback)}")
            return
        
        # 구독 상태 표시
        self._all_responses_subscribed = True
        
        # 백그라운드에서 전체 응답 모니터링 시작
        asyncio.create_task(self._monitor_all_agent_responses(callback))
        
        logger.info("🔍 에이전트 전체 응답 구독 시작")
    
    async def _monitor_all_agent_responses(self, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """모든 에이전트 응답 모니터링"""
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(self.AGENT_TO_BACKEND)
        
        logger.info("🔍 _monitor_all_agent_responses 시작")
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        logger.info(f"📥 _monitor_all_agent_responses 메시지 수신: {data.get('type', 'unknown')}")
                        
                        # 모든 메시지를 콜백으로 전달
                        if callable(callback):
                            try:
                                await callback(data)
                                logger.info(f"✅ _monitor_all_agent_responses 콜백 실행 완료")
                            except Exception as e:
                                logger.error(f"전체 응답 콜백 실행 오류: {e}")
                                
                    except json.JSONDecodeError as e:
                        logger.error(f"메시지 파싱 오류: {e}")
                        
        except Exception as e:
            logger.error(f"전체 응답 모니터링 오류: {e}")
        finally:
            await pubsub.close()
    
    # 에이전트 상태 구독
    async def subscribe_to_agent_status(self, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """에이전트 상태 업데이트 구독"""
        await self._ensure_connection()
        
        # 중복 구독 방지
        if self._status_subscribed:
            logger.info("⚠️ 이미 상태 구독 중입니다. 중복 구독을 건너뜁니다.")
            return
        
        # 콜백 유효성 검사
        if callback is None:
            logger.warning("⚠️ None 콜백은 등록할 수 없습니다")
            return
        
        if not callable(callback):
            logger.warning(f"⚠️ 콜백이 callable이 아닙니다: {type(callback)}")
            return
        
        self._status_subscribers.append(callback)
        
        # 백그라운드에서 상태 모니터링 시작
        self._status_monitor_task = asyncio.create_task(self._monitor_agent_status())
        self._status_subscribed = True
        
        logger.info("🔍 에이전트 상태 구독 시작")
    
    # 에이전트 간 통신 구독
    async def subscribe_to_agent_to_agent(self, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """에이전트 간 통신 구독 (명료화 완료 등)"""
        await self._ensure_connection()
        
        # 중복 구독 방지
        if hasattr(self, '_agent_to_agent_subscribed') and self._agent_to_agent_subscribed:
            logger.info("⚠️ 이미 에이전트 간 통신 구독 중입니다. 중복 구독을 건너뜁니다.")
            return
        
        # 콜백 유효성 검사
        if callback is None:
            logger.warning("⚠️ None 콜백은 등록할 수 없습니다")
            return
        
        if not callable(callback):
            logger.warning(f"⚠️ 콜백이 callable이 아닙니다: {type(callback)}")
            return
        
        # 백그라운드에서 에이전트 간 통신 모니터링 시작
        self._agent_to_agent_monitor_task = asyncio.create_task(self._monitor_agent_to_agent(callback))
        self._agent_to_agent_subscribed = True
        
        logger.info("🔍 에이전트 간 통신 구독 시작")
    
    async def _monitor_agent_to_agent(self, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """에이전트 간 통신 모니터링"""
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(self.AGENT_TO_AGENT)
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        
                        # 모든 메시지를 콜백으로 전달
                        if callable(callback):
                            try:
                                await callback(data)
                            except Exception as e:
                                logger.error(f"에이전트 간 통신 콜백 실행 오류: {e}")
                                
                    except json.JSONDecodeError as e:
                        logger.error(f"에이전트 간 통신 메시지 파싱 오류: {e}")
                        
        except Exception as e:
            logger.error(f"에이전트 간 통신 모니터링 오류: {e}")
        finally:
            await pubsub.close()
    
    async def _monitor_agent_status(self):
        """에이전트 상태 모니터링"""
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(self.AGENT_STATUS)
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        
                        # 등록된 모든 콜백 실행
                        valid_callbacks = [cb for cb in self._status_subscribers if cb is not None and callable(cb)]
                        
                        for callback in valid_callbacks:
                            try:
                                await callback(data)
                            except Exception as e:
                                logger.error(f"상태 콜백 실행 오류: {e}")
                        
                        # None이나 callable이 아닌 콜백 제거
                        self._status_subscribers = valid_callbacks
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"상태 메시지 파싱 오류: {e}")
                        
        finally:
            await pubsub.close()
    
    # 편의 메서드들
    async def send_classify_request(self, request_id: str, question: str, context: str = "", session_id: int = None):
        """질문 분류 요청 전송"""
        message = {
            "type": "classify_question",
            "request_id": request_id,
            "question": question,
            "context": context,
            "session_id": session_id  # session_id 추가
        }
        await self.send_to_agent("QuestionClassifierAgent", message)
    
    async def send_clarification_request(self, request_id: str, clarification_data: dict):
        """명료화 처리 요청 전송"""
        message = {
            "type": "process_clarification",
            "request_id": request_id,
            "clarification": clarification_data
        }
        await self.send_to_agent("QuestionImprovementAgent", message)
    
    async def send_answer_request(self, request_id: str, question: str, context: dict, session_id: int = None):
        """답변 생성 요청 전송"""
        message = {
            "type": "generate_answer",
            "request_id": request_id,
            "question": question,
            "context": context,
            "session_id": session_id
        }
        await self.send_to_agent("AnswerGeneratorAgent", message)
    
    async def send_summary_request(self, request_id: str, conversation_text: str, session_id: int):
        """대화 요약 생성 요청 전송"""
        message = {
            "type": "generate_summary",
            "request_id": request_id,
            "conversation_text": conversation_text,
            "session_id": session_id
        }
        await self.send_to_agent("ObserverAgent", message)
    
    async def send_observation_request(self, request_id: str, session_id: str, question: str, answer: str):
        """학습 관찰 요청 전송"""
        message = {
            "type": "observe_learning",
            "request_id": request_id,
            "session_id": session_id,
            "question": question,
            "answer": answer
        }
        await self.send_to_agent("ObserverAgent", message)
    
    # Redis Streams 메서드들
    async def send_to_agent_stream(self, message: Dict[str, Any]) -> str:
        """에이전트로 메시지 전송 (Streams)"""
        if not self._streams_initialized:
            raise RuntimeError("Streams가 초기화되지 않았습니다")
        
        try:
            # 메시지에 타임스탬프 추가
            message["timestamp"] = datetime.utcnow().isoformat()
            
            # 모든 값을 문자열로 변환 (Redis Streams 요구사항)
            stream_message = {}
            for key, value in message.items():
                if isinstance(value, (dict, list)):
                    stream_message[key] = json.dumps(value, ensure_ascii=False)
                else:
                    stream_message[key] = str(value)
            
            message_id = await self.redis_client.xadd(
                self.BACKEND_TO_AGENT_STREAM,
                stream_message
            )
            logger.info(f"📤 Streams로 에이전트에 메시지 전송: {message_id}")
            return message_id.decode() if isinstance(message_id, bytes) else str(message_id)
            
        except Exception as e:
            logger.error(f"❌ Streams 메시지 전송 실패: {e}")
            raise
    
    async def read_from_agent_stream(self, count: int = 1, block: int = 1000, session_id: int = None) -> List[Dict[str, Any]]:
        """에이전트로부터 메시지 수신 (Streams) - 세션별 독립 채널 사용"""
        if not self._streams_initialized:
            raise RuntimeError("Streams가 초기화되지 않았습니다")
        
        try:
            # 세션별 독립 Stream 채널 사용
            if session_id:
                stream_name = self.get_session_stream(session_id)
                consumer_name = f"backend_consumer_session_{session_id}"
                
                # 세션별 채널과 Consumer Group이 존재하는지 확인하고 생성
                await self._ensure_session_stream_exists(stream_name, consumer_name)
            else:
                stream_name = self.AGENT_TO_BACKEND_STREAM
                consumer_name = self._consumer_name
            
            # 세션별 독립 채널에서 메시지 읽기
            messages = await self.redis_client.xreadgroup(
                self.BACKEND_CONSUMER_GROUP,
                consumer_name,
                {stream_name: ">"},
                count=count,
                block=block
            )
            
            if messages:
                # 세션별 독립 채널이므로 모든 메시지가 현재 세션의 메시지
                filtered_messages = []
                
                for msg_id, fields in messages[0][1]:
                    msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
                    filtered_messages.append((msg_id, fields))
                
                logger.info(f"📥 Streams에서 세션 {session_id} 메시지 수신: {len(filtered_messages)}개")
                return filtered_messages
            else:
                return []
                
        except Exception as e:
            logger.error(f"❌ Streams 메시지 수신 실패: {e}")
            raise
    
    async def _ensure_session_stream_exists(self, stream_name: str, consumer_name: str):
        """세션별 Stream 채널과 Consumer Group이 존재하는지 확인하고 생성"""
        try:
            # Stream이 존재하는지 확인
            try:
                await self.redis_client.xinfo_stream(stream_name)
                logger.debug(f"✅ 세션 Stream 채널 존재: {stream_name}")
            except redis.ResponseError as e:
                if "no such key" in str(e).lower():
                    # Stream이 존재하지 않으면 빈 메시지로 생성
                    await self.redis_client.xadd(stream_name, {"init": "true"})
                    logger.info(f"🆕 세션 Stream 채널 생성: {stream_name}")
                else:
                    raise
            
            # Consumer Group이 존재하는지 확인하고 생성
            try:
                await self.redis_client.xgroup_create(stream_name, self.BACKEND_CONSUMER_GROUP, id="0", mkstream=True)
                logger.info(f"🆕 세션 Consumer Group 생성: {stream_name} -> {self.BACKEND_CONSUMER_GROUP}")
            except redis.ResponseError as e:
                if "BUSYGROUP" in str(e):
                    # Consumer Group이 이미 존재함
                    logger.debug(f"✅ 세션 Consumer Group 존재: {stream_name} -> {self.BACKEND_CONSUMER_GROUP}")
                else:
                    raise
                    
        except Exception as e:
            logger.error(f"❌ 세션 Stream 설정 실패: {e}")
            raise

    async def ack_stream_message(self, message_id: str, stream_name: str = None):
        """Streams 메시지 처리 완료 확인 - 세션별 독립 채널 지원"""
        if not self._streams_initialized:
            raise RuntimeError("Streams가 초기화되지 않았습니다")
        
        try:
            # 세션별 독립 채널 또는 기본 채널 사용
            target_stream = stream_name or self.AGENT_TO_BACKEND_STREAM
            
            await self.redis_client.xack(
                target_stream,
                self.BACKEND_CONSUMER_GROUP,
                message_id
            )
            logger.debug(f"✅ Streams 메시지 ACK: {message_id} (채널: {target_stream})")
            
        except Exception as e:
            logger.error(f"❌ Streams ACK 실패: {e}")
            raise
    
    async def get_stream_info(self, stream: str) -> Dict[str, Any]:
        """스트림 정보 조회"""
        try:
            info = await self.redis_client.xinfo_stream(stream)
            return info
            
        except Exception as e:
            logger.error(f"❌ 스트림 정보 조회 실패: {e}")
            return {}
    
    async def get_pending_messages(self) -> List[Dict[str, Any]]:
        """처리되지 않은 메시지 조회"""
        try:
            pending = await self.redis_client.xpending(
                self.AGENT_TO_BACKEND_STREAM,
                self.BACKEND_CONSUMER_GROUP
            )
            return pending
            
        except Exception as e:
            logger.error(f"❌ Pending 메시지 조회 실패: {e}")
            return []
    
    # Streams 기반 편의 메서드들
    async def send_classify_request_stream(self, request_id: str, question: str, context: str = "", session_id: int = None, is_new_question: bool = False) -> str:
        """질문 분류 요청 전송 (Streams)"""
        message = {
            "type": "classify_question",
            "request_id": request_id,
            "question": question,
            "context": context,
            "session_id": session_id,
            "target_agent": "QuestionClassifierAgent",
            "is_new_question": is_new_question
        }
        return await self.send_to_agent_stream(message)
    
    async def send_clarification_request_stream(self, request_id: str, clarification_data: dict, session_id: int = None) -> str:
        """명료화 처리 요청 전송 (Streams)"""
        message = {
            "type": "process_clarification",
            "request_id": request_id,
            "clarification": clarification_data,
            "session_id": session_id,
            "target_agent": "QuestionImprovementAgent"
        }
        return await self.send_to_agent_stream(message)
    
    async def send_answer_request_stream(self, request_id: str, question: str, context: str, evaluation: dict, session_id: int = None) -> str:
        """답변 생성 요청 전송 (Streams)"""
        message = {
            "type": "generate_answer",
            "request_id": request_id,
            "question": question,
            "context": context,
            "evaluation": evaluation,
            "session_id": session_id,
            "target_agent": "AnswerGeneratorAgent"
        }
        return await self.send_to_agent_stream(message)
    
    async def send_summary_request_stream(self, request_id: str, conversation_text: str, session_id: int) -> str:
        """대화 요약 생성 요청 전송 (Streams)"""
        message = {
            "type": "generate_summary",
            "request_id": request_id,
            "conversation_text": conversation_text,
            "session_id": session_id,
            "target_agent": "ObserverAgent"
        }
        return await self.send_to_agent_stream(message)
    
    # 헬스 체크
    async def health_check(self) -> bool:
        """Redis 연결 상태 확인"""
        try:
            if not self._is_initialized:
                return False
            await self.redis_client.ping()
            return True
        except Exception:
            return False

# 전역 Redis 클라이언트 인스턴스
_redis_client = None

async def get_redis_client() -> RedisAgentClient:
    """Redis 클라이언트 인스턴스 반환 (싱글톤)"""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisAgentClient()
        await _redis_client.initialize()
        logger.info("🔒 Redis 클라이언트 싱글톤 인스턴스 생성 완료")
    return _redis_client

async def close_redis_client():
    """Redis 클라이언트 종료"""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None