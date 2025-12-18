"""
A/B 테스트 서비스
사용자 모드 할당, 상호작용 추적, 설문조사 관리
"""

import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta

from app.models.models import UserModel, ConversationSession
from app.models.ab_test_models import (
    AbTestSession, AbTestInteraction, AbTestSurvey, UserModeType
)
from app.services.user_mode_service import UserModeService

logger = logging.getLogger(__name__)

class AbTestService:
    """A/B 테스트 서비스"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_mode_service = UserModeService(db)
    
    async def start_test_session(self, user_id: int) -> AbTestSession:
        """새로운 A/B 테스트 세션을 시작합니다."""
        try:
            # 사용자 모드 할당
            assigned_mode = await self.user_mode_service.get_or_assign_mode(user_id)
            mode_type = UserModeType.AGENT if assigned_mode == 'agent' else UserModeType.FREEPASS
            
            # 기존 활성 세션이 있는지 확인
            existing_session_stmt = select(AbTestSession).where(
                and_(
                    AbTestSession.user_id == user_id,
                    AbTestSession.is_active == True
                )
            )
            existing_result = await self.db.execute(existing_session_stmt)
            existing_session = existing_result.scalar_one_or_none()
            
            if existing_session:
                logger.info(f"기존 활성 세션 사용 (user_id: {user_id}, session_id: {existing_session.id})")
                return existing_session
            
            # 새 세션 생성
            new_session = AbTestSession(
                user_id=user_id,
                assigned_mode=mode_type
            )
            
            self.db.add(new_session)
            await self.db.commit()
            await self.db.refresh(new_session)
            
            logger.info(f"A/B 테스트 세션 시작 (user_id: {user_id}, session_id: {new_session.id}, mode: {mode_type})")
            return new_session
            
        except Exception as e:
            logger.error(f"A/B 테스트 세션 시작 실패 (user_id: {user_id}): {e}")
            await self.db.rollback()
            raise
    
    async def record_interaction(
        self,
        user_id: int,
        question_text: str,
        response_text: Optional[str] = None,
        conversation_session_id: Optional[int] = None,
        response_time_seconds: Optional[float] = None,
        question_type: Optional[str] = None
    ) -> AbTestInteraction:
        """상호작용을 기록합니다."""
        try:
            # 활성 세션 찾기
            session_stmt = select(AbTestSession).where(
                and_(
                    AbTestSession.user_id == user_id,
                    AbTestSession.is_active == True
                )
            )
            session_result = await self.db.execute(session_stmt)
            session = session_result.scalar_one_or_none()
            
            if not session:
                # 세션이 없으면 새로 시작
                session = await self.start_test_session(user_id)
            
            # 상호작용 기록
            interaction = AbTestInteraction(
                session_id=session.id,
                user_id=user_id,
                conversation_session_id=conversation_session_id,
                question_text=question_text,
                response_text=response_text,
                response_time_seconds=response_time_seconds,
                question_type=question_type,
                question_asked_at=datetime.utcnow()
            )
            
            if response_text:
                interaction.response_received_at = datetime.utcnow()
            
            self.db.add(interaction)
            
            # 세션 통계 업데이트
            session.total_messages += 1
            if response_text:
                session.total_responses += 1
            else:
                session.total_questions += 1
            
            await self.db.commit()
            await self.db.refresh(interaction)
            
            logger.info(f"상호작용 기록됨 (user_id: {user_id}, interaction_id: {interaction.id})")
            return interaction
            
        except Exception as e:
            logger.error(f"상호작용 기록 실패 (user_id: {user_id}): {e}")
            await self.db.rollback()
            raise
    
    async def update_interaction_response(
        self,
        interaction_id: int,
        response_text: str,
        response_time_seconds: Optional[float] = None
    ) -> Optional[AbTestInteraction]:
        """상호작용의 응답을 업데이트합니다."""
        try:
            stmt = select(AbTestInteraction).where(AbTestInteraction.id == interaction_id)
            result = await self.db.execute(stmt)
            interaction = result.scalar_one_or_none()
            
            if interaction:
                interaction.response_text = response_text
                interaction.response_received_at = datetime.utcnow()
                
                if response_time_seconds:
                    interaction.response_time_seconds = response_time_seconds
                
                # 세션 통계 업데이트
                session_stmt = select(AbTestSession).where(AbTestSession.id == interaction.session_id)
                session_result = await self.db.execute(session_stmt)
                session = session_result.scalar_one_or_none()
                
                if session:
                    session.total_responses += 1
                
                await self.db.commit()
                await self.db.refresh(interaction)
                
                logger.info(f"상호작용 응답 업데이트됨 (interaction_id: {interaction_id})")
            
            return interaction
            
        except Exception as e:
            logger.error(f"상호작용 응답 업데이트 실패 (interaction_id: {interaction_id}): {e}")
            await self.db.rollback()
            return None
    
    async def end_test_session(
        self,
        user_id: int,
        satisfaction_data: Optional[Dict[str, Any]] = None
    ) -> Optional[AbTestSession]:
        """A/B 테스트 세션을 종료합니다."""
        try:
            # 활성 세션 찾기
            session_stmt = select(AbTestSession).where(
                and_(
                    AbTestSession.user_id == user_id,
                    AbTestSession.is_active == True
                )
            )
            session_result = await self.db.execute(session_stmt)
            session = session_result.scalar_one_or_none()
            
            if session:
                session.is_active = False
                session.session_ended_at = datetime.utcnow()
                
                # 만족도 데이터 저장
                if satisfaction_data:
                    session.overall_satisfaction = satisfaction_data.get('overall_satisfaction')
                    session.response_quality = satisfaction_data.get('response_quality')
                    session.response_speed = satisfaction_data.get('response_speed')
                    session.learning_effectiveness = satisfaction_data.get('learning_effectiveness')
                    session.positive_feedback = satisfaction_data.get('positive_feedback')
                    session.negative_feedback = satisfaction_data.get('negative_feedback')
                    session.suggestions = satisfaction_data.get('suggestions')
                
                await self.db.commit()
                await self.db.refresh(session)
                
                logger.info(f"A/B 테스트 세션 종료 (user_id: {user_id}, session_id: {session.id})")
            
            return session
            
        except Exception as e:
            logger.error(f"A/B 테스트 세션 종료 실패 (user_id: {user_id}): {e}")
            await self.db.rollback()
            return None
    
    async def submit_survey(
        self,
        user_id: int,
        survey_data: Dict[str, Any]
    ) -> Optional[AbTestSurvey]:
        """설문조사를 제출합니다."""
        try:
            # 최근 세션 찾기
            session_stmt = select(AbTestSession).where(
                AbTestSession.user_id == user_id
            ).order_by(AbTestSession.created_at.desc())
            session_result = await self.db.execute(session_stmt)
            session = session_result.scalar_one_or_none()
            
            if not session:
                logger.error(f"세션을 찾을 수 없음 (user_id: {user_id})")
                return None
            
            # 설문조사 생성
            survey = AbTestSurvey(
                user_id=user_id,
                session_id=session.id,
                overall_experience=survey_data.get('overall_experience'),
                ease_of_use=survey_data.get('ease_of_use'),
                response_quality=survey_data.get('response_quality'),
                response_speed=survey_data.get('response_speed'),
                learning_effectiveness=survey_data.get('learning_effectiveness'),
                preferred_mode=UserModeType(survey_data.get('preferred_mode')) if survey_data.get('preferred_mode') else None,
                mode_comparison_rating=survey_data.get('mode_comparison_rating'),
                best_features=survey_data.get('best_features'),
                worst_features=survey_data.get('worst_features'),
                improvement_suggestions=survey_data.get('improvement_suggestions'),
                would_recommend=survey_data.get('would_recommend'),
                would_use_again=survey_data.get('would_use_again'),
                additional_comments=survey_data.get('additional_comments')
            )
            
            self.db.add(survey)
            await self.db.commit()
            await self.db.refresh(survey)
            
            logger.info(f"설문조사 제출됨 (user_id: {user_id}, survey_id: {survey.id})")
            return survey
            
        except Exception as e:
            logger.error(f"설문조사 제출 실패 (user_id: {user_id}): {e}")
            await self.db.rollback()
            return None
    
    async def get_test_statistics(self) -> Dict[str, Any]:
        """A/B 테스트 통계를 조회합니다."""
        try:
            # 전체 통계
            total_users_stmt = select(func.count(func.distinct(AbTestSession.user_id)))
            total_sessions_stmt = select(func.count(AbTestSession.id))
            total_interactions_stmt = select(func.count(AbTestInteraction.id))
            
            # 모드별 통계
            agent_sessions_stmt = select(func.count(AbTestSession.id)).where(
                AbTestSession.assigned_mode == UserModeType.AGENT
            )
            freepass_sessions_stmt = select(func.count(AbTestSession.id)).where(
                AbTestSession.assigned_mode == UserModeType.FREEPASS
            )
            
            # 결과 조회
            total_users = await self.db.execute(total_users_stmt)
            total_sessions = await self.db.execute(total_sessions_stmt)
            total_interactions = await self.db.execute(total_interactions_stmt)
            agent_sessions = await self.db.execute(agent_sessions_stmt)
            freepass_sessions = await self.db.execute(freepass_sessions_stmt)
            
            return {
                'total_users': total_users.scalar() or 0,
                'total_sessions': total_sessions.scalar() or 0,
                'total_interactions': total_interactions.scalar() or 0,
                'agent_sessions': agent_sessions.scalar() or 0,
                'freepass_sessions': freepass_sessions.scalar() or 0,
                'agent_percentage': (agent_sessions.scalar() / max(total_sessions.scalar(), 1)) * 100,
                'freepass_percentage': (freepass_sessions.scalar() / max(total_sessions.scalar(), 1)) * 100
            }
            
        except Exception as e:
            logger.error(f"테스트 통계 조회 실패: {e}")
            return {
                'total_users': 0,
                'total_sessions': 0,
                'total_interactions': 0,
                'agent_sessions': 0,
                'freepass_sessions': 0,
                'agent_percentage': 0,
                'freepass_percentage': 0
            }

# 서비스 인스턴스 생성 함수
async def get_ab_test_service(db: AsyncSession) -> AbTestService:
    """A/B 테스트 서비스 인스턴스를 생성합니다."""
    return AbTestService(db)
