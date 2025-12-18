"""
Admin API endpoints.
All endpoints return JSON responses for frontend consumption.
"""

from fastapi import APIRouter, HTTPException, Depends, Request, status, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, exists
from datetime import datetime, timedelta
import logging
import redis.asyncio as redis
import os
from app.utils.timezone import get_current_kst, format_datetime_for_frontend

from app.models.models import UserModel, QuestionModel, SurveyResponseModel, TeacherEvaluationModel, UserRole, ConversationSession, SessionMessage, ConversationEvaluation
from app.schemas.schemas import User
from app.core.db.session import get_db
from app.core.auth.dependencies import get_current_admin
from app.services.evaluation_service import EvaluationService
from pydantic import BaseModel
from typing import List, Optional

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_redis_client():
    """Redis 클라이언트 생성"""
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
    client = await redis.from_url(redis_url, decode_responses=True)
    try:
        yield client
    finally:
        await client.close()


async def get_stats(current_user: UserModel, db: AsyncSession):
    """관리자 대시보드 통계 데이터 조회"""
    try:
        # 총 질문 수
        total_questions = await db.scalar(
            select(func.count()).select_from(QuestionModel)
        )
        
        # 활동 학생 수 (질문을 한 학생)
        active_students = await db.scalar(
            select(func.count(func.distinct(QuestionModel.user_id)))
            .select_from(QuestionModel)
        )
        
        # 평균 만족도 점수
        avg_total = await db.scalar(
            select(func.avg(
                (SurveyResponseModel.relevance_score + 
                 SurveyResponseModel.guidance_score + 
                 SurveyResponseModel.clarity_score) / 3
            ))
            .select_from(SurveyResponseModel)
        )
        
        # 총 설문 응답 수
        total_evaluated = await db.scalar(
            select(func.count()).select_from(SurveyResponseModel)
        )
        
        return {
            "total_questions": total_questions or 0,
            "active_students": active_students or 0,
            "avg_total": round(avg_total or 0, 2),
            "total_evaluated": total_evaluated or 0
        }
        
    except Exception as e:
        logger.error(f"통계 데이터 조회 중 오류: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="통계 데이터 조회 중 오류가 발생했습니다."
        )


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """관리자 대시보드 통계 API"""
    try:
        stats = await get_stats(current_user, db)
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"대시보드 통계 조회 중 오류: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="대시보드 통계 조회 중 오류가 발생했습니다."
        )


@router.get("/system-status")
async def get_system_status(
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """시스템 전체 상태 조회 API"""
    try:
        # 전체 사용자 수
        total_users = await db.scalar(
            select(func.count()).select_from(UserModel)
        )
        
        # 오늘 생성된 질문 수
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        questions_today = await db.scalar(
            select(func.count()).select_from(QuestionModel)
            .where(QuestionModel.created_at >= today)
        )
        
        # 활성 세션 수 (최근 1시간 이내 업데이트된 세션)
        one_hour_ago = datetime.now() - timedelta(hours=1)
        active_sessions = await db.scalar(
            select(func.count()).select_from(ConversationSession)
            .where(ConversationSession.updated_at >= one_hour_ago)
        )
        
        # 에이전트 상태 확인 (Redis Streams 활동 기반)
        agent_status = "running"
        avg_response_time = 0
        success_rate = 100
        agent_details = []
        
        try:
            # Redis Streams 존재 여부로 에이전트 활동 확인
            backend_to_agent_stream = await redis_client.exists("maice:backend_to_agent_stream")
            agent_to_backend_stream = await redis_client.exists("maice:agent_to_backend_stream")
            
            if backend_to_agent_stream and agent_to_backend_stream:
                agent_status = "running"
                
                # 메인 스트림 길이 확인 (처리된 메시지 수)
                main_stream_len = await redis_client.xlen("maice:agent_to_backend_stream")
                
                # 최근 세션 스트림 확인으로 각 에이전트 활동 추정
                session_streams = await redis_client.keys("maice:agent_to_backend_stream_session_*")
                
                # 각 에이전트별 처리량 조회 (Redis 메트릭 기반)
                agent_names = [
                    "QuestionClassifierAgent",
                    "QuestionImprovementAgent", 
                    "AnswerGeneratorAgent",
                    "ObserverAgent",
                    "FreeTalkerAgent"
                ]
                
                for agent_name in agent_names:
                    try:
                        # Redis 메트릭에서 실제 처리량 조회
                        requests_key = f"maice:metrics:{agent_name}:counter:requests_total"
                        requests = await redis_client.get(requests_key)
                        processed_count = int(float(requests)) if requests else 0
                        
                        # 에러 수도 함께 조회
                        errors_key = f"maice:metrics:{agent_name}:counter:errors_total"
                        errors = await redis_client.get(errors_key)
                        error_count = int(float(errors)) if errors else 0
                        
                        # 활성 세션 수 조회
                        sessions_key = f"maice:metrics:{agent_name}:gauge:active_sessions"
                        sessions = await redis_client.get(sessions_key)
                        active_count = int(float(sessions)) if sessions else 0
                        
                        agent_details.append({
                            "name": agent_name,
                            "status": "running" if processed_count > 0 else "idle",
                            "processed_messages": processed_count,
                            "pending_messages": active_count,
                            "errors": error_count
                        })
                    except Exception as e:
                        logger.debug(f"에이전트 {agent_name} 메트릭 조회 실패: {e}")
                        # 메트릭이 없으면 0으로 설정
                        agent_details.append({
                            "name": agent_name,
                            "status": "idle",
                            "processed_messages": 0,
                            "pending_messages": 0,
                            "errors": 0
                        })
                
                if session_streams:
                    # 최근 세션이 있으면 에이전트가 활발히 동작 중
                    avg_response_time = 150  # ms (예상값)
                else:
                    # 스트림은 있지만 최근 세션이 없음 - 대기 중
                    avg_response_time = 0
            else:
                agent_status = "stopped"
                
        except Exception as e:
            logger.warning(f"Redis 에이전트 상태 조회 실패: {e}")
            agent_status = "unknown"
        
        # 최근 활동 로그 (최근 10개 메시지 - SessionMessage 기반)
        recent_query = (
            select(SessionMessage, UserModel, ConversationSession)
            .join(ConversationSession, SessionMessage.conversation_session_id == ConversationSession.id)
            .join(UserModel, ConversationSession.user_id == UserModel.id)
            .where(SessionMessage.sender == 'user')  # 사용자 메시지만
            .order_by(SessionMessage.created_at.desc())
            .limit(10)
        )
        result = await db.execute(recent_query)
        messages = result.all()
        
        recent_activities = [
            {
                "time": format_datetime_for_frontend(msg[0].created_at),
                "user": msg[1].google_name or msg[1].username,
                "action": f"{msg[2].title or '제목 없음'} - {msg[0].message_type}",
                "status": "완료"
            }
            for msg in messages
        ]
        
        result = {
            "total_users": total_users or 0,
            "active_sessions": active_sessions or 0,
            "questions_today": questions_today or 0,
            "agent_status": agent_status,
            "avg_response_time": avg_response_time,
            "success_rate": success_rate,
            "agents": agent_details,
            "recent_activities": recent_activities,
            "timestamp": get_current_kst().isoformat()
        }
        
        logger.info(f"📊 시스템 상태 조회 결과: users={total_users}, sessions={active_sessions}, questions_today={questions_today}, agent_status={agent_status}, agents_count={len(agent_details)}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"시스템 상태 조회 중 오류: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="시스템 상태 조회 중 오류가 발생했습니다."
        )


@router.get("/questions/recent")
async def get_recent_questions(
    limit: int = 5,
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """최근 질문 목록 조회 API"""
    try:
        query = (
            select(QuestionModel, UserModel)
            .join(UserModel, QuestionModel.user_id == UserModel.id)
            .order_by(QuestionModel.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(query)
        questions = result.all()
        
        recent_questions = [
            {
                "id": q[0].id,
                "student_id": q[1].username,
                "question": q[0].content,
                "created_at": q[0].created_at.isoformat(),
                "has_survey": q[0].survey_responses is not None
            }
            for q in questions
        ]
        
        return {"questions": recent_questions}
        
    except Exception as e:
        logger.error(f"최근 질문 조회 중 오류: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="최근 질문 조회 중 오류가 발생했습니다."
        )


@router.get("/students")
async def get_students(
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    role: Optional[UserRole] = None  # 역할 필터 추가
):
    """사용자 목록 조회 API (모든 역할 또는 특정 역할 필터링)"""
    try:
        # 역할 필터가 있으면 해당 역할만 조회, 없으면 모든 사용자 조회
        query = select(UserModel)
        if role:
            query = query.where(UserModel.role == role)
        
        query = query.order_by(UserModel.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        users = result.scalars().all()
        
        # 각 사용자의 세션 수 조회
        user_list = []
        for user in users:
            session_count = await db.scalar(
                select(func.count()).select_from(ConversationSession)
                .where(ConversationSession.user_id == user.id)
            )
            
            last_session = await db.scalar(
                select(ConversationSession)
                .where(ConversationSession.user_id == user.id)
                .order_by(ConversationSession.updated_at.desc())
                .limit(1)
            )
            
            user_list.append({
                "id": user.id,
                "username": user.username,
                "role": user.role.value if user.role else None,
                "google_name": user.google_name,
                "google_email": user.google_email,
                "created_at": user.created_at.isoformat(),
                "session_count": session_count or 0,
                "last_session_at": last_session.updated_at.isoformat() if last_session else None
            })
        
        # 전체 사용자 수 조회
        count_query = select(func.count()).select_from(UserModel)
        if role:
            count_query = count_query.where(UserModel.role == role)
        
        total_count = await db.scalar(count_query)
        
        return {
            "students": user_list,
            "total": total_count,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"사용자 목록 조회 중 오류: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 목록 조회 중 오류가 발생했습니다."
        )


@router.get("/students/{user_id}/sessions")
async def get_student_sessions(
    user_id: int,
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """특정 학생의 세션 목록 조회 API"""
    try:
        # 학생 정보 확인
        student = await db.get(UserModel, user_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="학생을 찾을 수 없습니다."
            )
        
        # 학생의 세션 목록 조회
        query = (
            select(ConversationSession)
            .where(ConversationSession.user_id == user_id)
            .order_by(ConversationSession.updated_at.desc())
        )
        result = await db.execute(query)
        sessions = result.scalars().all()
        
        # 각 세션의 메시지 수 및 평가 여부 조회
        session_list = []
        for session in sessions:
            message_count = await db.scalar(
                select(func.count()).select_from(SessionMessage)
                .where(SessionMessage.conversation_session_id == session.id)
            )
            eval_count = await db.scalar(
                select(func.count()).select_from(ConversationEvaluation)
                .where(ConversationEvaluation.conversation_session_id == session.id)
                .where(ConversationEvaluation.evaluation_status == 'completed')
            )
            last_eval = await db.scalar(
                select(ConversationEvaluation)
                .where(ConversationEvaluation.conversation_session_id == session.id)
                .where(ConversationEvaluation.evaluation_status == 'completed')
                .order_by(ConversationEvaluation.created_at.desc())
                .limit(1)
            )
            # 평가 진행중 여부 확인 (pending 상태)
            pending_eval = await db.scalar(
                select(ConversationEvaluation)
                .where(ConversationEvaluation.conversation_session_id == session.id)
                .where(ConversationEvaluation.evaluation_status == 'pending')
                .order_by(ConversationEvaluation.created_at.desc())
                .limit(1)
            )
            
            session_list.append({
                "id": session.id,
                "title": session.title or "제목 없음",
                "is_active": session.is_active,
                "current_stage": session.current_stage,
                "message_count": message_count or 0,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "has_evaluation": bool(eval_count),
                "last_evaluation_at": last_eval.created_at.isoformat() if last_eval else None,
                "evaluation_in_progress": bool(pending_eval)
            })
        
        return {
            "student": {
                "id": student.id,
                "username": student.username,
                "google_name": student.google_name,
                "google_email": student.google_email
            },
            "sessions": session_list,
            "total": len(session_list)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"학생 세션 조회 중 오류: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="학생 세션 조회 중 오류가 발생했습니다."
        )


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: int,
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """특정 세션의 메시지 목록 조회 API"""
    try:
        # 세션 정보 확인
        session = await db.get(ConversationSession, session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="세션을 찾을 수 없습니다."
            )
        
        # 사용자 정보 확인
        student = await db.get(UserModel, session.user_id)
        
        # 메시지 목록 조회
        query = (
            select(SessionMessage)
            .where(SessionMessage.conversation_session_id == session_id)
            .order_by(SessionMessage.created_at.asc())
        )
        result = await db.execute(query)
        messages = result.scalars().all()
        
        message_list = []
        for msg in messages:
            message_list.append({
                "id": msg.id,
                "sender": msg.sender,
                "content": msg.content,
                "message_type": msg.message_type,
                "parent_message_id": msg.parent_message_id,
                "created_at": msg.created_at.isoformat()
            })
        
        return {
            "session": {
                "id": session.id,
                "title": session.title,
                "is_active": session.is_active,
                "current_stage": session.current_stage,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat()
            },
            "student": {
                "id": student.id if student else None,
                "username": student.username if student else None,
                "google_name": student.google_name if student else None
            },
            "messages": message_list,
            "total": len(message_list)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"세션 메시지 조회 중 오류: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="세션 메시지 조회 중 오류가 발생했습니다."
        )


# Pydantic 스키마
class BatchEvaluationRequest(BaseModel):
    session_ids: List[int]


# 평가 API 엔드포인트
@router.post("/evaluate-session/{session_id}")
async def evaluate_session(
    session_id: int,
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """특정 세션에 대한 평가 실행"""
    try:
        # 세션 존재 확인
        session = await db.get(ConversationSession, session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="세션을 찾을 수 없습니다."
            )
        
        # 평가 서비스 실행
        evaluation_service = EvaluationService(db)
        evaluation = await evaluation_service.evaluate_session(session_id, current_user.id)
        
        # 평가 결과 반환
        return {
            "success": True,
            "evaluation_id": evaluation.id,
            "overall_score": evaluation.overall_score,
            # 신규 3+3 점수 체계 요약
            "question_total_score": evaluation.question_total_score,
            "answer_total_score": evaluation.response_total_score,
            # 하위 호환을 위해 기존 키는 제외 또는 null 처리(프론트는 목록 API 사용 권장)
            "overall_assessment": evaluation.overall_assessment
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"세션 평가 중 오류: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"세션 평가 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/evaluate-sessions/batch")
async def batch_evaluate_sessions(
    request: BatchEvaluationRequest,
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """여러 세션에 대한 일괄 평가 실행"""
    try:
        logger.info(
            f"📥 일괄 평가 요청 수신: user_id={current_user.id}, sessions={len(request.session_ids)}"
        )
        evaluation_service = EvaluationService(db)
        results = await evaluation_service.batch_evaluate_sessions(
            request.session_ids,
            current_user.id
        )
        
        # 성공/실패 통계
        successful = [r for r in results if r is not None]
        failed = [i for i, r in enumerate(results) if r is None]
        
        return {
            "success": True,
            "total": len(request.session_ids),
            "successful": len(successful),
            "failed": len(failed),
            "results": [
                {
                    "session_id": session_id,
                    "success": result is not None,
                    "evaluation_id": result.id if result else None,
                    "overall_score": result.overall_score if result else None
                }
                for session_id, result in zip(request.session_ids, results)
            ]
        }
        
    except Exception as e:
        logger.error(f"일괄 평가 중 오류: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"일괄 평가 중 오류가 발생했습니다: {str(e)}"
        )


class EvaluateAllRequest(BaseModel):
    only_unevaluated: Optional[bool] = True


async def _execute_batch_evaluation(
    session_ids: List[int],
    evaluated_by: int
):
    """백그라운드에서 실행되는 일괄 평가 함수"""
    from app.core.db.session import async_session
    
    db = async_session()
    try:
        evaluation_service = EvaluationService(db)
        await evaluation_service.batch_evaluate_sessions(session_ids, evaluated_by)
        logger.info(f"✅ 백그라운드 일괄 평가 완료: {len(session_ids)}개 세션")
    except Exception as e:
        logger.error(f"❌ 백그라운드 일괄 평가 중 오류: {str(e)}", exc_info=True)
    finally:
        await db.close()


@router.post("/evaluate-sessions/all")
async def evaluate_all_sessions(
    request: EvaluateAllRequest,
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """모든 학생의 모든 세션 일괄 평가 (백그라운드 실행, 기본: 미평가 세션만)"""
    try:
        logger.info(
            f"📥 전체 일괄 평가 요청 수신: user_id={current_user.id}, only_unevaluated={request.only_unevaluated}"
        )
        
        # 전체 세션 수 확인 (디버깅용)
        total_sessions_count = await db.scalar(
            select(func.count()).select_from(ConversationSession)
        )
        logger.info(f"📊 전체 세션 수: {total_sessions_count}개")
        
        # 모든 세션 ID 조회 (student 역할 사용자의 세션만)
        session_ids_query = (
            select(ConversationSession.id)
            .join(UserModel, ConversationSession.user_id == UserModel.id)
            .where(UserModel.role == UserRole.STUDENT)
        )
        if request.only_unevaluated:
            # completed 평가가 없는 세션만 (NOT EXISTS 사용)
            completed_eval_exists = (
                select(1)
                .where(
                    and_(
                        ConversationEvaluation.conversation_session_id == ConversationSession.id,
                        ConversationEvaluation.evaluation_status == 'completed'
                    )
                )
            )
            session_ids_query = session_ids_query.where(~exists(completed_eval_exists))

        result = await db.execute(session_ids_query)
        session_ids = [row[0] for row in result.all()]
        
        logger.info(f"🔍 평가 대상 세션 조회 결과: total={len(session_ids)}개")

        if not session_ids:
            logger.warning(f"⚠️ 평가할 세션이 없습니다. only_unevaluated={request.only_unevaluated}")
            return {
                "success": True,
                "message": "평가할 세션이 없습니다.",
                "total": 0,
                "successful": 0,
                "failed": 0,
                "status": "completed"
            }
        
        logger.info(f"📊 백그라운드 평가 시작: {len(session_ids)}개 세션")
        
        # 백그라운드 작업으로 실행
        background_tasks.add_task(_execute_batch_evaluation, session_ids, current_user.id)

        return {
            "success": True,
            "message": f"평가가 백그라운드에서 시작되었습니다. 총 {len(session_ids)}개 세션이 처리됩니다.",
            "total": len(session_ids),
            "status": "processing"
        }

    except Exception as e:
        logger.error(f"전체 일괄 평가 중 오류: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"전체 일괄 평가 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/sessions/{session_id}/evaluations")
async def get_session_evaluations(
    session_id: int,
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """특정 세션의 평가 결과 조회"""
    try:
        evaluation_service = EvaluationService(db)
        evaluations = await evaluation_service.get_session_evaluations(session_id)
        
        evaluation_list = []
        for eval in evaluations:
            # 평가자 정보 조회
            evaluator = await db.get(UserModel, eval.evaluated_by)
            
            evaluation_list.append({
                "id": eval.id,
                "session_id": eval.conversation_session_id,
                "student_id": eval.student_id,
                "evaluator": {
                    "id": evaluator.id if evaluator else None,
                    "username": evaluator.username if evaluator else None
                },
                # 질문 세부 점수
                "question_professionalism_score": eval.question_professionalism_score,
                "question_structuring_score": eval.question_structuring_score,
                "question_context_application_score": eval.question_context_application_score,
                "question_total_score": eval.question_total_score,
                "question_level_feedback": eval.question_level_feedback,
                # 답변 세부 점수
                "answer_customization_score": eval.answer_customization_score,
                "answer_systematicity_score": eval.answer_systematicity_score,
                "answer_expandability_score": eval.answer_expandability_score,
                "answer_total_score": eval.response_total_score,
                "response_appropriateness_feedback": eval.response_appropriateness_feedback,
                "overall_score": eval.overall_score,
                "overall_assessment": eval.overall_assessment,
                "evaluation_status": eval.evaluation_status,
                "created_at": eval.created_at.isoformat(),
                "updated_at": eval.updated_at.isoformat()
            })
        
        return {
            "session_id": session_id,
            "evaluations": evaluation_list,
            "total": len(evaluation_list)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"평가 결과 조회 중 오류: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="평가 결과 조회 중 오류가 발생했습니다."
        )