"""
모니터링 API 엔드포인트

에이전트 상태, 성능 메트릭, 시스템 헬스 체크 등
실시간 모니터링을 위한 API를 제공합니다.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import redis.asyncio as redis
import os
from app.utils.timezone import get_current_kst

from app.models.models import (
    UserModel, QuestionModel, ConversationSession, 
    SurveyResponseModel, MAICEEvaluationModel
)
from app.core.auth.dependencies import get_current_admin
from app.core.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


async def get_redis_client():
    """Redis 클라이언트 생성"""
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
    client = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
    try:
        yield client
    finally:
        await client.close()


@router.get("/agents/status")
async def get_agents_status(
    current_user: UserModel = Depends(get_current_admin),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    모든 에이전트 상태 조회
    
    Returns:
        - agent_name: 에이전트 이름
        - is_alive: 살아있는지 여부
        - last_update: 마지막 업데이트 시간
        - metrics_count: 메트릭 개수
    """
    try:
        # 에이전트 상태 키 조회
        agent_keys = await redis_client.keys("maice:agent_status:*")
        
        agents_status = []
        for key in agent_keys:
            agent_name = key.split(":")[-1]
            status = await redis_client.hgetall(key)
            
            if status:
                agents_status.append({
                    "agent_name": agent_name,
                    "is_alive": status.get("is_alive") == "true",
                    "last_update": float(status.get("last_update", 0)),
                    "metrics_count": int(status.get("metrics_count", 0))
                })
        
        return {
            "timestamp": get_current_kst().isoformat(),
            "agents": agents_status,
            "total_agents": len(agents_status),
            "active_agents": sum(1 for a in agents_status if a["is_alive"])
        }
        
    except Exception as e:
        logger.error(f"에이전트 상태 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="에이전트 상태 조회 중 오류가 발생했습니다."
        )


@router.get("/agents/{agent_name}/metrics")
async def get_agent_metrics(
    agent_name: str,
    current_user: UserModel = Depends(get_current_admin),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    특정 에이전트의 상세 메트릭 조회
    
    Args:
        agent_name: 에이전트 이름 (QuestionClassifierAgent, AnswerGeneratorAgent 등)
    """
    try:
        metrics = {
            "agent_name": agent_name,
            "timestamp": get_current_kst().isoformat(),
            "counters": {},
            "gauges": {},
            "histograms": {}
        }
        
        # 카운터 조회
        counter_keys = await redis_client.keys(f"maice:metrics:{agent_name}:counter:*")
        for key in counter_keys:
            metric_name = key.split(":")[-1]
            value = await redis_client.get(key)
            if value:
                metrics["counters"][metric_name] = float(value)
        
        # 게이지 조회
        gauge_keys = await redis_client.keys(f"maice:metrics:{agent_name}:gauge:*")
        for key in gauge_keys:
            metric_name = key.split(":")[-1]
            value = await redis_client.get(key)
            if value:
                metrics["gauges"][metric_name] = float(value)
        
        # 히스토그램 조회
        histogram_keys = await redis_client.keys(f"maice:metrics:{agent_name}:histogram:*")
        for key in histogram_keys:
            metric_name = key.split(":")[-1]
            stats = await redis_client.hgetall(key)
            if stats:
                metrics["histograms"][metric_name] = {
                    k: float(v) for k, v in stats.items()
                }
        
        return metrics
        
    except Exception as e:
        logger.error(f"에이전트 메트릭 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="에이전트 메트릭 조회 중 오류가 발생했습니다."
        )


@router.get("/metrics/summary")
async def get_metrics_summary(
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    전체 시스템 메트릭 요약
    
    Returns:
        - 총 요청 수
        - 평균 응답 시간
        - 에러율
        - 활성 세션 수
        - 에이전트별 통계
    """
    try:
        # 에이전트 목록 조회
        agent_keys = await redis_client.keys("maice:agent_status:*")
        agent_names = [key.split(":")[-1] for key in agent_keys]
        
        summary = {
            "timestamp": get_current_kst().isoformat(),
            "system": {
                "total_requests": 0,
                "total_errors": 0,
                "error_rate": 0.0,
                "avg_response_time": 0.0,
                "active_sessions": 0
            },
            "agents": []
        }
        
        total_requests = 0
        total_errors = 0
        response_times = []
        
        # 각 에이전트별 메트릭 수집
        for agent_name in agent_names:
            # 요청 수
            requests_key = f"maice:metrics:{agent_name}:counter:requests_total"
            requests = await redis_client.get(requests_key)
            agent_requests = float(requests) if requests else 0
            
            # 에러 수
            errors_key = f"maice:metrics:{agent_name}:counter:errors_total"
            errors = await redis_client.get(errors_key)
            agent_errors = float(errors) if errors else 0
            
            # 응답 시간
            duration_key = f"maice:metrics:{agent_name}:histogram:request_duration_seconds"
            duration_stats = await redis_client.hgetall(duration_key)
            agent_avg_time = float(duration_stats.get("avg", 0)) if duration_stats else 0
            
            # 활성 세션
            sessions_key = f"maice:metrics:{agent_name}:gauge:active_sessions"
            sessions = await redis_client.get(sessions_key)
            agent_sessions = float(sessions) if sessions else 0
            
            # 에이전트별 정보
            summary["agents"].append({
                "name": agent_name,
                "requests": agent_requests,
                "errors": agent_errors,
                "error_rate": (agent_errors / agent_requests * 100) if agent_requests > 0 else 0,
                "avg_response_time": agent_avg_time,
                "active_sessions": agent_sessions
            })
            
            # 전체 합산
            total_requests += agent_requests
            total_errors += agent_errors
            if agent_avg_time > 0:
                response_times.append(agent_avg_time)
        
        # 시스템 전체 통계
        summary["system"]["total_requests"] = total_requests
        summary["system"]["total_errors"] = total_errors
        summary["system"]["error_rate"] = (total_errors / total_requests * 100) if total_requests > 0 else 0
        summary["system"]["avg_response_time"] = sum(response_times) / len(response_times) if response_times else 0
        summary["system"]["active_sessions"] = sum(a["active_sessions"] for a in summary["agents"])
        
        # 데이터베이스 통계 추가
        total_questions = await db.scalar(select(func.count()).select_from(QuestionModel))
        active_sessions_db = await db.scalar(
            select(func.count()).select_from(ConversationSession).where(
                ConversationSession.is_active == True
            )
        )
        
        summary["database"] = {
            "total_questions": total_questions or 0,
            "active_sessions": active_sessions_db or 0
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"메트릭 요약 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="메트릭 요약 조회 중 오류가 발생했습니다."
        )


@router.get("/performance/timeline")
async def get_performance_timeline(
    hours: int = 24,
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    시간별 성능 추이 데이터
    
    Args:
        hours: 조회할 시간 범위 (기본 24시간)
    """
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # 시간별 질문 수 집계
        from sqlalchemy import extract
        
        questions_by_hour = await db.execute(
            select(
                extract('hour', QuestionModel.created_at).label('hour'),
                func.count(QuestionModel.id).label('count')
            )
            .where(QuestionModel.created_at >= cutoff_time)
            .group_by(extract('hour', QuestionModel.created_at))
            .order_by(extract('hour', QuestionModel.created_at))
        )
        
        timeline = {
            "start_time": cutoff_time.isoformat(),
            "end_time": datetime.utcnow().isoformat(),
            "hours": hours,
            "data": []
        }
        
        for row in questions_by_hour:
            timeline["data"].append({
                "hour": int(row.hour),
                "questions_count": row.count
            })
        
        return timeline
        
    except Exception as e:
        logger.error(f"성능 타임라인 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="성능 타임라인 조회 중 오류가 발생했습니다."
        )


@router.get("/health/detailed")
async def get_detailed_health(
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    상세 헬스 체크
    
    Returns:
        - API 서버 상태
        - 데이터베이스 상태
        - Redis 상태
        - 각 에이전트 상태
    """
    try:
        health = {
            "timestamp": get_current_kst().isoformat(),
            "overall_status": "healthy",
            "components": {}
        }
        
        # API 서버 상태
        health["components"]["api"] = {
            "status": "healthy",
            "uptime": "unknown"  # TODO: 실제 업타임 추가
        }
        
        # 데이터베이스 상태
        try:
            await db.execute(select(1))
            health["components"]["database"] = {
                "status": "healthy",
                "type": "PostgreSQL"
            }
        except Exception as e:
            health["components"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health["overall_status"] = "degraded"
        
        # Redis 상태
        try:
            await redis_client.ping()
            redis_info = await redis_client.info("memory")
            health["components"]["redis"] = {
                "status": "healthy",
                "memory_used": redis_info.get("used_memory_human", "unknown")
            }
        except Exception as e:
            health["components"]["redis"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health["overall_status"] = "degraded"
        
        # 에이전트 상태
        agent_keys = await redis_client.keys("maice:agent_status:*")
        agents_health = []
        
        for key in agent_keys:
            agent_name = key.split(":")[-1]
            status = await redis_client.hgetall(key)
            
            if status:
                is_alive = status.get("is_alive") == "true"
                last_update = float(status.get("last_update", 0))
                
                # 1분 이상 업데이트 없으면 비정상으로 간주
                is_stale = (datetime.utcnow().timestamp() - last_update) > 60
                
                agents_health.append({
                    "name": agent_name,
                    "status": "healthy" if (is_alive and not is_stale) else "unhealthy",
                    "last_update": last_update
                })
                
                if not is_alive or is_stale:
                    health["overall_status"] = "degraded"
        
        health["components"]["agents"] = {
            "status": "healthy" if all(a["status"] == "healthy" for a in agents_health) else "degraded",
            "agents": agents_health,
            "total": len(agents_health),
            "healthy": sum(1 for a in agents_health if a["status"] == "healthy")
        }
        
        return health
        
    except Exception as e:
        logger.error(f"상세 헬스 체크 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="헬스 체크 중 오류가 발생했습니다."
        )


@router.get("/logs/recent")
async def get_recent_logs(
    limit: int = 50,
    level: str = "INFO",
    agent_name: Optional[str] = None,
    current_user: UserModel = Depends(get_current_admin),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    최근 로그 조회 (Redis에서)
    
    Args:
        limit: 조회할 로그 개수
        level: 로그 레벨 필터 (INFO, WARNING, ERROR)
        agent_name: 특정 에이전트 필터
    
    Note: 이 기능은 향후 로그 수집 시스템과 통합 필요
    """
    try:
        # TODO: 실제 로그 수집 시스템 구현
        # 현재는 플레이스홀더
        
        logs = {
            "timestamp": get_current_kst().isoformat(),
            "total": 0,
            "logs": []
        }
        
        return logs
        
    except Exception as e:
        logger.error(f"로그 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그 조회 중 오류가 발생했습니다."
        )


@router.get("/processing-logs/{session_id}")
async def get_processing_logs(
    session_id: int,
    current_user: UserModel = Depends(get_current_admin),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    세션별 처리 로그 조회
    
    Args:
        session_id: 세션 ID
    
    Returns:
        - 에이전트별 처리 단계 로그
        - 타임스탬프
        - 처리 상태
    """
    try:
        # 세션별 스트림에서 처리 로그 읽기
        stream_name = f"maice:agent_to_backend_stream_session_{session_id}"
        
        # 스트림이 존재하는지 확인
        exists = await redis_client.exists(stream_name)
        if not exists:
            return {
                "session_id": session_id,
                "logs": [],
                "total": 0,
                "message": "해당 세션의 처리 로그가 없습니다."
            }
        
        # 스트림에서 최근 100개 메시지 읽기
        messages = await redis_client.xrevrange(stream_name, count=100)
        
        processing_logs = []
        for msg_id, msg_data in messages:
            msg_type = msg_data.get("type", b"").decode() if isinstance(msg_data.get("type"), bytes) else msg_data.get("type", "")
            
            # processing_log 타입만 필터링
            if msg_type == "processing_log":
                log_entry = {
                    "message_id": msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id),
                    "agent_name": msg_data.get("agent_name", b"").decode() if isinstance(msg_data.get("agent_name"), bytes) else msg_data.get("agent_name", ""),
                    "stage": msg_data.get("stage", b"").decode() if isinstance(msg_data.get("stage"), bytes) else msg_data.get("stage", ""),
                    "message": msg_data.get("message", b"").decode() if isinstance(msg_data.get("message"), bytes) else msg_data.get("message", ""),
                    "timestamp": msg_data.get("timestamp", b"").decode() if isinstance(msg_data.get("timestamp"), bytes) else msg_data.get("timestamp", "")
                }
                processing_logs.append(log_entry)
        
        # 타임스탬프 순으로 정렬 (최신순)
        processing_logs.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return {
            "session_id": session_id,
            "logs": processing_logs,
            "total": len(processing_logs),
            "timestamp": get_current_kst().isoformat()
        }
        
    except Exception as e:
        logger.error(f"처리 로그 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="처리 로그 조회 중 오류가 발생했습니다."
        )


@router.get("/processing-summary")
async def get_processing_summary(
    hours: int = 1,
    current_user: UserModel = Depends(get_current_admin),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    전체 처리 요약 통계
    
    Args:
        hours: 조회할 시간 범위 (기본 1시간)
    
    Returns:
        - 에이전트별 처리 건수
        - 평균 처리 시간
        - 성공/실패 비율
    """
    try:
        # 에이전트 목록
        agent_names = [
            "QuestionClassifier",
            "QuestionImprovement", 
            "AnswerGenerator",
            "Observer",
            "FreeTalker"
        ]
        
        summary = {
            "timestamp": get_current_kst().isoformat(),
            "time_range_hours": hours,
            "agents": []
        }
        
        for agent_name in agent_names:
            # 요청 수
            requests_total_key = f"maice:metrics:{agent_name}:counter:requests_total{{operation=classification}}" if agent_name == "QuestionClassifier" else f"maice:metrics:{agent_name}:counter:requests_total"
            requests_value = await redis_client.get(requests_total_key)
            requests_total = float(requests_value) if requests_value else 0
            
            # 성공 수
            success_key = f"maice:metrics:{agent_name}:counter:classification_success_total" if agent_name == "QuestionClassifier" else f"maice:metrics:{agent_name}:counter:answer_success_total"
            success_value = await redis_client.get(success_key)
            success_total = float(success_value) if success_value else 0
            
            # 실패 수
            failed_key = f"maice:metrics:{agent_name}:counter:classification_failed_total" if agent_name == "QuestionClassifier" else f"maice:metrics:{agent_name}:counter:answer_failed_total"
            failed_value = await redis_client.get(failed_key)
            failed_total = float(failed_value) if failed_value else 0
            
            # 평균 처리 시간
            operation = "classification" if agent_name == "QuestionClassifier" else "answer_generation"
            duration_key = f"maice:metrics:{agent_name}:histogram:request_duration_seconds{{operation={operation}}}"
            duration_stats = await redis_client.hgetall(duration_key)
            avg_duration = float(duration_stats.get("avg", 0)) if duration_stats else 0
            
            agent_summary = {
                "agent_name": agent_name,
                "total_requests": int(requests_total),
                "successful": int(success_total),
                "failed": int(failed_total),
                "success_rate": (success_total / requests_total * 100) if requests_total > 0 else 0,
                "avg_duration_seconds": round(avg_duration, 3)
            }
            
            summary["agents"].append(agent_summary)
        
        return summary
        
    except Exception as e:
        logger.error(f"처리 요약 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="처리 요약 조회 중 오류가 발생했습니다."
        )


