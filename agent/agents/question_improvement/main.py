#!/usr/bin/env python3
"""
질문 명료화 에이전트 독립 실행기
"""

import asyncio
import logging
import signal
import sys
import os

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from agents.question_improvement.agent import QuestionImprovementAgent

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class QuestionImprovementService:
    """질문 명료화 에이전트 서비스"""
    
    def __init__(self):
        self.agent = None
        self.is_running = False
        self._shutdown_event = asyncio.Event()
        
        # 시그널 핸들러 설정
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """시그널 핸들러"""
        logger.info(f"🛑 시그널 수신: {signum}")
        self._shutdown_event.set()
    
    async def start(self):
        """서비스 시작"""
        try:
            logger.info("🚀 질문 명료화 에이전트 서비스 시작")
            
            # 에이전트 생성 및 초기화
            self.agent = QuestionImprovementAgent()
            await self.agent.initialize()
            
            self.is_running = True
            logger.info("✅ 질문 명료화 에이전트 초기화 완료")
            
            # 구독자 시작 (백그라운드)
            subscriber_task = asyncio.create_task(
                self.agent.run_subscriber(), 
                name="question_improvement_subscriber"
            )
            
            # 종료 신호 대기
            await self._shutdown_event.wait()
            
            logger.info("🛑 종료 신호 수신, 서비스 종료 시작")
            
            # 구독자 태스크 정리
            if not subscriber_task.done():
                subscriber_task.cancel()
                try:
                    await subscriber_task
                except asyncio.CancelledError:
                    logger.info("✅ 구독자 태스크 취소됨")
            
        except Exception as e:
            logger.error(f"❌ 서비스 실행 오류: {e}")
            raise
        
        finally:
            # 에이전트 정리
            if self.agent:
                await self.agent.cleanup()
            self.is_running = False
            logger.info("🛑 질문 명료화 에이전트 서비스 종료")

async def main():
    """메인 함수"""
    service = QuestionImprovementService()
    
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("🛑 키보드 인터럽트로 종료")
    except Exception as e:
        logger.error(f"❌ 메인 함수 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 키보드 인터럽트로 종료")
    except Exception as e:
        logger.error(f"❌ 메인 실행 오류: {e}")
        sys.exit(1)
