"""
이미지 → LaTeX 변환 서비스
Gemini Vision API를 사용하여 이미지에서 수학 공식을 LaTeX로 변환
"""

import os
import base64
import io
import logging
from typing import Optional, Tuple
from PIL import Image
import google.generativeai as genai
from fastapi import HTTPException, UploadFile
from app.core.config import settings

logger = logging.getLogger(__name__)


class ImageToLatexService:
    """이미지에서 LaTeX 변환을 처리하는 서비스"""
    
    def __init__(self):
        """서비스 초기화"""
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_VISION_MODEL
        
        if not self.api_key:
            logger.warning("GEMINI_API_KEY가 설정되지 않았습니다")
            return
            
        # Gemini API 설정
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
        
        # 이미지 처리 설정
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.max_image_size = 1536  # 최대 이미지 크기 (균형잡힌 품질과 속도)
        self.supported_formats = {'image/jpeg', 'image/png', 'image/webp'}
    
    async def convert_image_to_latex(self, image_file: UploadFile) -> str:
        """
        이미지를 LaTeX로 변환
        
        Args:
            image_file: 업로드된 이미지 파일
            
        Returns:
            str: 변환된 LaTeX 문자열
            
        Raises:
            HTTPException: 변환 실패 시
        """
        try:
            # 1. 파일 검증
            await self._validate_image_file(image_file)
            
            # 2. 이미지 전처리
            processed_image = await self._process_image(image_file)
            
            # 3. Gemini API 호출
            latex_result = await self._call_gemini_api(processed_image)
            
            # 4. 결과 검증 및 정제
            cleaned_latex = self._clean_latex_result(latex_result)
            
            # 5. MathLive 호환성을 위한 LaTeX 명령어 변환
            mathlive_compatible_latex = self._convert_to_mathlive_compatible(cleaned_latex)
            
            logger.info(f"이미지 → LaTeX 변환 성공: {mathlive_compatible_latex[:100]}...")
            return mathlive_compatible_latex
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"이미지 → LaTeX 변환 실패: {e}")
            raise HTTPException(
                status_code=500,
                detail="이미지 변환 중 오류가 발생했습니다. 다시 시도해주세요."
            )
    
    def _convert_to_mathlive_compatible(self, latex: str) -> str:
        """
        MathLive 호환성을 위한 LaTeX 명령어 변환
        """
        # \dots를 \ldots로 변환 (MathLive가 더 잘 인식함)
        latex = latex.replace(r'\dots', r'\ldots')
        
        # 기타 MathLive 호환성 개선
        latex = latex.replace(r'\cdots', r'\ldots')  # \cdots도 \ldots로 통일
        latex = latex.replace(r'\vdots', r'\ldots')  # \vdots도 \ldots로 통일
        
        # 추가적인 MathLive 호환성 변환들
        latex = latex.replace(r'\times', r'\cdot')  # \times를 \cdot로 변환 (더 안정적)
        
        return latex
    
    async def _validate_image_file(self, image_file: UploadFile) -> None:
        """이미지 파일 검증"""
        # 파일 크기 검증
        if image_file.size and image_file.size > self.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"파일 크기가 너무 큽니다. 최대 {self.max_file_size // (1024*1024)}MB까지 지원됩니다."
            )
        
        # 파일 형식 검증
        if image_file.content_type not in self.supported_formats:
            raise HTTPException(
                status_code=400,
                detail="지원되지 않는 파일 형식입니다. JPG, PNG, WebP 파일만 지원됩니다."
            )
        
        # API 키 검증
        if not self.api_key:
            raise HTTPException(
                status_code=503,
                detail="이미지 변환 서비스가 현재 사용할 수 없습니다."
            )
    
    async def _process_image(self, image_file: UploadFile) -> Image.Image:
        """이미지 전처리"""
        try:
            # 파일 내용 읽기
            image_data = await image_file.read()
            
            # PIL Image로 변환
            image = Image.open(io.BytesIO(image_data))
            
            # RGB 모드로 변환 (RGBA, L 등 처리)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 이미지 크기 조정
            if max(image.size) > self.max_image_size:
                image.thumbnail((self.max_image_size, self.max_image_size), Image.Resampling.LANCZOS)
            
            logger.info(f"이미지 전처리 완료: {image.size}, {image.mode}")
            return image
            
        except Exception as e:
            logger.error(f"이미지 전처리 실패: {e}")
            raise HTTPException(
                status_code=400,
                detail="이미지 파일을 처리할 수 없습니다. 올바른 이미지 파일인지 확인해주세요."
            )
    
    async def _call_gemini_api(self, image: Image.Image) -> str:
        """Gemini Vision API 호출"""
        try:
            # 프롬프트 설정
            prompt = """
이미지의 수학 내용을 LaTeX로 변환하세요. 설명이나 추가 텍스트 없이 순수한 수학 내용만 반환하세요.

요구사항:
1. 수학 공식이 있다면 LaTeX 형식으로 변환
   - 인라인 수식: $...$ 형태로 감싸기
   - 블록 수식: $$...$$ 형태로 감싸기
2. 한글 설명이 있다면 그대로 포함
3. 줄바꿈이 필요한 경우 \\n 사용
4. 수식과 텍스트가 함께 있다면 자연스럽게 연결
5. 수식이 없다면 한글 텍스트만 반환
6. 내용이 없다면 빈 문자열 반환

예시:
- "이차방정식의 해는 $x = \\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}$ 입니다."
- "수학적 귀납법을 사용하여 다음을 증명하겠습니다:\\n$$1+2+\\ldots+(2n-1) = n^2$$"
- "위의 공식에서 $n=1$일 때 $1 = 1^2$이므로 성립합니다."

중요: "다음은", "분석한 결과", "이미지에 포함된" 등의 설명 문구는 절대 포함하지 마세요.
"""
            
            # 이미지를 바이트로 변환 (토큰 절약을 위해 품질 낮춤)
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG', quality=90)
            img_byte_arr = img_byte_arr.getvalue()
            
            # Gemini API 호출 (토큰 제한 증가)
            generation_config = {
                "temperature": 0.1,  # 낮은 온도로 일관된 결과
                "max_output_tokens": 4000,  # 출력 토큰 제한 증가
                "top_p": 0.8,
                "top_k": 40
            }
            
            # 안전 설정을 최대한 완화 (수학 문제 분석을 위해)
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_ONLY_HIGH"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH", 
                    "threshold": "BLOCK_ONLY_HIGH"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_ONLY_HIGH"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_ONLY_HIGH"
                }
            ]
            
            # 안전 설정 없이 시도 (수학 문제 분석을 위해)
            response = self.model.generate_content([
                prompt,
                {
                    "mime_type": "image/jpeg",
                    "data": img_byte_arr
                }
            ], generation_config=generation_config)
            
            # 응답 상세 로깅
            logger.info(f"Gemini API 응답: {response}")
            logger.info(f"응답 텍스트: {response.text}")
            logger.info(f"응답 후보들: {response.candidates}")
            
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                logger.info(f"첫 번째 후보: {candidate}")
                logger.info(f"finish_reason: {getattr(candidate, 'finish_reason', 'None')}")
                logger.info(f"safety_ratings: {getattr(candidate, 'safety_ratings', 'None')}")
                
                if hasattr(candidate, 'content') and candidate.content:
                    logger.info(f"후보 내용: {candidate.content}")
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        logger.info(f"내용 부분들: {candidate.content.parts}")
            
            # 응답 검증 및 에러 처리
            if not response.text:
                # finish_reason 확인
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'finish_reason'):
                        finish_reason = candidate.finish_reason
                        logger.error(f"finish_reason 상세: {finish_reason}")
                        if finish_reason == 2:  # SAFETY
                            raise Exception("이미지 내용이 안전 정책에 위배되어 분석할 수 없습니다. 수학 문제 이미지만 업로드해주세요.")
                        elif finish_reason == 3:  # RECITATION
                            raise Exception("이미지에서 텍스트를 인식할 수 없습니다. 더 선명한 이미지를 업로드해주세요.")
                        elif finish_reason == 4:  # OTHER
                            raise Exception("이미지 분석 중 오류가 발생했습니다.")
                
                raise Exception("Gemini API에서 응답을 받지 못했습니다")
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Gemini API 호출 실패: {e}")
            raise HTTPException(
                status_code=503,
                detail="이미지 분석 서비스에 일시적인 문제가 있습니다. 잠시 후 다시 시도해주세요."
            )
    
    def _clean_latex_result(self, latex_result: str) -> str:
        """LaTeX 결과 정제"""
        if not latex_result:
            return ""
        
        # 불필요한 텍스트 제거
        cleaned = latex_result.strip()
        
        # "No mathematical expression found" 처리
        if "no mathematical expression found" in cleaned.lower():
            return ""
        
        # LaTeX 코드 블록 마커 제거 (```latex, ``` 등)
        if cleaned.startswith("```"):
            lines = cleaned.split('\n')
            if len(lines) > 1:
                cleaned = '\n'.join(lines[1:-1]) if lines[-1].strip() == "```" else '\n'.join(lines[1:])
        
        # 불필요한 공백 정리
        cleaned = cleaned.strip()
        
        # 기본적인 LaTeX 문법 검증
        if not self._is_valid_latex(cleaned):
            logger.warning(f"잠재적으로 잘못된 LaTeX: {cleaned}")
        
        return cleaned
    
    def _is_valid_latex(self, latex: str) -> bool:
        """기본적인 LaTeX 문법 검증"""
        if not latex:
            return False
        
        # 기본적인 LaTeX 명령어나 수학 기호가 있는지 확인
        latex_indicators = [
            '\\',  # LaTeX 명령어
            '{', '}',  # 그룹
            '^', '_',  # 위첨자, 아래첨자
            '+', '-', '*', '/',  # 기본 연산자
            '=', '<', '>',  # 비교 연산자
            '(', ')', '[', ']',  # 괄호
        ]
        
        return any(indicator in latex for indicator in latex_indicators)
