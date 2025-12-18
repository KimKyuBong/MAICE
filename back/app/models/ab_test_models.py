"""
A/B 테스트 관련 모델들
사용자 모드 할당과 설문조사 데이터를 관리
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum
from datetime import datetime

Base = declarative_base()

class UserModeType(str, enum.Enum):
    """사용자 모드 타입"""
    AGENT = "agent"
    FREEPASS = "freepass"

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
