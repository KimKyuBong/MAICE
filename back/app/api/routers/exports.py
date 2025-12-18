"""
Data export API endpoints.
All endpoints return file responses for data download.
"""

from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
import tempfile
import pandas as pd
import logging

from app.models.models import UserModel, UserRole, QuestionModel, SurveyResponseModel, TeacherEvaluationModel
from app.core.db.session import get_db
from app.core.auth.dependencies import get_current_admin

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/all")
async def export_all_data(
    request: Request,
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """모든 데이터를 Excel 파일로 내보내기"""
    try:
        # 사용자 데이터 조회
        query = select(UserModel)
        result = await db.execute(query)
        users = result.scalars().all()
        
        # 질문 데이터 조회
        query = select(QuestionModel)
        result = await db.execute(query)
        questions = result.scalars().all()
        
        # 설문 응답 데이터 조회
        query = select(SurveyResponseModel)
        result = await db.execute(query)
        survey_responses = result.scalars().all()
        
        # 각 데이터프레임 생성
        user_data = [
            {
                "ID": user.id,
                "사용자명": user.username,
                "역할": user.role.value,

                "질문 횟수": user.question_count if user.role == UserRole.STUDENT else 0,
                "최대 질문 수": user.max_questions if user.role == UserRole.STUDENT else 0,
                "생성 시간": user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else ""
            } for user in users
        ]
        
        question_data = [
            {
                "ID": question.id,
                "사용자 ID": question.user_id,
                "질문": question.content,
                "답변": question.answer,
                "이미지 경로": question.image_path,
                "생성 시간": question.created_at.strftime("%Y-%m-%d %H:%M:%S") if question.created_at else ""
            } for question in questions
        ]
        
        survey_data = [
            {
                "ID": survey.id,
                "질문 ID": survey.question_id,
                "사용자 ID": survey.user_id,
                "응답 내용": survey.content,
                "적절성 점수": survey.relevance_score,
                "안내성 점수": survey.guidance_score,
                "명확성 점수": survey.clarity_score,
                "피드백": survey.text_feedback,
                "어려운 단어": survey.difficult_words,
                "생성 시간": survey.created_at.strftime("%Y-%m-%d %H:%M:%S") if survey.created_at else ""
            } for survey in survey_responses
        ]
        
        # 엑셀 파일 생성
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            with pd.ExcelWriter(tmp.name, engine="openpyxl") as writer:
                pd.DataFrame(user_data).to_excel(writer, sheet_name="사용자", index=False)
                pd.DataFrame(question_data).to_excel(writer, sheet_name="질문", index=False)
                pd.DataFrame(survey_data).to_excel(writer, sheet_name="설문응답", index=False)
            tmp_path = tmp.name
        
        # 파일 응답 반환
        return FileResponse(
            tmp_path, 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"data_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
        
    except Exception as e:
        logger.error(f"전체 데이터 내보내기 중 오류 발생: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="데이터 내보내기 중 오류가 발생했습니다."
        )


@router.get("/students")
async def export_students_excel(
    request: Request,
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """학생 데이터를 Excel 파일로 내보내기"""
    try:
        # 학생 목록 조회
        query = select(UserModel).where(UserModel.role == UserRole.STUDENT)
        result = await db.execute(query)
        students = result.scalars().all()
        
        # DataFrame 생성
        data = []
        for student in students:
            # 질문 수 조회
            question_count_query = select(QuestionModel).where(QuestionModel.user_id == student.id)
            question_count_result = await db.execute(question_count_query)
            question_count = len(question_count_result.scalars().all())
            
            data.append({
                '학번': student.username,
                '최대 질문 수': student.max_questions,
                '사용한 질문 수': question_count,
                '남은 질문 수': (student.max_questions - question_count) if student.max_questions else 0,
                '생성일': student.created_at.strftime('%Y-%m-%d %H:%M:%S'),

            })
        
        df = pd.DataFrame(data)
        
        # Excel 파일 생성
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            with pd.ExcelWriter(tmp.name, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name='Students', index=False)
            tmp_path = tmp.name
        
        return FileResponse(
            tmp_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=students.xlsx"}
        )
        
    except Exception as e:
        logger.error(f"학생 데이터 내보내기 중 오류 발생: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="데이터 내보내기 중 오류가 발생했습니다."
        )


@router.get("/teacher-evaluations")
async def export_teacher_evaluations_excel(
    request: Request,
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """교사 평가 데이터를 Excel 파일로 내보내기"""
    try:
        # 교사 평가 데이터 조회
        query = select(TeacherEvaluationModel)
        result = await db.execute(query)
        evaluations = result.scalars().all()
        
        # DataFrame 생성
        data = []
        for eval in evaluations:
            data.append({
                '평가 ID': eval.id,
                '평가받은 교사': eval.user.username if eval.user else 'N/A',
                '평가자': eval.evaluator.username if eval.evaluator else 'N/A',
                '문항 1': eval.q1_score,
                '문항 2': eval.q2_score,
                '문항 3': eval.q3_score,
                '문항 4': eval.q4_score,
                '문항 5': eval.q5_score,
                '총점': eval.total_score,
                '평가일': eval.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        df = pd.DataFrame(data)
        
        # Excel 파일 생성
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            with pd.ExcelWriter(tmp.name, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name='Teacher Evaluations', index=False)
            tmp_path = tmp.name
        
        return FileResponse(
            tmp_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=teacher_evaluations.xlsx"}
        )
        
    except Exception as e:
        logger.error(f"교사 평가 데이터 내보내기 중 오류 발생: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="데이터 내보내기 중 오류가 발생했습니다."
        )


@router.get("/questions")
async def export_questions_excel(
    request: Request,
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """질문 데이터를 Excel 파일로 내보내기"""
    try:
        # 질문 데이터 조회
        query = select(QuestionModel, UserModel).join(
            UserModel, QuestionModel.user_id == UserModel.id
        )
        result = await db.execute(query)
        questions = result.all()
        
        # DataFrame 생성
        data = []
        for question, user in questions:
            data.append({
                '질문 ID': question.id,
                '학생 ID': user.username,
                '질문 내용': question.content,
                '답변 내용': question.answer,
                '이미지 경로': question.image_path,
                '생성일': question.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                '답변일': question.answered_at.strftime('%Y-%m-%d %H:%M:%S') if question.answered_at else None
            })
        
        df = pd.DataFrame(data)
        
        # Excel 파일 생성
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            with pd.ExcelWriter(tmp.name, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name='Questions', index=False)
            tmp_path = tmp.name
        
        return FileResponse(
            tmp_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=questions.xlsx"}
        )
        
    except Exception as e:
        logger.error(f"질문 데이터 내보내기 중 오류 발생: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="데이터 내보내기 중 오류가 발생했습니다."
        )


@router.get("/surveys")
async def export_surveys_excel(
    request: Request,
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """설문 응답 데이터를 Excel 파일로 내보내기"""
    try:
        # 설문 응답 데이터 조회
        query = select(SurveyResponseModel, UserModel).join(
            UserModel, SurveyResponseModel.user_id == UserModel.id
        )
        result = await db.execute(query)
        surveys = result.all()
        
        # DataFrame 생성
        data = []
        for survey, user in surveys:
            data.append({
                '설문 ID': survey.id,
                '학생 ID': user.username,
                '질문 ID': survey.question_id,
                '응답 내용': survey.content,
                '적절성 점수': survey.relevance_score,
                '안내성 점수': survey.guidance_score,
                '명확성 점수': survey.clarity_score,
                '평균 점수': round((survey.relevance_score + survey.guidance_score + survey.clarity_score) / 3, 2),
                '피드백': survey.text_feedback,
                '어려운 단어': survey.difficult_words,
                '생성일': survey.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        df = pd.DataFrame(data)
        
        # Excel 파일 생성
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            with pd.ExcelWriter(tmp.name, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name='Surveys', index=False)
            tmp_path = tmp.name
        
        return FileResponse(
            tmp_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=surveys.xlsx"}
        )
        
    except Exception as e:
        logger.error(f"설문 데이터 내보내기 중 오류 발생: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="데이터 내보내기 중 오류가 발생했습니다."
        ) 