from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal


@dataclass
class EvaluationResult:
    scores: List[float] = field(default_factory=list)  # 12 detailed scores
    category_scores: Dict[str, float] = field(default_factory=dict)  # {"수학적 전문성": 0-5, ... , "총점": 0-15}
    total_score: float = 0.0
    question_grade: str = "normal"  # normal | excellent | rejected
    is_excellent: bool = False
    is_rejected: bool = False
    weak_areas: List[str] = field(default_factory=list)
    detailed_feedback: str = ""


@dataclass
class AgentRequest:
    request_id: str
    question: str
    context: str = ""
    session_id: Optional[int] = None
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    request_id: str
    evaluation: Dict[str, Any] = field(default_factory=dict)
    answer: Optional[str] = None
    feedback: Optional[str] = None
    question_grade: Optional[str] = None
    is_excellent: Optional[bool] = None
    is_rejected: Optional[bool] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProgressEvent:
    request_id: str
    stage: str
    message: str
    progress: int = 0
    timestamp: Optional[str] = None


@dataclass
class AnswerEvent:
    request_id: str
    type: Literal['connected', 'chunk', 'complete', 'error']
    content: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None
