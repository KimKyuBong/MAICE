"""
새로운 MAICE Agent 기반 세션 서비스
SessionMessage 모델을 사용하여 메시지 기반 대화 관리
"""

import logging
import json
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from datetime import datetime

from app.models.models import ConversationSession, SessionMessage, MessageType, SessionSummary
from app.services.maice.interfaces import ISessionService
from app.utils.timezone import utc_to_kst

logger = logging.getLogger(__name__)


class NewSessionService(ISessionService):
    """새로운 MAICE Agent 기반 세션 서비스"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_new_session(self, user_id: int, initial_question: str) -> int:
        """새로운 대화 세션 생성"""
        try:
            # 새 세션 생성
            from app.models.models import ConversationStage
            
            # 초기 질문을 기반으로 제목 생성 (최대 50자)
            title = initial_question[:47] + "..." if len(initial_question) > 50 else initial_question
            if not title.strip():
                title = "새 대화"  # 빈 질문인 경우 기본값 사용
            
            new_session = ConversationSession(
                user_id=user_id,
                title=title,  # 첫 질문을 제목으로 사용 (에이전트 모드의 경우 요약 에이전트가 나중에 업데이트)
                is_active=True,
                current_stage=ConversationStage.INITIAL_QUESTION,
                last_message_type=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db.add(new_session)
            await self.db.flush()  # ID를 얻기 위해 flush
            
            # 초기 사용자 질문 저장 제거 - 프리패스 완료 시 저장됨
            
            await self.db.commit()
            logger.info(f"✅ 새 세션 생성 완료: {new_session.id}, 제목: '{title}'")
            return new_session.id
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ 세션 생성 실패: {e}")
            raise
    
    async def save_user_message(self, session_id: int, user_id: int, 
                               content: str, message_type: str, 
                               parent_message_id: int = None, 
                               request_id: str = None) -> int:
        """사용자 메시지 저장"""
        try:
            message = SessionMessage(
                conversation_session_id=session_id,
                user_id=user_id,
                sender='user',
                content=content,
                message_type=message_type,
                parent_message_id=parent_message_id,
                request_id=request_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db.add(message)
            await self.db.flush()  # ID를 얻기 위해 flush
            
            # 세션 상태 업데이트 (커밋 포함)
            await self.update_session_state(
                session_id=session_id,
                last_message_type=message_type
            )
            
            logger.info(f"✅ 사용자 메시지 저장 완료: 세션 {session_id}, 타입 {message_type}")
            return message.id
            
        except Exception as e:
            logger.error(f"❌ 사용자 메시지 저장 실패: {e}")
            raise
    
    async def save_maice_message(self, session_id: int, user_id: int, 
                                content: str, message_type: str, 
                                parent_message_id: int = None, 
                                request_id: str = None) -> int:
        """MAICE Agent 메시지 저장 (중복 방지 포함)"""
        try:
            from sqlalchemy import select
            from datetime import timedelta
            
            # 중복 체크: 같은 세션, 같은 내용, 같은 타입, 최근 30초 내
            # 명료화 질문은 연속으로 다른 내용이 올 수 있으므로 중복 체크 제외
            if message_type == 'maice_clarification_question':
                # 명료화 질문은 중복 체크 생략하고 항상 새로 저장
                existing_message = None
            else:
                recent_time = datetime.utcnow() - timedelta(seconds=30)
                existing_query = select(SessionMessage).where(
                    SessionMessage.conversation_session_id == session_id,
                    SessionMessage.content == content,
                    SessionMessage.message_type == message_type,
                    SessionMessage.sender == 'maice',
                    SessionMessage.created_at > recent_time
                )
                result = await self.db.execute(existing_query)
                existing_message = result.scalar_one_or_none()
            
            if existing_message:
                logger.info(f"⚠️ 중복 메시지 감지, 저장 건너뜀: 세션 {session_id}, 타입 {message_type}, 기존 ID {existing_message.id}")
                return existing_message.id
            
            # 중복이 아닌 경우만 새로 저장
            message = SessionMessage(
                conversation_session_id=session_id,
                user_id=user_id,
                sender='maice',
                content=content,
                message_type=message_type,
                parent_message_id=parent_message_id,
                request_id=request_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db.add(message)
            await self.db.flush()  # ID를 얻기 위해 flush
            
            # 세션 상태 업데이트 (커밋 포함)
            await self.update_session_state(
                session_id=session_id,
                last_message_type=message_type
            )
            
            logger.info(f"✅ MAICE 메시지 저장 완료: 세션 {session_id}, 타입 {message_type}, 새 ID {message.id}")
            return message.id
            
        except Exception as e:
            logger.error(f"❌ MAICE 메시지 저장 실패: {e}")
            raise
    
    async def get_conversation_history(self, session_id: int, user_id: int = None) -> List[Dict[str, Any]]:
        """대화 히스토리 조회 (시간순) - 사용자 권한 검증 포함"""
        try:
            # 세션 소유권 확인
            if user_id:
                session_query = select(ConversationSession).where(
                    ConversationSession.id == session_id,
                    ConversationSession.user_id == user_id
                )
                session_result = await self.db.execute(session_query)
                session = session_result.scalar_one_or_none()
                
                if not session:
                    logger.warning(f"⚠️ 세션 {session_id}에 대한 접근 권한이 없습니다. 사용자: {user_id}")
                    raise ValueError(f"세션 {session_id}에 대한 접근 권한이 없습니다.")
            
            # 사용자에게 보여줄 메시지 타입만 필터링 (레거시 타입 포함)
            visible_message_types = [
                # 새로운 타입들
                MessageType.USER_QUESTION,
                MessageType.USER_CLARIFICATION_RESPONSE, 
                MessageType.USER_FOLLOW_UP,
                MessageType.MAICE_CLARIFICATION_QUESTION,
                MessageType.MAICE_ANSWER,
                MessageType.MAICE_FOLLOW_UP,
                # 레거시 타입들 (기존 데이터 호환성)
                "user_question",
                "question", 
                "clarification",
                "clarification_answer",
                "clarification_response", 
                "answer"
            ]
            
            query = select(SessionMessage).where(
                SessionMessage.conversation_session_id == session_id,
                SessionMessage.message_type.in_(visible_message_types)
            ).order_by(SessionMessage.created_at.asc())
            
            result = await self.db.execute(query)
            messages = result.scalars().all()
            
            # 딕셔너리 형태로 변환
            history = []
            for message in messages:
                history.append({
                    "id": message.id,
                    "sender": message.sender,
                    "content": message.content,
                    "message_type": message.message_type,
                    "parent_message_id": message.parent_message_id,
                    "request_id": message.request_id,
                    "created_at": utc_to_kst(message.created_at)
                })
            
            logger.info(f"✅ 대화 히스토리 조회 완료: 세션 {session_id}, {len(history)}개 메시지")
            return history
            
        except Exception as e:
            logger.error(f"❌ 대화 히스토리 조회 실패: {e}")
            raise
    
    async def get_session_state(self, session_id: int) -> Optional[Dict[str, Any]]:
        """세션 상태 조회 - 최신 상태 보장"""
        try:
            # 트랜잭션 커밋하여 최신 상태 보장
            await self.db.commit()
            
            query = select(ConversationSession).where(
                ConversationSession.id == session_id
            )
            result = await self.db.execute(query)
            session = result.scalar_one_or_none()
            
            if not session:
                return None
            
            return {
                "session_id": session.id,
                "current_stage": session.current_stage,
                "last_message_type": session.last_message_type,
                "is_active": session.is_active,
                "created_at": utc_to_kst(session.created_at),
                "updated_at": utc_to_kst(session.updated_at)
            }
            
        except Exception as e:
            logger.error(f"❌ 세션 상태 조회 실패: {e}")
            raise
    
    async def update_session_state(self, session_id: int, **kwargs) -> None:
        """세션 상태 업데이트"""
        try:
            update_data = {
                "updated_at": datetime.utcnow()
            }
            update_data.update(kwargs)
            
            await self.db.execute(
                update(ConversationSession)
                .where(ConversationSession.id == session_id)
                .values(**update_data)
            )
            
            # 변경사항 커밋
            await self.db.commit()
            
            logger.info(f"✅ 세션 상태 업데이트 완료: 세션 {session_id}")
            
        except Exception as e:
            logger.error(f"❌ 세션 상태 업데이트 실패: {e}")
            raise
    
    async def get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """사용자의 모든 세션을 조회"""
        try:
            query = (
                select(ConversationSession)
                .where(ConversationSession.user_id == user_id)
                .order_by(ConversationSession.created_at.desc())
            )
            result = await self.db.execute(query)
            sessions = result.scalars().all()
            
            sessions_data = []
            for session in sessions:
                # 각 세션의 메시지 수 조회
                message_count_query = select(func.count(SessionMessage.id)).where(
                    SessionMessage.conversation_session_id == session.id
                )
                message_count_result = await self.db.execute(message_count_query)
                message_count = message_count_result.scalar()
                
                sessions_data.append({
                    "id": session.id,
                    "title": session.title,
                    "is_active": session.is_active,
                    "message_count": message_count or 0,
                    "current_stage": session.current_stage,
                    "last_message_type": session.last_message_type,
                    "created_at": utc_to_kst(session.created_at),
                    "updated_at": utc_to_kst(session.updated_at)
                })
            
            logger.info(f"✅ 사용자 세션 목록 조회 완료: 사용자 {user_id}, {len(sessions_data)}개 세션")
            return sessions_data
            
        except Exception as e:
            logger.error(f"❌ 사용자 세션 목록 조회 실패: {e}")
            raise
    
    async def get_recent_messages(self, session_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """최근 메시지들을 조회"""
        try:
            query = (
                select(SessionMessage)
                .where(SessionMessage.conversation_session_id == session_id)
                .order_by(SessionMessage.created_at.desc())
                .limit(limit)
            )
            result = await self.db.execute(query)
            messages = result.scalars().all()
            
            # 시간순으로 정렬하여 반환
            messages.reverse()
            
            recent_messages = []
            for message in messages:
                recent_messages.append({
                    "id": message.id,
                    "sender": message.sender,
                    "content": message.content,
                    "message_type": message.message_type,
                    "created_at": utc_to_kst(message.created_at)
                })
            
            return recent_messages
            
        except Exception as e:
            logger.error(f"❌ 최근 메시지 조회 실패: {e}")
            raise
    
    async def get_session_by_id(self, session_id: int, user_id: int = None) -> Optional[ConversationSession]:
        """세션 ID로 세션을 조회 - 사용자 권한 검증 포함"""
        try:
            query = select(ConversationSession).where(
                ConversationSession.id == session_id
            )
            
            # 사용자 권한 검증
            if user_id:
                query = query.where(ConversationSession.user_id == user_id)
            
            result = await self.db.execute(query)
            session = result.scalar_one_or_none()
            
            if user_id and not session:
                logger.warning(f"⚠️ 세션 {session_id}에 대한 접근 권한이 없습니다. 사용자: {user_id}")
                raise ValueError(f"세션 {session_id}에 대한 접근 권한이 없습니다.")
            
            return session
            
        except Exception as e:
            logger.error(f"❌ 세션 조회 실패: {e}")
            raise
    
    async def save_conversation_summary(self, session_id: int, summary_data: Dict[str, Any]) -> None:
        """요약 에이전트로부터 받은 요약 정보를 세션에 저장"""
        try:
            # 세션 정보 업데이트
            update_data = {
                "conversation_summary": summary_data.get("conversation_summary", ""),
                "learning_context": json.dumps(summary_data.get("learning_context", {}), ensure_ascii=False),
                "last_summary_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            await self.db.execute(
                update(ConversationSession)
                .where(ConversationSession.id == session_id)
                .values(**update_data)
            )
            
            # SessionSummary에도 저장 (기존 방식 유지)
            if summary_data.get("conversation_summary"):
                summary = SessionSummary(
                    session_id=session_id,
                    summary_content=summary_data["conversation_summary"],
                    summary_type="conversation",
                    created_at=datetime.utcnow()
                )
                self.db.add(summary)
            
            await self.db.commit()
            logger.info(f"✅ 세션 요약 정보 저장 완료: 세션 {session_id}")
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ 세션 요약 정보 저장 실패: {e}")
            raise
    
    async def get_session_context(self, session_id: int) -> Dict[str, Any]:
        """세션의 맥락 정보를 조회 (새 질문 시 사용)"""
        try:
            query = select(ConversationSession).where(
                ConversationSession.id == session_id
            )
            result = await self.db.execute(query)
            session = result.scalar_one_or_none()
            
            if not session:
                return {}
            
            context = {
                "session_id": session.id,
                "title": session.title,
                "conversation_summary": session.conversation_summary,
                "learning_context": json.loads(session.learning_context) if session.learning_context else {},
                "last_summary_at": session.last_summary_at.isoformat() if session.last_summary_at else None,
                "current_stage": session.current_stage,
                "last_message_type": session.last_message_type
            }
            
            # 최근 메시지들도 포함
            recent_messages = await self.get_recent_messages(session_id, limit=5)
            context["recent_messages"] = recent_messages
            
            return context
            
        except Exception as e:
            logger.error(f"❌ 세션 맥락 정보 조회 실패: {e}")
            return {}
    
    async def delete_session(self, session_id: int, user_id: int) -> bool:
        """세션 삭제 - 사용자 권한 검증 포함"""
        try:
            from app.models.models import SessionSummary
            
            # 세션 소유권 확인
            session_query = select(ConversationSession).where(
                ConversationSession.id == session_id,
                ConversationSession.user_id == user_id
            )
            session_result = await self.db.execute(session_query)
            session = session_result.scalar_one_or_none()
            
            if not session:
                logger.warning(f"⚠️ 세션 {session_id}에 대한 삭제 권한이 없습니다. 사용자: {user_id}")
                raise ValueError(f"세션 {session_id}에 대한 삭제 권한이 없습니다.")
            
            # 1. 세션 요약(SessionSummary) 삭제
            await self.db.execute(
                delete(SessionSummary).where(
                    SessionSummary.session_id == session_id
                )
            )
            
            # 2. 세션과 관련된 모든 메시지 삭제
            await self.db.execute(
                delete(SessionMessage).where(
                    SessionMessage.conversation_session_id == session_id
                )
            )
            
            # 3. 세션 삭제
            await self.db.execute(
                delete(ConversationSession).where(
                    ConversationSession.id == session_id
                )
            )
            
            await self.db.commit()
            logger.info(f"✅ 세션 삭제 완료: {session_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ 세션 삭제 실패: {e}")
            raise
    
    async def save_summary_to_session(self, session_id: int, user_id: int, 
                                    original_question: str, summary_content: str, 
                                    request_id: str = None) -> None:
        """세션 요약 저장"""
        try:
            # 세션 소유권 확인
            session_query = select(ConversationSession).where(
                ConversationSession.id == session_id,
                ConversationSession.user_id == user_id
            )
            session_result = await self.db.execute(session_query)
            session = session_result.scalar_one_or_none()
            
            if not session:
                logger.warning(f"⚠️ 세션 {session_id}에 대한 요약 저장 권한이 없습니다. 사용자: {user_id}")
                raise ValueError(f"세션 {session_id}에 대한 요약 저장 권한이 없습니다.")
            
            # SessionSummary에 저장
            from app.models.models import SessionSummary
            summary = SessionSummary(
                session_id=session_id,
                summary_content=summary_content,
                summary_type="conversation",
                request_id=request_id,
                created_at=datetime.utcnow()
            )
            self.db.add(summary)
            
            # 세션의 요약 정보 업데이트
            await self.update_session_state(
                session_id=session_id,
                conversation_summary=summary_content,
                last_summary_at=datetime.utcnow()
            )
            
            await self.db.commit()
            logger.info(f"✅ 세션 요약 저장 완료: 세션 {session_id}")
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ 세션 요약 저장 실패: {e}")
            raise
    
    async def update_session_title_directly(self, session_id: int, title: str) -> None:
        """요약 에이전트가 생성한 제목으로 직접 업데이트"""
        try:
            # 제목 길이 제한 (최대 100자)
            if len(title) > 100:
                title = title[:100] + "..."
            
            await self.update_session_state(
                session_id=session_id,
                title=title
            )
            
            logger.info(f"✅ 세션 제목 직접 업데이트 완료: {title}")
            
        except Exception as e:
            logger.error(f"❌ 세션 제목 직접 업데이트 실패: {e}")
            raise
    
    async def update_session_title_from_summary(self, session_id: int, 
                                              summary_content: str, 
                                              original_question: str) -> None:
        """요약을 기반으로 세션 제목 업데이트 (fallback)"""
        try:
            # 요약에서 첫 번째 문장을 제목으로 사용
            title = summary_content.split('.')[0][:50]
            if len(summary_content.split('.')[0]) > 50:
                title += "..."
            
            await self.update_session_state(
                session_id=session_id,
                title=title
            )
            
            logger.info(f"✅ 세션 제목 업데이트 완료: {title}")
            
        except Exception as e:
            logger.error(f"❌ 세션 제목 업데이트 실패: {e}")
            raise
    
    async def get_session_summary(self, session_id: int) -> Optional[str]:
        """세션의 최신 요약을 조회합니다."""
        try:
            # 최신 세션 요약 조회
            summary_query = select(SessionSummary).where(
                SessionSummary.session_id == session_id
            ).order_by(SessionSummary.created_at.desc()).limit(1)
            
            summary_result = await self.db.execute(summary_query)
            summary = summary_result.scalar_one_or_none()
            
            if summary:
                logger.info(f"✅ 세션 요약 조회 완료: 세션 {session_id}")
                return summary.summary_content
            else:
                logger.info(f"ℹ️ 세션 요약이 없습니다: 세션 {session_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 세션 요약 조회 실패: {e}")
            return None