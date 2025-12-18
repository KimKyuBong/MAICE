"""
Field() 사용법 차이점 비교
"""

from pydantic import BaseModel, Field
from typing import Optional

class ExampleWithoutEllipsis(BaseModel):
    """Field(...) 없이 정의된 모델 (잘못된 예시)"""
    # 필수 필드들이지만 명확하지 않음
    name: str
    age: Optional[int] = None

class ExampleWithEllipsis(BaseModel):
    """Field(...) 사용한 모델 (올바른 예시)"""
    # 필수 필드임이 명확함
    name: str = Field(..., description="사용자명")
    age: Optional[int] = Field(None, description="나이")


# 반환 타입은 같지만 의미가 다릅니다

def create_user_bad():
    # 좋지 않은 예시 - 필수/선택 필드의 구분이 애매함
    return ExampleWithoutEllipsis(name="John")


def create_user_good():
    # 좋은 예시 - Field(...)로 필수 필드임을 명확히 표시
    return ExampleWithEllipsis(name="John")


def demo_field_meanings():
    """Field() 사용법 데모"""
    
    # 1. Field(...) = 필수 필드
    print("Field(...) 의미:", "이 필드는 반드시 제공되어야 함")
    
    # 2. Field(None) = 선택적 필드
    print("Field(None) 의미:", "이 필드는 선택적이며 기본값은 None")
    
    # 3. Field(default_value) = 기본값이 있는 필드
    print("Field(default) 의미:", "이 필드는 생략 가능하며 기본값 제공")
    
    # 실제 사용 예시
    essential_field = Field(..., description="최소 길이", min_length=1)
    optional_field = Field(None, description="선택적 필드") 
    field_with_default = Field("default", description="기본값 필드")


if __name__ == "__main__":
    demo_field_meanings()

