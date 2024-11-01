from .base import ExpressionBase, SolutionStepBase
from .student import StudentBase, StudentCreate, StudentResponse
from .submission import StudentSubmissionBase, StudentSubmissionCreate, StudentSubmissionResponse
from .analysis import ImageAnalysisResponse, ImageProcessingResponse
from .grading import GradingResponse, GradingUpdate, DetailedScore
from .criteria import (
    DetailedCriteriaBase,
    DetailedCriteriaCreate,
    DetailedCriteriaResponse,
    GradingCriteriaBase,
    GradingCriteriaCreate,
    GradingCriteriaResponse
)

# 순환 참조 해결
StudentResponse.update_forward_refs()
GradingResponse.update_forward_refs()

__all__ = [
    "ExpressionBase",
    "SolutionStepBase",
    "StudentBase",
    "StudentCreate",
    "StudentResponse",
    "StudentSubmissionBase",
    "StudentSubmissionCreate",
    "StudentSubmissionResponse",
    "ImageAnalysisResponse",
    "ImageProcessingResponse",
    "GradingResponse",
    "GradingUpdate",
    "DetailedScore",
    "DetailedCriteriaBase",
    "DetailedCriteriaCreate",
    "DetailedCriteriaResponse",
    "GradingCriteriaBase",
    "GradingCriteriaCreate",
    "GradingCriteriaResponse"
]
