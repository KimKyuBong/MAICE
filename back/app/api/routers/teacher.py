"""
교사용 API 엔드포인트.
- 교사가 학생 세션을 조회하고 평가할 수 있는 기능 제공
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, String
from typing import List, Optional, Any, Dict
from datetime import datetime, date
import logging

from app.models.models import (
    UserModel, 
    ConversationSession, 
    SessionMessage, 
    ConversationEvaluation,
    UserRole
)
from app.core.db.session import get_db
from app.core.auth.dependencies import get_current_teacher
from pydantic import BaseModel, Field, validator
from typing import Dict

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# 요청/응답 스키마
# ============================================================================

class ChecklistElement(BaseModel):
    """체크리스트 요소"""
    value: int = Field(..., ge=0, le=1, description="0=미충족, 1=충족")
    evidence: str = Field("", max_length=50, description="근거 (10자 내외 권장)")


class ChecklistItem(BaseModel):
    """항목별 체크리스트 (4개 요소)"""
    element1: ChecklistElement
    element2: ChecklistElement
    element3: ChecklistElement
    element4: ChecklistElement


class ManualEvaluationRequest(BaseModel):
    """수동 평가 생성/업데이트 요청 (v4.5 교사 의견 포함)"""
    session_id: int
    
    # A 영역: 질문 평가 (15점)
    A1: Optional[ChecklistItem] = Field(None, description="A1. 수학적 전문성 체크리스트")
    A2: Optional[ChecklistItem] = Field(None, description="A2. 질문 구조화 체크리스트")
    A3: Optional[ChecklistItem] = Field(None, description="A3. 학습 맥락 적용 체크리스트")
    
    # B 영역: 답변 평가 (15점)
    B1: Optional[ChecklistItem] = Field(None, description="B1. 학습자 맞춤도 체크리스트")
    B2: Optional[ChecklistItem] = Field(None, description="B2. 설명의 체계성 체크리스트")
    B3: Optional[ChecklistItem] = Field(None, description="B3. 학습 내용 확장성 체크리스트")
    
    # C 영역: 맥락 평가 (10점)
    C1: Optional[ChecklistItem] = Field(None, description="C1. 대화 일관성 체크리스트")
    C2: Optional[ChecklistItem] = Field(None, description="C2. 학습 과정 지원성 체크리스트")
    
    # 교사 의견 (v4.5 추가)
    item_feedbacks: Optional[Dict[str, Any]] = Field(None, description="각 항목별 교사 의견 (객체 또는 문자열)")
    rubric_overall_feedback: Optional[str] = Field(None, description="루브릭 총평")
    educational_llm_suggestions: Optional[str] = Field(None, description="LLM 교육적 활용을 위한 제안")


# 기존 호환성을 위한 레거시 스키마 (v4.0)
class LegacyManualEvaluationRequest(BaseModel):
    """레거시 수동 평가 요청 (v4.0 - 하위 호환성)"""
    session_id: int
    # 질문 평가 (각 0~5점)
    question_professionalism_score: Optional[int] = Field(None, ge=0, le=5, description="수학적 전문성 점수")
    question_structuring_score: Optional[int] = Field(None, ge=0, le=5, description="질문 구조화 점수")
    question_context_application_score: Optional[int] = Field(None, ge=0, le=5, description="학습 맥락 적용 점수")
    question_feedback: Optional[str] = Field(None, description="질문 평가 피드백")
    
    # 답변 평가 (각 0~5점)
    answer_customization_score: Optional[int] = Field(None, ge=0, le=5, description="학습자 맞춤도 점수")
    answer_systematicity_score: Optional[int] = Field(None, ge=0, le=5, description="설명의 체계성 점수")
    answer_expandability_score: Optional[int] = Field(None, ge=0, le=5, description="학습 내용 확장성 점수")
    answer_feedback: Optional[str] = Field(None, description="답변 평가 피드백")
    
    # 맥락 평가 (v4.3 추가)
    context_dialogue_coherence_score: Optional[int] = Field(None, ge=0, le=5, description="대화 일관성 점수")
    context_learning_support_score: Optional[int] = Field(None, ge=0, le=5, description="학습 과정 지원성 점수")
    context_feedback: Optional[str] = Field(None, description="맥락 평가 피드백")
    
    # 종합 평가
    overall_assessment: Optional[str] = Field(None, description="종합 평가")


class SessionListItem(BaseModel):
    """세션 목록 항목"""
    id: int
    title: Optional[str]
    student_id: int
    student_username: str
    message_count: int
    is_active: bool
    created_at: str
    updated_at: str
    has_manual_evaluation: bool
    last_evaluation_at: Optional[str]
    
    class Config:
        from_attributes = True


class MessageItem(BaseModel):
    """메시지 항목"""
    id: int
    sender: str
    content: str
    message_type: Optional[str]
    created_at: str
    
    class Config:
        from_attributes = True


class SessionDetailResponse(BaseModel):
    """세션 상세 응답"""
    id: int
    title: Optional[str]
    student_id: int
    student_username: Optional[str]  # username이 없을 수 있음
    is_active: bool
    created_at: str
    updated_at: str
    messages: List[MessageItem]
    current_evaluation: Optional[dict] = None
    
    class Config:
        from_attributes = True


# ============================================================================
# API 엔드포인트
# ============================================================================

@router.get("/sessions", response_model=dict)
async def get_all_sessions(
    current_user: UserModel = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
    student_id: Optional[int] = None,
    has_evaluation: Optional[bool] = None
):
    """
    모든 학생의 세션 목록 조회 (교사용)
    
    - 학생별 필터링 가능
    - 평가 여부 필터링 가능
    """
    try:
        # has_evaluation 필터가 true면 평가된 세션만 조회
        if has_evaluation:
            # 현재 교사가 평가 완료한 세션만 조회
            query = (
                select(
                    ConversationSession,
                    UserModel.username
                )
                .join(UserModel, ConversationSession.user_id == UserModel.id)
                .join(
                    ConversationEvaluation,
                    ConversationEvaluation.conversation_session_id == ConversationSession.id
                )
                .where(
                    or_(
                        UserModel.role == UserRole.STUDENT,
                        UserModel.role.is_(None)
                    )
                )
                .where(ConversationEvaluation.evaluated_by == current_user.id)
                .where(ConversationEvaluation.evaluation_status == 'completed')
                .distinct()  # 중복 제거 (한 세션에 여러 평가가 있을 수 있음)
            )
        else:
            # 기본 쿼리: 학생 세션 (STUDENT 역할 또는 역할 미지정 사용자)
            query = (
                select(
                    ConversationSession,
                    UserModel.username
                )
                .join(UserModel, ConversationSession.user_id == UserModel.id)
                .where(
                    or_(
                        UserModel.role == UserRole.STUDENT,
                        UserModel.role.is_(None)
                    )
                )
            )
        
        # 필터링
        if student_id:
            query = query.where(ConversationSession.user_id == student_id)
        
        # 정렬 및 페이징
        query = query.order_by(ConversationSession.updated_at.desc())
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        rows = result.all()
        
        # 세션 목록 생성
        session_list = []
        for session, username in rows:
            # 메시지 수 조회
            message_count = await db.scalar(
                select(func.count(SessionMessage.id))
                .where(SessionMessage.conversation_session_id == session.id)
            )
            
            # 수동 평가 여부 확인 (evaluation_status가 'completed'이고 해당 교사가 평가한 경우)
            manual_eval = await db.scalar(
                select(ConversationEvaluation)
                .where(ConversationEvaluation.conversation_session_id == session.id)
                .where(ConversationEvaluation.evaluated_by == current_user.id)
                .where(ConversationEvaluation.evaluation_status == 'completed')
                .order_by(ConversationEvaluation.created_at.desc())
                .limit(1)
            )
            
            session_list.append({
                "id": session.id,
                "title": session.title or "제목 없음",
                "student_id": session.user_id,
                "student_username": username,
                "message_count": message_count or 0,
                "is_active": session.is_active,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "has_manual_evaluation": bool(manual_eval),
                "last_evaluation_at": manual_eval.updated_at.isoformat() if manual_eval else None
            })
        
        # 전체 개수 조회
        if has_evaluation:
            # 평가된 세션만 카운트
            total_query = (
                select(func.count(func.distinct(ConversationSession.id)))
                .join(UserModel, ConversationSession.user_id == UserModel.id)
                .join(
                    ConversationEvaluation,
                    ConversationEvaluation.conversation_session_id == ConversationSession.id
                )
                .where(
                    or_(
                        UserModel.role == UserRole.STUDENT,
                        UserModel.role.is_(None)
                    )
                )
                .where(ConversationEvaluation.evaluated_by == current_user.id)
                .where(ConversationEvaluation.evaluation_status == 'completed')
            )
        else:
            # 전체 세션 카운트
            total_query = (
                select(func.count(ConversationSession.id))
                .join(UserModel, ConversationSession.user_id == UserModel.id)
                .where(
                    or_(
                        UserModel.role == UserRole.STUDENT,
                        UserModel.role.is_(None)
                    )
                )
            )
        
        if student_id:
            total_query = total_query.where(ConversationSession.user_id == student_id)
        
        total_count = await db.scalar(total_query)
        
        return {
            "sessions": session_list,
            "total_count": total_count,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"❌ 세션 목록 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"세션 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/sessions/random", response_model=SessionDetailResponse)
async def get_random_unevaluated_session(
    current_user: UserModel = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db)
):
    """
    미평가 세션 중 랜덤하게 하나 가져오기
    
    - 현재 교사가 평가하지 않은 세션만 대상
    - agent와 freepass 세션을 균등하게 배분
    - 없으면 404 에러
    """
    try:
        # 채점 대상 세션 ID 목록 (총 100개)
        TARGET_SESSION_IDS = [
            38, 40, 41, 44, 46, 47, 48, 50, 51, 53, 60, 66, 72, 74, 75, 78, 83, 91, 92, 95,
            97, 98, 100, 111, 112, 116, 123, 125, 128, 130, 133, 139, 142, 143, 147, 150, 
            155, 157, 159, 160, 172, 179, 196, 199, 203, 206, 213, 223, 227, 228, 234, 235, 
            237, 238, 239, 240, 246, 248, 252, 253, 254, 257, 264, 276, 281, 283, 284, 285, 
            292, 293, 296, 300, 301, 302, 303, 306, 310, 311, 315, 317, 321, 324, 326, 337, 
            338, 339, 341, 349, 350, 352, 355, 357, 359, 364, 365, 367, 369, 371, 374, 380
        ]
        
        logger.info(f"🎯 채점 대상 세션: {len(TARGET_SESSION_IDS)}개 (ID 목록 필터 활성화)")
        
        # 채점 기준일: 2025년 10월 20일
        cutoff_date = datetime(2025, 10, 20)
        
        # 미평가 세션 조회 (현재 교사가 평가하지 않은 세션 - 목록 내에서만)
        subquery = (
            select(ConversationEvaluation.conversation_session_id)
            .where(ConversationEvaluation.evaluated_by == current_user.id)
            .where(ConversationEvaluation.evaluation_status == 'completed')
            .where(ConversationEvaluation.conversation_session_id.in_(TARGET_SESSION_IDS))
        )
        
        # 현재 교사가 채점한 agent/freepass 세션 개수 확인 (목록 내에서만)
        agent_count_query = (
            select(func.count(ConversationEvaluation.id))
            .join(ConversationSession, ConversationEvaluation.conversation_session_id == ConversationSession.id)
            .join(UserModel, ConversationSession.user_id == UserModel.id)
            .where(ConversationEvaluation.evaluated_by == current_user.id)
            .where(ConversationEvaluation.evaluation_status == 'completed')
            .where(UserModel.assigned_mode == 'agent')
            .where(ConversationEvaluation.conversation_session_id.in_(TARGET_SESSION_IDS))
        )
        
        freepass_count_query = (
            select(func.count(ConversationEvaluation.id))
            .join(ConversationSession, ConversationEvaluation.conversation_session_id == ConversationSession.id)
            .join(UserModel, ConversationSession.user_id == UserModel.id)
            .where(ConversationEvaluation.evaluated_by == current_user.id)
            .where(ConversationEvaluation.evaluation_status == 'completed')
            .where(UserModel.assigned_mode == 'freepass')
            .where(ConversationEvaluation.conversation_session_id.in_(TARGET_SESSION_IDS))
        )
        
        agent_count_result = await db.execute(agent_count_query)
        freepass_count_result = await db.execute(freepass_count_query)
        
        agent_count = agent_count_result.scalar() or 0
        freepass_count = freepass_count_result.scalar() or 0
        
        logger.info(f"📊 채점 현황 - agent: {agent_count}개, freepass: {freepass_count}개")
        
        # 부족한 쪽을 우선 선택 (동률이면 None으로 랜덤 선택)
        preferred_mode = None
        if agent_count < freepass_count:
            preferred_mode = 'agent'
            logger.info(f"🎯 agent 세션 우선 선택 (현재 차이: {freepass_count - agent_count})")
        elif freepass_count < agent_count:
            preferred_mode = 'freepass'
            logger.info(f"🎯 freepass 세션 우선 선택 (현재 차이: {agent_count - freepass_count})")
        else:
            logger.info(f"⚖️ agent와 freepass 동률, 랜덤 선택")
        
        # 최소 2개 메시지가 있는 세션
        message_count_subquery = (
            select(
                SessionMessage.conversation_session_id,
                func.count(SessionMessage.id).label('message_count')
            )
            .group_by(SessionMessage.conversation_session_id)
            .having(func.count(SessionMessage.id) >= 2)
            .subquery()
        )
        
        # user와 maice 메시지가 모두 있는 세션
        user_message_subquery = (
            select(SessionMessage.conversation_session_id)
            .where(SessionMessage.sender == 'user')
            .group_by(SessionMessage.conversation_session_id)
            .subquery()
        )
        
        maice_message_subquery = (
            select(SessionMessage.conversation_session_id)
            .where(SessionMessage.sender == 'maice')
            .group_by(SessionMessage.conversation_session_id)
            .subquery()
        )
        
        # 기본 쿼리 구성
        query = (
            select(ConversationSession)
            .join(UserModel, ConversationSession.user_id == UserModel.id)
            .join(message_count_subquery, ConversationSession.id == message_count_subquery.c.conversation_session_id)
            .join(user_message_subquery, ConversationSession.id == user_message_subquery.c.conversation_session_id)
            .join(maice_message_subquery, ConversationSession.id == maice_message_subquery.c.conversation_session_id)
            .where(
                or_(
                    UserModel.role == UserRole.STUDENT,
                    UserModel.role.is_(None),
                    UserModel.role == UserRole.ADMIN  # 테스트용
                )
            )
            .where(ConversationSession.created_at >= cutoff_date)
            .where(ConversationSession.id.notin_(subquery))
            .where(ConversationSession.id.in_(TARGET_SESSION_IDS))  # 특정 세션 ID만 채점 대상
        )
        
        # 우선 모드가 있으면 해당 모드의 세션 먼저 시도
        if preferred_mode:
            preferred_query = query.where(UserModel.assigned_mode == preferred_mode).order_by(func.random()).limit(1)
            result = await db.execute(preferred_query)
            session = result.scalar_one_or_none()
            
            if session:
                logger.info(f"✅ {preferred_mode} 세션 선택됨 (ID: {session.id})")
            else:
                # 우선 모드 세션이 없으면 반대 모드에서 선택
                other_mode = 'freepass' if preferred_mode == 'agent' else 'agent'
                logger.info(f"⚠️ {preferred_mode} 세션 없음, {other_mode} 세션에서 선택")
                other_query = query.where(UserModel.assigned_mode == other_mode).order_by(func.random()).limit(1)
                result = await db.execute(other_query)
                session = result.scalar_one_or_none()
                
                if session:
                    logger.info(f"✅ {other_mode} 세션 선택됨 (ID: {session.id})")
        else:
            # 동률이면 랜덤 선택
            random_query = query.order_by(func.random()).limit(1)
            result = await db.execute(random_query)
            session = result.scalar_one_or_none()
            
            if session:
                student = await db.get(UserModel, session.user_id)
                mode = student.assigned_mode if student else "알 수 없음"
                logger.info(f"✅ {mode} 세션 랜덤 선택됨 (ID: {session.id})")
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="평가할 세션이 없습니다. 모든 세션을 평가했습니다!"
            )
        
        # 학생 정보 조회
        student = await db.get(UserModel, session.user_id)
        student_username = student.username if student else "알 수 없음"
        
        # 메시지 조회
        messages_query = (
            select(SessionMessage)
            .where(SessionMessage.conversation_session_id == session.id)
            .order_by(SessionMessage.created_at.asc())
        )
        messages_result = await db.execute(messages_query)
        messages = messages_result.scalars().all()
        
        return SessionDetailResponse(
            id=session.id,
            title=session.title,
            student_id=session.user_id,
            student_username=student_username,
            is_active=session.is_active,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
            messages=[
                MessageItem(
                    id=msg.id,
                    sender=msg.sender,
                    content=msg.content,
                    message_type=msg.message_type,
                    created_at=msg.created_at.isoformat()
                )
                for msg in messages
            ],
            current_evaluation=None  # 항상 새로 평가
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 랜덤 세션 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"랜덤 세션 조회 중 오류가 발생했습니다: {str(e)}"
        )



@router.get("/sessions/by-item-score", response_model=dict)
async def get_sessions_by_item_score(
    item: str = Query(..., description="항목 코드 (A1~C2)"),
    min_score: int = Query(1, ge=1, le=5, description="최소 점수"),
    max_score: int = Query(5, ge=1, le=5, description="최대 점수"),
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
    limit: int = Query(100, ge=1, le=200, description="가져올 개수"),
    current_user: UserModel = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db)
):
    """
    특정 항목의 점수 범위로 세션 필터링
    - item: A1~C2 항목 코드
    - min_score, max_score: 점수 범위 (1~5)
    """
    try:
        # 항목별 점수 컬럼 매핑
        score_column_map = {
            'A1': ConversationEvaluation.question_professionalism_score,
            'A2': ConversationEvaluation.question_structuring_score,
            'A3': ConversationEvaluation.question_context_application_score,
            'B1': ConversationEvaluation.answer_customization_score,
            'B2': ConversationEvaluation.answer_systematicity_score,
            'B3': ConversationEvaluation.answer_expandability_score,
            'C1': ConversationEvaluation.context_dialogue_coherence_score,
            'C2': ConversationEvaluation.context_learning_support_score,
        }
        
        if item not in score_column_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"유효하지 않은 항목: {item}. A1~A3, B1~B3, C1~C2 중 선택하세요."
            )
        
        score_column = score_column_map[item]
        
        # 평가된 세션 중 해당 항목 점수가 범위 내인 세션 조회 (테스트: 모든 필터 제거)
        query = (
            select(ConversationSession, ConversationEvaluation, UserModel)
            .join(ConversationEvaluation, ConversationSession.id == ConversationEvaluation.conversation_session_id)
            .join(UserModel, ConversationSession.user_id == UserModel.id)
            .where(score_column >= min_score)
            .where(score_column <= max_score)
            .order_by(score_column.desc(), ConversationSession.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        
        result = await db.execute(query)
        rows = result.all()
        
        # 총 개수 조회
        count_query = (
            select(func.count(ConversationSession.id))
            .join(ConversationEvaluation, ConversationSession.id == ConversationEvaluation.conversation_session_id)
            .where(score_column >= min_score)
            .where(score_column <= max_score)
        )
        count_result = await db.execute(count_query)
        total_count = count_result.scalar_one()
        
        sessions_data = []
        for session, evaluation, user in rows:
            # 해당 항목의 실제 점수 추출
            item_score = getattr(evaluation, score_column_map[item].key)
            
            sessions_data.append({
                "id": session.id,
                "title": session.title,
                "student_id": user.id,
                "student_username": user.username if user else "알 수 없음",
                "created_at": session.created_at.isoformat(),
                "item_score": item_score,
                "overall_score": evaluation.overall_score,
                "evaluated_by": evaluation.evaluated_by,
                "evaluated_at": evaluation.updated_at.isoformat() if evaluation.updated_at else None,
                "has_item_feedback": bool(evaluation.item_feedbacks and evaluation.item_feedbacks.get(item))
            })
        
        return {
            "sessions": sessions_data,
            "total_count": total_count,
            "skip": skip,
            "limit": limit,
            "item": item,
            "min_score": min_score,
            "max_score": max_score
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 항목별 세션 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"항목별 세션 조회 중 오류가 발생했습니다: {str(e)}"
        )



@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(
    session_id: int,
    current_user: UserModel = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db)
):
    """세션 상세 정보 조회 (대화 내용 포함)"""
    try:
        # 세션 조회
        session = await db.get(ConversationSession, session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="세션을 찾을 수 없습니다."
            )
        
        # 학생 정보 조회
        student = await db.get(UserModel, session.user_id)
        student_username = student.username if student else "알 수 없음"
        
        # 메시지 조회
        messages_query = (
            select(SessionMessage)
            .where(SessionMessage.conversation_session_id == session_id)
            .order_by(SessionMessage.created_at.asc())
        )
        messages_result = await db.execute(messages_query)
        messages = messages_result.scalars().all()
        
        # 현재 평가 조회 (해당 교사가 평가한 것)
        current_eval = await db.scalar(
            select(ConversationEvaluation)
            .where(ConversationEvaluation.conversation_session_id == session_id)
            .where(ConversationEvaluation.evaluated_by == current_user.id)
            .where(ConversationEvaluation.evaluation_status == 'completed')
            .order_by(ConversationEvaluation.created_at.desc())
            .limit(1)
        )
        
        # 평가 정보 포맷팅
        eval_data = None
        if current_eval:
            eval_data = {
                "id": current_eval.id,
                "question_professionalism_score": current_eval.question_professionalism_score,
                "question_structuring_score": current_eval.question_structuring_score,
                "question_context_application_score": current_eval.question_context_application_score,
                "question_total_score": current_eval.question_total_score,
                "answer_customization_score": current_eval.answer_customization_score,
                "answer_systematicity_score": current_eval.answer_systematicity_score,
                "answer_expandability_score": current_eval.answer_expandability_score,
                "answer_total_score": current_eval.response_total_score,
                "context_dialogue_coherence_score": current_eval.context_dialogue_coherence_score,
                "context_learning_support_score": current_eval.context_learning_support_score,
                "context_total_score": current_eval.context_total_score,
                "checklist_data": current_eval.checklist_data,  # v4.3 체크리스트 데이터
                "item_feedbacks": current_eval.item_feedbacks,  # v4.5 항목별 의견
                "rubric_overall_feedback": current_eval.rubric_overall_feedback,  # v4.5 루브릭 총평
                "educational_llm_suggestions": current_eval.educational_llm_suggestions,  # v4.5 LLM 제안
                "overall_score": current_eval.overall_score,
                "created_at": current_eval.created_at.isoformat(),
                "updated_at": current_eval.updated_at.isoformat()
            }
        
        return SessionDetailResponse(
            id=session.id,
            title=session.title,
            student_id=session.user_id,
            student_username=student_username,
            is_active=session.is_active,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
            messages=[
                MessageItem(
                    id=msg.id,
                    sender=msg.sender,
                    content=msg.content,
                    message_type=msg.message_type,
                    created_at=msg.created_at.isoformat()
                )
                for msg in messages
            ],
            current_evaluation=eval_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 세션 상세 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"세션 상세 조회 중 오류가 발생했습니다: {str(e)}"
        )


def calculate_item_score(item: Optional[ChecklistItem]) -> tuple[int, int]:
    """체크리스트 항목의 점수 계산: (충족 개수, 점수)"""
    if not item:
        return 0, 1  # 기본값: 0개 충족 = 1점
    
    checked_count = sum([
        item.element1.value,
        item.element2.value,
        item.element3.value,
        item.element4.value
    ])
    score = checked_count + 1  # 0개=1점, 1개=2점, ..., 4개=5점
    return checked_count, score


def build_checklist_data(request: ManualEvaluationRequest) -> Dict:
    """체크리스트 데이터를 JSON 구조로 변환"""
    checklist = {}
    
    # 각 항목별로 4개 요소를 저장
    element_names = {
        "A1": ["concept_accuracy", "curriculum_hierarchy", "terminology_appropriateness", "problem_direction_specificity"],
        "A2": ["question_singularity", "condition_completeness", "sentence_logic", "intent_clarity"],
        "A3": ["current_stage_description", "prior_learning_mention", "difficulty_specification", "learning_goal_presentation"],
        "B1": ["level_based_approach", "prior_knowledge_connection", "difficulty_adjustment", "personalized_feedback"],
        "B2": ["concept_hierarchy", "stepwise_logic", "key_emphasis", "example_appropriateness"],
        "B3": ["advanced_direction", "application_connection", "misconception_correction", "self_directed_induction"],
        "C1": ["goal_centered_consistency", "context_reference", "topic_continuity", "previous_turn_connection"],
        "C2": ["thinking_process_induction", "understanding_check", "metacognitive_promotion", "deep_thinking_guidance"]
    }
    
    for item_key in ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2"]:
        item = getattr(request, item_key, None)
        if item:
            checklist[item_key] = {}
            elements = [item.element1, item.element2, item.element3, item.element4]
            for i, element_name in enumerate(element_names[item_key]):
                checklist[item_key][element_name] = {
                    "value": elements[i].value,
                    "evidence": elements[i].evidence
                }
    
    return checklist


@router.post("/evaluations/manual", response_model=dict)
@router.put("/evaluations/manual", response_model=dict)
async def create_or_update_manual_evaluation(
    request: ManualEvaluationRequest,
    current_user: UserModel = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db)
):
    """
    수동 평가 생성 또는 업데이트 (v4.3 체크리스트 방식)
    
    - 기존 평가가 있으면 업데이트, 없으면 새로 생성
    - 8개 항목 x 4개 요소 = 32개 체크리스트
    - 각 항목 점수 = 충족 요소 개수 + 1 (0개=1점, 4개=5점)
    - 총점 = 40점 (A영역 15점 + B영역 15점 + C영역 10점)
    """
    try:
        # 세션 존재 확인
        session = await db.get(ConversationSession, request.session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="세션을 찾을 수 없습니다."
            )
        
        # 기존 평가 조회
        existing_eval = await db.scalar(
            select(ConversationEvaluation)
            .where(ConversationEvaluation.conversation_session_id == request.session_id)
            .where(ConversationEvaluation.evaluated_by == current_user.id)
            .order_by(ConversationEvaluation.created_at.desc())
            .limit(1)
        )
        
        # 체크리스트 데이터 구축
        checklist_data = build_checklist_data(request)
        
        # 점수 계산 (v4.3 방식)
        _, a1_score = calculate_item_score(request.A1)
        _, a2_score = calculate_item_score(request.A2)
        _, a3_score = calculate_item_score(request.A3)
        question_total = a1_score + a2_score + a3_score  # 15점 만점
        
        _, b1_score = calculate_item_score(request.B1)
        _, b2_score = calculate_item_score(request.B2)
        _, b3_score = calculate_item_score(request.B3)
        answer_total = b1_score + b2_score + b3_score  # 15점 만점
        
        _, c1_score = calculate_item_score(request.C1)
        _, c2_score = calculate_item_score(request.C2)
        context_total = c1_score + c2_score  # 10점 만점
        
        overall_score = question_total + answer_total + context_total  # 40점 만점
        
        if existing_eval:
            # 업데이트
            existing_eval.question_professionalism_score = a1_score
            existing_eval.question_structuring_score = a2_score
            existing_eval.question_context_application_score = a3_score
            existing_eval.question_total_score = question_total
            
            existing_eval.answer_customization_score = b1_score
            existing_eval.answer_systematicity_score = b2_score
            existing_eval.answer_expandability_score = b3_score
            existing_eval.response_total_score = answer_total
            
            existing_eval.context_dialogue_coherence_score = c1_score
            existing_eval.context_learning_support_score = c2_score
            existing_eval.context_total_score = context_total
            
            existing_eval.checklist_data = checklist_data
            existing_eval.item_feedbacks = request.item_feedbacks
            existing_eval.rubric_overall_feedback = request.rubric_overall_feedback
            existing_eval.educational_llm_suggestions = request.educational_llm_suggestions
            existing_eval.overall_score = overall_score
            existing_eval.evaluation_status = "completed"
            existing_eval.updated_at = datetime.utcnow()
            
            evaluation = existing_eval
            is_new = False
        else:
            # 신규 생성
            evaluation = ConversationEvaluation(
                conversation_session_id=request.session_id,
                student_id=session.user_id,
                evaluated_by=current_user.id,
                question_professionalism_score=a1_score,
                question_structuring_score=a2_score,
                question_context_application_score=a3_score,
                question_total_score=question_total,
                answer_customization_score=b1_score,
                answer_systematicity_score=b2_score,
                answer_expandability_score=b3_score,
                response_total_score=answer_total,
                context_dialogue_coherence_score=c1_score,
                context_learning_support_score=c2_score,
                context_total_score=context_total,
                checklist_data=checklist_data,
                item_feedbacks=request.item_feedbacks,
                rubric_overall_feedback=request.rubric_overall_feedback,
                educational_llm_suggestions=request.educational_llm_suggestions,
                overall_score=overall_score,
                evaluation_status="completed"
            )
            db.add(evaluation)
            is_new = True
        
        await db.commit()
        await db.refresh(evaluation)
        
        logger.info(f"✅ 수동 평가 {'생성' if is_new else '업데이트'} 완료: 세션 {request.session_id}, 교사 {current_user.id}, 총점 {overall_score}/40")
        
        return {
            "success": True,
            "message": f"평가가 {'생성' if is_new else '업데이트'}되었습니다.",
            "evaluation": {
                "id": evaluation.id,
                "session_id": evaluation.conversation_session_id,
                "question_total_score": evaluation.question_total_score,
                "answer_total_score": evaluation.response_total_score,
                "context_total_score": evaluation.context_total_score,
                "overall_score": evaluation.overall_score
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ 수동 평가 저장 실패: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"평가 저장 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/evaluation/teacher-stats", response_model=dict)
async def get_teacher_evaluation_stats(
    current_user: UserModel = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db)
):
    """
    교사별 평가 통계 조회 (관리자용)
    - 각 교사의 평가 현황
    - 교사별 평가 완료 세션 수
    """
    try:
        # 채점 대상 세션 ID 목록 (총 100개)
        TARGET_SESSION_IDS = [
            38, 40, 41, 44, 46, 47, 48, 50, 51, 53, 60, 66, 72, 74, 75, 78, 83, 91, 92, 95,
            97, 98, 100, 111, 112, 116, 123, 125, 128, 130, 133, 139, 142, 143, 147, 150, 
            155, 157, 159, 160, 172, 179, 196, 199, 203, 206, 213, 223, 227, 228, 234, 235, 
            237, 238, 239, 240, 246, 248, 252, 253, 254, 257, 264, 276, 281, 283, 284, 285, 
            292, 293, 296, 300, 301, 302, 303, 306, 310, 311, 315, 317, 321, 324, 326, 337, 
            338, 339, 341, 349, 350, 352, 355, 357, 359, 364, 365, 367, 369, 371, 374, 380
        ]
        
        # 관리자 권한 확인
        if current_user.role != UserRole.ADMIN:
            # 자기 자신의 통계만 조회 (목록 내에서만)
            teacher_stats_query = (
                select(
                    ConversationEvaluation.evaluated_by,
                    func.count(func.distinct(ConversationEvaluation.conversation_session_id)).label('evaluated_count')
                )
                .where(ConversationEvaluation.evaluation_status == 'completed')
                .where(ConversationEvaluation.evaluated_by == current_user.id)
                .where(ConversationEvaluation.conversation_session_id.in_(TARGET_SESSION_IDS))
                .group_by(ConversationEvaluation.evaluated_by)
            )
        else:
            # 전체 교사 통계 (목록 내에서만)
            teacher_stats_query = (
                select(
                    ConversationEvaluation.evaluated_by,
                    func.count(func.distinct(ConversationEvaluation.conversation_session_id)).label('evaluated_count')
                )
                .where(ConversationEvaluation.evaluation_status == 'completed')
                .where(ConversationEvaluation.conversation_session_id.in_(TARGET_SESSION_IDS))
                .group_by(ConversationEvaluation.evaluated_by)
            )
        
        result = await db.execute(teacher_stats_query)
        teacher_data = result.all()
        
        # 교사 정보 및 agent/freepass 통계 가져오기 (관리자만 agent/freepass 구분 정보 제공)
        teacher_stats = []
        for teacher_id, count in teacher_data:
            teacher = await db.get(UserModel, teacher_id)
            if teacher:
                stat_item = {
                    "teacher_id": teacher_id,
                    "teacher_username": teacher.username,
                    "evaluated_count": count,
                    "progress_percent": round(count / 100 * 100, 1)  # 100개 기준
                }
                
                # 관리자만 agent/freepass 구분 정보 제공 (블라인드 테스트 유지)
                if current_user.role == UserRole.ADMIN:
                    # 해당 교사의 agent/freepass 채점 개수 (목록 내에서만)
                    agent_count_query = (
                        select(func.count(ConversationEvaluation.id))
                        .join(ConversationSession, ConversationEvaluation.conversation_session_id == ConversationSession.id)
                        .join(UserModel, ConversationSession.user_id == UserModel.id)
                        .where(ConversationEvaluation.evaluated_by == teacher_id)
                        .where(ConversationEvaluation.evaluation_status == 'completed')
                        .where(UserModel.assigned_mode == 'agent')
                        .where(ConversationEvaluation.conversation_session_id.in_(TARGET_SESSION_IDS))
                    )
                    
                    freepass_count_query = (
                        select(func.count(ConversationEvaluation.id))
                        .join(ConversationSession, ConversationEvaluation.conversation_session_id == ConversationSession.id)
                        .join(UserModel, ConversationSession.user_id == UserModel.id)
                        .where(ConversationEvaluation.evaluated_by == teacher_id)
                        .where(ConversationEvaluation.evaluation_status == 'completed')
                        .where(UserModel.assigned_mode == 'freepass')
                        .where(ConversationEvaluation.conversation_session_id.in_(TARGET_SESSION_IDS))
                    )
                    
                    agent_count_result = await db.execute(agent_count_query)
                    freepass_count_result = await db.execute(freepass_count_query)
                    
                    agent_count = agent_count_result.scalar() or 0
                    freepass_count = freepass_count_result.scalar() or 0
                    
                    stat_item["agent_count"] = agent_count
                    stat_item["freepass_count"] = freepass_count
                    stat_item["balance_diff"] = abs(agent_count - freepass_count)
                
                teacher_stats.append(stat_item)
        
        # 채점 기준일: 2025년 10월 20일
        cutoff_date = datetime(2025, 10, 20)
        
        # 최소 2개 메시지가 있는 세션 서브쿼리
        message_count_subquery = (
            select(
                SessionMessage.conversation_session_id,
                func.count(SessionMessage.id).label('message_count')
            )
            .group_by(SessionMessage.conversation_session_id)
            .having(func.count(SessionMessage.id) >= 2)
            .subquery()
        )
        
        # 전체 통계 (조건 충족하는 세션만)
        total_sessions_query = (
            select(func.count(ConversationSession.id))
            .join(UserModel, ConversationSession.user_id == UserModel.id)
            .join(message_count_subquery, ConversationSession.id == message_count_subquery.c.conversation_session_id)
            .where(
                or_(
                    UserModel.role == UserRole.STUDENT,
                    UserModel.role.is_(None)
                )
            )
            .where(ConversationSession.created_at >= cutoff_date)
        )
        total_sessions_result = await db.execute(total_sessions_query)
        total_sessions = total_sessions_result.scalar_one()
        
        # 현재 교사의 평가 완료 세션 수 (관리자는 전체 합계)
        if current_user.role == UserRole.ADMIN:
            # 관리자는 모든 교사의 평가 합산
            evaluated_sessions_query = (
                select(func.count(func.distinct(ConversationEvaluation.conversation_session_id)))
                .where(ConversationEvaluation.evaluation_status == 'completed')
            )
        else:
            # 일반 교사는 자신의 평가만
            evaluated_sessions_query = (
                select(func.count(func.distinct(ConversationEvaluation.conversation_session_id)))
                .where(ConversationEvaluation.evaluation_status == 'completed')
                .where(ConversationEvaluation.evaluated_by == current_user.id)
            )
        evaluated_sessions_result = await db.execute(evaluated_sessions_query)
        evaluated_sessions = evaluated_sessions_result.scalar_one()
        
        # 각 교사들의 달성률 평균 계산
        achievement_rate = 0
        if teacher_stats:
            total_progress = sum(stat['progress_percent'] for stat in teacher_stats)
            achievement_rate = round(total_progress / len(teacher_stats), 1)
        
        return {
            "teacher_stats": sorted(teacher_stats, key=lambda x: x['evaluated_count'], reverse=True),
            "total_sessions": total_sessions,
            "evaluated_sessions": evaluated_sessions,
            "target_goal": 100,  # 교사별 목표: 100개
            "achievement_rate": achievement_rate  # 각 교사들의 달성률 평균
        }
        
    except Exception as e:
        logger.error(f"❌ 교사별 평가 통계 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"교사별 평가 통계 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/evaluation/stats", response_model=dict)
async def get_evaluation_stats(
    current_user: UserModel = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db)
):
    """
    전체 평가 통계 조회
    - 전체 세션 수
    - 평가 완료 세션 수
    - 항목별 의견 작성 통계
    """
    try:
        # 채점 대상 세션 ID 목록 (총 100개)
        TARGET_SESSION_IDS = [
            38, 40, 41, 44, 46, 47, 48, 50, 51, 53, 60, 66, 72, 74, 75, 78, 83, 91, 92, 95,
            97, 98, 100, 111, 112, 116, 123, 125, 128, 130, 133, 139, 142, 143, 147, 150, 
            155, 157, 159, 160, 172, 179, 196, 199, 203, 206, 213, 223, 227, 228, 234, 235, 
            237, 238, 239, 240, 246, 248, 252, 253, 254, 257, 264, 276, 281, 283, 284, 285, 
            292, 293, 296, 300, 301, 302, 303, 306, 310, 311, 315, 317, 321, 324, 326, 337, 
            338, 339, 341, 349, 350, 352, 355, 357, 359, 364, 365, 367, 369, 371, 374, 380
        ]
        
        # 채점 기준일: 2025년 10월 20일
        cutoff_date = datetime(2025, 10, 20)
        
        # 최소 2개 메시지가 있는 세션 서브쿼리
        message_count_subquery = (
            select(
                SessionMessage.conversation_session_id,
                func.count(SessionMessage.id).label('message_count')
            )
            .group_by(SessionMessage.conversation_session_id)
            .having(func.count(SessionMessage.id) >= 2)
            .subquery()
        )
        
        # 전체 학생 세션 수 (목록 내에서만)
        total_sessions_query = (
            select(func.count(ConversationSession.id))
            .join(UserModel, ConversationSession.user_id == UserModel.id)
            .join(message_count_subquery, ConversationSession.id == message_count_subquery.c.conversation_session_id)
            .where(
                or_(
                    UserModel.role == UserRole.STUDENT,
                    UserModel.role.is_(None)
                )
            )
            .where(ConversationSession.created_at >= cutoff_date)
            .where(ConversationSession.id.in_(TARGET_SESSION_IDS))
        )
        total_sessions_result = await db.execute(total_sessions_query)
        total_sessions = total_sessions_result.scalar_one()
        
        # 현재 교사의 평가 완료 세션 수 (목록 내에서만)
        evaluated_sessions_query = (
            select(func.count(func.distinct(ConversationEvaluation.conversation_session_id)))
            .where(ConversationEvaluation.evaluation_status == 'completed')
            .where(ConversationEvaluation.evaluated_by == current_user.id)
            .where(ConversationEvaluation.conversation_session_id.in_(TARGET_SESSION_IDS))
        )
        evaluated_sessions_result = await db.execute(evaluated_sessions_query)
        evaluated_sessions = evaluated_sessions_result.scalar_one()
        
        # 항목별 의견 작성 통계 (현재 교사의 평가만, 목록 내에서만)
        item_feedback_stats = {}
        for item in ['A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'C1', 'C2']:
            # JSONB에서 특정 키가 존재하고 비어있지 않은 경우 카운트
            count_query = (
                select(func.count(ConversationEvaluation.id))
                .where(ConversationEvaluation.evaluation_status == 'completed')
                .where(ConversationEvaluation.evaluated_by == current_user.id)
                .where(ConversationEvaluation.conversation_session_id.in_(TARGET_SESSION_IDS))
                .where(ConversationEvaluation.item_feedbacks.isnot(None))
                .where(
                    func.jsonb_typeof(
                        ConversationEvaluation.item_feedbacks[item]
                    ) == 'string'
                )
                .where(
                    func.length(
                        func.cast(ConversationEvaluation.item_feedbacks[item], String)
                    ) > 0
                )
            )
            count_result = await db.execute(count_query)
            item_feedback_stats[item] = count_result.scalar_one()
        
        # 루브릭 총평 작성 수 (현재 교사의 평가만, 목록 내에서만)
        overall_feedback_query = (
            select(func.count(ConversationEvaluation.id))
            .where(ConversationEvaluation.evaluation_status == 'completed')
            .where(ConversationEvaluation.evaluated_by == current_user.id)
            .where(ConversationEvaluation.conversation_session_id.in_(TARGET_SESSION_IDS))
            .where(ConversationEvaluation.rubric_overall_feedback.isnot(None))
            .where(func.length(ConversationEvaluation.rubric_overall_feedback) > 0)
        )
        overall_feedback_result = await db.execute(overall_feedback_query)
        overall_feedback_count = overall_feedback_result.scalar_one()
        
        # LLM 제안 작성 수 (현재 교사의 평가만, 목록 내에서만)
        llm_suggestions_query = (
            select(func.count(ConversationEvaluation.id))
            .where(ConversationEvaluation.evaluation_status == 'completed')
            .where(ConversationEvaluation.evaluated_by == current_user.id)
            .where(ConversationEvaluation.conversation_session_id.in_(TARGET_SESSION_IDS))
            .where(ConversationEvaluation.educational_llm_suggestions.isnot(None))
            .where(func.length(ConversationEvaluation.educational_llm_suggestions) > 0)
        )
        llm_suggestions_result = await db.execute(llm_suggestions_query)
        llm_suggestions_count = llm_suggestions_result.scalar_one()
        
        return {
            "total_sessions": total_sessions,
            "evaluated_sessions": evaluated_sessions,
            "unevaluated_sessions": total_sessions - evaluated_sessions,
            "evaluation_progress_percent": round(evaluated_sessions / total_sessions * 100, 1) if total_sessions > 0 else 0,
            "item_feedback_stats": item_feedback_stats,
            "overall_feedback_count": overall_feedback_count,
            "llm_suggestions_count": llm_suggestions_count,
            "target_goal": 100
        }
        
    except Exception as e:
        logger.error(f"❌ 평가 통계 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"평가 통계 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/rubric-feedbacks", response_model=dict)
async def get_rubric_feedbacks(
    current_user: UserModel = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db)
):
    """
    현재 교사의 루브릭 평가 의견 조회
    """
    try:
        await db.refresh(current_user)
        return {
            "rubric_feedbacks": current_user.rubric_feedbacks or {}
        }
    except Exception as e:
        logger.error(f"❌ 루브릭 의견 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"루브릭 의견 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.put("/rubric-feedbacks", response_model=dict)
async def update_rubric_feedbacks(
    feedbacks: Dict[str, Any],
    current_user: UserModel = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db)
):
    """
    현재 교사의 루브릭 평가 의견 저장/업데이트
    """
    try:
        current_user.rubric_feedbacks = feedbacks
        current_user.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(current_user)
        
        logger.info(f"✅ 루브릭 의견 저장 완료: 교사 {current_user.id}, 항목 수 {len(feedbacks)}")
        
        return {
            "success": True,
            "rubric_feedbacks": current_user.rubric_feedbacks
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ 루브릭 의견 저장 실패: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"루브릭 의견 저장 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/students", response_model=dict)
async def get_students_list(
    current_user: UserModel = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """학생 목록 조회 (교사용)"""
    try:
        query = (
            select(UserModel)
            .where(
                or_(
                    UserModel.role == UserRole.STUDENT,
                    UserModel.role.is_(None)
                )
            )
            .order_by(UserModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        
        result = await db.execute(query)
        students = result.scalars().all()
        
        # 각 학생의 세션 수 조회
        student_list = []
        for student in students:
            session_count = await db.scalar(
                select(func.count(ConversationSession.id))
                .where(ConversationSession.user_id == student.id)
            )
            
            student_list.append({
                "id": student.id,
                "username": student.username,
                "session_count": session_count or 0,
                "created_at": student.created_at.isoformat()
            })
        
        total_count = await db.scalar(
            select(func.count(UserModel.id))
            .where(
                or_(
                    UserModel.role == UserRole.STUDENT,
                    UserModel.role.is_(None)
                )
            )
        )
        
        return {
            "students": student_list,
            "total_count": total_count,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"❌ 학생 목록 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"학생 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )







