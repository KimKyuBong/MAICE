"""
MAICE 에이전트 공통 상수 정의
백엔드의 models.py와 동일하게 유지해야 함
"""

class ConversationStage:
    """대화 세션 상태 상수 - 백엔드와 동일하게 유지"""
    
    # 초기 상태
    INITIAL_QUESTION = "initial_question"
    
    # 진행 상태
    PROCESSING_QUESTION = "processing_question"
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


class MessageType:
    """메시지 타입 상수 - 백엔드와 동일하게 유지"""
    
    # 사용자 메시지 타입
    USER_QUESTION = "user_question"
    USER_CLARIFICATION_RESPONSE = "user_clarification_response"
    USER_FOLLOW_UP = "user_follow_up"
    
    # MAICE Agent 메시지 타입
    MAICE_CLARIFICATION_QUESTION = "maice_clarification_question"
    MAICE_ANSWER = "maice_answer"
    MAICE_FOLLOW_UP = "maice_follow_up"
    MAICE_PROCESSING = "maice_processing"
    
    # 레거시 호환성을 위한 별칭
    CLARIFICATION = "clarification"
    CLARIFICATION_RESPONSE = "clarification_response"
    CLARIFICATION_PROGRESS = "clarification_progress"
    SUMMARY_COMPLETE = "summary_complete"


class AgentMessageType:
    """에이전트 간 통신 메시지 타입"""
    
    # 질문 분류 관련
    QUESTION_CLASSIFICATION = "question_classification"
    CLASSIFICATION_RESULT = "classification_result"
    
    # 명료화 관련
    CLARIFICATION_START = "clarification_start"
    CLARIFICATION_PROGRESS = "clarification_progress"
    CLARIFICATION_QUESTION = "clarification_question"
    CLARIFICATION_RESPONSE = "clarification_response"
    CLARIFICATION_COMPLETE = "clarification_complete"
    
    # 답변 생성 관련
    ANSWER_GENERATION = "answer_generation"
    ANSWER_CHUNK = "answer_chunk"
    ANSWER_COMPLETE = "answer_complete"
    
    # 요약 관련
    SUMMARY_START = "summary_start"
    SUMMARY_COMPLETE = "summary_complete"


class KnowledgeType:
    """지식 분류 타입 상수"""
    
    K1 = "K1"  # 개념 설명
    K2 = "K2"  # 절차 설명
    K3 = "K3"  # 문제 해결
    K4 = "K4"  # 심화 학습


class AnswerabilityType:
    """답변 가능성 타입 상수"""
    
    ANSWERABLE = "answerable"
    NEEDS_CLARIFY = "needs_clarify"
    UNANSWERABLE = "unanswerable"