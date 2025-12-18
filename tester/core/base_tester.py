"""
기본 테스터 클래스 - 공통 기능들을 제공
"""

import asyncio
import json
import logging
import random
from datetime import datetime
from typing import Dict, Any, List, Optional
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class BaseTester:
    """테스터의 기본 클래스"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.is_connected = False
        
    async def connect(self) -> bool:
        """Redis에 연결"""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            self.is_connected = True
            logger.info("✅ Redis 연결 완료")
            return True
        except Exception as e:
            logger.error(f"❌ Redis 연결 실패: {e}")
            return False
            
    async def disconnect(self):
        """Redis 연결 해제"""
        try:
            if self.pubsub:
                await self.pubsub.close()
            if self.redis_client:
                await self.redis_client.close()
            self.is_connected = False
            logger.info("✅ Redis 연결 해제 완료")
        except Exception as e:
            logger.error(f"❌ Redis 연결 해제 실패: {e}")
            
    async def publish_event(self, channel: str, data: Dict[str, Any]) -> bool:
        """이벤트 발행"""
        if not self.is_connected:
            logger.error("❌ Redis에 연결되지 않음")
            return False
            
        try:
            await self.redis_client.publish(channel, json.dumps(data, ensure_ascii=False))
            logger.info(f"📤 이벤트 발행 완료: {channel}")
            return True
        except Exception as e:
            logger.error(f"❌ 이벤트 발행 실패: {e}")
            return False
            
    async def subscribe_channel(self, channel: str) -> bool:
        """채널 구독"""
        if not self.is_connected:
            logger.error("❌ Redis에 연결되지 않음")
            return False
            
        try:
            self.pubsub = self.redis_client.pubsub()
            await self.pubsub.subscribe(channel)
            logger.info(f"📡 채널 구독 완료: {channel}")
            return True
        except Exception as e:
            logger.error(f"❌ 채널 구독 실패: {e}")
            return False
            
    async def get_message(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """메시지 수신"""
        if not self.pubsub:
            return None
            
        try:
            message = await self.pubsub.get_message(timeout=timeout)
            if message and message['type'] == 'message':
                data = json.loads(message['data'])
                return {
                    'channel': message['channel'].decode(),
                    'data': data,
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"❌ 메시지 수신 실패: {e}")
            
        return None
        
    def generate_session_id(self) -> str:
        """세션 ID 생성 (데이터베이스 호환)"""
        # 현재 시간을 초 단위로 사용하고, 작은 랜덤 값 추가
        timestamp = int(datetime.now().timestamp())
        random_suffix = random.randint(1000, 9999)
        return f"test_{timestamp}_{random_suffix}"
        
    async def wait_for_event(self, expected_channel: str, timeout: float = 30.0) -> Optional[Dict[str, Any]]:
        """특정 이벤트 대기"""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            message = await self.get_message(timeout=1.0)
            if message and message['channel'] == expected_channel:
                return message
                
        logger.warning(f"⚠️ 이벤트 대기 시간 초과: {expected_channel}")
        return None
        
    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """테스트 결과 로깅"""
        status = "✅ 성공" if success else "❌ 실패"
        logger.info(f"{status} - {test_name}: {details}")
        
    async def cleanup(self):
        """리소스 정리"""
        await self.disconnect()
