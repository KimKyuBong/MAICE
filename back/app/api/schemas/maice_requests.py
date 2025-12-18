"""
MAICE API 요청/응답 모델
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from app.utils.timezone import utc_to_kst


class BaseRequest(BaseModel):
    """기본 요청 모델"""
    session_id: Optional[int] = Field(None, description="세션 ID")
    request_id: Optional[str] = Field(None, description="요청 ID")
    timestamp: Optional[str] = Field(None, description="타임스탬프")


class ChatRequest(BaseRequest):
    """채팅 요청 모델"""
    message: str = Field(..., description="메시지 내용", min_length=1, max_length=4000)
    message_type: str = Field("question", description="메시지 타입")
    use_agents: Optional[bool] = Field(None, description="에이전트 사용 여부 (Deprecated: 백엔드에서 사용자별로 자동 할당)")
    conversation_history: Optional[List[Dict[str, Any]]] = Field(None, description="대화 히스토리")
    
    class Config:
        json_encoders = {
            datetime: lambda v: utc_to_kst(v) if v else None
        }


class ClarificationRequest(BaseRequest):
    """명료화 답변 요청 모델"""
    clarification_answer: str = Field(..., description="명료화 답변", min_length=1, max_length=2000)
    question_index: int = Field(..., ge=1, description="질문 인덱스")
    total_questions: int = Field(..., ge=1, description="총 질문 수")


class SessionRequest(BaseModel):
    """세션 생성 요청 모델"""
    initial_question: Optional[str] = Field(None, description="초기 질문", max_length=2000)


class StreamChunkRequest(BaseModel):
    """스트리밍 청크 요청 모델"""
    chunk_id: str = Field(..., description="청크 ID")
    chunk_index: int = Field(..., description="청크 인덱스", ge=0)
    total_chunks: Optional[int] = Field(None, description="전체 청크 수")
    stream_type: str = Field(..., description="스트림 타입")
    
    class Config:
        json_encoders = {
            datetime: lambda v: utc_to_kst(v) if v else None
        }
