from pydantic import BaseModel, Field, field_validator, model_validator, validator
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime, timezone

# ===== 데이터 저장용 모델들 =====

class QuestionClassificationData(BaseModel):
    """질문 분류 데이터"""
    request_id: str = Field(..., description="요청 ID")
    original_question: str = Field(..., description="원본 질문")
    knowledge_code: str = Field(..., description="지식 코드")
    quality: str = Field(..., description="질문 품질")
    missing_fields: List[str] = Field(default_factory=list, description="누락된 필드")
    unit_tags: List[str] = Field(default_factory=list, description="단원 태그")
    reasoning: str = Field(..., description="분류 근거")
    created_at: Optional[datetime] = Field(default=None, description="생성 시간")

class ClarificationSessionData(BaseModel):
    """명료화 세션 데이터"""
    request_id: str = Field(..., description="요청 ID")
    original_question: str = Field(..., description="원본 질문")
    initial_missing_fields: List[str] = Field(default_factory=list, description="초기 누락 필드")
    friendly_questions: List[str] = Field(default_factory=list, description="친화적 질문들")
    unit_tags: List[str] = Field(default_factory=list, description="단원 태그")
    status: str = Field(default="active", description="세션 상태 (active, completed, cancelled)")
    created_at: Optional[datetime] = Field(default=None, description="생성 시간")

class ClarificationConversationData(BaseModel):
    """명료화 대화 데이터"""
    request_id: str = Field(..., description="요청 ID")
    turn_number: int = Field(..., description="대화 턴 번호")
    current_focus: str = Field(..., description="현재 집중 영역")
    clarification_question: str = Field(..., description="명료화 질문")
    student_response: str = Field(..., description="학생 답변")
    created_at: Optional[datetime] = Field(default=None, description="생성 시간")

class AnswerEvaluationData(BaseModel):
    """답변 평가 데이터"""
    request_id: str = Field(..., description="요청 ID")
    session_id: int = Field(..., description="세션 ID")
    question: str = Field(..., description="질문")
    answer: str = Field(..., description="답변")
    evaluation: Dict[str, Any] = Field(..., description="평가 결과")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="메타데이터")
    created_at: Optional[datetime] = Field(default=None, description="생성 시간")

class FinalAnswerData(BaseModel):
    """최종 답변 데이터"""
    request_id: str = Field(..., description="요청 ID")
    session_id: int = Field(..., description="세션 ID")
    question: str = Field(..., description="질문")
    answer: str = Field(..., description="답변")
    evaluation: Dict[str, Any] = Field(..., description="평가 결과")
    created_at: Optional[datetime] = Field(default=None, description="생성 시간")

class StudentLearningStatusData(BaseModel):
    """학생 학습 상태 데이터"""
    session_id: int = Field(..., description="세션 ID")
    question_type: str = Field(..., description="질문 유형")
    understanding_level: str = Field(..., description="이해 수준")
    difficulty_areas: List[str] = Field(default_factory=list, description="어려운 영역")
    learning_style: str = Field(..., description="학습 스타일")
    analysis_summary: str = Field(..., description="분석 요약")
    created_at: Optional[datetime] = Field(default=None, description="생성 시간")

class SessionSummaryData(BaseModel):
    """세션 요약 데이터"""
    session_id: int = Field(..., description="세션 ID")
    conversation_summary: str = Field(..., description="대화 요약")
    student_status: Dict[str, Any] = Field(default_factory=dict, description="학생 상태")
    created_at: Optional[datetime] = Field(default=None, description="생성 시간")

class SessionTitleData(BaseModel):
    """세션 제목 데이터"""
    session_id: int = Field(..., description="세션 ID")
    title: str = Field(..., description="세션 제목")
    updated_at: Optional[datetime] = Field(default=None, description="업데이트 시간")

# ===== 에이전트별 요청/응답 모델들 =====

class QuestionClassificationRequest(BaseModel):
    """질문 분류 요청 모델"""
    request_id: str = Field(..., description="요청 ID")
    question: str = Field(..., description="분류할 질문")
    context: str = Field(default="", description="질문 컨텍스트")
    grade_hint: str = Field(default="고1", description="학년 힌트")
    processing_time_ms: int = Field(default=0, description="처리 시간(ms)")

class QuestionClassificationResult(BaseModel):
    """질문 분류 결과 모델"""
    request_id: str = Field(..., description="요청 ID")
    knowledge_code: str = Field(..., description="지식 코드")
    quality: str = Field(..., description="질문 품질")
    missing_fields: List[str] = Field(default_factory=list, description="누락된 필드")
    clarification_questions: List[str] = Field(default_factory=list, description="명료화 질문들")
    unit_tags: List[str] = Field(default_factory=list, description="단원 태그")
    policy_flags: Dict[str, Any] = Field(default_factory=dict, description="정책 플래그")
    reasoning: str = Field(..., description="분류 근거")
    success: bool = Field(default=True, description="성공 여부")
    error: Optional[str] = Field(default=None, description="오류 메시지")

class ClarificationSessionRequest(BaseModel):
    """명료화 세션 요청 모델"""
    request_id: str = Field(..., description="요청 ID")
    original_question: str = Field(..., description="원본 질문")
    missing_fields: List[str] = Field(default_factory=list, description="누락된 필드")
    friendly_questions: List[str] = Field(default_factory=list, description="친화적 질문들")
    unit_tags: List[str] = Field(default_factory=list, description="단원 태그")

class ClarificationTurnRequest(BaseModel):
    """명료화 턴 요청 모델"""
    request_id: str = Field(..., description="요청 ID")
    turn_number: int = Field(..., description="대화 턴 번호")
    current_focus: str = Field(..., description="현재 집중 영역")
    clarification_question: str = Field(..., description="명료화 질문")
    student_response: str = Field(..., description="학생 답변")

class AnswerEvaluationRequest(BaseModel):
    """답변 평가 요청 모델"""
    request_id: str = Field(..., description="요청 ID")
    session_id: int = Field(..., description="세션 ID")
    question: str = Field(..., description="질문")
    answer: str = Field(..., description="답변")
    evaluation: Dict[str, Any] = Field(..., description="평가 결과")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="메타데이터")

class FinalAnswerRequest(BaseModel):
    """최종 답변 요청 모델"""
    request_id: str = Field(..., description="요청 ID")
    session_id: int = Field(..., description="세션 ID")
    question: str = Field(..., description="질문")
    answer: str = Field(..., description="답변")
    evaluation: Dict[str, Any] = Field(..., description="평가 결과")

class LearningStatusRequest(BaseModel):
    """학습 상태 요청 모델"""
    session_id: int = Field(..., description="세션 ID")
    question_type: str = Field(..., description="질문 유형")
    understanding_level: str = Field(..., description="이해 수준")
    difficulty_areas: List[str] = Field(default_factory=list, description="어려운 영역")
    learning_style: str = Field(..., description="학습 스타일")
    analysis_summary: str = Field(..., description="분석 요약")

class SessionSummaryRequest(BaseModel):
    """세션 요약 요청 모델"""
    session_id: int = Field(..., description="세션 ID")
    conversation_summary: str = Field(..., description="대화 요약")
    student_status: Dict[str, Any] = Field(default_factory=dict, description="학생 상태")

class SessionTitleRequest(BaseModel):
    """세션 제목 요청 모델"""
    session_id: int = Field(..., description="세션 ID")
    title: str = Field(..., description="세션 제목")

# ===== 공통 응답 모델들 =====

class DatabaseResponse(BaseModel):
    """데이터베이스 작업 응답 모델"""
    success: bool = Field(..., description="성공 여부")
    message: str = Field(..., description="응답 메시지")
    data: Optional[Dict[str, Any]] = Field(default=None, description="응답 데이터")
    error: Optional[str] = Field(default=None, description="오류 메시지")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="응답 시간")

class AgentTaskResult(BaseModel):
    """에이전트 작업 결과 모델"""
    agent_name: str = Field(..., description="에이전트 이름")
    success: bool = Field(..., description="성공 여부")
    result: Dict[str, Any] = Field(..., description="작업 결과")
    error: Optional[str] = Field(default=None, description="오류 메시지")
    processing_time_ms: int = Field(default=0, description="처리 시간(ms)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="완료 시간")

# ===== 유틸리티 모델들 =====

class DatabaseConnectionConfig(BaseModel):
    """데이터베이스 연결 설정 모델"""
    host: str = Field(default="postgres", description="데이터베이스 호스트")
    port: int = Field(default=5432, description="데이터베이스 포트")
    database: str = Field(default="maice_agent", description="데이터베이스 이름")
    username: str = Field(default="postgres", description="사용자명")
    password: str = Field(default="postgres", description="비밀번호")
    min_connections: int = Field(default=2, description="최소 연결 수")
    max_connections: int = Field(default=10, description="최대 연결 수")
    command_timeout: int = Field(default=30, description="명령 타임아웃(초)")

class TableSchema(BaseModel):
    """테이블 스키마 모델"""
    table_name: str = Field(..., description="테이블 이름")
    columns: List[Dict[str, str]] = Field(..., description="컬럼 정보")
    indexes: List[str] = Field(default_factory=list, description="인덱스 정보")
    constraints: List[str] = Field(default_factory=list, description="제약 조건")

# ===== 기존 에이전트 모델들 (통합) =====

class QuestionClassified(BaseModel):
    """질문 분류 결과 (기존 schemas.py에서 이동)"""
    request_id: Optional[str] = Field(default=None, description="요청 ID")
    question: str = Field(..., description="질문")
    context: Optional[str] = Field(default="", description="컨텍스트")
    knowledge_code: str = Field(..., pattern=r"^K[1-4]$", description="지식 코드")
    quality: str = Field(..., pattern=r"^(answerable|needs_clarify|unanswerable)$", description="질문 품질")
    grade_hint: str = Field(default="고1", description="학년 힌트")
    unit_tags: List[str] = Field(default_factory=list, description="단원 태그")
    missing_fields: List[str] = Field(default_factory=list, description="누락된 필드")
    clarification_questions: List[str] = Field(default_factory=list, description="명료화 질문들")
    policy_flags: Dict[str, bool] = Field(default_factory=dict, description="정책 플래그")

    @validator("knowledge_code")
    def _kc(cls, v: str) -> str:
        v = v.upper()
        return v if v in {"K1", "K2", "K3", "K4"} else "K1"

    @validator("quality")
    def _qt(cls, v: str) -> str:
        return v if v in {"answerable", "needs_clarify", "unanswerable"} else "answerable"

    def with_korean_label(self) -> Dict:
        data = self.dict()
        label_map = {
            "answerable": "답변 가능",
            "needs_clarify": "의견 보충",
            "unanswerable": "답변 거부",
        }
        data["quality_label"] = label_map.get(self.quality, "답변 가능")
        return data

class EvaluationResult(BaseModel):
    """평가 결과 (기존 common/models.py에서 이동)"""
    scores: List[float] = Field(default_factory=list, description="12개 상세 점수 (0~1 스케일)")
    category_scores: Dict[str, float] = Field(default_factory=dict, description="카테고리별 총점 (총점 포함)")
    total_score: Optional[float] = Field(default=None, description="카테고리 점수 합계 (총점)")
    question_grade: Optional[Literal['normal', 'excellent', 'rejected']] = Field(default=None, description="질문 등급")
    is_excellent: Optional[bool] = Field(default=None, description="우수 질문 여부")
    is_rejected: Optional[bool] = Field(default=None, description="거부 질문 여부")
    weak_areas: List[str] = Field(default_factory=list, description="약점 영역")
    detailed_feedback: str = Field(default="", description="상세 피드백")

    @field_validator('scores', mode='before')
    @classmethod
    def ensure_scores_length_and_range(cls, v):
        # Coerce to list of floats, length 12, clamp 0..1
        vals: List[float] = []
        try:
            for item in list(v)[:12]:
                try:
                    f = float(item)
                except Exception:
                    f = 0.5
                f = max(0.0, min(1.0, f))
                vals.append(f)
        except Exception:
            vals = []
        while len(vals) < 12:
            vals.append(0.5)
        return vals

    @model_validator(mode='after')
    def compute_category_and_grade(self):
        # Compute category scores if missing
        cs = dict(self.category_scores or {})
        if not cs or not all(k in cs for k in ("수학적 전문성", "질문 구조화", "학습 맥락 적용")):
            math_expertise = sum(self.scores[0:4]) + 1
            question_structure = sum(self.scores[4:8]) + 1
            learning_context = sum(self.scores[8:12]) + 1
            cs = {
                "수학적 전문성": round(math_expertise, 3),
                "질문 구조화": round(question_structure, 3),
                "학습 맥락 적용": round(learning_context, 3),
            }
        total = cs.get("총점")
        if total is None:
            total = cs["수학적 전문성"] + cs["질문 구조화"] + cs["학습 맥락 적용"]
            cs["총점"] = round(total, 3)
        self.category_scores = cs
        self.total_score = total

        # Compute grade flags if missing
        if self.is_rejected is None:
            self.is_rejected = (
                cs["수학적 전문성"] <= 3.0 and
                cs["질문 구조화"] <= 3.0 and
                cs["학습 맥락 적용"] <= 3.0
            )
        if self.is_excellent is None:
            self.is_excellent = (self.total_score >= 12.0)
        if self.question_grade is None:
            self.question_grade = (
                'rejected' if self.is_rejected else ('excellent' if self.is_excellent else 'normal')
            )
        return self

class AgentRequest(BaseModel):
    """에이전트 요청 (기존 common/models.py에서 이동)"""
    request_id: str = Field(..., description="요청 ID")
    question: str = Field(..., description="질문")
    context: str = Field(default="", description="컨텍스트")
    session_id: Optional[int] = Field(default=None, description="세션 ID")
    timestamp: Optional[str] = Field(default=None, description="타임스탬프")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="메타데이터")

class AgentResponse(BaseModel):
    """에이전트 응답 (기존 common/models.py에서 이동)"""
    request_id: str = Field(..., description="요청 ID")
    evaluation: Dict[str, Any] = Field(default_factory=dict, description="평가 결과")
    answer: Optional[str] = Field(default=None, description="답변")
    feedback: Optional[str] = Field(default=None, description="피드백")
    question_grade: Optional[Literal['normal', 'excellent', 'rejected']] = Field(default=None, description="질문 등급")
    is_excellent: Optional[bool] = Field(default=None, description="우수 질문 여부")
    is_rejected: Optional[bool] = Field(default=None, description="거부 질문 여부")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="메타데이터")

class ProgressEvent(BaseModel):
    """진행 상황 이벤트 (기존 common/models.py에서 이동)"""
    request_id: str = Field(..., description="요청 ID")
    stage: str = Field(..., description="단계")
    message: str = Field(..., description="메시지")
    progress: int = Field(default=0, description="진행률")
    timestamp: Optional[str] = Field(default=None, description="타임스탬프")

class AnswerEvent(BaseModel):
    """답변 이벤트 (기존 common/models.py에서 이동)"""
    request_id: str = Field(..., description="요청 ID")
    type: Literal['connected', 'chunk', 'complete', 'error'] = Field(..., description="이벤트 타입")
    content: Optional[str] = Field(default=None, description="내용")
    message: Optional[str] = Field(default=None, description="메시지")
    timestamp: Optional[str] = Field(default=None, description="타임스탬프")
