from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.analysis.ocr_service import OCRService
from app.services.grading.grading_service import GradingService
from app.database import get_db
from app.schemas.submission import SubmissionResponse
from app.dependencies import get_ocr_service, get_grading_service
import logging
import os
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/submissions",
    tags=["submissions"]
)

@router.post("/", response_model=SubmissionResponse)
async def create_submission(
    student_id: str = Form(...),
    problem_key: str = Form(...),
    file: UploadFile = File(...),
    ocr_service: OCRService = Depends(get_ocr_service),
    grading_service: GradingService = Depends(get_grading_service),
    db: AsyncSession = Depends(get_db)
):
    """제출물 생성 및 처리"""
    try:
        logger.info(f"Received submission - student_id: {student_id}, problem_key: {problem_key}")
        logger.info(f"File details - filename: {file.filename}, content_type: {file.content_type}")

        # 이미지 저장
        file_path = f"{student_id}/{problem_key}/{file.filename}"
        full_path = os.path.join(settings.UPLOAD_DIR, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"Image saved to: {full_path}")

        # OCR 분석
        ocr_result = await ocr_service.analyze_image(
            image_path=file_path,
            student_id=student_id,
            problem_key=problem_key,
            db=db
        )

        if not ocr_result:
            logger.error("OCR analysis failed")
            return SubmissionResponse(success=False, error="OCR 분석 실패")

        logger.info("OCR analysis completed successfully")
        return SubmissionResponse(
            success=True,
            message="제출 처리 완료",
            data={"ocr_result": ocr_result}
        )

    except Exception as e:
        logger.error(f"Error processing submission: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
