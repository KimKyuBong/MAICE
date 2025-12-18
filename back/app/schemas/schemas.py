from pydantic import BaseModel, Field
from typing import Optional, List, Union
from datetime import datetime
from app.models.models import UserRole
from app.utils.timezone import utc_to_kst


class TimezoneBaseModel(BaseModel):
    """
    모든 스키마의 Base 클래스
    datetime 필드를 자동으로 UTC → KST로 변환
    """
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: utc_to_kst(v) if v else None
        }


class UserBase(TimezoneBaseModel):
    """사용자 기본 정보 모델"""
    username: str = Field(..., min_length=3, max_length=50, description="사용자명")
    role: UserRole = Field(..., description="사용자 역할")
    question_count: int = Field(default=0, ge=0, description="질문 수")
    max_questions: int = Field(default=0, ge=0, description="최대 질문 수")


class UserCreate(UserBase):
    """사용자 생성 모델"""
    password: str = Field(..., min_length=6, description="비밀번호")
    max_questions: Optional[int] = Field(None, ge=0, description="최대 질문 수")


class UserUpdate(BaseModel):
    """사용자 정보 업데이트 모델"""
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="사용자명")
    password: Optional[str] = Field(None, min_length=6, description="비밀번호")
    role: Optional[UserRole] = Field(None, description="사용자 역할")
    max_questions: Optional[int] = Field(None, ge=0, description="최대 질문 수")


class UserPreferencesUpdate(BaseModel):
    """사용자 설정 업데이트 모델 (관리자용)"""
    max_questions: Optional[int] = Field(None, ge=0, description="최대 질문 수")
    remaining_questions: Optional[int] = Field(None, ge=0, description="잔여 질문 수")
    assigned_mode: Optional[str] = Field(None, description="할당된 모드 (agent/freepass/None)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "max_questions": 20,
                "remaining_questions": 15,
                "assigned_mode": "agent"
            }
        }


class User(UserBase):
    """사용자 정보 응답 모델"""
    id: int = Field(..., description="사용자 ID")
    access_token: Optional[str] = Field(None, description="액세스 토큰")
    question_count: int = Field(..., ge=0, description="질문 수")
    max_questions: Optional[int] = Field(None, ge=0, description="최대 질문 수")
    created_at: datetime = Field(..., description="생성 시간")
    
    # A/B 테스트 관련 필드
    assigned_mode: Optional[str] = Field(None, description="할당된 모드 (agent/freepass)")
    mode_assigned_at: Optional[datetime] = Field(None, description="모드 할당 시각")
    
    # 학생 설정 관련 필드
    remaining_questions: Optional[int] = Field(None, ge=0, description="잔여 질문 수")
    
    # 통계 필드
    session_count: Optional[int] = Field(None, ge=0, description="세션 수")
    
    # 연구 동의 관련 필드
    research_consent: Optional[bool] = Field(None, description="연구 참여 동의 여부")
    research_consent_date: Optional[datetime] = Field(None, description="동의 날짜")
    research_consent_version: Optional[str] = Field(None, description="동의서 버전")
    research_consent_withdrawn_at: Optional[datetime] = Field(None, description="동의 철회 날짜")
    
    # Google OAuth 필드
    google_id: Optional[str] = Field(None, description="Google ID")
    google_email: Optional[str] = Field(None, description="Google 이메일")
    google_name: Optional[str] = Field(None, description="Google 이름")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: utc_to_kst(v) if v else None
        }

class QuestionBase(TimezoneBaseModel):
    """질문 기본 정보 모델 (자동 시간 변환)"""
    question_text: str = Field(..., min_length=1, max_length=4000, description="질문 내용")
    answer_text: Optional[str] = Field(None, max_length=8000, description="답변 내용")
    image_path: Optional[str] = Field(None, description="이미지 경로")


class QuestionCreate(QuestionBase):
    """질문 생성 모델"""
    pass


class Question(QuestionBase):
    """질문 정보 응답 모델"""
    id: int = Field(..., description="질문 ID")
    user_id: int = Field(..., description="사용자 ID")
    created_at: datetime = Field(..., description="생성 시간")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: utc_to_kst(v) if v else None
        }

class QuestionResponse(TimezoneBaseModel):
    id: int
    question: str
    answer: str
    image_path: Optional[str] = None
    analysis: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True

class SurveyResponseBase(TimezoneBaseModel):
    response_text: Optional[str] = None
    relevance_score: Optional[int] = None
    guidance_score: Optional[int] = None
    clarity_score: Optional[int] = None
    feedback_text: Optional[str] = None
    difficult_words: Optional[str] = None

class SurveyResponseCreate(SurveyResponseBase):
    question_id: int

class SurveyResponse(SurveyResponseBase):
    id: int
    user_id: int
    question_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class QuestionScores(BaseModel):
    relevance: int  # 수학 관련성
    clarity: int    # 명료한 질문
    context: int    # 충분한 맥락

class AnswerScores(BaseModel):
    suitability: int  # 수준 적합도
    clarity: int      # 명료한 설명
    guidance: int     # 교육적 안내

class TeacherEvaluationBase(TimezoneBaseModel):
    # 질문 평가 (1-5점 척도)
    question_relevance_score: int     # 수학 관련성
    question_clarity_score: int       # 명료한 질문
    question_context_score: int       # 충분한 맥락
    
    # 답변 평가 (1-5점 척도)
    answer_suitability_score: int     # 수준 적합도
    answer_clarity_score: int         # 명료한 설명
    answer_guidance_score: int        # 교육적 안내

class TeacherEvaluationCreateDetailed(BaseModel):
    question_id: int
    question_scores: QuestionScores
    answer_scores: AnswerScores

class TeacherEvaluationCreate(TeacherEvaluationBase):
    question_id: int

class TeacherEvaluation(TeacherEvaluationBase):
    id: int
    user_id: int
    question_id: int
    evaluated_by: int
    created_at: datetime
    question: Question

    class Config:
        from_attributes = True

class TeacherEvaluationUpdate(BaseModel):
    type: str  # "question" 또는 "answer"
    scores: Union[QuestionScores, AnswerScores]

class GPTEvaluationBase(TimezoneBaseModel):
    answer_rating: int
    clarity_rating: int
    educational_rating: int
    feedback: str

class GPTEvaluationCreate(GPTEvaluationBase):
    question_id: int
    teacher_id: int

class GPTEvaluation(GPTEvaluationBase):
    id: int
    question_id: int
    teacher_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    """인증 토큰 모델"""
    access_token: str = Field(..., description="액세스 토큰")
    token_type: str = Field(default="bearer", description="토큰 타입")
    role: str = Field(..., description="사용자 역할")

    class Config:
        json_encoders = {
            datetime: lambda v: utc_to_kst(v) if v else None
        }


class TokenData(BaseModel):
    """토큰 데이터 모델"""
    username: Optional[str] = Field(None, description="사용자명")
    role: Optional[str] = Field(None, description="사용자 역할")


# SSE 응답을 위한 스키마
class SSEBaseMessage(TimezoneBaseModel):
    """SSE 기본 메시지 모델"""
    type: str = Field(..., description="메시지 타입")
    progress: Optional[int] = Field(None, ge=0, le=100, description="진행률 (%)")
    timestamp: Optional[str] = Field(None, description="타임스탬프")


class SSEConnectedMessage(SSEBaseMessage):
    """SSE 연결 확인 메시지"""
    type: str = Field(default="connected", description="메시지 타입")
    request_id: str = Field(..., description="요청 ID")
    message: str = Field(..., description="연결 메시지")
    session_id: Optional[int] = Field(None, description="세션 ID")


class SSEProcessingMessage(SSEBaseMessage):
    """SSE 처리 중 메시지"""
    type: str = Field(default="processing", description="메시지 타입")
    message: str = Field(..., description="처리 상태 메시지")
    progress: int = Field(..., ge=0, le=100, description="진행률")


class SSEClarificationMessage(SSEBaseMessage):
    """SSE 명료화 질문 메시지"""
    type: str = Field(default="clarification_question", description="메시지 타입")
    message: str = Field(..., description="명료화 질문")
    progress: int = Field(..., ge=0, le=100, description="진행률")


class SSEClarificationQuestionsMessage(SSEBaseMessage):
    """SSE 명료화 질문들 메시지"""
    type: str = Field(default="clarification_questions", description="메시지 타입")
    questions: List[str] = Field(..., min_items=1, description="명료화 질문 목록")
    message: str = Field(..., description="메시지")
    progress: int = Field(..., ge=0, le=100, description="진행률")


class SSEClarificationNeededMessage(SSEBaseMessage):
    """SSE 명료화 필요 메시지"""
    type: str = Field(default="clarification_needed", description="메시지 타입")
    message: str = Field(..., description="명료화 필요 메시지")
    progress: int = Field(..., ge=0, le=100, description="진행률")

class SSEClarificationCompleteMessage(SSEBaseMessage):
    type: str = "clarification_complete"
    status: str
    completed: bool
    summary_completed: bool
    progress: int

class SSEAnswerChunkMessage(SSEBaseMessage):
    type: str = "answer_chunk"
    chunk: str
    chunk_index: int
    total_chunks: Optional[int] = None
    progress: int

class SSEAnswerCompleteMessage(SSEBaseMessage):
    type: str = "answer_complete"
    status: str
    completed: bool
    summary_completed: bool
    progress: int

class SSEStreamingStartMessage(SSEBaseMessage):
    type: str = "streaming_start"
    message: str
    progress: int

class SSEStreamingCompleteMessage(SSEBaseMessage):
    type: str = "streaming_complete"
    status: str
    completed: bool
    summary_completed: bool
    progress: int

class SSECompleteMessage(SSEBaseMessage):
    type: str = "complete"
    request_id: str
    session_id: Optional[int] = None
    status: str
    completed: bool
    summary_completed: bool

class SSEAnswerReadyMessage(SSEBaseMessage):
    type: str = "answer_ready"
    message: str
    progress: int

class SSESummaryReadyMessage(SSEBaseMessage):
    type: str = "summary_ready"
    message: str
    progress: int

class SSESummaryMessage(SSEBaseMessage):
    type: str = "summary"
    summary: str
    status: str
    completed: bool
    summary_completed: bool
    progress: int

class SSEErrorMessage(SSEBaseMessage):
    type: str = "error"
    message: str
    error: Optional[str] = None

# Union 타입으로 모든 SSE 메시지 타입 지원
SSEMessage = Union[
    SSEConnectedMessage,
    SSEProcessingMessage,
    SSEClarificationMessage,
    SSEClarificationQuestionsMessage,
    SSEClarificationNeededMessage,
    SSEClarificationCompleteMessage,
    SSEAnswerChunkMessage,
    SSEAnswerCompleteMessage,
    SSEStreamingStartMessage,
    SSEStreamingCompleteMessage,
    SSECompleteMessage,
    SSEErrorMessage
]

class TeacherEvaluationResponse(TimezoneBaseModel):
    id: int
    user_id: int
    question_id: int
    evaluated_by: int
    question_relevance_score: int
    question_clarity_score: int
    question_context_score: int
    answer_suitability_score: int
    answer_clarity_score: int
    answer_guidance_score: int
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: utc_to_kst(v) if v else None
        }


# 연구 동의 관련 스키마
class ResearchConsentBase(TimezoneBaseModel):
    """연구 동의 기본 모델"""
    consent_version: str = Field(..., description="동의서 버전")


class ResearchConsentUpdate(BaseModel):
    """연구 동의 업데이트 모델"""
    research_consent: bool = Field(..., description="연구 참여 동의 여부")
    consent_version: Optional[str] = Field("1.0", description="동의서 버전")


class ResearchConsentResponse(TimezoneBaseModel):
    """연구 동의 응답 모델"""
    research_consent: bool = Field(..., description="연구 참여 동의 여부")
    research_consent_date: Optional[datetime] = Field(None, description="동의 날짜")
    research_consent_version: Optional[str] = Field(None, description="동의서 버전")
    research_consent_withdrawn_at: Optional[datetime] = Field(None, description="동의 철회 날짜")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: utc_to_kst(v) if v else None
        }