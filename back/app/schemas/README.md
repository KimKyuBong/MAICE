# Pydantic 스키마 타임존 자동 변환

## 개요

모든 응답 스키마에서 `datetime` 필드를 자동으로 **UTC → KST**로 변환합니다.

## TimezoneBaseModel

```python
class TimezoneBaseModel(BaseModel):
    """
    모든 스키마의 Base 클래스
    datetime 필드를 자동으로 UTC → KST로 변환
    """
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: utc_to_kst(v) if v else None
        }
```

## 적용된 스키마

다음 Base 스키마들이 `TimezoneBaseModel`을 상속받아 자동 변환을 적용합니다:

### ✅ 사용자 관련
- `UserBase` → `User`, `UserCreate`, `UserUpdate` 등 모든 사용자 스키마

### ✅ 질문 관련
- `QuestionBase` → `QuestionCreate`, `QuestionUpdate`, `QuestionResponse`

### ✅ 설문 응답 관련
- `SurveyResponseBase` → `SurveyResponseCreate`

### ✅ 평가 관련
- `TeacherEvaluationBase` → 모든 교사 평가 스키마
- `TeacherEvaluationResponse`
- `GPTEvaluationBase`

### ✅ SSE 메시지
- `SSEBaseMessage` → 모든 SSE 응답 메시지

### ✅ 연구 동의
- `ResearchConsentBase` → `ResearchConsentResponse`

## 사용 예시

### Before (수동 변환)
```python
from app.utils.timezone import format_datetime_for_frontend

recent_activities = [
    {
        "time": format_datetime_for_frontend(msg.created_at),  # 수동 변환
        "user": user.username,
    }
]
```

### After (자동 변환)
```python
# response_model을 사용하면 자동 변환됨
@router.get("/users", response_model=List[User])
async def get_users():
    users = await user_service.get_users()
    return users  # datetime 필드가 자동으로 KST로 변환됨
```

## 변환 규칙

- **Input**: UTC datetime (DB 저장 시간)
- **Output**: KST ISO 형식 문자열 (`YYYY-MM-DDTHH:MM:SS+09:00`)
- **변환**: UTC + 9시간
- **Null 처리**: None → None

## 주의사항

1. **새로운 스키마 작성 시**: `TimezoneBaseModel`을 상속받거나, Base 스키마를 상속받으세요
2. **수동 변환이 필요한 경우**: `format_datetime_for_frontend()` 사용 (dict 응답 등)
3. **response_model 없는 경우**: 수동으로 `format_datetime_for_frontend()` 호출 필요

## 관련 파일

- `app/schemas/schemas.py` - 스키마 정의
- `app/utils/timezone.py` - 타임존 변환 유틸리티

