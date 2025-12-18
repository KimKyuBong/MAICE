#!/usr/bin/env python3
"""
MAICE 시스템 고급 테스터 실행 파일
기본값: 5개 질문씩 진행
"""

import asyncio
import logging
from advanced_tester import AdvancedTester

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def main():
    """메인 실행 함수"""
    try:
        # 테스터 인스턴스 생성
        tester = AdvancedTester()
        
        # 연결
        await tester.connect()
        
        # 기본값: 5개 질문씩 진행
        num_questions = 5
        test_mode = "combined"  # 원문 + 페르소나
        
        logging.info(f"🎯 테스트 시작 - 질문 수: {num_questions}, 모드: {test_mode}")
        
        # 테스트 실행
        results = await tester.run_test(
            num_questions=num_questions,
            test_mode=test_mode
        )
        
        # 결과 출력
        logging.info(f"✅ 테스트 완료 - 총 결과: {len(results)}개")
        
        # 성공/실패 통계
        success_count = sum(1 for r in results if r and r.get('completed', False))
        logging.info(f"📊 성공: {success_count}/{len(results)}")
        
    except KeyboardInterrupt:
        logging.info("⚠️ 사용자에 의해 중단됨")
    except Exception as e:
        logging.error(f"❌ 테스트 실행 중 오류: {e}")
    finally:
        # 연결 해제
        if 'tester' in locals():
            await tester.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
