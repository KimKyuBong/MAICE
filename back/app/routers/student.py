from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
import logging
from app.database import get_db
from app.schemas import StudentResponse
from app import models

router = APIRouter(prefix="/students", tags=["students"])
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[StudentResponse])
async def get_students(db: AsyncSession = Depends(get_db)):
    """모든 학생 목록 조회"""
    try:
        result = await db.execute(
            select(models.Student)
            .options(
                selectinload(models.Student.gradings)
                .selectinload(models.Grading.detailed_scores)
            )
            .order_by(models.Student.id)
        )
        students = result.scalars().all()
        return students
    except Exception as e:
        logger.error(f"Failed to get students: {e}")
        raise HTTPException(status_code=500, detail="Failed to get students") 