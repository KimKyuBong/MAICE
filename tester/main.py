#!/usr/bin/env python3
"""
고급 테스터 메인 실행 파일 - 분리된 모듈 사용
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from tester.core.advanced_tester import AdvancedTester

# .env 파일 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('advanced_tester.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

async def main():
    """메인 함수"""
    logger = logging.getLogger(__name__)
    
    # 테스터 생성 및 실행
    tester = AdvancedTester()
    
    try:
        # 초기화
        if not await tester.initialize():
            logger.error("❌ 테스터 초기화 실패")
            return
            
        # 테스트 실행 - 기본 자동화 모드
        results = await tester.run_test(mode="combined", question_count=5)
        
        # 결과 출력
        logger.info("📊 테스트 결과:")
        logger.info(f"   모드: {results.get('mode', 'unknown')}")
        logger.info(f"   총 질문 수: {results.get('total_questions', 0)}")
        logger.info(f"   성공: {results.get('success_count', 0)}")
        logger.info(f"   실패: {results.get('failed_count', 0)}")
        
    except Exception as e:
        logger.error(f"❌ 테스트 실행 중 오류 발생: {e}")
        
    finally:
        # 정리
        await tester.cleanup()
        logger.info("✅ 테스터 정리 완료")

if __name__ == "__main__":
    asyncio.run(main())
