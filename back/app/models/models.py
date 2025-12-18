from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text, Boolean, Float
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects import postgresql
import enum
from datetime import datetime
import sqlalchemy as sa
import bcrypt

Base = declarative_base()

def hash_password(password: str) -> str:
    """비밀번호를 해시화합니다."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호가 올바른지 확인합니다."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"

class UserModeType(str, enum.Enum):
    """사용자 모드 타입"""
    AGENT = "agent"
    FREEPASS = "freepass"

class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(Enum(UserRole))
    access_token = Column(String, nullable=True)
    question_count = Column(Integer, default=0)
    max_questions = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 교사 관련 필드
    individual_evaluations = Column(Integer, default=0)  # 개별 평가 수
    group_evaluations = Column(Integer, default=0)      # 그룹 평가 수
    feedback_submissions = Column(Integer, default=0)    # 의견 제출 수
    
    # 학생 관련 필드
    remaining_questions = Column(Integer, default=0)     # 잔여 질문 수
    progress_rate = Column(Integer, default=0)          # 진행률
    
    # Google OAuth 필드
    google_id = Column(String, nullable=True, unique=True, index=True)  # Google 사용자 ID
    google_email = Column(String, nullable=True)  # Google 이메일
    google_name = Column(String, nullable=True)   # Google 이름
    google_picture = Column(String, nullable=True)  # Google 프로필 사진 URL
    google_verified_email = Column(sa.Boolean, default=False)  # 이메일 인증 여부
    
    # A/B 테스트를 위한 모드 할당 필드
    assigned_mode = Column(String, nullable=True)  # 'agent' 또는 'freepass' - 랜덤 할당된 모드
    mode_assigned_at = Column(DateTime, nullable=True)  # 모드 할당 시각
    
    # 연구 참여 동의 관련 필드
    research_consent = Column(sa.Boolean, nullable=True, default=False)  # 연구 참여 동의 여부
    research_consent_date = Column(DateTime, nullable=True)  # 동의 날짜
    research_consent_version = Column(String, nullable=True)  # 동의서 버전
    research_consent_withdrawn_at = Column(DateTime, nullable=True)  # 동의 철회 날짜
    
    # 교사 루브릭 평가 의견
    rubric_feedbacks = Column(postgresql.JSONB, nullable=True, comment='루브릭 항목별 의견')

    questions = relationship("QuestionModel", primaryjoin="and_(UserModel.id==QuestionModel.user_id)", back_populates="user")
    answered_questions = relationship("QuestionModel", primaryjoin="and_(UserModel.id==QuestionModel.answered_by)", back_populates="answered_by_user")
    survey_responses = relationship("SurveyResponseModel", back_populates="user")
    teacher_evaluations = relationship("TeacherEvaluationModel", foreign_keys="TeacherEvaluationModel.user_id", back_populates="user")
    evaluations_given = relationship("TeacherEvaluationModel", foreign_keys="TeacherEvaluationModel.evaluated_by", back_populates="evaluator")
    group_analyses = relationship("TeacherGroupAnalysis", back_populates="teacher")
    gpt_feedbacks = relationship("GPTFeedback", back_populates="teacher")
    maice_evaluations = relationship("MAICEEvaluationModel", back_populates="user")
    conversation_sessions = relationship("ConversationSession", back_populates="user")

    def set_password(self, password: str):
        """비밀번호를 해시화하여 저장합니다."""
        self.password_hash = hash_password(password)

    def verify_password(self, plain_password: str) -> bool:
        """비밀번호가 올바른지 확인합니다."""
        return verify_password(plain_password, self.password_hash)
    
    @classmethod
    def create_google_user(cls, google_data: dict, role: UserRole = UserRole.STUDENT):
        """Google OAuth 데이터로 사용자 생성"""
        user = cls(
            username=google_data['email'],  # 이메일을 username으로 사용
            google_id=google_data['google_id'],
            google_email=google_data['email'],
            google_name=google_data.get('name', ''),
            google_picture=google_data.get('picture', ''),
            google_verified_email=google_data.get('verified_email', False),
            role=role,
            question_count=0,
            remaining_questions=10 if role == UserRole.STUDENT else None,  # 학생은 기본 10개 질문
            max_questions=10 if role == UserRole.STUDENT else None
        )
        return user
    
    def is_google_user(self) -> bool:
        """Google OAuth 사용자인지 확인"""
        return self.google_id is not None
    
    def has_research_consent(self) -> bool:
        """연구 참여 동의 여부 확인"""
        return self.research_consent is True and self.research_consent_withdrawn_at is None
    
    def give_research_consent(self, version: str = "1.0"):
        """연구 참여 동의"""
        self.research_consent = True
        self.research_consent_date = datetime.utcnow()
        self.research_consent_version = version
        self.research_consent_withdrawn_at = None
        self.updated_at = datetime.utcnow()
    
    def withdraw_research_consent(self):
        """연구 참여 동의 철회"""
        self.research_consent = False
        self.research_consent_withdrawn_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

# QuestionModel - SessionMessage로 교체 예정 (레거시 지원을 위해 임시 유지)
class QuestionModel(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    conversation_session_id = Column(Integer, ForeignKey("conversation_sessions.id"), nullable=True)
    question_text = Column(String)
    answer_text = Column(String, nullable=True)
    image_path = Column(String, nullable=True)
    
    # 메시지 타입 및 요청 ID 추가
    message_type = Column(String, default="question")  # question, clarification, answer, clarification_response
    request_id = Column(String, nullable=True)  # 요청 추적용 ID
    
    created_at = Column(DateTime, default=datetime.utcnow)
    answered_at = Column(DateTime, nullable=True)
    answered_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    user = relationship("UserModel", primaryjoin="and_(QuestionModel.user_id==UserModel.id)", back_populates="questions")
    answered_by_user = relationship("UserModel", primaryjoin="and_(QuestionModel.answered_by==UserModel.id)", back_populates="answered_questions")
    survey_responses = relationship("SurveyResponseModel", back_populates="question")
    teacher_evaluations = relationship("TeacherEvaluationModel", back_populates="question")
    gpt_evaluations = relationship("GPTEvaluationModel", back_populates="question", uselist=False)
    maice_evaluations = relationship("MAICEEvaluationModel", back_populates="question", uselist=False)
    # conversation_session = relationship("ConversationSession", back_populates="questions")  # 제거됨


class SessionMessage(Base):
    """MAICE Agent와의 대화 메시지 모델"""
    
    __tablename__ = "session_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_session_id = Column(Integer, ForeignKey("conversation_sessions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sender = Column(String(20), nullable=False)  # 'user' 또는 'maice'
    content = Column(Text, nullable=False)
    message_type = Column(String(50), nullable=False)  # 메시지 타입
    parent_message_id = Column(Integer, ForeignKey("session_messages.id"), nullable=True)
    request_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 관계 설정
    conversation_session = relationship("ConversationSession", back_populates="messages")
    user = relationship("UserModel")
    parent_message = relationship("SessionMessage", remote_side=[id])
    
    def __repr__(self):
        return f"<SessionMessage(id={self.id}, sender={self.sender}, type={self.message_type})>"


class MessageType:
    """메시지 타입 상수"""
    
    # 사용자 메시지 타입
    USER_QUESTION = "user_question"
    USER_CLARIFICATION_RESPONSE = "user_clarification_response"
    USER_FOLLOW_UP = "user_follow_up"
    
    # MAICE Agent 메시지 타입
    MAICE_CLARIFICATION_QUESTION = "maice_clarification_question"
    CLARIFICATION_QUESTION = "clarification_question"  # 에이전트 간 통신용
    MAICE_ANSWER = "maice_answer"
    MAICE_FOLLOW_UP = "maice_follow_up"
    MAICE_PROCESSING = "maice_processing"
    
    # 시스템 메시지 타입
    SUMMARY_COMPLETE = "summary_complete"
    ERROR = "error"
    
    # 스트리밍 메시지 타입
    ANSWER_CHUNK = "answer_chunk"
    ANSWER_RESULT = "answer_result"
    ANSWER_COMPLETE = "answer_complete"
    CLARIFICATION_STATUS = "clarification_status"
    
    # 에이전트 통신 메시지 타입
    CLASSIFICATION_START = "classification_start"
    CLASSIFICATION_PROGRESS = "classification_progress"
    CLASSIFICATION_COMPLETE = "classification_complete"
    CLARIFICATION_START = "clarification_start"
    CLARIFICATION_PROGRESS = "clarification_progress"
    CLARIFICATION_COMPLETE = "clarification_complete"
    CLARIFICATION_SUFFICIENT = "clarification_sufficient"
    
    # Observer 에이전트 메시지 타입
    OBSERVATION_SUCCESS = "observation_success"
    OBSERVATION_ERROR = "observation_error"
    SUMMARY_SUCCESS = "summary_success"
    SUMMARY_ERROR = "summary_error"
    SUMMARY_START = "summary_start"
    SUMMARY_PROGRESS = "summary_progress"
    

class ConversationStage:
    """대화 세션 상태 상수 - 에이전트와 동일하게 유지"""
    
    # 초기 상태
    INITIAL_QUESTION = "initial_question"
    
    # 진행 상태
    PROCESSING_QUESTION = "processing_question"
    PROCESSING_FOLLOWUP = "processing_followup"
    CLARIFICATION = "clarification"
    GENERATING_ANSWER = "generating_answer"
    
    # 완료 상태 (다음 질문 대기)
    READY_FOR_NEW_QUESTION = "ready_for_new_question"
    
    @classmethod
    def is_clarification_state(cls, stage: str) -> bool:
        """명료화 진행 중인 상태인지 확인"""
        return stage == cls.CLARIFICATION
    
    @classmethod
    def is_ready_for_new_question(cls, stage: str) -> bool:
        """새 질문을 받을 수 있는 상태인지 확인"""
        return stage == cls.READY_FOR_NEW_QUESTION
    
    @classmethod
    def is_processing_state(cls, stage: str) -> bool:
        """질문 처리 중인 상태인지 확인"""
        return stage in [cls.PROCESSING_QUESTION, cls.PROCESSING_FOLLOWUP]


class QuestionType:
    """질문 타입 구분"""
    
    NEW_QUESTION = "new_question"
    FOLLOW_UP = "follow_up"
    CLARIFICATION_RESPONSE = "clarification_response"
    
    @classmethod
    def get_all_stages(cls):
        """모든 상태 목록 반환"""
        return [
            cls.INITIAL_QUESTION,
            cls.PROCESSING_QUESTION,
            cls.CLARIFICATION,
            cls.GENERATING_ANSWER,
            cls.READY_FOR_NEW_QUESTION
        ]
    
    @classmethod
    def get_user_types(cls):
        """사용자 메시지 타입 목록"""
        return [
            cls.USER_QUESTION,
            cls.USER_CLARIFICATION_RESPONSE,
            cls.USER_FOLLOW_UP,
        ]
    
    @classmethod
    def get_maice_types(cls):
        """MAICE Agent 메시지 타입 목록"""
        return [
            cls.MAICE_CLARIFICATION_QUESTION,
            cls.MAICE_ANSWER,
            cls.MAICE_FOLLOW_UP,
            cls.MAICE_PROCESSING,
        ]
    
    @classmethod
    def is_user_type(cls, message_type: str) -> bool:
        """사용자 메시지 타입인지 확인"""
        return message_type in cls.get_user_types()
    
    @classmethod
    def is_maice_type(cls, message_type: str) -> bool:
        """MAICE Agent 메시지 타입인지 확인"""
        return message_type in cls.get_maice_types()


class SurveyResponseModel(Base):
    __tablename__ = "survey_responses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    response_text = Column(String, nullable=True)
    relevance_score = Column(Integer, nullable=True)
    guidance_score = Column(Integer, nullable=True)
    clarity_score = Column(Integer, nullable=True)
    feedback_text = Column(String, nullable=True)
    difficult_words = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("UserModel", back_populates="survey_responses")
    question = relationship("QuestionModel", back_populates="survey_responses")

class TeacherEvaluationModel(Base):
    __tablename__ = "teacher_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    
    # 질문 평가 (1-5점 척도)
    question_relevance_score = Column(Integer, nullable=False)  # 수학 관련성
    question_clarity_score = Column(Integer, nullable=False)    # 명료한 질문
    question_context_score = Column(Integer, nullable=False)    # 충분한 맥락
    
    # 답변 평가 (1-5점 척도)
    answer_suitability_score = Column(Integer, nullable=False)  # 수준 적합도
    answer_clarity_score = Column(Integer, nullable=False)      # 명료한 설명
    answer_guidance_score = Column(Integer, nullable=False)     # 교육적 안내
    
    created_at = Column(DateTime, default=datetime.utcnow)
    evaluated_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # 관계 설정
    user = relationship("UserModel", foreign_keys=[user_id], back_populates="teacher_evaluations")
    evaluator = relationship("UserModel", foreign_keys=[evaluated_by], back_populates="evaluations_given")
    question = relationship("QuestionModel", back_populates="teacher_evaluations")

class TeacherGroupAnalysis(Base):
    __tablename__ = "teacher_group_analysis"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"))
    
    # 질문 분석
    low_quality_questions_characteristics = Column(Text)
    medium_quality_questions_characteristics = Column(Text)
    high_quality_questions_characteristics = Column(Text)
    
    # 답변 분석
    low_quality_answers_characteristics = Column(Text)
    medium_quality_answers_characteristics = Column(Text)
    high_quality_answers_characteristics = Column(Text)
    
    # 종합 분석
    good_question_characteristics = Column(Text)
    good_answer_characteristics = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    teacher = relationship("UserModel", back_populates="group_analyses")

# GPT 답변 평가를 위한 새로운 모델
class GPTEvaluationModel(Base):
    __tablename__ = "gpt_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"))
    teacher_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    answer_rating = Column(Integer, nullable=False)
    clarity_rating = Column(Integer, nullable=False)
    educational_rating = Column(Integer, nullable=False)
    feedback = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)

    question = relationship("QuestionModel", back_populates="gpt_evaluations")
    teacher = relationship("UserModel")

class GPTFeedback(Base):
    """GPT 피드백 모델"""
    __tablename__ = "gpt_feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"))
    feedback_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    teacher = relationship("UserModel", back_populates="gpt_feedbacks")

class ConversationSession(Base):
    """대화 세션 모델"""
    __tablename__ = "conversation_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=True)  # 세션 제목 (자동 생성 또는 사용자 지정)
    is_active = Column(sa.Boolean, default=True)  # 활성 세션 여부
    
    # 세션 상태 관리 필드 추가
    current_stage = Column(String, default="initial_question")  # 현재 대화 단계
    stage_metadata = Column(Text, nullable=True)  # 단계별 상세 데이터 (JSON)
    last_message_type = Column(String, nullable=True)  # 마지막 메시지 타입
    
    # 요약 및 맥락 정보 필드 추가
    conversation_summary = Column(Text, nullable=True)  # 전체 대화 요약
    learning_context = Column(Text, nullable=True)  # 학습 맥락 정보 (JSON)
    last_summary_at = Column(DateTime, nullable=True)  # 마지막 요약 생성 시간
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 설정
    user = relationship("UserModel", back_populates="conversation_sessions")
    # questions = relationship("QuestionModel", back_populates="conversation_session")  # 제거 예정
    summaries = relationship("SessionSummary", back_populates="conversation_session")
    messages = relationship("SessionMessage", back_populates="conversation_session")

class SessionSummary(Base):
    """세션별 요약 모델"""
    __tablename__ = "session_summaries"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("conversation_sessions.id"), nullable=False)
    summary_content = Column(Text, nullable=False)  # 요약 내용
    request_id = Column(String, nullable=True)  # 요약을 생성한 요청 ID
    summary_type = Column(String, default="conversation")  # 요약 유형 (conversation, clarification 등)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 설정
    conversation_session = relationship("ConversationSession", back_populates="summaries") 

class MAICEEvaluationModel(Base):
    """MAICE 자동 평가 결과를 저장하는 모델"""
    __tablename__ = "maice_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # 12개 세부 평가 점수 (0, 0.5, 1점)
    math_concept_accuracy = Column(Integer, nullable=False)      # 수학적 개념/원리의 정확성
    curriculum_hierarchy = Column(Integer, nullable=False)       # 교과과정 내 위계성 파악
    math_terminology = Column(Integer, nullable=False)          # 수학적 용어 사용의 적절성
    problem_solving_direction = Column(Integer, nullable=False) # 문제해결 방향의 구체성
    core_question_singularity = Column(Integer, nullable=False) # 핵심 질문의 단일성
    condition_completeness = Column(Integer, nullable=False)     # 조건 제시의 완결성
    sentence_structure_logic = Column(Integer, nullable=False)   # 문장 구조의 논리성
    question_intent_clarity = Column(Integer, nullable=False)   # 질문 의도의 명시성
    current_learning_stage = Column(Integer, nullable=False)    # 현재 학습 단계 설명
    prerequisite_learning = Column(Integer, nullable=False)     # 선수학습 내용 언급
    specific_difficulty = Column(Integer, nullable=False)       # 구체적 어려움 명시
    learning_goal = Column(Integer, nullable=False)             # 학습 목표 제시
    
    # 카테고리별 점수
    math_expertise_score = Column(Integer, nullable=False)      # 수학적 전문성 (5점 만점)
    question_structure_score = Column(Integer, nullable=False)   # 질문 구조화 (5점 만점)
    learning_context_score = Column(Integer, nullable=False)     # 학습 맥락 적용 (5점 만점)
    total_score = Column(Integer, nullable=False)               # 총점 (15점 만점)
    
    # 평가 결과
    is_excellent = Column(sa.Boolean, default=False)           # 우수한 질문 여부
    is_math_related = Column(sa.Boolean, default=True)         # 수학 관련성
    feedback_text = Column(Text, nullable=True)                # 피드백 텍스트
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 설정
    question = relationship("QuestionModel", back_populates="maice_evaluations")
    user = relationship("UserModel", back_populates="maice_evaluations")

class StudentLearningStatus(Base):
    """학생의 학습 상태를 추적하는 모델"""
    __tablename__ = "student_learning_status"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("conversation_sessions.id"), nullable=False)
    
    # 학습 진행 상황
    conversation_count = Column(Integer, default=1)  # 총 대화 수
    current_learning_stage = Column(String, nullable=True)  # 현재 학습 단계
    learning_progress = Column(String, nullable=True)  # 학습 진행도
    
    # 학생 상태 분석
    question_type = Column(String, nullable=True)  # 질문 유형 (방법론, 원리, 개념 등)
    understanding_level = Column(String, nullable=True)  # 이해 수준 (초급, 중급, 고급)
    difficulty_areas = Column(Text, nullable=True)  # 어려워하는 부분들
    
    # 학습 요약
    conversation_summary = Column(Text, nullable=True)  # 대화 요약
    learning_insights = Column(Text, nullable=True)  # 학습 인사이트
    next_steps = Column(Text, nullable=True)  # 다음 학습 단계
    
    # 메타데이터
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 설정
    user = relationship("UserModel")
    session = relationship("ConversationSession")
    
    def update_status(self, 
                     question_type: str = None,
                     understanding_level: str = None,
                     difficulty_areas: str = None,
                     conversation_summary: str = None,
                     learning_insights: str = None,
                     next_steps: str = None):
        """학습 상태를 업데이트합니다."""
        if question_type:
            self.question_type = question_type
        if understanding_level:
            self.understanding_level = understanding_level
        if difficulty_areas:
            self.difficulty_areas = difficulty_areas
        if conversation_summary:
            self.conversation_summary = conversation_summary
        if learning_insights:
            self.learning_insights = learning_insights
        if next_steps:
            self.next_steps = next_steps
        
        self.updated_at = datetime.utcnow()

# A/B 테스트 관련 모델들
class AbTestSession(Base):
    """A/B 테스트 세션 모델 - 사용자별 테스트 세션 추적"""
    __tablename__ = "ab_test_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_mode = Column(Enum(UserModeType), nullable=False)
    session_started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    session_ended_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # 세션 통계
    total_messages = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)
    total_responses = Column(Integer, default=0)
    
    # 사용자 만족도 (세션 종료 시 수집)
    overall_satisfaction = Column(Integer, nullable=True)  # 1-5 점수
    response_quality = Column(Integer, nullable=True)      # 1-5 점수
    response_speed = Column(Integer, nullable=True)        # 1-5 점수
    learning_effectiveness = Column(Integer, nullable=True) # 1-5 점수
    
    # 추가 피드백
    positive_feedback = Column(Text, nullable=True)
    negative_feedback = Column(Text, nullable=True)
    suggestions = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 설정
    user = relationship("UserModel")
    interactions = relationship("AbTestInteraction", back_populates="session")

class AbTestInteraction(Base):
    """A/B 테스트 상호작용 모델 - 개별 질문-답변 상호작용 추적"""
    __tablename__ = "ab_test_interactions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("ab_test_sessions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    conversation_session_id = Column(Integer, ForeignKey("conversation_sessions.id"), nullable=True)
    
    # 상호작용 기본 정보
    question_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=True)
    question_type = Column(String(50), nullable=True)  # 수학 개념, 문제 해결, 기타 등
    
    # 시간 측정
    response_time_seconds = Column(Float, nullable=True)  # 응답 시간 (초)
    question_asked_at = Column(DateTime, default=datetime.utcnow)
    response_received_at = Column(DateTime, nullable=True)
    
    # 품질 평가 (자동/수동)
    question_complexity = Column(Integer, nullable=True)  # 1-5 점수 (자동 평가)
    response_accuracy = Column(Integer, nullable=True)    # 1-5 점수 (자동 평가)
    response_clarity = Column(Integer, nullable=True)     # 1-5 점수 (자동 평가)
    
    # 사용자 평가 (선택적)
    user_rating = Column(Integer, nullable=True)  # 1-5 점수
    user_feedback = Column(Text, nullable=True)
    
    # 메타데이터
    clarifications_needed = Column(Integer, default=0)  # 명료화 요청 횟수
    follow_up_questions = Column(Integer, default=0)    # 후속 질문 횟수
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 설정
    session = relationship("AbTestSession", back_populates="interactions")
    user = relationship("UserModel")
    conversation_session = relationship("ConversationSession")

class AbTestSurvey(Base):
    """A/B 테스트 설문조사 모델 - 전체 테스트 종료 후 수집"""
    __tablename__ = "ab_test_surveys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("ab_test_sessions.id"), nullable=False)
    
    # 기본 만족도 (1-5 점수)
    overall_experience = Column(Integer, nullable=False)
    ease_of_use = Column(Integer, nullable=False)
    response_quality = Column(Integer, nullable=False)
    response_speed = Column(Integer, nullable=False)
    learning_effectiveness = Column(Integer, nullable=False)
    
    # 비교 평가 (다른 모드와 비교했을 때)
    preferred_mode = Column(Enum(UserModeType), nullable=True)  # 선호하는 모드
    mode_comparison_rating = Column(Integer, nullable=True)     # 모드 비교 평가 (1-5)
    
    # 구체적 평가
    best_features = Column(Text, nullable=True)      # 가장 좋았던 기능
    worst_features = Column(Text, nullable=True)     # 가장 아쉬웠던 기능
    improvement_suggestions = Column(Text, nullable=True)  # 개선 제안
    
    # 사용 의도
    would_recommend = Column(Integer, nullable=True)  # 추천 의향 (1-5)
    would_use_again = Column(Integer, nullable=True)  # 재사용 의향 (1-5)
    
    # 추가 의견
    additional_comments = Column(Text, nullable=True)
    
    # 설문 완료 정보
    survey_completed_at = Column(DateTime, default=datetime.utcnow)
    survey_duration_minutes = Column(Float, nullable=True)  # 설문 완료 시간 (분)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 설정
    user = relationship("UserModel")
    session = relationship("AbTestSession")


class ConversationEvaluation(Base):
    """대화 세션 평가 모델 - LLM을 통한 자동 평가"""
    __tablename__ = "conversation_evaluations"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_session_id = Column(Integer, ForeignKey("conversation_sessions.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    evaluated_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # 평가 실행한 교사
    
    # 질문 평가(각 0~5) - 세부 점수 및 합계(0~15)
    question_professionalism_score = Column(Float, nullable=True)
    question_structuring_score = Column(Float, nullable=True)
    question_context_application_score = Column(Float, nullable=True)
    question_total_score = Column(Float, nullable=True)
    question_level_feedback = Column(Text, nullable=True)

    # 답변 평가(각 0~5) - 세부 점수 및 합계(0~15)
    answer_customization_score = Column(Float, nullable=True)
    answer_systematicity_score = Column(Float, nullable=True)
    answer_expandability_score = Column(Float, nullable=True)
    response_total_score = Column(Float, nullable=True)
    response_appropriateness_feedback = Column(Text, nullable=True)
    
    # 맥락 평가(v4.3 추가) - C1, C2 각 5점, 총 10점
    context_dialogue_coherence_score = Column(Float, nullable=True)  # C1: 대화 일관성
    context_learning_support_score = Column(Float, nullable=True)    # C2: 학습 과정 지원성
    context_total_score = Column(Float, nullable=True)  # C영역 총점 (10점)
    
    # v4.3 체크리스트 데이터 (32개 요소 + evidence)
    # JSON 구조: {"A1": {"concept_accuracy": {"value": 1, "evidence": "귀납법 용어 정확"}, ...}, ...}
    checklist_data = Column(postgresql.JSONB, nullable=True)
    
    # 교사 의견 (v4.5 추가)
    # JSON 구조: {"A1": "의견...", "A2": "의견...", ...}
    item_feedbacks = Column(postgresql.JSONB, nullable=True, comment='각 항목별 교사 의견')
    rubric_overall_feedback = Column(Text, nullable=True, comment='루브릭 총평')
    educational_llm_suggestions = Column(Text, nullable=True, comment='LLM 교육적 활용을 위한 제안')
    
    # 종합 평가 (레거시)
    overall_assessment = Column(Text, nullable=True)
    overall_score = Column(Float, nullable=True)  # v4.3: 전체 합계(0~40)
    
    # 평가 메타데이터
    evaluation_status = Column(String(50), default="pending")  # pending, completed, failed
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 관계 설정
    conversation_session = relationship("ConversationSession")
    student = relationship("UserModel", foreign_keys=[student_id])
    evaluator = relationship("UserModel", foreign_keys=[evaluated_by])
    
    def __repr__(self):
        return f"<ConversationEvaluation(id={self.id}, session_id={self.conversation_session_id}, overall_score={self.overall_score})>"