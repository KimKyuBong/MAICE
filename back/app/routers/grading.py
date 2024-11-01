from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import logging
import json
from app.database import get_db
from app.schemas import GradingResponse, GradingUpdate
from app import models

router = APIRouter(prefix="/gradings", tags=["gradings"])
logger = logging.getLogger(__name__)

@router.get("/{grading_id}", response_model=GradingResponse)
async def get_grading(
    grading_id: int,
    db: AsyncSession = Depends(get_db)
) -> GradingResponse:
    """채점 결과 조회"""
    try:
        result = await db.execute(
            select(models.Grading)
            .options(
                selectinload(models.Grading.detailed_scores),
                selectinload(models.Grading.submission)
            )
            .filter_by(id=grading_id)
        )
        grading = result.scalar_one_or_none()
        
        if not grading:
            raise HTTPException(status_code=404, detail="채점 결과를 찾을 수 없습니다.")
            
        return GradingResponse(
            id=grading.id,
            submission_id=grading.submission_id,
            student_id=grading.student_id,
            problem_key=grading.problem_key,
            extracted_text=grading.extracted_text,
            solution_steps=json.loads(grading.solution_steps) if grading.solution_steps else [],
            latex_expressions=json.loads(grading.latex_expressions) if grading.latex_expressions else [],
            total_score=grading.total_score,
            max_score=grading.max_score,
            feedback=grading.feedback,
            grading_number=grading.grading_number,
            image_path=grading.image_path,
            created_at=grading.created_at,
            detailed_scores=grading.detailed_scores,
            submission=grading.submission
        )
        
    except Exception as e:
        logger.error(f"채점 결과 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{grading_id}", response_model=GradingResponse)
async def update_grading(
    grading_id: int,
    updates: GradingUpdate,
    db: AsyncSession = Depends(get_db)
):
    """채점 결과 수정"""
    try:
        result = await db.execute(
            select(models.Grading).filter_by(id=grading_id)
        )
        grading = result.scalar_one_or_none()
        
        if not grading:
            raise HTTPException(status_code=404, detail="채점 결과를 찾을 수 없습니다.")
        
        for field, value in updates.dict(exclude_unset=True).items():
            setattr(grading, field, value)
            
        await db.commit()
        await db.refresh(grading)
        return grading
    except Exception as e:
        await db.rollback()
        logger.error(f"채점 결과 수정 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{grading_id}")
async def delete_grading(grading_id: int, db: AsyncSession = Depends(get_db)):
    """채점 결과 삭제"""
    try:
        result = await db.execute(
            select(models.Grading).filter_by(id=grading_id)
        )
        grading = result.scalar_one_or_none()
        
        if not grading:
            raise HTTPException(status_code=404, detail="채점 결과를 찾을 수 없습니다.")
            
        await db.delete(grading)
        await db.commit()
        
        return {"message": "채점 결과가 성공적으로 삭제되었습니다."}
    except Exception as e:
        await db.rollback()
        logger.error(f"채점 결과 삭제 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))