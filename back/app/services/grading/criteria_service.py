from app.services.base_service import BaseService
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload
import logging
from app import models
from typing import Optional, Dict, List
from app.core.config import settings

logger = logging.getLogger(__name__)

class CriteriaService(BaseService):
    def __init__(self):
        super().__init__(settings)
        
    async def get_criteria(self, problem_key: str, db: AsyncSession) -> Optional[models.GradingCriteria]:
        """채점 기준 조회"""
        try:
            result = await db.execute(
                select(models.GradingCriteria)
                .options(selectinload(models.GradingCriteria.detailed_criteria))
                .filter_by(problem_key=problem_key)
            )
            criteria = result.scalar_one_or_none()
            
            if not criteria:
                logger.warning(f"No grading criteria found for problem: {problem_key}")
                return None
                
            return criteria

        except Exception as e:
            logger.error(f"Error fetching grading criteria: {str(e)}")
            raise

    async def create_criteria(self, 
                            problem_key: str, 
                            total_points: float,
                            correct_answer: str,
                            detailed_criteria: List[Dict],
                            db: AsyncSession) -> models.GradingCriteria:
        """새로운 채점 기준 생성"""
        try:
            criteria = models.GradingCriteria(
                problem_key=problem_key,
                total_points=total_points,
                correct_answer=correct_answer
            )
            
            # 세부 기준 추가
            for detail in detailed_criteria:
                detailed = models.DetailedCriteria(
                    item=detail["item"],
                    points=detail["points"],
                    description=detail["description"]
                )
                criteria.detailed_criteria.append(detailed)
            
            db.add(criteria)
            await db.commit()
            await db.refresh(criteria)
            
            return criteria

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating grading criteria: {str(e)}")
            raise

    async def update_criteria(self,
                            problem_key: str,
                            updates: Dict,
                            db: AsyncSession) -> Optional[models.GradingCriteria]:
        """채점 기준 업데이트"""
        try:
            criteria = await self.get_criteria(problem_key, db)
            if not criteria:
                return None

            # 기본 정보 업데이트
            for key, value in updates.items():
                if hasattr(criteria, key):
                    setattr(criteria, key, value)

            # 세부 기준 업데이트
            if "detailed_criteria" in updates:
                # 기존 세부 기준 삭제
                await db.execute(
                    delete(models.DetailedCriteria)
                    .where(models.DetailedCriteria.grading_criteria_id == criteria.id)
                )
                
                # 새로운 세부 기준 추가
                for detail in updates["detailed_criteria"]:
                    detailed = models.DetailedCriteria(
                        item=detail["item"],
                        points=detail["points"],
                        description=detail["description"],
                        grading_criteria_id=criteria.id
                    )
                    db.add(detailed)

            await db.commit()
            await db.refresh(criteria)
            return criteria

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating grading criteria: {str(e)}")
            raise