"""
직접 스트리밍 AI 에이전트 서비스 - 폴링/큐 제거
"""
import logging
import json
import time
import uuid
import asyncio
from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime
from sqlalchemy import select

from app.utils.redis_client import get_redis_client
from app.services.maice.interfaces import ISessionService, IAgentService
from app.models.models import ConversationStage, MessageType, ConversationSession
from .utils import MessageFormatter, ResponseHelper, TimeConstants

logger = logging.getLogger(__name__)


class AIAgentService(IAgentService):
    """직접 스트리밍 AI 에이전트 서비스 - 폴링/큐 제거"""
    
    def __init__(self, session_service: ISessionService):
        self.session_service = session_service
        self.redis_client = None
        self._streams_initialized = False
        self._classification_results: Dict[int, Dict[str, Any]] = {}
        self._session_states: Dict[int, Dict[str, Any]] = {}  # 세션 상태 관리
    
    def _format_streaming_chunk(self, fields: Dict, session_id: int, request_id: str) -> Dict[str, Any]:
        """통일된 streaming_chunk 메시지 형식 생성"""
        return {
            "type": "streaming_chunk",
            "session_id": session_id,
            "request_id": request_id,
            "content": fields.get(b"content", fields.get(b"chunk", b"")).decode(),
            "chunk_index": int(fields.get(b"chunk_index", b"0").decode()),
            "is_final": fields.get(b"is_final", b"false").decode().lower() == "true",
            "timestamp": fields.get(b"timestamp", b"").decode()
        }
    
    async def initialize(self):
        """서비스 초기화"""
        self.redis_client = await get_redis_client()
        logger.info("✅ 직접 스트리밍 에이전트 서비스 초기화 완료")
        
        if hasattr(self.redis_client, '_streams_initialized') and self.redis_client._streams_initialized:
            self._streams_initialized = True
            logger.info("✅ Redis Streams 초기화 확인됨")
        else:
            logger.warning("⚠️ Redis Streams가 초기화되지 않음")
    
    async def process_freepass_streaming(self, question: str, conversation_history: Optional[list] = None,
                                       user_id: Optional[int] = None, session_id: Optional[int] = None):
        """프리패스 모드 처리 - 프리토커 에이전트로 라우팅"""
        # 요청 ID를 함수 스코프에서 유지하기 위해 먼저 선언
        freepass_request_id = str(uuid.uuid4())
        
        try:
            request_id = freepass_request_id  # 지역 변수로도 유지
            start_time = datetime.now()
            
            logger.info(f"🚀 프리패스 요청 시작: '{question[:50]}...' (요청 ID: {request_id})")
            logger.info(f"🔍 프리패스 요청 파라미터: session_id={session_id}, user_id={user_id}")
            
            # 세션 ID가 없으면 새 세션 생성
            session_created = False
            if not session_id and user_id:
                try:
                    session_id = await self.session_service.create_new_session(user_id, question)
                    logger.info(f"✅ 프리패스 모드 새 세션 생성: {session_id}")
                    session_created = True
                except Exception as e:
                    logger.error(f"❌ 프리패스 모드 세션 생성 실패: {e}")
                    session_id = None
            
            # 세션 ID가 있으면 대화 히스토리 조회
            from .utils import ContextBuilder
            actual_conversation_history = await ContextBuilder.build_freepass_history(
                self.session_service, session_id, conversation_history
            )
            
            # 에이전트로 요청 전송
            request_data = {
                "type": "freepass_request",
                "target_agent": "FreeTalkerAgent",
                "request_id": request_id,
                "message_id": request_id,  # 메시지 ID로 사용 (프롬프트 추적용)
                "question": question,
                "conversation_history": actual_conversation_history,
                "user_id": user_id,
                "session_id": session_id,
                "timestamp": start_time.isoformat()
            }
            
            # Redis Streams로 에이전트에 요청 전송
            await self.redis_client.send_to_agent_stream(request_data)
            
            logger.info(f"📤 프리패스 요청 전송 완료: {request_id}")
            
            # 새 세션 생성 시 즉시 세션 정보 전달
            if session_created and session_id:
                session_info_data = {
                    "type": "session_info",
                    "session_id": session_id,
                    "message": "새 세션이 시작되었습니다."
                }
                session_info_msg = f"data: {json.dumps(session_info_data, ensure_ascii=True)}\n\n"
                yield session_info_msg
                logger.info(f"📤 새 세션 정보 전송: {session_id}")
            
            # 응답 수신을 위한 타임아웃 설정 (120초)
            timeout_seconds = 120
            start_listen_time = datetime.now()
            is_complete = False
            
            while not is_complete:
                # 타임아웃 체크
                if (datetime.now() - start_listen_time).total_seconds() > timeout_seconds:
                    logger.error(f"⏰ 프리패스 응답 타임아웃: {request_id}")
                    break
                
                try:
                    # Redis Streams에서 응답 수신 (세션별 독립 처리) - 동시 처리 개선
                    messages = await self.redis_client.read_from_agent_stream(
                        count=20,  # 10 → 20으로 증가
                        block=1000,  # 1초 블록
                        session_id=session_id  # 세션별 고유 Consumer Name 사용
                    )
                    
                    if messages:
                        # 동시 처리할 메시지들 분류
                        tasks = []
                        for message_id, fields in messages:
                            # message_id는 이미 문자열이므로 그대로 사용
                            try:
                                # 메시지 타입 확인 (bytes로 접근)
                                msg_type = fields.get(b"type", b"").decode()
                                msg_request_id = fields.get(b"request_id", b"").decode()
                                
                                logger.info(f"🔍 백엔드 수신 메시지: type={msg_type}, request_id={msg_request_id}, fields={list(fields.keys())}")
                                
                                # 통일된 streaming_chunk 처리
                                if msg_type == "streaming_chunk":
                                    chunk_data = self._format_streaming_chunk(fields, session_id, freepass_request_id)
                                    yield f"data: {json.dumps(chunk_data, ensure_ascii=True)}\n\n"
                                    logger.info(f"📤 스트리밍 청크 전송: 세션 {session_id}, 요청 {freepass_request_id[:8]}, 청크 {chunk_data['chunk_index']}")
                                    continue
                                
                                # 스트리밍 완료 처리
                                if msg_type == "streaming_complete" or msg_type == "freepass_complete":
                                    # 스트리밍 완료 메시지 처리 (통일된 형식)
                                    full_response = fields.get(b"full_response", b"").decode()
                                    
                                    # ⚠️ 중요: 청크는 이미 streaming_chunk로 전송되었으므로 여기서는 전송하지 않음
                                    # full_response는 안전장치로 answer_complete에 포함하여 전송
                                    logger.info(f"📤 프리패스 모드 스트리밍 완료 확인")
                                    
                                    # answer_complete 전송 (안전장치: 완전한 답변으로 갈아치우기)
                                    complete_data = {
                                        "type": "answer_complete",
                                        "session_id": session_id,
                                        "request_id": freepass_request_id,
                                        "full_response": full_response,  # 청크 순서/누락 대비 안전장치
                                        "status": "completed",
                                        "timestamp": fields.get(b"timestamp", b"").decode()
                                    }
                                    yield f"data: {json.dumps(complete_data, ensure_ascii=True)}\n\n"
                                    logger.info(f"📤 프리패스 모드 answer_complete 전송 (full_response 포함)")
                                    
                                    # 프리패스 모드는 요약 없음 - 가짜 summary_complete 전송
                                    fake_summary = {
                                        "type": "summary_complete",
                                        "session_id": session_id,
                                        "request_id": freepass_request_id,
                                        "summary": "",
                                        "status": "completed",
                                        "timestamp": fields.get(b"timestamp", b"").decode()
                                    }
                                    yield f"data: {json.dumps(fake_summary, ensure_ascii=True)}\n\n"
                                    logger.info(f"📤 프리패스 모드 summary_complete 전송 (요약 없음)")
                                    
                                    # DB에 프리패스 대화 저장 (동시 처리)
                                    if session_id and user_id and full_response:
                                        tasks.append(self._save_freepass_conversation(session_id, user_id, question, full_response))
                                    
                                    is_complete = True
                                    logger.info(f"✅ 프리패스 모드 스트리밍 응답 완료: {freepass_request_id[:8]}")
                                    break
                                
                                # 해당 요청의 응답인지 확인 (streaming_chunk가 아닌 경우만)
                                if request_id and msg_request_id != request_id:
                                    continue
                                if request_id and not msg_request_id:
                                    continue
                                
                                
                                elif msg_type == "freepass_error":
                                    # 오류 메시지 처리
                                    error_data = {
                                        "type": "freepass_error",
                                        "error": fields.get(b"error", b"").decode(),
                                        "message": fields.get(b"message", b"FreeTalker agent error").decode(),
                                        "request_id": request_id,
                                        "timestamp": fields.get(b"timestamp", b"").decode()
                                    }
                                    
                                    error_msg = f"data: {json.dumps(error_data, ensure_ascii=True)}\n\n"
                                    yield error_msg
                                    
                                    is_complete = True
                                    logger.error(f"❌ 프리패스 오류: {error_data['error']}")
                                    break
                            
                            except Exception as e:
                                logger.error(f"❌ 프리패스 메시지 처리 오류: {e}")
                                continue
                        
                        # DB 저장 작업들 동시 처리
                        if tasks:
                            await asyncio.gather(*tasks, return_exceptions=True)
                
                except Exception as e:
                    logger.error(f"❌ 프리패스 스트림 읽기 오류: {e}")
                    await asyncio.sleep(0.1)  # 짧은 대기 후 재시도
                    continue
            
            # 처리 시간 계산
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            logger.info(f"✅ 프리패스 요청 완료: {request_id}, 처리시간: {processing_time:.2f}초")
            
        except Exception as e:
            logger.error(f"❌ 프리패스 처리 오류: {str(e)}")
            error_msg = {
                "type": "freepass_error",
                "error": str(e),
                "message": "프리패스 처리 중 오류가 발생했습니다.",
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=True)}\n\n"
    
    async def process_with_streaming_parallel(self, question: str, session_id: int, 
                                            request_id: Optional[str], user_id: int, is_followup: bool = False):
        """Redis Streams에서 직접 읽어서 SSE로 전송 - 세션별 병렬 처리 최적화"""
        try:
            if not request_id:
                request_id = str(uuid.uuid4())
            
            logger.info(f"🚀 병렬 스트리밍 시작: 세션 {session_id}, 요청 {request_id}")
            logger.info(f"🔍 입력 파라미터: question='{question}', session_id={session_id}, user_id={user_id}")
            
            # 맥락 준비: 후속질문의 경우 최근 대화 내용만 사용, 새로운 질문의 경우 요약도 포함
            from .utils import ContextBuilder
            context, context_parts = await ContextBuilder.build_streaming_context(
                self.session_service, session_id, is_followup
            )
            
            # 후속 질문 여부는 chat_service에서 이미 판단됨
            is_new_question = not is_followup  # 후속질문이면 새로운 질문이 아님
            logger.info(f"🔍 질문 타입: {'후속 질문' if is_followup else '새로운 질문'}: 세션 {session_id}")
            logger.info(f"🔍 에이전트로 전달: is_new_question={is_new_question}, is_followup={is_followup}")
            
            # 질문 분류 요청 전송 (새로운 질문 플래그 포함)
            if self._streams_initialized:
                await self.redis_client.send_classify_request_stream(request_id, question, context, session_id, is_new_question=is_new_question)
                logger.info(f"📤 Streams로 질문 분류 요청 전송: {request_id}, 새로운 질문: {is_new_question}")
            else:
                await self.redis_client.send_classify_request(request_id, question, context, session_id, is_new_question=is_new_question)
                logger.info(f"📤 pub/sub으로 질문 분류 요청 전송: {request_id}, 새로운 질문: {is_new_question}")
            
            # Redis Streams에서 직접 메시지 읽기 (병렬 처리 최적화)
            logger.info(f"🔍 Redis Streams 병렬 읽기 시작: 세션 {session_id}")
            
            start_time = time.time()
            max_wait_time = TimeConstants.STREAMING_TIMEOUT
            
            while time.time() - start_time < max_wait_time:
                try:
                    # Redis Streams에서 직접 메시지 읽기 (배치 처리로 최적화) - 세션별 순서 보장
                    messages = await self.redis_client.read_from_agent_stream(count=10, block=100, session_id=session_id)
                    
                    if messages:
                        # 배치로 받은 메시지들을 병렬 처리
                        for msg_id, fields in messages:
                            # 메시지 ID를 string으로 변환 (bytes -> string)
                            msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
                            # 세션별 독립 채널을 사용하므로 세션 ID 필터링 불필요
                            
                            message_type = fields.get(b'type', b'').decode()
                            logger.info(f"📥 병렬 메시지 수신: {message_type}, 세션 {session_id}")
                            
                            # 메시지 타입에 따라 처리
                            logger.info(f"🔍 메시지 타입 확인: {message_type}, 세션 {session_id}")
                            if message_type == MessageType.CLASSIFICATION_COMPLETE:
                                # 분류 결과 처리
                                result_data = json.loads(fields.get(b'result', b'{}').decode())
                                is_new_question = fields.get(b'is_new_question', b'false').decode().lower() == 'true'
                                logger.info(f"🔍 분류 결과: {result_data}, 새로운 질문: {is_new_question}")
                                
                                # 분류 결과를 메모리에 저장
                                self._classification_results[session_id] = result_data
                                
                                # 분류 결과에 따른 처리
                                quality = result_data.get("quality", "answerable")
                                if quality == "needs_clarify":
                                    # 명료화 필요 - 명료화 에이전트에서 질문을 생성하여 전송할 예정
                                    logger.info(f"✅ 명료화 필요: 세션 {session_id}, 명료화 에이전트에서 질문 생성 대기 중")
                                
                                else:
                                    # answerable인 경우 - 에이전트가 자체적으로 처리하도록 함
                                    logger.info(f"✅ answerable 질문 - 에이전트가 자체 처리: {quality}, 새로운 질문: {is_new_question}")
                                    # 백엔드에서는 답변 생성 요청을 보내지 않음
                            
                            elif message_type == MessageType.CLARIFICATION_QUESTION:
                                # 명료화 질문 직접 전송 (첫 번째 또는 추가 명료화)
                                logger.info(f"🎯 명료화 질문 처리 시작: 세션 {session_id}")
                                logger.info(f"🔍 명료화 질문 처리 조건 확인: message_type={message_type}, MessageType.CLARIFICATION_QUESTION={MessageType.CLARIFICATION_QUESTION}")
                                
                                # 세션 상태 업데이트 (yield 전에 실행)
                                logger.info(f"🔄 세션 {session_id} 상태 업데이트 시작: clarification")
                                try:
                                    await self.session_service.update_session_state(
                                        session_id=session_id,
                                        current_stage=ConversationStage.CLARIFICATION,
                                        last_message_type=MessageType.MAICE_CLARIFICATION_QUESTION
                                    )
                                    logger.info(f"✅ 세션 {session_id} 상태를 명료화 대기로 업데이트 완료")
                                except Exception as e:
                                    logger.error(f"❌ 세션 {session_id} 상태 업데이트 실패: {e}")
                                
                                sse_message = {
                                    "type": MessageType.CLARIFICATION_QUESTION,
                                    "session_id": session_id,
                                    "message": fields.get(b'message', b'').decode(),
                                    "question_index": fields.get(b'question_index', b'1').decode(),
                                    "total_questions": fields.get(b'total_questions', b'1').decode(),
                                    "timestamp": fields.get(b'timestamp', b'').decode()
                                }
                                yield MessageFormatter.format_sse_message(sse_message)
                                
                                # 명료화 질문을 DB에 저장
                                try:
                                    await self.session_service.save_maice_message(
                                        session_id=session_id,
                                        user_id=user_id,
                                        content=sse_message["message"],
                                        message_type=MessageType.MAICE_CLARIFICATION_QUESTION,
                                        request_id=request_id
                                    )
                                    logger.info(f"✅ 명료화 질문 DB 저장 완료")
                                except Exception as e:
                                    logger.error(f"❌ 명료화 질문 DB 저장 실패: {e}")
                                
                                # 명료화 질문 전송 후 종료
                                stream_name = self.redis_client.get_session_stream(session_id)
                                await self.redis_client.ack_stream_message(msg_id_str, stream_name)
                                return
                            
                            elif message_type == MessageType.CLARIFICATION_START:
                                # 명료화 시작 상태 전송
                                sse_message = {
                                    "type": MessageType.CLARIFICATION_STATUS,
                                    "session_id": session_id,
                                    "status": "preparing_clarification",
                                    "message": fields.get(b'message', b'Preparing clarification question...').decode(),
                                    "timestamp": fields.get(b'timestamp', b'').decode()
                                }
                                yield MessageFormatter.format_sse_message(sse_message)
                                stream_name = self.redis_client.get_session_stream(session_id)
                                await self.redis_client.ack_stream_message(msg_id_str, stream_name)
                            
                            elif message_type == MessageType.CLARIFICATION_PROGRESS:
                                # 명료화 진행 상황 전송
                                sse_message = {
                                    "type": MessageType.CLARIFICATION_STATUS,
                                    "session_id": session_id,
                                    "status": "processing_clarification",
                                    "message": fields.get(b'message', b'Preparing clarification question...').decode(),
                                    "progress": int(fields.get(b'progress', b'50').decode()),
                                    "timestamp": fields.get(b'timestamp', b'').decode()
                                }
                                yield MessageFormatter.format_sse_message(sse_message)
                                
                                # 진행 상황을 DB에 저장
                                try:
                                    await self.session_service.save_maice_message(
                                        session_id=session_id,
                                        user_id=user_id,
                                        content=sse_message["message"],
                                        message_type=MessageType.MAICE_PROCESSING
                                    )
                                    logger.info(f"✅ 명료화 진행 상황 DB 저장 완료")
                                except Exception as e:
                                    logger.error(f"❌ 명료화 진행 상황 DB 저장 실패: {e}")
                            
                            # 스트리밍 청크 처리
                            elif message_type == MessageType.ANSWER_CHUNK or message_type == "streaming_chunk":
                                chunk_index = int(fields.get(b'chunk_index', b'0').decode())
                                logger.info(f"🔍 streaming_chunk 메시지 수신: 세션 {session_id}, 청크 인덱스 {chunk_index}")
                                
                                # 첫 번째 청크일 때 세션 상태를 답변 생성 중으로 업데이트
                                if chunk_index == 0:
                                    await self.session_service.update_session_state(
                                        session_id=session_id,
                                        current_stage=ConversationStage.GENERATING_ANSWER,
                                        last_message_type=MessageType.MAICE_ANSWER
                                    )
                                    logger.info(f"✅ 세션 {session_id} 상태를 답변 생성 중으로 업데이트")
                                
                                # 통일된 형식으로 변환 및 전송
                                sse_message = self._format_streaming_chunk(fields, session_id, request_id)
                                yield MessageFormatter.format_sse_message(sse_message)
                                logger.info(f"📤 스트리밍 청크 전송: 세션 {session_id}, 요청 {request_id[:8]}, 청크 {sse_message['chunk_index']}")
                                
                                # 메시지 확인 처리
                                stream_name = self.redis_client.get_session_stream(session_id)
                                await self.redis_client.ack_stream_message(msg_id_str, stream_name)
                                
                                # 각 청크마다 루프를 한번 돌도록 break
                                if sse_message["is_final"]:
                                    logger.info(f"✅ 스트리밍 완료: 세션 {session_id}")
                                    # 답변 완료 시 바로 새로운 질문 대기 상태로 업데이트
                                    await self.session_service.update_session_state(
                                        session_id=session_id,
                                        current_stage=ConversationStage.READY_FOR_NEW_QUESTION,
                                        last_message_type=MessageType.MAICE_ANSWER
                                    )
                                    logger.info(f"✅ 세션 {session_id} 상태를 새로운 질문 대기로 즉시 업데이트")
                                break  # 메시지 처리 후 즉시 다음 루프로
                            
                            elif message_type == MessageType.ANSWER_RESULT:
                                # 답변 결과 처리 (DB 저장용)
                                answer_content = fields.get(b'answer', b'').decode()
                                
                                # 디버깅: 실제 받은 answer 길이 확인
                                logger.info(f"✅ 답변 결과 수신: 세션 {session_id}, 길이 {len(answer_content)}자")
                                logger.info(f"🔍 받은 answer 끝부분(마지막 100자): ...{answer_content[-100:] if len(answer_content) > 100 else answer_content}")
                                
                                # unanswerable 질문의 경우 스트리밍 청크가 없으므로 여기서 생성
                                # 전체 답변을 하나의 청크로 전송
                                logger.info(f"📤 unanswerable 답변을 스트리밍 청크로 변환: 세션 {session_id}")
                                
                                # 전체 답변을 하나의 청크로 전송
                                sse_message = {
                                    "type": "streaming_chunk",
                                    "session_id": session_id,
                                    "request_id": request_id,
                                    "content": answer_content,
                                    "chunk_index": 0,
                                    "is_final": True,
                                    "timestamp": fields.get(b'timestamp', b'').decode()
                                }
                                yield MessageFormatter.format_sse_message(sse_message)
                                logger.info(f"📤 unanswerable 답변 스트리밍 청크 전송 완료: 세션 {session_id}")
                                
                                # 세션 상태를 답변 생성 중으로 업데이트
                                await self.session_service.update_session_state(
                                    session_id=session_id,
                                    current_stage=ConversationStage.GENERATING_ANSWER,
                                    last_message_type=MessageType.MAICE_ANSWER
                                )
                                logger.info(f"✅ 세션 {session_id} 상태를 답변 생성 중으로 업데이트")
                                
                                # 답변을 DB에 저장
                                try:
                                    await self.session_service.save_maice_message(
                                        session_id=session_id,
                                        user_id=user_id,
                                        content=answer_content,
                                        message_type=MessageType.MAICE_ANSWER
                                    )
                                    logger.info(f"✅ 답변 DB 저장 완료: 세션 {session_id}")
                                except Exception as e:
                                    logger.error(f"❌ 답변 DB 저장 실패: {e}")
                                
                                # 답변 완료 시 바로 새로운 질문 대기 상태로 업데이트
                                await self.session_service.update_session_state(
                                    session_id=session_id,
                                    current_stage=ConversationStage.READY_FOR_NEW_QUESTION,
                                    last_message_type=MessageType.MAICE_ANSWER
                                )
                                logger.info(f"✅ 세션 {session_id} 상태를 새로운 질문 대기로 즉시 업데이트")
                                
                                # 답변 완료 메시지 전송
                                sse_message = {
                                    "type": MessageType.ANSWER_COMPLETE,
                                    "session_id": session_id,
                                    "status": "completed",
                                    "timestamp": fields.get(b'timestamp', b'').decode()
                                }
                                yield MessageFormatter.format_sse_message(sse_message)
                                stream_name = self.redis_client.get_session_stream(session_id)
                                await self.redis_client.ack_stream_message(msg_id_str, stream_name)
                            
                            elif message_type == MessageType.SUMMARY_COMPLETE:
                                # 요약 완료 처리
                                summary_content = fields.get(b'summary', b'').decode()
                                data_field = fields.get(b'data', b'')
                                
                                # 요약 에이전트가 생성한 제목 추출
                                suggested_title = ""
                                logger.info(f"🔍 data_field 존재 여부: {bool(data_field)}")
                                if data_field:
                                    logger.info(f"🔍 data_field 길이: {len(data_field)}")
                                    logger.info(f"🔍 data_field 내용 (처음 200자): {data_field.decode()[:200]}")
                                    try:
                                        # data_field는 이미 JSON 문자열로 변환되어 있음
                                        data_dict = json.loads(data_field.decode())
                                        logger.info(f"🔍 파싱된 data_dict 키들: {list(data_dict.keys())}")
                                        suggested_title = data_dict.get('title', '')
                                        logger.info(f"📝 요약 에이전트 제목 추출: '{suggested_title}'")
                                    except Exception as e:
                                        logger.warning(f"⚠️ 제목 데이터 파싱 실패: {e}")
                                        logger.warning(f"⚠️ data_field 내용: {data_field.decode()[:200]}...")
                                else:
                                    logger.warning(f"⚠️ data_field가 비어있습니다")
                                
                                logger.info(f"📝 요약 완료 수신: 세션 {session_id}")
                                
                                # 세션의 실제 소유자 확인 (session_service를 통해 DB 접근)
                                session_owner_query = select(ConversationSession.user_id).where(
                                    ConversationSession.id == session_id
                                )
                                session_owner_result = await self.session_service.db.execute(session_owner_query)
                                session_owner_id = session_owner_result.scalar_one_or_none()
                                
                                if not session_owner_id:
                                    logger.error(f"❌ 세션 {session_id}을 찾을 수 없습니다")
                                    continue
                                
                                logger.info(f"🔍 세션 {session_id} 실제 소유자: {session_owner_id}")
                                
                                # 요약을 DB에 저장 (세션의 실제 소유자 사용)
                                try:
                                    await self.session_service.save_summary_to_session(
                                        session_id, session_owner_id, question, summary_content, request_id
                                    )
                                    logger.info(f"✅ 요약 DB 저장 완료: 세션 {session_id}")
                                    
                                    # 세션 제목 업데이트 (요약 에이전트 제목 우선 사용)
                                    if suggested_title:
                                        await self.session_service.update_session_title_directly(
                                            session_id, suggested_title
                                        )
                                        logger.info(f"✅ 요약 에이전트 제목으로 세션 제목 업데이트 완료: '{suggested_title}'")
                                    else:
                                        await self.session_service.update_session_title_from_summary(
                                            session_id, summary_content, question
                                        )
                                        logger.info(f"✅ 요약 내용에서 제목 추출하여 업데이트 완료: 세션 {session_id}")
                                    
                                except Exception as e:
                                    logger.error(f"❌ 요약 저장/제목 업데이트 실패: {e}")
                                
                                # 요약 완료 메시지 전송
                                sse_message = {
                                    "type": MessageType.SUMMARY_COMPLETE,
                                    "session_id": session_id,
                                    "summary": summary_content,
                                    "status": "completed",
                                    "timestamp": fields.get(b'timestamp', b'').decode()
                                }
                                yield MessageFormatter.format_sse_message(sse_message)
                                stream_name = self.redis_client.get_session_stream(session_id)
                                await self.redis_client.ack_stream_message(msg_id_str, stream_name)
                                return
                            
                            elif message_type == MessageType.ERROR:
                                # 오류 처리
                                error_msg = fields.get(b'error_message', b'Unknown error').decode()
                                
                                # 에러 메시지를 DB에 저장
                                try:
                                    await self.session_service.save_maice_message(
                                        session_id=session_id,
                                        user_id=user_id,
                                        content=error_msg,
                                        message_type=MessageType.ERROR
                                    )
                                    logger.info(f"✅ 에러 메시지 DB 저장 완료")
                                except Exception as e:
                                    logger.error(f"❌ 에러 메시지 DB 저장 실패: {e}")
                                
                                yield self._format_error_message(error_msg)
                                stream_name = self.redis_client.get_session_stream(session_id)
                                await self.redis_client.ack_stream_message(msg_id_str, stream_name)
                                return
                            
                            # 메시지 처리 완료 확인
                            stream_name = self.redis_client.get_session_stream(session_id)
                            await self.redis_client.ack_stream_message(msg_id_str, stream_name)
                    
                    else:
                        # 메시지가 없으면 잠시 대기
                        await asyncio.sleep(0.01)  # 10ms 대기
                
                except Exception as e:
                    logger.error(f"❌ 병렬 스트리밍 처리 오류: {e}")
                    await asyncio.sleep(0.1)  # 오류 시 100ms 대기
            
            # 타임아웃 처리
            logger.warning(f"⏰ 세션 {session_id} 처리 타임아웃")
            yield MessageFormatter.format_error_message("처리 시간이 초과되었습니다.")
            
        except Exception as e:
            logger.error(f"❌ 병렬 스트리밍 실패: {e}")
            yield MessageFormatter.format_error_message(f"스트리밍 처리 중 오류가 발생했습니다: {str(e)}")

    
    # AIAgentService는 순수 스트리밍 역할만 담당
    # 즉시 메시지 처리 - 포맷팅과 저장은 각 콘텍스트에서 관리
    
    async def process_clarification_response_parallel(self, session_id: int, 
                                                    clarification_answer: str, 
                                                    request_id: str, user_id: int) -> AsyncGenerator[str, None]:
        """명료화 답변 처리 - 병렬 처리 최적화"""
        try:
            logger.info(f"🚀 병렬 명료화 답변 처리 시작: 세션 {session_id}, 답변: {clarification_answer}")
            
            # 명료화 답변은 chat_service.py에서 이미 저장됨 - 중복 저장 방지
            
            # 처리 시작 시점 기록 (이 시점 이후 메시지만 읽기)
            processing_start_time = time.time()
            processing_timestamp = datetime.utcnow().isoformat()
            logger.info(f"🕐 명료화 처리 시작 시점: {processing_timestamp}")
            
            # 명료화 히스토리와 원본 질문 조회
            clarification_history = []
            original_question = None
            try:
                conversation_history = await self.session_service.get_conversation_history(session_id)
                if conversation_history:
                    # 명료화 질문과 답변만 추출
                    last_clarification_question = None
                    for msg in conversation_history:
                        msg_type = msg.get("message_type", "")
                        content = msg.get("content", "")
                        
                        # 원본 질문 찾기 (첫 번째 사용자 질문)
                        if not original_question and msg_type == MessageType.USER_QUESTION:
                            original_question = content
                            logger.info(f"🔍 원본 질문 발견: {original_question[:50]}...")
                        
                        if msg_type == MessageType.MAICE_CLARIFICATION_QUESTION:
                            last_clarification_question = content
                        elif msg_type == MessageType.USER_CLARIFICATION_RESPONSE and last_clarification_question:
                            clarification_history.append({
                                "question": last_clarification_question,
                                "answer": content
                            })
                            last_clarification_question = None
                    
                    logger.info(f"📚 명료화 히스토리 {len(clarification_history)}개 로드됨")
                    logger.info(f"📚 원본 질문: {original_question}")
            except Exception as e:
                logger.warning(f"⚠️ 명료화 히스토리 조회 실패: {e}")
            
            # 명료화 개선 요청 전송 (히스토리 + 원본 질문 포함)
            if self._streams_initialized:
                clarification_data = {
                    "answer": clarification_answer,
                    "user_id": user_id,
                    "clarification_history": clarification_history,  # 이전 명료화 히스토리
                    "original_question": original_question  # 원본 질문 추가 - 매우 중요!
                }
                await self.redis_client.send_clarification_request_stream(
                    request_id, clarification_data, session_id
                )
                logger.info(f"📤 명료화 개선 요청 전송: {request_id}, 히스토리 {len(clarification_history)}개, 원본: {original_question[:50] if original_question else 'None'}...")
            
            # Redis Streams에서 직접 메시지 읽기 (처리 시작 이후 메시지만) - 병렬 처리 최적화
            start_time = time.time()
            max_wait_time = TimeConstants.CLARIFICATION_TIMEOUT
            
            while time.time() - start_time < max_wait_time:
                try:
                    messages = await self.redis_client.read_from_agent_stream(count=10, block=100, session_id=session_id)
                    
                    if messages:
                        logger.info(f"🔍 Streams에서 읽은 메시지 개수: {len(messages)}")
                        logger.info(f"🔍 메시지 리스트 전체: {messages}")
                        
                        for i, (msg_id, fields) in enumerate(messages):
                            # 메시지 ID를 string으로 변환 (bytes -> string)
                            msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
                            msg_timestamp = fields.get(b'timestamp', b'').decode()
                            msg_type = fields.get(b'type', b'').decode()
                            
                            logger.info(f"🔍 메시지 [{i}] ID: {msg_id_str}, 타입: {msg_type}, 타임스탬프: {msg_timestamp}")
                            logger.info(f"🔍 메시지 [{i}] 필드 상세: {fields}")
                            
                            # 세션별 독립 채널을 사용하므로 다른 세션 메시지는 올 수 없음
                            # msg_session_id 체크 불필요
                            
                            message_type = fields.get(b'type', b'').decode()
                            logger.info(f"🎯 세션 {session_id} 처리할 메시지: ID={msg_id_str}, 타입={message_type}, 타임스탬프={msg_timestamp}")
                            
                            if message_type == MessageType.CLARIFICATION_QUESTION:
                                # 타임스탬프 체크: 처리 시작 이후 메시지만 처리
                                if msg_timestamp < processing_timestamp:
                                    logger.info(f"⏰ 처리 시작 이전 메시지 건너뜀: {msg_timestamp} < {processing_timestamp}")
                                    try:
                                        stream_name = self.redis_client.get_session_stream(session_id)
                                        await self.redis_client.ack_stream_message(msg_id_str, stream_name)
                                        logger.info(f"✅ 이전 메시지 ACK 성공: {msg_id_str}")
                                    except Exception as ack_error:
                                        logger.error(f"❌ 이전 메시지 ACK 실패: {msg_id_str}, 오류: {ack_error}")
                                    continue
                                
                                # 추가 명료화 질문 처리 (처리 시작 이후 메시지만)
                                new_message = fields.get(b'message', b'').decode()
                                logger.info(f"🔍 Streams에서 받은 새로운 명료화 질문 (처리 시작 이후): {new_message[:50]}...")
                                
                                sse_message = {
                                    "type": MessageType.CLARIFICATION_QUESTION,
                                    "session_id": session_id,
                                    "message": new_message,
                                    "question_index": fields.get(b'question_index', b'additional').decode(),
                                    "total_questions": fields.get(b'total_questions', b'ongoing').decode(),
                                    "timestamp": fields.get(b'timestamp', b'').decode()
                                }
                                logger.info(f"🔍 프론트엔드에 전송할 SSE 메시지: {sse_message}")
                                yield MessageFormatter.format_sse_message(sse_message)
                                
                                # 추가 명료화 질문을 DB에 저장
                                await ResponseHelper.save_streaming_response(
                                    self.session_service, session_id, user_id,
                                    "추가 명료화 질문", sse_message["message"],
                                    MessageType.MAICE_CLARIFICATION_QUESTION, request_id
                                )
                                
                                # 세션별 독립 채널에서 ACK 처리
                                stream_name = self.redis_client.get_session_stream(session_id)
                                await self.redis_client.ack_stream_message(msg_id_str, stream_name)
                                logger.info(f"✅ 명료화 질문 메시지 ACK 완료: {msg_id_str}")
                                return  # 추가 명료화 질문 전송 후 종료
                            
                            elif message_type == MessageType.ANSWER_RESULT:
                                # 답변 결과 처리 (명료화 실패 후 거절 응답)
                                answer_content = fields.get(b'answer', b'').decode()
                                
                                # 디버깅: 실제 받은 answer 길이 확인
                                logger.info(f"✅ 답변 결과 수신: 세션 {session_id}, 길이 {len(answer_content)}자")
                                logger.info(f"🔍 받은 answer 끝부분(마지막 100자): ...{answer_content[-100:] if len(answer_content) > 100 else answer_content}")
                                
                                # ⚠️ 중요: 청크는 이미 streaming_chunk로 전송되었으므로 여기서는 전송하지 않음
                                # answer_content는 DB 저장용으로만 사용
                                
                                # 답변을 DB에 저장
                                try:
                                    # 세션의 실제 소유자 ID 조회 (DB에서 직접 조회)
                                    from sqlalchemy import select
                                    from app.models.models import ConversationSession
                                    
                                    session_query = select(ConversationSession.user_id).where(ConversationSession.id == session_id)
                                    session_result = await self.session_service.db.execute(session_query)
                                    actual_user_id = session_result.scalar_one_or_none() or user_id
                                    
                                    logger.info(f"🔍 세션 {session_id} 실제 소유자: {actual_user_id}")
                                    
                                    await self.session_service.save_maice_message(
                                        session_id=session_id,
                                        user_id=actual_user_id,
                                        content=answer_content,
                                        message_type=MessageType.MAICE_ANSWER
                                    )
                                    logger.info(f"✅ 답변 DB 저장 완료: 세션 {session_id}")
                                except Exception as e:
                                    logger.error(f"❌ 답변 DB 저장 실패: {e}")
                                
                                # answer_complete 전송 (안전장치: 완전한 답변으로 갈아치우기)
                                sse_message = {
                                    "type": MessageType.ANSWER_COMPLETE,
                                    "session_id": session_id,
                                    "full_response": answer_content,  # 청크 순서/누락 대비 안전장치
                                    "status": "completed",
                                    "timestamp": fields.get(b'timestamp', b'').decode()
                                }
                                yield MessageFormatter.format_sse_message(sse_message)
                                logger.info(f"📤 에이전트 모드 answer_complete 전송 (full_response 포함): 세션 {session_id}")
                                stream_name = self.redis_client.get_session_stream(session_id)
                                await self.redis_client.ack_stream_message(msg_id_str, stream_name)
                                # answer_result 처리 후에도 summary_complete 대기
                            
                            elif message_type == MessageType.CLARIFICATION_COMPLETE:
                                # 명료화 완료 - 개선된 질문으로 답변 생성
                                improved_question = fields.get(b'improved_question', b'').decode()
                                
                                # 개선된 질문은 내부 처리용으로 DB 저장하지 않음 - 중복 저장 방지
                                
                                # QuestionImprovement가 이미 AnswerGenerator에 요청을 보냄
                                # 백엔드는 답변 스트리밍만 처리
                                async for answer_message in self.stream_answer_response_parallel(session_id, request_id):
                                    yield answer_message
                                
                                stream_name = self.redis_client.get_session_stream(session_id)
                                await self.redis_client.ack_stream_message(msg_id_str, stream_name)
                                return
                            
                            elif message_type == MessageType.SUMMARY_COMPLETE:
                                # 요약 완료 처리
                                summary_content = fields.get(b'summary', b'').decode()
                                data_field = fields.get(b'data', b'') # data 필드 추가
                                logger.info(f"📝 요약 완료 수신: 세션 {session_id}")
                                
                                # 요약 에이전트가 생성한 제목 추출
                                suggested_title = ""
                                if data_field:
                                    try:
                                        # data_field는 이미 JSON 문자열로 변환되어 있음
                                        data_dict = json.loads(data_field.decode())
                                        suggested_title = data_dict.get('title', '')
                                        logger.info(f"📝 요약 에이전트 제목 추출: '{suggested_title}'")
                                    except Exception as e:
                                        logger.warning(f"⚠️ 제목 데이터 파싱 실패: {e}")
                                        logger.warning(f"⚠️ data_field 내용: {data_field.decode()[:200]}...")
                                
                                # 요약을 DB에 저장
                                try:
                                    # 세션의 실제 소유자 ID 조회 (DB에서 직접 조회)
                                    from sqlalchemy import select
                                    from app.models.models import ConversationSession
                                    
                                    session_query = select(ConversationSession.user_id).where(ConversationSession.id == session_id)
                                    session_result = await self.session_service.db.execute(session_query)
                                    actual_user_id = session_result.scalar_one_or_none()
                                    
                                    if not actual_user_id:
                                        logger.error(f"❌ 세션 {session_id}을 찾을 수 없습니다")
                                        continue
                                    
                                    logger.info(f"🔍 세션 {session_id} 실제 소유자: {actual_user_id}")
                                    
                                    await self.session_service.save_summary_to_session(
                                        session_id, actual_user_id, clarification_answer, summary_content, request_id
                                    )
                                    logger.info(f"✅ 요약 DB 저장 완료: 세션 {session_id}")
                                    
                                    # 세션 제목 업데이트 - 요약 에이전트 제목 우선 사용
                                    if suggested_title:
                                        await self.session_service.update_session_title_directly(
                                            session_id, suggested_title
                                        )
                                        logger.info(f"✅ 세션 제목 업데이트 완료 (요약 에이전트 제목 사용): {suggested_title}")
                                    else:
                                        await self.session_service.update_session_title_from_summary(
                                            session_id, summary_content, clarification_answer
                                        )
                                        logger.info(f"✅ 세션 제목 업데이트 완료 (요약 내용 기반): {summary_content.split('.')[0][:50]}...")
                                    
                                except Exception as e:
                                    logger.error(f"❌ 요약 저장/제목 업데이트 실패: {e}")
                                
                                # 세션 상태를 새로운 질문 대기 상태로 업데이트
                                await self.session_service.update_session_state(
                                    session_id=session_id,
                                    current_stage=ConversationStage.READY_FOR_NEW_QUESTION,
                                    last_message_type=MessageType.SUMMARY_COMPLETE
                                )
                                logger.info(f"✅ 세션 {session_id} 상태를 새로운 질문 대기로 업데이트")
                                
                                # 요약 완료 메시지 전송
                                sse_message = {
                                    "type": MessageType.SUMMARY_COMPLETE,
                                    "session_id": session_id,
                                    "summary": summary_content,
                                    "status": "completed",
                                    "ready_for_new_question": True,
                                    "timestamp": fields.get(b'timestamp', b'').decode()
                                }
                                yield MessageFormatter.format_sse_message(sse_message)
                                stream_name = self.redis_client.get_session_stream(session_id)
                                await self.redis_client.ack_stream_message(msg_id_str, stream_name)
                                return
                            
                            elif message_type == MessageType.ERROR:
                                error_msg = fields.get(b'error_message', b'Unknown error').decode()
                                yield self._format_error_message(error_msg)
                                stream_name = self.redis_client.get_session_stream(session_id)
                                await self.redis_client.ack_stream_message(msg_id_str, stream_name)
                                return
                            
                            stream_name = self.redis_client.get_session_stream(session_id)
                            await self.redis_client.ack_stream_message(msg_id_str, stream_name)
                    
                    else:
                        await asyncio.sleep(0.01)
                
                except Exception as e:
                    logger.error(f"❌ 병렬 명료화 답변 처리 오류: {e}")
                    await asyncio.sleep(0.1)
            
            # 타임아웃
            yield MessageFormatter.format_error_message("명료화 처리 시간이 초과되었습니다.")
            
        except Exception as e:
            logger.error(f"❌ 병렬 명료화 답변 처리 실패: {e}")
            yield MessageFormatter.format_error_message(f"명료화 처리 중 오류가 발생했습니다: {str(e)}")

    
    async def _save_freepass_conversation(
        self, session_id: int, user_id: int, question: str, response: str
    ):
        """프리패스 대화를 DB에 저장"""
        try:
            # 사용자 메시지 저장 (새 세션/기존 세션 모두)
            await self.session_service.save_user_message(
                session_id=session_id,
                user_id=user_id,
                content=question,
                message_type=MessageType.USER_QUESTION
            )
            
            await self.session_service.save_maice_message(
                session_id=session_id,
                user_id=user_id,
                content=response,
                message_type=MessageType.MAICE_ANSWER
            )
            
            # 세션이 새로 생성된 경우 (메시지 수가 2개 이하인 경우) 첫 질문으로 제목 업데이트
            try:
                messages = await self.session_service.get_recent_messages(session_id, limit=5)
                if len(messages) <= 2:  # 첫 질문과 답변만 있는 경우
                    # 첫 질문을 기반으로 제목 생성 (최대 50자)
                    title = question[:47] + "..." if len(question) > 50 else question
                    await self.session_service.update_session_title_directly(session_id, title)
                    logger.info(f"✅ 프리패스 세션 제목 업데이트: '{title}'")
            except Exception as title_error:
                logger.warning(f"⚠️ 프리패스 세션 제목 업데이트 실패: {title_error}")
            
            logger.info(f"✅ 프리패스 대화 저장 완료: 세션 {session_id}")
            
        except Exception as e:
            logger.error(f"❌ 프리패스 대화 저장 실패: {e}")
            raise


    async def stream_answer_response_parallel(self, session_id: int, request_id: str) -> AsyncGenerator[str, None]:
        """답변 스트리밍 - 병렬 처리 최적화"""
        try:
            logger.info(f"🔄 병렬 답변 스트리밍 시작: 세션 {session_id}, 요청 {request_id[:8]}")
            
            start_time = time.time()
            max_wait_time = TimeConstants.CLARIFICATION_TIMEOUT
            
            while time.time() - start_time < max_wait_time:
                try:
                    messages = await self.redis_client.read_from_agent_stream(count=10, block=100, session_id=session_id)
                    
                    if messages:
                        for msg_id, fields in messages:
                            # 메시지 ID를 string으로 변환 (bytes -> string)
                            msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
                            # 세션별 독립 채널을 사용하므로 세션 ID 필터링 불필요
                            
                            message_type = fields.get(b'type', b'').decode()
                            
                            if message_type == MessageType.ANSWER_CHUNK or message_type == "streaming_chunk":
                                chunk_index = int(fields.get(b'chunk_index', b'0').decode())
                                is_final = fields.get(b'is_final', b'false').decode().lower() == 'true'
                                content = fields.get(b'chunk', fields.get(b'content', b'')).decode()
                                
                                # 첫 번째 청크일 때 세션 상태를 답변 생성 중으로 업데이트
                                if chunk_index == 0:
                                    await self.session_service.update_session_state(
                                        session_id=session_id,
                                        current_stage=ConversationStage.GENERATING_ANSWER,
                                        last_message_type=MessageType.MAICE_ANSWER
                                    )
                                    logger.info(f"✅ 세션 {session_id} 상태를 답변 생성 중으로 업데이트")
                                
                                # 통일된 형식으로 변환 및 전송
                                sse_message = self._format_streaming_chunk(fields, session_id, request_id)
                                logger.info(f"📤 스트리밍 청크 전송: 세션 {session_id}, 요청 {request_id[:8]}, 청크 {sse_message['chunk_index']}")
                                yield MessageFormatter.format_sse_message(sse_message)
                                stream_name = self.redis_client.get_session_stream(session_id)
                                await self.redis_client.ack_stream_message(msg_id_str, stream_name)
                                
                                if is_final:
                                    logger.info(f"✅ 병렬 답변 스트리밍 완료: 세션 {session_id}")
                                    # 답변 완료 시 바로 새로운 질문 대기 상태로 업데이트
                                    await self.session_service.update_session_state(
                                        session_id=session_id,
                                        current_stage=ConversationStage.READY_FOR_NEW_QUESTION,
                                        last_message_type=MessageType.MAICE_ANSWER
                                    )
                                    logger.info(f"✅ 세션 {session_id} 상태를 새로운 질문 대기로 즉시 업데이트")
                                    # 최종 청크인 경우에만 break
                                    break
                                
                                # 중간 청크는 계속 처리
                            
                            elif message_type == MessageType.ANSWER_RESULT:
                                # 답변 결과 처리 (우선순위 높음)
                                answer_content = fields.get(b'answer', b'').decode()
                                
                                # 디버깅: 실제 받은 answer 길이 확인
                                logger.info(f"✅ 답변 결과 수신: 세션 {session_id}, 길이 {len(answer_content)}자")
                                logger.info(f"🔍 받은 answer 끝부분(마지막 100자): ...{answer_content[-100:] if len(answer_content) > 100 else answer_content}")
                                
                                # ⚠️ 중요: 청크는 이미 streaming_chunk로 전송되었으므로 여기서는 전송하지 않음
                                # answer_content는 DB 저장용으로만 사용
                                
                                # 답변을 DB에 저장
                                try:
                                    # 세션의 실제 소유자 ID 조회 (DB에서 직접 조회)
                                    from sqlalchemy import select
                                    from app.models.models import ConversationSession
                                    
                                    session_query = select(ConversationSession.user_id).where(ConversationSession.id == session_id)
                                    session_result = await self.session_service.db.execute(session_query)
                                    actual_user_id = session_result.scalar_one_or_none()
                                    
                                    if not actual_user_id:
                                        logger.error(f"❌ 세션 {session_id}을 찾을 수 없습니다")
                                        continue
                                    
                                    logger.info(f"🔍 세션 {session_id} 실제 소유자: {actual_user_id}")
                                    
                                    await self.session_service.save_maice_message(
                                        session_id=session_id,
                                        user_id=actual_user_id,  # 실제 세션 소유자 ID 사용
                                        content=answer_content,
                                        message_type=MessageType.MAICE_ANSWER
                                    )
                                    logger.info(f"✅ 답변 DB 저장 완료: 세션 {session_id}")
                                except Exception as e:
                                    logger.error(f"❌ 답변 DB 저장 실패: {e}")
                                
                                # answer_complete 전송 (안전장치: 완전한 답변으로 갈아치우기)
                                sse_message = {
                                    "type": MessageType.ANSWER_COMPLETE,
                                    "session_id": session_id,
                                    "full_response": answer_content,  # 청크 순서/누락 대비 안전장치
                                    "status": "completed",
                                    "timestamp": fields.get(b'timestamp', b'').decode()
                                }
                                yield MessageFormatter.format_sse_message(sse_message)
                                logger.info(f"📤 에이전트 모드(병렬) answer_complete 전송 (full_response 포함): 세션 {session_id}")
                                stream_name = self.redis_client.get_session_stream(session_id)
                                await self.redis_client.ack_stream_message(msg_id_str, stream_name)
                                # answer_result 처리 후에도 summary_complete 대기
                            
                            elif message_type == MessageType.SUMMARY_COMPLETE:
                                # 요약 완료 처리
                                summary_content = fields.get(b'summary', b'').decode()
                                logger.info(f"📝 요약 완료 수신: 세션 {session_id}")
                                
                                # 요약을 DB에 저장 (원본 질문을 가져와야 함)
                                try:
                                    # 세션의 첫 번째 질문을 가져오기
                                    conversation_history = await self.session_service.get_conversation_history(session_id)
                                    original_question = ""
                                    if conversation_history:
                                        for conv in conversation_history:
                                            if conv.get("message_type") == "question":
                                                original_question = conv.get("question_text", "")
                                                break
                                    
                                    # 세션의 실제 소유자 ID 조회
                                    session_query = select(ConversationSession.user_id).where(ConversationSession.id == session_id)
                                    session_result = await self.session_service.db.execute(session_query)
                                    actual_user_id = session_result.scalar_one_or_none()
                                    
                                    if not actual_user_id:
                                        logger.error(f"❌ 세션 {session_id}을 찾을 수 없습니다")
                                        continue
                                    
                                    logger.info(f"🔍 세션 {session_id} 실제 소유자: {actual_user_id}")
                                    
                                    await self.session_service.save_summary_to_session(
                                        session_id, actual_user_id, original_question, summary_content, None
                                    )
                                    logger.info(f"✅ 요약 DB 저장 완료: 세션 {session_id}")
                                    
                                    # 세션 제목 업데이트
                                    await self.session_service.update_session_title_from_summary(
                                        session_id, summary_content, original_question
                                    )
                                    logger.info(f"✅ 세션 제목 업데이트 완료: 세션 {session_id}")
                                    
                                except Exception as e:
                                    logger.error(f"❌ 요약 저장/제목 업데이트 실패: {e}")
                                
                                # 세션 상태를 새로운 질문 대기 상태로 업데이트
                                await self.session_service.update_session_state(
                                    session_id=session_id,
                                    current_stage=ConversationStage.READY_FOR_NEW_QUESTION,
                                    last_message_type=MessageType.SUMMARY_COMPLETE
                                )
                                logger.info(f"✅ 세션 {session_id} 상태를 새로운 질문 대기로 업데이트")
                                
                                # 요약 완료 메시지 전송
                                sse_message = {
                                    "type": MessageType.SUMMARY_COMPLETE,
                                    "session_id": session_id,
                                    "summary": summary_content,
                                    "status": "completed",
                                    "ready_for_new_question": True,
                                    "timestamp": fields.get(b'timestamp', b'').decode()
                                }
                                yield MessageFormatter.format_sse_message(sse_message)
                                stream_name = self.redis_client.get_session_stream(session_id)
                                await self.redis_client.ack_stream_message(msg_id_str, stream_name)
                                return
                            
                            elif message_type == MessageType.ERROR:
                                error_msg = fields.get(b'error_message', b'Unknown error').decode()
                                yield self._format_error_message(error_msg)
                                stream_name = self.redis_client.get_session_stream(session_id)
                                await self.redis_client.ack_stream_message(msg_id_str, stream_name)
                                return
                            
                            stream_name = self.redis_client.get_session_stream(session_id)
                            await self.redis_client.ack_stream_message(msg_id_str, stream_name)
                    
                    else:
                        await asyncio.sleep(0.01)
                
                except Exception as e:
                    logger.error(f"❌ 병렬 답변 스트리밍 오류: {e}")
                    await asyncio.sleep(0.1)
            
            # 타임아웃
            yield MessageFormatter.format_error_message("답변 생성 시간이 초과되었습니다.")
            
        except Exception as e:
            logger.error(f"❌ 병렬 답변 스트리밍 실패: {e}")
            yield MessageFormatter.format_error_message(f"답변 생성 중 오류가 발생했습니다: {str(e)}")
