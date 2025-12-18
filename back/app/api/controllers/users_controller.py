"""
Users API Controller
사용자 관련 API 엔드포인트를 처리
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import logging

from app.core.db.session import get_db
from app.core.auth.dependencies import get_current_admin
from app.services.user_service import UserService, UserValidationService
from app.api.controllers.base_controller import BaseController
from app.api.schemas.error_codes import ApiErrorCode
from app.api.schemas.standard_responses import SuccessResponse
from app.schemas.schemas import User, UserCreate, UserUpdate, UserPreferencesUpdate
from app.models.models import UserModel, UserRole
from typing import List, Optional

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[User])
async def get_users(
    role: Optional[UserRole] = Query(None, description="역할별 필터링"),
    skip: int = Query(0, ge=0, description="건너뛸 항목 수"),
    limit: int = Query(100, ge=1, le=1000, description="반환할 항목 수"),
    search: Optional[str] = Query(None, description="사용자명 검색"),
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """사용자 목록 조회 API"""
    try:
        BaseController.log_request("사용자 목록 조회", current_user.id, role=role, skip=skip, limit=limit, search=search)
        
        user_service = UserService(db)
        users = await user_service.get_users(role, skip, limit, search)
        
        BaseController.log_response("사용자 목록 조회", True)
        return users
        
    except Exception as e:
        error = BaseController.handle_exception(e, "사용자 목록 조회", "사용자 목록 조회 중 오류가 발생했습니다")
        raise error


@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """특정 사용자 조회 API"""
    try:
        BaseController.log_request("사용자 조회", current_user.id, user_id=user_id)
        
        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise BaseController.create_error_response(
                ApiErrorCode.NOT_FOUND,
                "사용자를 찾을 수 없습니다",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        BaseController.log_response("사용자 조회", True)
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        error = BaseController.handle_exception(e, "사용자 조회", "사용자 조회 중 오류가 발생했습니다")
        raise error


@router.post("/", response_model=User)
async def create_user(
    user_data: UserCreate,
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """새로운 사용자 생성 API"""
    try:
        BaseController.log_request("사용자 생성", current_user.id, username=user_data.username)
        
        # 데이터 검증
        validated_data = UserValidationService.validate_user_create(user_data)
        
        # 사용자 생성
        user_service = UserService(db)
        new_user = await user_service.create_user(validated_data)
        
        BaseController.log_response("사용자 생성", True, username=user_data.username)
        return new_user
        
    except ValueError as e:
        raise BaseController.create_error_response(
            ApiErrorCode.VALIDATION_ERROR.value,
            str(e),
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except HTTPException:
        raise
    except Exception as e:
        error = BaseController.handle_exception(e, "사용자 생성", "사용자 생성 중 오류가 발생했습니다")
        raise error


@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """사용자 정보 업데이트 API"""
    try:
        BaseController.log_request("사용자 업데이트", current_user.id, user_id=user_id)
        
        # 데이터 검증
        validated_data = UserValidationService.validate_user_update(user_id, user_data)
        
        # 사용자 업데이트
        user_service = UserService(db)
        updated_user = await user_service.update_user(user_id, validated_data)
        if not updated_user:
            raise BaseController.create_error_response(
                ApiErrorCode.NOT_FOUND,
                "사용자를 찾을 수 없습니다",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        BaseController.log_response("사용자 업데이트", True, user_id=user_id)
        return updated_user
        
    except HTTPException:
        raise
    except ValueError as e:
        raise BaseController.create_error_response(
            ApiErrorCode.VALIDATION_ERROR.value,
            str(e),
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        error = BaseController.handle_exception(e, "사용자 업데이트", "사용자 업데이트 중 오류가 발생했습니다")
        raise error


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """사용자 삭제 API"""
    try:
        BaseController.log_request("사용자 삭제", current_user.id, user_id=user_id)
        
        user_service = UserService(db)
        success = await user_service.delete_user(user_id)
        if not success:
            raise BaseController.create_error_response(
                ApiErrorCode.NOT_FOUND,
                "사용자를 찾을 수 없습니다",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        BaseController.log_response("사용자 삭제", True, user_id=user_id)
        return {"message": "사용자가 성공적으로 삭제되었습니다"}
        
    except HTTPException:
        raise
    except ValueError as e:
        raise BaseController.create_error_response(
            ApiErrorCode.BUSINESS_RULE_VIOLATION.value,
            str(e),
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        error = BaseController.handle_exception(e, "사용자 삭제", "사용자 삭제 중 오류가 발생했습니다")
        raise error


@router.put("/{user_id}/preferences", response_model=User)
async def update_user_preferences(
    user_id: int,
    preferences: UserPreferencesUpdate,
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """사용자 설정 업데이트 API (관리자 전용)"""
    try:
        BaseController.log_request("사용자 설정 업데이트", current_user.id, user_id=user_id)
        
        user_service = UserService(db)
        
        # 사용자 존재 확인
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise BaseController.create_error_response(
                ApiErrorCode.NOT_FOUND,
                "사용자를 찾을 수 없습니다",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # 업데이트할 필드 준비
        update_data = {}
        
        if preferences.max_questions is not None:
            update_data['max_questions'] = preferences.max_questions
            
        if preferences.remaining_questions is not None:
            update_data['remaining_questions'] = preferences.remaining_questions
            
        if preferences.assigned_mode is not None:
            # assigned_mode가 빈 문자열이거나 "None"이면 None으로 설정
            if preferences.assigned_mode in ["", "None", "none"]:
                update_data['assigned_mode'] = None
                update_data['mode_assigned_at'] = None
            elif preferences.assigned_mode in ["agent", "freepass"]:
                # 모드가 변경되는 경우에만 할당 시각 업데이트
                if user.assigned_mode != preferences.assigned_mode:
                    from datetime import datetime
                    update_data['assigned_mode'] = preferences.assigned_mode
                    update_data['mode_assigned_at'] = datetime.utcnow()
                else:
                    update_data['assigned_mode'] = preferences.assigned_mode
            else:
                raise BaseController.create_error_response(
                    ApiErrorCode.VALIDATION_ERROR,
                    "assigned_mode는 'agent', 'freepass', 또는 None이어야 합니다",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        
        # 설정 업데이트
        updated_user = await user_service.update_user(user_id, update_data)
        
        BaseController.log_response("사용자 설정 업데이트", True, user_id=user_id)
        return updated_user
        
    except HTTPException:
        raise
    except ValueError as e:
        raise BaseController.create_error_response(
            ApiErrorCode.VALIDATION_ERROR.value,
            str(e),
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        error = BaseController.handle_exception(e, "사용자 설정 업데이트", "사용자 설정 업데이트 중 오류가 발생했습니다")
        raise error


@router.get("/{user_id}/stats")
async def get_user_stats(
    user_id: int,
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """사용자 통계 조회 API"""
    try:
        BaseController.log_request("사용자 통계 조회", current_user.id, user_id=user_id)
        
        user_service = UserService(db)
        stats = await user_service.get_user_stats(user_id)
        if not stats:
            raise BaseController.create_error_response(
                ApiErrorCode.NOT_FOUND,
                "사용자를 찾을 수 없습니다",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        BaseController.log_response("사용자 통계 조회", True, user_id=user_id)
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        error = BaseController.handle_exception(e, "사용자 통계 조회", "사용자 통계 조회 중 오류가 발생했습니다")
        raise error


@router.get("/student-links")
async def get_student_links(
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """학생 링크 정보 조회 API"""
    try:
        BaseController.log_request("학생 링크 조회", current_user.id)
        
        user_service = UserService(db)
        student_links = await user_service.get_students_with_stats()
        result = BaseController.create_success_response(
            data={"students": student_links},
            message="학생 링크 정보를 성공적으로 조회했습니다"
        )
        
        BaseController.log_response("학생 링크 조회", True)
        return result
        
    except Exception as e:
        error = BaseController.handle_exception(e, "학생 링크 조회", "학생 링크 조회 중 오류가 발생했습니다")
        raise error


@router.post("/bulk-quota")
async def bulk_update_quota(
    request: Request,
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """일괄 질문 한도 설정 API"""
    try:
        data = await request.json()
        grade = data.get('grade')
        class_num = data.get('class')
        quota = data.get('quota')
        operation = data.get('operation', 'set')
        
        BaseController.log_request("일괄 한도 설정", current_user.id, grade=grade, operation=operation)
        
        user_service = UserService(db)
        result = await user_service.bulk_update_student_quota(grade, class_num, quota, operation)
        response = BaseController.create_success_response(
            data=result,
            message="일괄 한도 설정이 성공적으로 완료되었습니다"
        )
        
        BaseController.log_response("일괄 한도 설정", True, updated_count=result.get('updated_count'))
        return response
        
    except ValueError as e:
        raise BaseController.create_error_response(
            ApiErrorCode.VALIDATION_ERROR.value,
            str(e),
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except HTTPException:
        raise
    except Exception as e:
        error = BaseController.handle_exception(e, "일괄 한도 설정", "일괄 한도 설정 중 오류가 발생했습니다")
        raise error
