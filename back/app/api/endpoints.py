from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from app.db import crud
from app.db.database import get_db
from app import schemas
from app.utils import evaluator, image_analyzer
from typing import List
import logging

router = APIRouter()

logger = logging.getLogger(__name__)

@router.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db=db, user=user)

@router.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.post("/evaluations/", response_model=schemas.Evaluation)
def create_evaluation(evaluation: schemas.EvaluationCreate, user_id: int, db: Session = Depends(get_db)):
    return crud.create_evaluation(db=db, evaluation=evaluation, user_id=user_id)

@router.get("/evaluations/", response_model=List[schemas.Evaluation])
def read_evaluations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    evaluations = crud.get_evaluations(db, skip=skip, limit=limit)
    return evaluations

@router.post("/evaluate-text/")
async def evaluate_text(text_answer: schemas.TextAnswer):
    evaluation_result = evaluator.evaluate_math_communication(text_answer.answer)
    return {"message": "텍스트 평가 완료", "evaluation":evaluation_result}

@router.post("/analyze-image/")
async def analyze_image(image: UploadFile = File(...)):
    image_path = "temp/test.png"
    with open(image_path, "wb") as f:
        f.write(await image.read())

    extracted_text = image_analyzer.analyze_math_image(image_path)
    logger.info(f"이미지 분석 결과: {extracted_text[:100]}...")  # 처음 100자만 로깅

    if extracted_text is None:
        return {"error": "이미지 분석 중 오류가 발생했습니다."}

    if not extracted_text:
        return {"error": "추출된 텍스트가 없습니다."}

    evaluation_result = evaluator.evaluate_math_communication(extracted_text)
    logger.info(f"평가 결과: {evaluation_result}")

    return {"evaluation": evaluation_result}
