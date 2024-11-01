from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
import logging
from typing import Any
from app.database import get_db
from app.schemas import GradingCriteriaCreate, GradingCriteriaResponse
from app import models

router = APIRouter(prefix="/criteria", tags=["criteria"])
logger = logging.getLogger(__name__)

@router.post("/", response_model=GradingCriteriaResponse)
async def create_grading_criteria(
    criteria: GradingCriteriaCreate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """채점 기준 등록 또는 업데이트"""
    try:
        result = await db.execute(
            select(models.GradingCriteria)
            .where(models.GradingCriteria.problem_key == criteria.problem_key)
        )
        existing_criteria = result.scalar_one_or_none()
        
        if existing_criteria:
            # 기존 세부 기준 삭제
            await db.execute(
                delete(models.DetailedCriteria)
                .where(models.DetailedCriteria.grading_criteria_id == existing_criteria.id)
            )
            
            # 기존 채점 기준 업데이트
            existing_criteria.total_points = criteria.total_points
            existing_criteria.correct_answer = criteria.correct_answer
            
            # 새로운 세부 기준 추가
            for detail in criteria.detailed_criteria:
                detailed_criteria = models.DetailedCriteria(
                    item=detail.item,
                    points=detail.points,
                    description=detail.description,
                    grading_criteria_id=existing_criteria.id
                )
                db.add(detailed_criteria)
            
            grading_criteria = existing_criteria
            logger.info(f"Updated grading criteria: {criteria.problem_key}")
            
        else:
            # 새로운 채점 기준 생성
            grading_criteria = models.GradingCriteria(
                problem_key=criteria.problem_key,
                total_points=criteria.total_points,
                correct_answer=criteria.correct_answer
            )
            
            db.add(grading_criteria)
            await db.flush()
            
            # 세부 기준 생성
            for detail in criteria.detailed_criteria:
                detailed_criteria = models.DetailedCriteria(
                    item=detail.item,
                    points=detail.points,
                    description=detail.description,
                    grading_criteria_id=grading_criteria.id
                )
                db.add(detailed_criteria)
            
            logger.info(f"Created grading criteria: {criteria.problem_key}")
        
        await db.commit()
        await db.refresh(grading_criteria)
        await db.refresh(grading_criteria, attribute_names=['detailed_criteria'])
        
        return grading_criteria
        
    except Exception as e:
        logger.error(f"채점 기준 등록/업데이트 중 오류 발생: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{problem_key}", response_model=GradingCriteriaResponse)
async def get_grading_criteria(
    problem_key: str,
    db: AsyncSession = Depends(get_db)
):
    """채점 기준 조회"""
    try:
        result = await db.execute(
            select(models.GradingCriteria)
            .options(selectinload(models.GradingCriteria.detailed_criteria))
            .filter_by(problem_key=problem_key)
        )
        criteria = result.scalar_one_or_none()
        
        if not criteria:
            raise HTTPException(status_code=404, detail="채점 기준을 찾을 수 없습니다.")
        
        return criteria
        
    except Exception as e:
        logger.error(f"채점 기준 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
