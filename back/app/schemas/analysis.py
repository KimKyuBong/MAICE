from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

# TextExtraction을 위한 Pydantic 모델
class SolutionStep(BaseModel):
    step_number: int
    content: str
    expressions: List[Dict[str, str]]

class TextExtraction(BaseModel):  # 모델을 위한 스키마 추가
    id: int
    student_id: str
    problem_key: str
    extraction_number: int
    extracted_text: str
    image_path: str
    solution_steps: str
    created_at: datetime

    class Config:
        from_attributes = True

class TextExtractionResponse(BaseModel):
    id: Optional[int] = None
    student_id: str
    problem_key: str
    extraction_number: int
    extracted_text: str
    image_path: str
    solution_steps: Optional[List[SolutionStep]] = None
    created_at: Optional[datetime] = None
    grading_id: Optional[int] = None

    class Config:
        from_attributes = True

class GradingResponse(BaseModel):
    id: int
    student_id: str
    problem_key: str
    submission_id: int
    extraction_id: int  # OCR 추출 결과와 연결
    image_path: str
    extracted_text: str
    solution_steps: List[Dict[str, Any]]
    total_score: float
    max_score: float
    feedback: str
    grading_number: int
    is_consolidated: bool
    created_at: datetime

    class Config:
        from_attributes = True

# 새로운 스키마 추가
class MultipleExtractionResult(BaseModel):
    results: List[TextExtractionResponse]
    gradings: List[GradingResponse]  # 채점 결과 추가
    count: int

class ImageAnalysisResponse(BaseModel):
    success: bool
    content: Optional[MultipleExtractionResult] = None
    error: Optional[str] = None

    class Config:
        from_attributes = True

class ImageProcessingResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True