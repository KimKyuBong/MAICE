from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any

class StudentSubmissionBase(BaseModel):
    student_id: str
    problem_key: str
    file_name: str
    image_path: str
    file_size: int
    mime_type: str

class StudentSubmissionCreate(StudentSubmissionBase):
    pass

class StudentSubmissionResponse(StudentSubmissionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class SubmissionResponse(BaseModel):
    """API 응답을 위한 공통 응답 스키마"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None