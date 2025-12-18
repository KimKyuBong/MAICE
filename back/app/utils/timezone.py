"""
타임존 변환 유틸리티
UTC 시간을 KST(한국 표준시)로 변환하는 함수들
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Union
import pytz

# 한국 표준시 타임존
KST = pytz.timezone('Asia/Seoul')
UTC = pytz.timezone('UTC')

def utc_to_kst(utc_dt: Optional[datetime]) -> Optional[str]:
    """
    UTC datetime을 KST 문자열로 변환
    
    Args:
        utc_dt: UTC 시간의 datetime 객체
        
    Returns:
        KST 시간의 ISO 형식 문자열 (YYYY-MM-DDTHH:MM:SS+09:00)
        None이 입력되면 None 반환
    """
    if utc_dt is None:
        return None
    
    try:
        # UTC 시간이라고 명시
        if utc_dt.tzinfo is None:
            utc_dt = UTC.localize(utc_dt)
        elif utc_dt.tzinfo != UTC:
            utc_dt = utc_dt.astimezone(UTC)
        
        # KST로 변환
        kst_dt = utc_dt.astimezone(KST)
        
        # ISO 형식으로 반환
        return kst_dt.isoformat()
        
    except Exception as e:
        # 오류 발생 시 원본 시간의 ISO 형식 반환
        return utc_dt.isoformat() if utc_dt else None

def utc_to_kst_simple(utc_dt: Optional[datetime]) -> Optional[str]:
    """
    UTC datetime을 KST 문자열로 변환 (간단한 버전)
    pytz 없이 +9시간만 추가
    
    Args:
        utc_dt: UTC 시간의 datetime 객체
        
    Returns:
        KST 시간의 ISO 형식 문자열
    """
    if utc_dt is None:
        return None
    
    try:
        # UTC 시간에 9시간 추가 (KST = UTC + 9)
        kst_dt = utc_dt + timedelta(hours=9)
        return kst_dt.isoformat()
        
    except Exception as e:
        return utc_dt.isoformat() if utc_dt else None

def format_datetime_for_frontend(utc_dt: Optional[datetime]) -> Optional[str]:
    """
    프론트엔드에서 사용할 수 있는 형식으로 datetime 변환
    
    Args:
        utc_dt: UTC 시간의 datetime 객체
        
    Returns:
        KST 시간의 사용자 친화적 문자열 형식
        예: "2024-01-15 14:30:25"
    """
    if utc_dt is None:
        return None
    
    try:
        # UTC에서 KST로 변환
        kst_dt = utc_dt + timedelta(hours=9)
        
        # 사용자 친화적 형식으로 포맷
        return kst_dt.strftime("%Y-%m-%d %H:%M:%S")
        
    except Exception as e:
        return utc_dt.strftime("%Y-%m-%d %H:%M:%S") if utc_dt else None

def get_current_kst() -> datetime:
    """
    현재 KST 시간을 반환
    
    Returns:
        현재 KST 시간의 datetime 객체
    """
    try:
        utc_now = datetime.utcnow()
        return utc_now + timedelta(hours=9)
    except Exception:
        return datetime.now()

def kst_to_utc(kst_dt: datetime) -> datetime:
    """
    KST datetime을 UTC로 변환
    
    Args:
        kst_dt: KST 시간의 datetime 객체
        
    Returns:
        UTC 시간의 datetime 객체
    """
    try:
        return kst_dt - timedelta(hours=9)
    except Exception:
        return kst_dt
