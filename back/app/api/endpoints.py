from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from app.db import crud
from app.db.database import get_db
from app import schemas
from app.utils import evaluator, image_analyzer  # document_loader와 retriever는 일시적으로 제거
from typing import List
import os
import json

router = APIRouter()

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
    # RAG 관련 코드를 주석 처리합니다
    # documents, doc_embeddings, file_names = document_loader.get_documents_and_embeddings()
    # retriever_instance = retriever.Retriever(documents, doc_embeddings, file_names)
    # relevant_info = retriever_instance.retrieve_relevant_info(text_answer.question)
    
    # 평가 함수에 학생의 답변만 전달합니다
    evaluation_result = evaluator.evaluate_math_communication(text_answer.answer, [])
    return {"message": "텍스트 평가 완료", "evaluation": evaluation_result}

@router.post("/analyze-image/")
async def analyze_image(image: UploadFile = File(...)):
    # 이미지 파일을 처리합니다
    image_path = "temp/test.png"
    
    # 이미지 파일 저장
    with open(image_path, "wb") as f:
        f.write(await image.read())

    # 이미지 분석
    response_content = image_analyzer.analyze_math_image(image_path)

    # 응답이 None인지 확인
    if response_content is None:
        return {"error": "이미지 분석 중 오류가 발생했습니다. 응답이 없습니다."}

    # JSON 형식 확인 및 정리
    try:
        extracted_data = response_content  # 이미 JSON 객체로 반환됨
    except Exception as e:
        print(f"응답 처리 중 오류: {e}")
        return {"error": "응답 처리 중 오류가 발생했습니다."}

    # 평가를 위해 evaluator에 데이터 전송
    evaluation_result = evaluator.evaluate_math_communication(extracted_data["extracted_text"])

    return {"evaluation": evaluation_result}
