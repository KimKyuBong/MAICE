from app.services.base_service import BaseService
import logging
import os
import asyncio
from typing import Any, Dict, Optional
from app.services.assistant.assistant_service import AssistantService
from app.core.config import settings
import json
from app.schemas.analysis import ImageAnalysisResponse, TextExtractionResponse, MultipleExtractionResult, GradingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models import TextExtraction

logger = logging.getLogger(__name__)

class OCRService(BaseService):
    def __init__(self, assistant_service: AssistantService):
        super().__init__(settings)
        self.assistant_service = assistant_service
        self.client = assistant_service.get_client()
        self.process_math_image_function = {
            "name": "process_math_image",
            "description": "Extract text and math expressions from the image and return them in the specified JSON format. Do not include any markdown formatting or additional explanations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Raw text exactly as it appears in the image, without any formatting or additional content"
                    },
                    "steps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "step_number": {"type": "integer"},
                                "content": {"type": "string"},
                                "expressions": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "latex": {"type": "string"}
                                        }
                                    }
                                }
                            },
                            "required": ["step_number", "content", "expressions"]
                        }
                    }
                },
                "required": ["text", "steps"]
            }
        }

    def _get_full_path(self, relative_path: str) -> str:
        """상대 경로를 절대 경로로 변환"""
        return os.path.join(self.base_dir, "uploads", relative_path)

    async def _wait_for_completion(self, thread_id: str, run_id: str, timeout: int = 300):
        """실행 완료 대기 및 function call 결과 처리"""
        start_time = asyncio.get_event_loop().time()
        while True:
            try:
                run = await self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run_id
                )
                
                if run.status == "requires_action":
                    # Function call 요청이 있는 경우
                    tool_calls = run.required_action.submit_tool_outputs.tool_calls
                    tool_outputs = []
                    
                    for tool_call in tool_calls:
                        if tool_call.function.name == "process_math_image":
                            # Function call의 arguments는 이미 JSON 문자열임
                            arguments = json.loads(tool_call.function.arguments)
                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "output": json.dumps({
                                    "text": arguments.get("text", ""),
                                    "steps": arguments.get("steps", [])
                                }, ensure_ascii=False)
                            })
                    
                    logger.info(f"Submitting tool outputs: {json.dumps(tool_outputs, ensure_ascii=False)}")
                    
                    # 결과 제출
                    await self.client.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread_id,
                        run_id=run_id,
                        tool_outputs=tool_outputs
                    )
                
                elif run.status == "completed":
                    return run
                elif run.status == "failed":
                    raise Exception(f"Run failed: {run.last_error}")
                elif run.status == "expired":
                    raise Exception("Run expired")
                
                if asyncio.get_event_loop().time() - start_time > timeout:
                    raise Exception("Run timed out")
                    
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error waiting for completion: {str(e)}")
                raise

    async def _get_analysis_result(self, thread_id: str, run_id: str = None) -> Dict[str, Any]:
        """분석 결과 가져오기"""
        try:
            # 1. 먼저 tool outputs에서 결과 확인
            if run_id:
                run = await self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run_id
                )
                if run.status == "requires_action":
                    tool_outputs = run.required_action.submit_tool_outputs.tool_calls
                    for tool_call in tool_outputs:
                        if tool_call.function.name == "process_math_image":
                            try:
                                return json.loads(tool_call.function.arguments)
                            except json.JSONDecodeError:
                                logger.error(f"Failed to parse tool output JSON: {tool_call.function.arguments}")
                                continue

            # 2. messages에서 결과 확인
            messages = await self.client.beta.threads.messages.list(
                thread_id=thread_id,
                order="desc",
                limit=1
            )
            
            if messages.data:
                message = messages.data[0]
                if message.role == "assistant":
                    for content in message.content:
                        if hasattr(content, 'text'):
                            try:
                                # 문자열로 변환하고 JSON 파싱
                                text_value = str(content.text.value)
                                return json.loads(text_value)
                            except (json.JSONDecodeError, AttributeError) as e:
                                logger.error(f"Failed to parse message JSON: {e}")
                                continue

            logger.warning("No valid analysis result found")
            return {}
                
        except Exception as e:
            logger.error(f"Error getting analysis result: {str(e)}")
            logger.exception("Detailed error:")
            raise

    async def _cleanup(self, thread_id: str, file_id: str):
        """리소스 정리"""
        try:
            # 스레드 삭제
            await self.client.beta.threads.delete(thread_id)
            logger.info(f"Thread deleted: {thread_id}")
            
            # 파일 삭제
            await self.client.files.delete(file_id)
            logger.info(f"File deleted: {file_id}")
            
        except Exception as e:
            logger.warning(f"Cleanup failed: {str(e)}")

    async def analyze_and_grade_single(
        self, 
        image_path: str, 
        student_id: str, 
        problem_key: str,
        extraction_number: int,
        file_id: str,
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """단일 OCR 분석 및 채점 수행"""
        thread_id = None
        try:
            # 1. 스레드 생성
            thread = await self.client.beta.threads.create()
            thread_id = thread.id
            logger.info(f"Thread created: {thread_id}")

            # 2. OCR 분석
            await self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=[{"type": "image_file", "image_file": {"file_id": file_id}}]
            )

            run = await self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_service.get_assistant('ocr').id,
                tools=[{"type": "function", "function": self.process_math_image_function}],
                temperature=0.6
            )
            
            run = await self._wait_for_completion(thread_id, run.id)
            result = await self._get_analysis_result(thread_id, run.id)

            if result and isinstance(result, dict) and "text" in result:
                # 3. OCR 결과 저장
                text_extraction = TextExtraction(
                    student_id=student_id,
                    problem_key=problem_key,
                    extraction_number=extraction_number,
                    extracted_text=result["text"],
                    image_path=image_path,
                    solution_steps=json.dumps(result.get("steps", []), ensure_ascii=False)
                )
                db.add(text_extraction)
                await db.flush()

                # 4. 채점 수행 및 저장
                grading = await self.grading_service.create_grading(
                    student_id=student_id,
                    problem_key=problem_key,
                    image_path=image_path,
                    extraction=text_extraction,
                    db=db
                )

                # 5. 응답 객체 생성
                extraction_response = TextExtractionResponse(
                    id=text_extraction.id,
                    student_id=text_extraction.student_id,
                    problem_key=text_extraction.problem_key,
                    extraction_number=text_extraction.extraction_number,
                    extracted_text=text_extraction.extracted_text,
                    image_path=text_extraction.image_path,
                    solution_steps=json.loads(text_extraction.solution_steps),
                    created_at=text_extraction.created_at,
                    grading_id=grading.id
                )

                grading_response = GradingResponse(
                    id=grading.id,
                    student_id=grading.student_id,
                    problem_key=grading.problem_key,
                    submission_id=grading.submission_id,
                    extraction_id=text_extraction.id,
                    image_path=grading.image_path,
                    extracted_text=grading.extracted_text,
                    solution_steps=json.loads(grading.solution_steps),
                    total_score=grading.total_score,
                    max_score=grading.max_score,
                    feedback=grading.feedback,
                    grading_number=grading.grading_number,
                    is_consolidated=grading.is_consolidated,
                    created_at=grading.created_at
                )

                return {
                    "extraction": extraction_response,
                    "grading": grading_response
                }

        except Exception as e:
            logger.error(f"Analysis and grading error: {str(e)}")
            return None
        finally:
            if thread_id:
                try:
                    await self.client.beta.threads.delete(thread_id)
                except Exception as e:
                    logger.warning(f"Thread cleanup failed: {str(e)}")

    async def analyze_image(
        self, 
        image_path: str, 
        student_id: str, 
        problem_key: str, 
        db: AsyncSession
    ) -> ImageAnalysisResponse:
        """이미지 분석 및 채점 (3회 수행)"""
        file_id = None
        try:
            # 1. 파일 업로드
            with open(self._get_full_path(image_path), 'rb') as file:
                response = await self.client.files.create(
                    file=file,
                    purpose='assistants'
                )
                file_id = response.id
                logger.info(f"File uploaded: {file_id}")

            # 2. 현재 extraction_number 가져오기
            extraction_query = select(func.count()).select_from(TextExtraction).filter_by(
                student_id=student_id,
                problem_key=problem_key
            )
            current_count = await db.scalar(extraction_query) or 0

            # 3. 3회 분석 및 채점 병렬 실행
            tasks = [
                self.analyze_and_grade_single(
                    image_path=image_path,
                    student_id=student_id,
                    problem_key=problem_key,
                    extraction_number=current_count + i + 1,
                    file_id=file_id,
                    db=db
                )
                for i in range(3)
            ]
            
            results = await asyncio.gather(*tasks)
            valid_results = [r for r in results if r is not None]

            if not valid_results:
                return ImageAnalysisResponse(success=False, error="No valid results found")

            # 4. 결과 분리 및 응답 생성
            extractions = []
            gradings = []
            
            for result in valid_results:
                extractions.append(result["extraction"])
                gradings.append(result["grading"])

            await db.commit()  # 모든 트랜잭션 커밋

            return ImageAnalysisResponse(
                success=True,
                content=MultipleExtractionResult(
                    results=extractions,
                    gradings=gradings,
                    count=len(valid_results)
                )
            )

        except Exception as e:
            await db.rollback()  # 오류 발생 시 롤백
            logger.error(f"OCR 분석 중 오류: {str(e)}")
            return ImageAnalysisResponse(success=False, error=str(e))
        
        finally:
            if file_id:
                try:
                    await self.client.files.delete(file_id)
                except Exception as e:
                    logger.warning(f"File cleanup failed: {str(e)}")