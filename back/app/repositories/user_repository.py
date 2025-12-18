"""
사용자 관련 Repository
사용자 데이터 접근 로직을 담당
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete
from app.models.models import UserModel, UserRole, QuestionModel, SurveyResponseModel, ConversationSession, SessionMessage, ConversationEvaluation
from app.repositories.base_repository import BaseEntityRepository
import logging

logger = logging.getLogger(__name__)


class UserRepository(BaseEntityRepository):
    """사용자 데이터 접근 Repository"""
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session, UserModel)
    
    async def get_users_by_role(
        self, 
        role: Optional[UserRole] = None,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """역할별 사용자 목록 조회 (세션 수 포함)"""
        try:
            query = select(UserModel)
            
            # username과 role이 NULL이 아닌 사용자만 조회 (필수 조건)
            query = query.where(
                and_(
                    UserModel.username.isnot(None),
                    UserModel.role.isnot(None)
                )
            )
            
            # 역할 필터
            if role:
                query = query.where(UserModel.role == role)
            
            # 검색 필터
            if search:
                query = query.where(UserModel.username.contains(search))
            
            # 페이지네이션
            query = query.offset(skip).limit(limit)
            
            result = await self.db_session.execute(query)
            users = result.scalars().all()
            
            # 각 사용자의 세션 수 조회
            users_with_sessions = []
            for user in users:
                user_dict = self._entity_to_dict(user)
                
                # 세션 수 조회 - admin.py와 동일한 방식 사용
                session_count = await self.db_session.scalar(
                    select(func.count()).select_from(ConversationSession)
                    .where(ConversationSession.user_id == user.id)
                )
                
                user_dict['session_count'] = session_count or 0
                users_with_sessions.append(user_dict)
                
                logger.info(f"👤 User {user.username} (ID: {user.id}): session_count = {session_count or 0}")
            
            logger.info(f"✅ 사용자 {len(users_with_sessions)}명 조회 완료 (세션 수 포함)")
            return users_with_sessions
            
        except Exception as e:
            logger.error(f"❌ 역할별 사용자 조회 실패: {str(e)}")
            raise
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """ID로 사용자 조회"""
        try:
            query = select(UserModel).where(UserModel.id == user_id)
            result = await self.db_session.execute(query)
            user = result.scalar_one_or_none()
            return self._entity_to_dict(user) if user else None
            
        except Exception as e:
            logger.error(f"❌ 사용자 조회 실패 (ID: {user_id}): {str(e)}")
            raise
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """사용자명으로 사용자 조회"""
        try:
            query = select(UserModel).where(UserModel.username == username)
            result = await self.db_session.execute(query)
            user = result.scalar_one_or_none()
            return self._entity_to_dict(user) if user else None
            
        except Exception as e:
            logger.error(f"❌ 사용자 조회 실패 (username: {username}): {str(e)}")
            raise
    
    async def get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """사용자 통계 조회"""
        try:
            # 사용자 정보
            user = await self.get_user_by_id(user_id)
            if not user:
                return None
            
            # 질문 수 조회
            question_count_query = select(func.count(QuestionModel.id)).where(
                QuestionModel.user_id == user_id
            )
            question_count_result = await self.db_session.execute(question_count_query)
            question_count = question_count_result.scalar() or 0
            
            # 설문 응답 수 조회
            survey_count_query = select(func.count(SurveyResponseModel.id)).where(
                SurveyResponseModel.user_id == user_id
            )
            survey_count_result = await self.db_session.execute(survey_count_query)
            survey_count = survey_count_result.scalar() or 0
            
            stats = {
                "user_id": user_id,
                "username": user.get("username"),
                "role": user.get("role"),
                "question_count": question_count,
                "survey_count": survey_count,
                "created_at": user.get("created_at"),
                "last_activity": user.get("updated_at")
            }
            
            # 학생 사용자 추가 통계
            if user.get("role") == UserRole.STUDENT.value:
                max_questions = user.get("max_questions", 0) or 0
                remaining_questions = max(max_questions - question_count, 0)
                progress_rate = (question_count / max_questions * 100) if max_questions > 0 else 0
                
                stats.update({
                    "max_questions": max_questions,
                    "remaining_questions": remaining_questions,
                    "progress_rate": round(progress_rate, 2)
                })
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ 사용자 통계 조회 실패 (ID: {user_id}): {str(e)}")
            raise
    
    async def get_students_with_stats(self) -> List[Dict[str, Any]]:
        """학생 목록과 통계 조회"""
        try:
            # 학생 조회
            query = select(UserModel).where(UserModel.role == UserRole.STUDENT)
            result = await self.db_session.execute(query)
            students = result.scalars().all()
            
            student_links = []
            for student in students:
                # 각 학생의 질문 수 조회
                question_count_query = select(func.count(QuestionModel.id)).where(
                    QuestionModel.user_id == student.id
                )
                question_count_result = await self.db_session.execute(question_count_query)
                question_count = question_count_result.scalar() or 0
                
                student_links.append({
                    "id": student.id,
                    "username": student.username,
                    "question_count": question_count,
                    "max_questions": student.max_questions or 0,
                    "created_at": student.created_at.strftime("%Y-%m-%d %H:%M:%S") if student.created_at else None
                })
            
            return student_links
            
        except Exception as e:
            logger.error(f"❌ 학생 목록 조회 실패: {str(e)}")
            raise
    
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """사용자 생성"""
        try:
            new_user = UserModel(**user_data)
            self.db_session.add(new_user)
            await self.db_session.commit()
            await self.db_session.refresh(new_user)
            
            # 사용자 생성 후 모드 자동 할당
            await self._assign_user_mode(new_user.id)
            
            return self._entity_to_dict(new_user)
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"❌ 사용자 생성 실패: {str(e)}")
            raise
    
    async def _assign_user_mode(self, user_id: int):
        """사용자에게 모드 자동 할당"""
        try:
            from app.services.user_mode_service import UserModeService
            
            user_mode_service = UserModeService(self.db_session)
            assigned_mode = await user_mode_service.assign_random_mode(user_id)
            logger.info(f"✅ 사용자 {user_id}에게 모드 '{assigned_mode}' 자동 할당 완료")
            
        except Exception as e:
            logger.error(f"❌ 사용자 {user_id} 모드 할당 실패: {str(e)}")
            # 모드 할당 실패해도 사용자 생성은 계속 진행
    
    async def update_user(self, user_id: int, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """사용자 정보 업데이트"""
        try:
            query = select(UserModel).where(UserModel.id == user_id)
            result = await self.db_session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            # 업데이트할 필드 반영
            for key, value in update_data.items():
                if hasattr(user, key) and value is not None:
                    setattr(user, key, value)
            
            await self.db_session.commit()
            await self.db_session.refresh(user)
            
            return self._entity_to_dict(user)
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"❌ 사용자 업데이트 실패 (ID: {user_id}): {str(e)}")
            raise
    
    async def delete_user(self, user_id: int) -> bool:
        """사용자 삭제"""
        try:
            query = select(UserModel).where(UserModel.id == user_id)
            result = await self.db_session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            # 관련 데이터 삭제 (Foreign Key 순서 중요!)
            logger.info(f"🗑️ 사용자 삭제 시작 (ID: {user_id}, username: {user.username})")
            
            # 1. 세션 메시지 삭제 (conversation_sessions에 종속)
            session_messages_deleted = await self.db_session.execute(
                delete(SessionMessage).where(
                    SessionMessage.conversation_session_id.in_(
                        select(ConversationSession.id).where(ConversationSession.user_id == user_id)
                    )
                )
            )
            logger.info(f"  ✓ 세션 메시지 {session_messages_deleted.rowcount}개 삭제")
            
            # 2. 세션 평가 삭제 (conversation_sessions에 종속)
            evaluations_deleted = await self.db_session.execute(
                delete(ConversationEvaluation).where(
                    ConversationEvaluation.conversation_session_id.in_(
                        select(ConversationSession.id).where(ConversationSession.user_id == user_id)
                    )
                )
            )
            logger.info(f"  ✓ 세션 평가 {evaluations_deleted.rowcount}개 삭제")
            
            # 3. 세션 삭제
            sessions_deleted = await self.db_session.execute(
                delete(ConversationSession).where(ConversationSession.user_id == user_id)
            )
            logger.info(f"  ✓ 세션 {sessions_deleted.rowcount}개 삭제")
            
            # 4. 질문 삭제
            questions_deleted = await self.db_session.execute(
                delete(QuestionModel).where(QuestionModel.user_id == user_id)
            )
            logger.info(f"  ✓ 질문 {questions_deleted.rowcount}개 삭제")
            
            # 5. 설문 응답 삭제
            surveys_deleted = await self.db_session.execute(
                delete(SurveyResponseModel).where(SurveyResponseModel.user_id == user_id)
            )
            logger.info(f"  ✓ 설문 응답 {surveys_deleted.rowcount}개 삭제")
            
            # 6. 사용자 삭제
            await self.db_session.delete(user)
            await self.db_session.commit()
            
            logger.info(f"✅ 사용자 삭제 완료 (ID: {user_id}, username: {user.username})")
            
            return True
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"❌ 사용자 삭제 실패 (ID: {user_id}): {str(e)}")
            raise
    
    async def bulk_update_student_quota(
        self, 
        grade: Optional[str] = None, 
        class_num: Optional[str] = None,
        quota: int = 0,
        operation: str = 'set'
    ) -> Dict[str, int]:
        """학생 한도 일괄 업데이트"""
        try:
            # 학생 조회 쿼리 구성
            query = select(UserModel).where(UserModel.role == UserRole.STUDENT)
            
            # 학년/반 필터링 (사용자명 기반)
            if grade:
                query = query.where(UserModel.username.like(f"%{grade}%"))
            if class_num:
                query = query.where(UserModel.username.like(f"%{class_num}%"))
            
            result = await self.db_session.execute(query)
            students = result.scalars().all()
            
            updated_count = 0
            for student in students:
                if operation == 'set':
                    student.max_questions = quota
                elif operation == 'add':
                    student.max_questions = (student.max_questions or 0) + quota
                updated_count += 1
            
            await self.db_session.commit()
            return {"updated_count": updated_count}
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"❌ 학생 한도 일괄 업데이트 실패: {str(e)}")
            raise

