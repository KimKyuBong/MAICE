from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any, List

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    
    class Config:
        orm_mode = True

class EvaluationBase(BaseModel):
    question_id: str
    student_answer: str

class EvaluationCreate(EvaluationBase):
    pass

class Evaluation(EvaluationBase):
    id: int
    evaluation_result: Dict[str, Any]
    created_at: datetime
    user_id: int

    class Config:
        orm_mode = True

class EvaluationList(BaseModel):
    evaluations: List[Evaluation]

class TextAnswer(BaseModel):
    answer: str
    question: str

class ImageAnswer(BaseModel):
    image_path: str
