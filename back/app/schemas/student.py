from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from .grading import GradingResponse

class StudentBase(BaseModel):
    id: str
    name: Optional[str] = None
    total_score: float = 0.0
    max_total_score: float = 0.0
    average_score: float = 0.0

class StudentCreate(StudentBase):
    pass

class StudentResponse(StudentBase):
    gradings: List[GradingResponse] = []

    class Config:
        from_attributes = True 