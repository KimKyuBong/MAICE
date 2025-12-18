"""
공통 프롬프트 유틸리티 함수들
"""

import re
import hashlib
from typing import Dict, Any, List
from datetime import datetime

def sanitize_text(text: str) -> str:
    """텍스트 정제 및 안전화"""
    if not text:
        return ""
    
    # HTML 태그 제거
    text = re.sub(r'<[^>]+>', '', text)
    # 특수 문자 일부 제거 (보안상 위험할 수 있는 것들)
    text = re.sub(r'[<>"\']', '', text)
    # 연속된 공백 정리
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def validate_prompt_content(content: str, dangerous_patterns: List[str] = None) -> tuple[bool, str]:
    """프롬프트 내용의 안전성 검증"""
    if not content or not content.strip():
        return False, "내용이 비어있습니다"
    
    # 기본 위험 패턴
    default_patterns = [
        r'system\s*:', r'user\s*:', r'assistant\s*:',  # 역할 변경 시도
        r'당신은\s*[^입니다]*입니다',  # 역할 재정의 시도
        r'프롬프트\s*무시', r'지시사항\s*변경',  # 지시사항 무시 시도
        r'JSON\s*형식\s*무시', r'응답\s*형식\s*변경',  # 응답 형식 변경 시도
        r'<script', r'javascript:', r'<iframe',  # 악성 코드 시도
    ]
    
    if dangerous_patterns:
        default_patterns.extend(dangerous_patterns)
    
    content_lower = content.lower()
    for pattern in default_patterns:
        if re.search(pattern, content_lower, re.IGNORECASE):
            return False, f"위험한 패턴이 감지되었습니다: {pattern}"
    
    return True, ""

def generate_safe_separators() -> Dict[str, str]:
    """안전한 구분자 생성"""
    return {
        "start": "===프롬프트시작===",
        "end": "===프롬프트종료===",
        "content": "---내용---"
    }

def create_separator_hash(separators: Dict[str, str]) -> str:
    """구분자 해시 생성"""
    combined = separators["start"] + separators["end"]
    return hashlib.md5(combined.encode()).hexdigest()[:8]

def format_prompt_with_variables(template: str, variables: Dict[str, Any]) -> str:
    """프롬프트 템플릿에 변수 적용"""
    try:
        return template.format(**variables)
    except KeyError as e:
        raise ValueError(f"프롬프트 템플릿에 필요한 변수가 누락되었습니다: {e}")

def extract_json_from_response(content: str) -> str:
    """LLM 응답에서 JSON 추출 및 LaTeX 백슬래시 이스케이프 처리"""
    if not content:
        return ""
    
    # JSON 블록 찾기 (```json ... ``` 또는 ``` ... ``` 형태)
    json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    json_match = re.search(json_pattern, content, re.DOTALL)
    
    json_content = ""
    if json_match:
        json_content = json_match.group(1)
    else:
        # 일반 중괄호 찾기
        start = content.find("{")
        if start == -1:
            return ""
        
        # 중괄호 균형 맞추기
        brace_count = 0
        end = -1
        
        for i in range(start, len(content)):
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end = i
                    break
        
        if end != -1 and end > start:
            json_content = content[start:end+1]
            
            # 이중 중괄호 정리 ({{ -> {, }} -> })
            json_content = json_content.replace("{{", "{").replace("}}", "}")
            
            # 추가 정리: 연속된 중괄호나 대괄호 정리
            json_content = re.sub(r'\{+', '{', json_content)
            json_content = re.sub(r'\}+', '}', json_content)
            json_content = re.sub(r'\[+', '[', json_content)
            json_content = re.sub(r'\]+', ']', json_content)
        else:
            return ""
    
    # LaTeX 백슬래시 이스케이프 처리
    # JSON에서 유효한 이스케이프 시퀀스: \" \\ \/ \b \f \n \r \t \uXXXX
    # 이 외의 백슬래시는 모두 이스케이프 처리 (LaTeX 수식의 \sum, \int 등)
    json_content = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', json_content)
    
    return json_content

def validate_json_structure(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
    """JSON 구조 검증 및 기본값 설정"""
    # 데이터가 딕셔너리가 아니면 기본 딕셔너리로 변환
    if not isinstance(data, dict):
        data = {}
    
    for field in required_fields:
        if field not in data or data[field] is None:
            if field.endswith('s'):
                data[field] = []
            elif field == "knowledge_code":
                data[field] = "K1"
            elif field == "quality":
                # quality는 기본값을 설정하지 않음 - LLM이 분류한 값을 그대로 유지
                data[field] = data.get(field, "answerable")
            elif field == "reasoning":
                data[field] = "분류 근거 없음"
            else:
                data[field] = {}
    
    return data
