"""
MAICE 서비스 인터페이스 정의
의존성 주입을 위한 추상 클래스들을 포함합니다.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession


class ISessionService(ABC):
    """세션 관리 서비스 인터페이스"""
    
    @abstractmethod
    async def create_new_session(self, user_id: int, question: str) -> int:
        """새 세션을 생성합니다."""
        pass
    
    @abstractmethod
    async def get_session_state(self, session_id: int) -> Optional[Dict[str, Any]]:
        """세션 상태를 조회합니다."""
        pass
    
    @abstractmethod
    async def update_session_state(self, session_id: int, **kwargs) -> None:
        """세션 상태를 업데이트합니다."""
        pass
    
    @abstractmethod
    async def get_recent_messages(self, session_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """최근 메시지들을 조회합니다."""
        pass
    
    @abstractmethod
    async def get_session_by_id(self, session_id: int) -> Optional[Any]:
        """세션 ID로 세션을 조회합니다."""
        pass


class IAgentService(ABC):
    """AI 에이전트 서비스 인터페이스"""
    
    @abstractmethod
    async def initialize(self) -> None:
        """서비스를 초기화합니다."""
        pass
    
    @abstractmethod
    async def process_freepass_streaming(self, question: str, conversation_history: Optional[list] = None,
                                       user_id: Optional[int] = None, session_id: Optional[int] = None) -> AsyncGenerator[str, None]:
        """프리패스 모드 스트리밍 처리"""
        pass
    
    @abstractmethod
    async def process_with_streaming_parallel(self, question: str, session_id: int, 
                                            request_id: Optional[str], user_id: int, is_followup: bool = False) -> AsyncGenerator[str, None]:
        """에이전트 모드 병렬 스트리밍 처리"""
        pass
    
    @abstractmethod
    async def process_clarification_response_parallel(self, session_id: int, 
                                                    clarification_answer: str, 
                                                    request_id: str, user_id: int) -> AsyncGenerator[str, None]:
        """명료화 답변 병렬 처리"""
        pass


class IChatService(ABC):
    """채팅 서비스 인터페이스"""
    
    @abstractmethod
    async def initialize(self) -> None:
        """서비스를 초기화합니다."""
        pass
    
    @abstractmethod
    async def process_question_streaming(self, question: str, user_id: int, 
                                       session_id: Optional[int] = None,
                                       conversation_history: Optional[list] = None,
                                       message_type: str = "question") -> AsyncGenerator[str, None]:
        """스트리밍 방식으로 질문을 처리합니다."""
        pass
    
    @abstractmethod
    async def get_session_status(self, session_id: int) -> Dict[str, Any]:
        """세션 상태를 조회합니다."""
        pass
