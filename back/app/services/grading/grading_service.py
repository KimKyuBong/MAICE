import os
from app.services.base_service import BaseService
from app.services.analysis.consolidation_service import ConsolidationService
from app.services.grading.criteria_service import CriteriaService
from app.services.grading.submission_service import SubmissionService
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import json
from typing import Dict, List, Optional
from app import models
from app.schemas import GradingResponse, ImageProcessingResponse
from fastapi import HTTPException, UploadFile
from app.services.assistant.assistant_service import AssistantService
from app.core.config import settings
from app.schemas.analysis import ImageAnalysisResponse
from sqlalchemy import func
from app.models import TextExtraction
import asyncio

from app.services.analysis.ocr_service import OCRService
from app.services.file.file_service import FileService

logger = logging.getLogger(__name__)

class GradingService(BaseService):
    def __init__(self, assistant_service: AssistantService):
        super().__init__(settings)
        self.assistant_service = assistant_service
        self.client = assistant_service.get_client()
        self.file_service = FileService()

    async def process_submission(
        self,
        student_id: str,
        problem_key: str,
        file: UploadFile,
        db: AsyncSession
    ) -> ImageProcessingResponse:
        """제출물 처리 및 OCR 분석"""
        try:
            # 파일 저장
            image_path = await self.file_service.save_file(student_id, problem_key, file)
            if not image_path:
                return ImageProcessingResponse(success=False, error="파일 저장 실패")

            # OCR 분석 수행
            ocr_service = OCRService(self.assistant_service)
            ocr_result = await ocr_service.analyze_image(
                image_path=image_path,
                student_id=student_id,
                problem_key=problem_key,
                db=db
            )

            if not ocr_result:
                await self.file_service.delete_file(image_path)  # 실패 시 파일 삭제
                return ImageProcessingResponse(success=False, error="OCR 분석 실패")

            # 채점 수행
            grading_result = await self.create_grading(
                student_id=student_id,
                problem_key=problem_key,
                image_path=image_path,
                extraction=ocr_result,
                db=db
            )

            return ImageProcessingResponse(
                success=True,
                message="제출 처리 완료",
                data={
                    "extraction": ocr_result,
                    "grading": grading_result
                }
            )

        except Exception as e:
            logger.error(f"제출 처리 중 오류: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    async def grade_submission(
        self,
        grading_id: int,
        db: AsyncSession
    ) -> GradingResponse:
        """제출물 채점 수행"""
        try:
            # 채점 정보 조회
            grading = await self._get_grading(grading_id, db)
            if not grading:
                raise HTTPException(status_code=404, detail="채점 정보를 찾을 수 없습니다")

            # 채점 기준 조회
            criteria = await self.criteria_service.get_criteria(
                grading.problem_key, db
            )
            if not criteria:
                raise HTTPException(status_code=404, detail="채점 기준을 찾을 수 없습니다")

            # GPT를 사용한 채점 수행
            evaluation = await self._perform_grading(grading, criteria)

            # 채점 결과 업데이트
            await self._update_grading_results(grading, evaluation, db)

            return await self._prepare_grading_response(grading, db)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"채점 중 오류: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def _perform_grading(
        self,
        grading: models.Grading,
        criteria: models.GradingCriteria
    ) -> Dict:
        """GPT를 사용한 채점 수행"""
        try:
            thread = await self.client.beta.threads.create()
            
            # 채점 요청 메시지 생성
            await self._create_grading_message(thread.id, grading, criteria)
            
            # 실행
            run = await self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.grading_assistant_id
            )

            return await self._process_grading_result(thread.id, run.id)

        except Exception as e:
            logger.error(f"채점 수행 중 오류: {str(e)}")
            raise

    async def _create_submission_record(
        self,
        student_id: str,
        problem_key: str,
        image_path: str,
        db: AsyncSession
    ) -> models.StudentSubmission:
        """제출 정보 생성"""
        try:
            abs_path = os.path.join(self.base_dir, "uploads", image_path)
            submission = models.StudentSubmission(
                student_id=student_id,
                problem_key=problem_key,
                file_name=os.path.basename(image_path),
                image_path=image_path,
                file_size=os.path.getsize(abs_path),
                mime_type="image/png"
            )
            db.add(submission)
            await db.flush()
            return submission
        except Exception as e:
            logger.error(f"제출 정보 생성 중 오류: {str(e)}")
            raise


    async def _create_grading_record(
        self,
        submission: models.StudentSubmission,
        ocr_result: ImageAnalysisResponse,
        attempt: int,
        db: AsyncSession
    ) -> models.Grading:
        """채점 정보 생성"""
        try:
            if not ocr_result.success:
                raise ValueError(ocr_result.error or "OCR analysis failed")

            content = ocr_result.content
            grading = models.Grading(
                student_id=submission.student_id,
                problem_key=submission.problem_key,
                submission_id=submission.id,
                image_path=submission.image_path,
                extracted_text=content.get("text", ""),
                solution_steps=json.dumps(content.get("steps", []), ensure_ascii=False),
                total_score=0.0,
                max_score=0.0,
                feedback="채점 진행 중...",
                grading_number=attempt,
                is_consolidated=False
            )
            db.add(grading)
            await db.flush()
            return grading

        except Exception as e:
            logger.error(f"채점 정보 생성 중 오류: {str(e)}")
            raise

    async def _create_grading_message(
        self,
        thread_id: str,
        grading: models.Grading,
        criteria: models.GradingCriteria
    ) -> None:
        """채점 요청 메시지 생성"""
        message_content = f"""다음 학생의 답안을 채점해주세요:

학생 답안:
{grading.extracted_text}

채점 기준:
총점: {criteria.total_points}
정답: {criteria.correct_answer}
세부기준:
{json.dumps([{
    'id': c.id,
    'item': c.item,
    'points': float(c.points),
    'description': c.description
} for c in criteria.detailed_criteria], ensure_ascii=False, indent=2)}"""

        await self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=[{"type": "text", "text": message_content}]
        )

    async def _process_grading_result(self, thread_id: str, run_id: str) -> Dict:
        """채점 결과 처리"""
        try:
            run_status = await self._wait_for_run_completion(thread_id, run_id)
            if not run_status:
                raise Exception("채점 실행 실패")

            messages = await self.client.beta.threads.messages.list(
                thread_id=thread_id,
                order="desc",
                limit=1
            )

            if not messages.data:
                raise Exception("채점 결과를 받지 못했습니다")

            return json.loads(messages.data[0].content[0].text.value)

        except Exception as e:
            logger.error(f"채점 결과 처리 중 오류: {str(e)}")
            raise

    async def _update_grading_results(
        self,
        grading: models.Grading,
        evaluation: Dict,
        db: AsyncSession
    ) -> None:
        """채점 결과 업데이트"""
        try:
            grading.total_score = evaluation["total_score"]
            grading.feedback = evaluation["feedback"]
            
            # 세부 점수 저장
            for score in evaluation["detailed_scores"]:
                detailed_score = models.DetailedScore(
                    grading_id=grading.id,
                    detailed_criteria_id=score["criteria_id"],
                    score=score["score"],
                    feedback=score.get("feedback", "")
                )
                db.add(detailed_score)
            
            await db.commit()

        except Exception as e:
            await db.rollback()
            logger.error(f"채점 결과 업데이트 중 오류: {str(e)}")
            raise

    async def _prepare_response_data(
        self,
        grading: models.Grading,
        submission: models.StudentSubmission
    ) -> Dict:
        """응답 데이터 준비"""
        return {
            "id": grading.id,
            "submission_id": submission.id,
            "student_id": grading.student_id,
            "problem_key": grading.problem_key,
            "extracted_text": grading.extracted_text,
            "solution_steps": json.loads(grading.solution_steps),
            "total_score": grading.total_score,
            "max_score": grading.max_score,
            "feedback": grading.feedback,
            "grading_number": grading.grading_number,
            "image_path": grading.image_path,
            "created_at": grading.created_at,
            "detailed_scores": [],
            "submission": {
                "id": submission.id,
                "student_id": submission.student_id,
                "problem_key": submission.problem_key,
                "file_name": submission.file_name,
                "image_path": submission.image_path,
                "file_size": submission.file_size,
                "mime_type": submission.mime_type,
                "created_at": submission.created_at
            }
        }

    async def _get_grading(self, grading_id: int, db: AsyncSession) -> Optional[models.Grading]:
        """채점 정보 조회"""
        result = await db.execute(
            select(models.Grading).filter_by(id=grading_id)
        )
        return result.scalar_one_or_none()

    async def create_grading(
        self,
        student_id: str,
        problem_key: str,
        image_path: str,
        extraction: Dict,
        db: AsyncSession
    ) -> models.Grading:
        """채점 수행"""
        try:
            # 1. 제출 정보 조회 또는 생성
            submission = await self._get_or_create_submission(
                student_id=student_id,
                problem_key=problem_key,
                image_path=image_path,
                db=db
            )

            # 2. 채점 번호 계산 (동일 제출물에 대한 채점 횟수)
            grading_query = select(func.count()).select_from(models.Grading).filter_by(
                submission_id=submission.id
            )
            grading_number = (await db.scalar(grading_query) or 0) + 1

            # 3. 채점 수행 (Assistant 이용)
            grading_assistant = self.assistant_service.get_assistant('grading')
            thread = await self.client.beta.threads.create()
            
            try:
                # 채점 요청 메시지 생성
                await self.client.beta.threads.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content=f"""
                    문제: {problem_key}
                    학생 답안:
                    {extraction.extracted_text}
                    
                    풀이 과정:
                    {extraction.solution_steps}
                    """
                )

                # 채점 실행
                run = await self.client.beta.threads.runs.create(
                    thread_id=thread.id,
                    assistant_id=grading_assistant.id
                )

                # 채점 결과 대기 및 가져오기
                messages = await self._wait_and_get_messages(thread.id, run.id)
                grading_result = self._parse_grading_result(messages)

                # 4. 채점 정보 저장
                grading = models.Grading(
                    student_id=student_id,
                    problem_key=problem_key,
                    submission_id=submission.id,
                    extraction_id=extraction.id,
                    image_path=image_path,
                    extracted_text=extraction.extracted_text,
                    solution_steps=extraction.solution_steps,
                    total_score=grading_result.get('total_score', 0.0),
                    max_score=grading_result.get('max_score', 0.0),
                    feedback=grading_result.get('feedback', '채점 완료'),
                    grading_number=grading_number,
                    is_consolidated=False
                )
                
                db.add(grading)
                await db.flush()
                
                logger.info(f"Created grading {grading.id} for extraction {extraction.id}")
                return grading

            finally:
                # 스레드 정리
                try:
                    await self.client.beta.threads.delete(thread.id)
                except Exception as e:
                    logger.warning(f"Thread cleanup failed: {str(e)}")

        except Exception as e:
            logger.error(f"채점 생성 중 오류: {str(e)}")
            raise

    async def _wait_and_get_messages(self, thread_id: str, run_id: str) -> List[Dict]:
        """채점 완료 대기 및 메시지 가져오기"""
        while True:
            run = await self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )
            if run.status == 'completed':
                break
            elif run.status in ['failed', 'cancelled', 'expired']:
                raise Exception(f"Grading failed with status: {run.status}")
            await asyncio.sleep(1)

        messages = await self.client.beta.threads.messages.list(
            thread_id=thread_id,
            order='desc',
            limit=1
        )
        return messages.data

    def _parse_grading_result(self, messages: List[Dict]) -> Dict:
        """채점 결과 파싱"""
        try:
            if not messages:
                raise ValueError("No grading messages found")
            
            content = messages[0].content[0].text.value
            # 여기서 채점 결과를 파싱하는 로직 구현
            # 예시 형

        except Exception as e:
            logger.error(f"채점 결과 파싱 중 오류: {str(e)}")
            raise

    async def _get_or_create_submission(
        self,
        student_id: str,
        problem_key: str,
        image_path: str,
        db: AsyncSession
    ) -> models.StudentSubmission:
        """제출 정보 조회 또는 생성"""
        try:
            # 기존 제출 정보 조회
            query = select(models.StudentSubmission).filter_by(
                student_id=student_id,
                problem_key=problem_key,
                image_path=image_path
            )
            result = await db.execute(query)
            submission = result.scalar_one_or_none()

            if submission:
                return submission

            # 새 제출 정보 생성
            abs_path = os.path.join(self.base_dir, "uploads", image_path)
            submission = models.StudentSubmission(
                student_id=student_id,
                problem_key=problem_key,
                file_name=os.path.basename(image_path),
                image_path=image_path,
                file_size=os.path.getsize(abs_path),
                mime_type="image/png"
            )
            db.add(submission)
            await db.flush()
            
            logger.info(f"Created new submission record for {student_id}, {problem_key}")
            return submission

        except Exception as e:
            logger.error(f"제출 정보 처리 중 오류: {str(e)}")
            raise