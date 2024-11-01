from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from .base import SolutionStepBase, ExpressionBase
from .submission import StudentSubmissionResponse

class DetailedScore(BaseModel):
    detailed_criteria_id: int
    score: float
    feedback: str

    class Config:
        from_attributes = True

class GradingUpdate(BaseModel):
    total_score: Optional[float] = None
    max_score: Optional[float] = None
    feedback: Optional[str] = None
    is_consolidated: Optional[bool] = None
    detailed_scores: Optional[List[DetailedScore]] = None

    class Config:
        from_attributes = True

class GradingResponse(BaseModel):
    id: int
    submission_id: int
    student_id: str
    problem_key: str
    extracted_text: str
    solution_steps: List[SolutionStepBase]
    latex_expressions: List[ExpressionBase]
    total_score: float
    max_score: float
    feedback: str
    grading_number: int
    image_path: str
    created_at: datetime
    detailed_scores: List[DetailedScore]
    submission: StudentSubmissionResponse

    class Config:
        from_attributes = True 