#!/usr/bin/env python3
"""
프리패스 모드 스트림 엔드포인트 직접 테스트
MCP 직접 테스트와 MAICE 시스템의 차이점을 확인
"""

import asyncio
import httpx
import json
import time
import logging
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"

# 타임아웃이 발생했던 질문들
TIMEOUT_QUESTIONS = [
    "시그마 k 공식 알려줘",
    "시그마 k제곱 공식 알려줘", 
    "적분의 정의 알려줘",
    "삼각함수의 정의 알려줘"
]

# 성공했던 질문들
SUCCESS_QUESTIONS = [
    "등차수열의 정의 알려줘",
    "미분의 정의 알려줘",
    "로그함수의 정의 알려줘"
]

async def test_freepass_stream(session: httpx.AsyncClient, question: str, test_id: int) -> Dict[str, Any]:
    """프리패스 모드 스트림 테스트"""
    start_time = time.time()
    
    try:
        logger.info(f"🚀 프리패스 테스트 {test_id} 시작: {question}")
        
        # 프리패스 모드로 요청 (use_agents=False)
        response = await session.post(
            f"{BASE_URL}/api/maice/test/chat",
            json={
                "question": question,
                "message": question,  # ChatRequest는 message 필드가 필수
                "use_agents": False,  # 프리패스 모드
                "conversation_history": [],
                "session_id": None
            },
            headers={"Accept": "text/event-stream"}
        )
        
        if response.status_code != 200:
            logger.error(f"❌ 요청 실패: {response.status_code}")
            return {
                "test_id": test_id,
                "question": question,
                "success": False,
                "error": f"HTTP {response.status_code}",
                "duration": time.time() - start_time
            }
        
        # SSE 스트리밍 응답 처리
        chunks = []
        async for line in response.aiter_lines():
            if line:
                line_str = line.strip()
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])
                        chunks.append(data)
                        
                        # 완료 신호 확인
                        if data.get("type") == "answer_complete":
                            duration = time.time() - start_time
                            logger.info(f"✅ 프리패스 완료 {test_id}: {duration:.2f}초, {len(chunks)}개 청크")
                            return {
                                "test_id": test_id,
                                "question": question,
                                "success": True,
                                "chunks": len(chunks),
                                "duration": duration,
                                "first_chunk_time": chunks[0].get("timestamp") if chunks else None,
                                "last_chunk_time": data.get("timestamp")
                            }
                    except json.JSONDecodeError:
                        continue
        
        # 타임아웃 또는 완료되지 않은 경우
        duration = time.time() - start_time
        logger.warning(f"⏰ 프리패스 타임아웃 {test_id}: {duration:.2f}초, {len(chunks)}개 청크")
        return {
            "test_id": test_id,
            "question": question,
            "success": False,
            "error": "timeout",
            "chunks": len(chunks),
            "duration": duration
        }
            
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"❌ 프리패스 오류 {test_id}: {e}")
        return {
            "test_id": test_id,
            "question": question,
            "success": False,
            "error": str(e),
            "duration": duration
        }

async def run_freepass_tests():
    """프리패스 모드 테스트 실행"""
    logger.info("🎯 프리패스 모드 스트림 테스트 시작")
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as session:
        # 타임아웃 질문들 테스트
        logger.info("\n🔍 타임아웃 질문들 프리패스 테스트:")
        timeout_tasks = []
        for i, question in enumerate(TIMEOUT_QUESTIONS):
            timeout_tasks.append(test_freepass_stream(session, question, i + 1))
        
        timeout_results = await asyncio.gather(*timeout_tasks, return_exceptions=True)
        
        # 성공 질문들 테스트
        logger.info("\n✅ 성공 질문들 프리패스 테스트:")
        success_tasks = []
        for i, question in enumerate(SUCCESS_QUESTIONS):
            success_tasks.append(test_freepass_stream(session, question, i + 10))
        
        success_results = await asyncio.gather(*success_tasks, return_exceptions=True)
        
        # 결과 분석
        all_results = []
        for result in timeout_results + success_results:
            if isinstance(result, dict):
                all_results.append(result)
            else:
                logger.error(f"예외 발생: {result}")
        
        # 결과 출력
        logger.info("\n📊 프리패스 테스트 결과:")
        successful = [r for r in all_results if r.get("success")]
        failed = [r for r in all_results if not r.get("success")]
        
        logger.info(f"✅ 성공: {len(successful)}개")
        logger.info(f"❌ 실패: {len(failed)}개")
        
        if successful:
            durations = [r["duration"] for r in successful]
            logger.info(f"📈 성공 평균 응답시간: {sum(durations) / len(durations):.2f}초")
            logger.info(f"📈 최단 응답시간: {min(durations):.2f}초")
            logger.info(f"📈 최장 응답시간: {max(durations):.2f}초")
        
        logger.info("\n📋 상세 결과:")
        for result in all_results:
            status = "✅" if result.get("success") else "❌"
            logger.info(f"{status} 테스트 {result.get('test_id')}: {result.get('question')[:30]}... ({result.get('duration', 0):.1f}초, {result.get('chunks', 0)}개 청크)")
            if not result.get("success"):
                logger.info(f"   오류: {result.get('error')}")
        
        # 결과 저장
        with open("freepass_test_results.json", "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
        logger.info("💾 결과가 freepass_test_results.json에 저장되었습니다")

if __name__ == "__main__":
    asyncio.run(run_freepass_tests())
