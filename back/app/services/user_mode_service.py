"""
사용자 모드 할당 서비스
A/B 테스트를 위한 에이전트/프리패스 모드 랜덤 할당 관리
"""

import random
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime

from app.models.models import UserModel
from app.core.db.session import get_db

logger = logging.getLogger(__name__)

class UserModeService:
    """사용자 모드 할당 서비스"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user_mode(self, user_id: int) -> Optional[str]:
        """사용자의 할당된 모드를 조회합니다."""
        try:
            stmt = select(UserModel.assigned_mode).where(UserModel.id == user_id)
            result = await self.db.execute(stmt)
            assigned_mode = result.scalar_one_or_none()
            
            logger.info(f"사용자 {user_id}의 할당된 모드: {assigned_mode}")
            return assigned_mode
            
        except Exception as e:
            logger.error(f"사용자 모드 조회 실패 (user_id: {user_id}): {e}")
            return None
    
    async def assign_random_mode(self, user_id: int) -> str:
        """사용자에게 랜덤하게 모드를 할당합니다."""
        try:
            # 사용자 정보 조회 (OAuth 여부 확인)
            user_stmt = select(UserModel).where(UserModel.id == user_id)
            user_result = await self.db.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            
            if not user:
                logger.error(f"사용자를 찾을 수 없음 (user_id: {user_id})")
                return 'agent'  # 기본값
            
            # OAuth 사용자인지 확인
            is_oauth_user = user.google_id is not None
            logger.info(f"사용자 {user_id} 모드 할당 시작 (OAuth: {is_oauth_user}, Google ID: {user.google_id})")
            
            # 현재 모드 할당 현황 확인 (균등 분배를 위해)
            agent_count_stmt = select(func.count(UserModel.id)).where(
                UserModel.assigned_mode == 'agent'
            )
            freepass_count_stmt = select(func.count(UserModel.id)).where(
                UserModel.assigned_mode == 'freepass'
            )
            
            agent_count_result = await self.db.execute(agent_count_stmt)
            freepass_count_result = await self.db.execute(freepass_count_stmt)
            
            agent_count = agent_count_result.scalar() or 0
            freepass_count = freepass_count_result.scalar() or 0
            
            logger.info(f"현재 모드 할당 현황 - 에이전트: {agent_count}, 프리패스: {freepass_count}")
            
            # 균등 분배를 위한 로직
            if agent_count < freepass_count:
                assigned_mode = 'agent'
            elif freepass_count < agent_count:
                assigned_mode = 'freepass'
            else:
                # 동일한 경우 랜덤 선택
                assigned_mode = random.choice(['agent', 'freepass'])
            
            # 사용자 모드 업데이트
            user_stmt = select(UserModel).where(UserModel.id == user_id)
            user_result = await self.db.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            
            if user:
                user.assigned_mode = assigned_mode
                user.mode_assigned_at = datetime.utcnow()
                await self.db.commit()
                
                logger.info(f"사용자 {user_id}에게 모드 '{assigned_mode}' 할당 완료")
                return assigned_mode
            else:
                logger.error(f"사용자를 찾을 수 없음 (user_id: {user_id})")
                return 'agent'  # 기본값
                
        except Exception as e:
            logger.error(f"모드 할당 실패 (user_id: {user_id}): {e}")
            await self.db.rollback()
            return 'agent'  # 기본값
    
    async def get_or_assign_mode(self, user_id: int) -> str:
        """사용자의 모드를 조회하고, 할당되지 않은 경우 랜덤 할당합니다."""
        try:
            # 기존 할당된 모드 확인
            assigned_mode = await self.get_user_mode(user_id)
            
            if assigned_mode:
                logger.info(f"사용자 {user_id}의 기존 모드 사용: {assigned_mode}")
                return assigned_mode
            else:
                # 모드 할당되지 않은 경우 랜덤 할당
                logger.info(f"사용자 {user_id}에게 새 모드 할당 시작")
                return await self.assign_random_mode(user_id)
                
        except Exception as e:
            logger.error(f"모드 조회/할당 실패 (user_id: {user_id}): {e}")
            return 'agent'  # 기본값
    
    async def get_mode_statistics(self) -> dict:
        """모드 할당 통계를 조회합니다."""
        try:
            # 전체 통계
            total_stmt = select(func.count(UserModel.id))
            agent_stmt = select(func.count(UserModel.id)).where(UserModel.assigned_mode == 'agent')
            freepass_stmt = select(func.count(UserModel.id)).where(UserModel.assigned_mode == 'freepass')
            unassigned_stmt = select(func.count(UserModel.id)).where(UserModel.assigned_mode.is_(None))
            
            # OAuth 사용자 통계
            oauth_total_stmt = select(func.count(UserModel.id)).where(UserModel.google_id.isnot(None))
            oauth_agent_stmt = select(func.count(UserModel.id)).where(
                and_(UserModel.assigned_mode == 'agent', UserModel.google_id.isnot(None))
            )
            oauth_freepass_stmt = select(func.count(UserModel.id)).where(
                and_(UserModel.assigned_mode == 'freepass', UserModel.google_id.isnot(None))
            )
            oauth_unassigned_stmt = select(func.count(UserModel.id)).where(
                and_(UserModel.assigned_mode.is_(None), UserModel.google_id.isnot(None))
            )
            
            # 일반 사용자 통계
            regular_total_stmt = select(func.count(UserModel.id)).where(UserModel.google_id.is_(None))
            regular_agent_stmt = select(func.count(UserModel.id)).where(
                and_(UserModel.assigned_mode == 'agent', UserModel.google_id.is_(None))
            )
            regular_freepass_stmt = select(func.count(UserModel.id)).where(
                and_(UserModel.assigned_mode == 'freepass', UserModel.google_id.is_(None))
            )
            regular_unassigned_stmt = select(func.count(UserModel.id)).where(
                and_(UserModel.assigned_mode.is_(None), UserModel.google_id.is_(None))
            )
            
            # 결과 조회
            total = (await self.db.execute(total_stmt)).scalar() or 0
            agent_count = (await self.db.execute(agent_stmt)).scalar() or 0
            freepass_count = (await self.db.execute(freepass_stmt)).scalar() or 0
            unassigned_count = (await self.db.execute(unassigned_stmt)).scalar() or 0
            
            oauth_total = (await self.db.execute(oauth_total_stmt)).scalar() or 0
            oauth_agent = (await self.db.execute(oauth_agent_stmt)).scalar() or 0
            oauth_freepass = (await self.db.execute(oauth_freepass_stmt)).scalar() or 0
            oauth_unassigned = (await self.db.execute(oauth_unassigned_stmt)).scalar() or 0
            
            regular_total = (await self.db.execute(regular_total_stmt)).scalar() or 0
            regular_agent = (await self.db.execute(regular_agent_stmt)).scalar() or 0
            regular_freepass = (await self.db.execute(regular_freepass_stmt)).scalar() or 0
            regular_unassigned = (await self.db.execute(regular_unassigned_stmt)).scalar() or 0
            
            return {
                'total': {
                    'total_users': total,
                    'agent_mode': agent_count,
                    'freepass_mode': freepass_count,
                    'unassigned': unassigned_count,
                    'agent_percentage': (agent_count / total * 100) if total > 0 else 0,
                    'freepass_percentage': (freepass_count / total * 100) if total > 0 else 0
                },
                'oauth_users': {
                    'total_users': oauth_total,
                    'agent_mode': oauth_agent,
                    'freepass_mode': oauth_freepass,
                    'unassigned': oauth_unassigned,
                    'agent_percentage': (oauth_agent / oauth_total * 100) if oauth_total > 0 else 0,
                    'freepass_percentage': (oauth_freepass / oauth_total * 100) if oauth_total > 0 else 0
                },
                'regular_users': {
                    'total_users': regular_total,
                    'agent_mode': regular_agent,
                    'freepass_mode': regular_freepass,
                    'unassigned': regular_unassigned,
                    'agent_percentage': (regular_agent / regular_total * 100) if regular_total > 0 else 0,
                    'freepass_percentage': (regular_freepass / regular_total * 100) if regular_total > 0 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"모드 통계 조회 실패: {e}")
            return {
                'total_users': 0,
                'agent_mode': 0,
                'freepass_mode': 0,
                'unassigned': 0,
                'agent_percentage': 0,
                'freepass_percentage': 0
            }

# 서비스 인스턴스 생성 함수
async def get_user_mode_service(db: AsyncSession = None) -> UserModeService:
    """사용자 모드 서비스 인스턴스를 생성합니다."""
    if db is None:
        async for session in get_db():
            return UserModeService(session)
    return UserModeService(db)
