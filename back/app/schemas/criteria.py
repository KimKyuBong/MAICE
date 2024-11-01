from pydantic import BaseModel
from typing import List

class DetailedCriteriaBase(BaseModel):
    item: str
    points: float
    description: str

class DetailedCriteriaCreate(DetailedCriteriaBase):
    pass

class DetailedCriteriaResponse(DetailedCriteriaBase):
    id: int
    grading_criteria_id: int

    class Config:
        from_attributes = True

class GradingCriteriaBase(BaseModel):
    problem_key: str
    total_points: float
    correct_answer: str

class GradingCriteriaCreate(GradingCriteriaBase):
    detailed_criteria: List[DetailedCriteriaCreate]

class GradingCriteriaResponse(GradingCriteriaBase):
    detailed_criteria: List[DetailedCriteriaResponse]

    class Config:
        from_attributes = True 