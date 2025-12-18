#!/usr/bin/env python3
"""
MCP 서버 30개 동시 스트림 테스트
완료 신호 감지 수정 후 실제 성능 확인
"""

import asyncio
import httpx
import json
import time
import logging
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MCP_SERVER_URL = "http://10.100.2.3:5555"

# 30개 테스트 질문들 (기존 질문들 확장)
TEST_QUESTIONS = [
    "시그마 k 공식 알려줘",
    "시그마 k제곱 공식 알려줘", 
    "적분의 정의 알려줘",
    "삼각함수의 정의 알려줘",
    "미분의 정의 알려줘",
    "로그함수의 정의 알려줘",
    "지수함수의 정의 알려줘",
    "수열의 극한 정의 알려줘",
    "함수의 극한 정의 알려줘",
    "연속성의 정의 알려줘",
    "도함수의 정의 알려줘",
    "부정적분의 정의 알려줘",
    "정적분의 정의 알려줘",
    "급수의 수렴 정의 알려줘",
    "함수의 그래프 그리는법 알려줘",
    "방정식의 해 구하는법 알려줘",
    "평면벡터 공식 알려줘",
    "공간벡터 공식 알려줘",
    "내적과 외적 계산법 알려줘",
    "행렬의 연산법 알려줘",
    "고유값과 고유벡터 알려줘",
    "편미분의 계산법 알려줘",
    "다중적분의 계산법 알려줘",
    "기하학 문제 풀이법 알려줘",
    "확률분포의 종류 알려줘",
    "회귀분석의 방법 알려줘",
    "통계적 추론 방법 알려줘",
    "수학적 귀납법 증명법 알려줘",
    "집합의 연산 법칙 알려줘",
    "조합론 문제 해결법 알려줘"
]

async def test_mcp_stream_direct(session: httpx.AsyncClient, question: str, test_id: int) -> Dict[str, Any]:
    """MCP 서버 스트림 엔드포인트 직접 테스트"""
    start_time = time.time()
    
    try:
        logger.info(f"🚀 MCP 스트림 30개 동시 테스트 {test_id} 시작: {question[:20]}...")
        
        # MCP 서버 스트림 엔드포인트 직접 호출
        mcp_url = f"{MCP_SERVER_URL}/api/chat/stream"
        request_data = {
            "message": f"System: 당신은 수학 교육 전문가입니다. 학생의 질문에 친근하고 이해하기 쉽게 답변해주세요.\n\nUser: {question}",
            "chat_hash": "maice-session"
        }
        
        response = await session.post(
            mcp_url,
            json=request_data,
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
            }
        )
        
        if response.status_code != 200:
            logger.error(f"❌ 요청 {test_id} 실패: {response.status_code}")
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
                        
                        # 완료 신호 확인 (수정된 완료 신호 감지)
                        msg_type = data.get("type")
                        if msg_type in ["done", "complete", "completed", "finished", "end", "stream_complete"]:
                            duration = time.time() - start_time
                            logger.info(f"✅ MCP 스트림 완료 {test_id}: {duration:.2f}초, {len(chunks)}개 청크")
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
        logger.warning(f"⏰ MCP 스트림 타임아웃 {test_id}: {duration:.2f}초, {len(chunks)}개 청크")
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
        logger.error(f"❌ MCP 스트림 오류 {test_id}: {e}")
        return {
            "test_id": test_id,
            "question": question,
            "success": False,
            "error": str(e),
            "duration": duration
        }

async def run_mcp_30_concurrent_tests():
    """MCP 서버 30개 동시 스트림 테스트 실행"""
    logger.info("🎯 MCP 서버 30개 동시 스트림 테스트 시작")
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as session:
        # 30개 동시 요청
        logger.info("⚡ 30개 요청 동시 시작!")
        tasks = []
        for i in range(30):
            question = TEST_QUESTIONS[i % len(TEST_QUESTIONS)]
            tasks.append(test_mcp_stream_direct(session, question, i + 1))
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # 결과 분석
        all_results = []
        for result in results:
            if isinstance(result, dict):
                all_results.append(result)
            else:
                logger.error(f"예외 발생: {result}")
        
        # 결과 출력
        logger.info("\n📊 MCP 서버 30개 동시 스트림 테스트 결과:")
        successful = [r for r in all_results if r.get("success")]
        failed = [r for r in all_results if not r.get("success")]
        
        logger.info(f"✅ 성공: {len(successful)}개")
        logger.info(f"❌ 실패: {len(failed)}개")
        logger.info(f"⏱️ 총 소요시간: {total_duration:.2f}초")
        
        if successful:
            durations = [r["duration"] for r in successful]
            logger.info(f"📈 성공 평균 응답시간: {sum(durations) / len(durations):.2f}초")
            logger.info(f"📈 최단 응답시간: {min(durations):.2f}초")
            logger.info(f"📈 최장 응답시간: {max(durations):.2f}초")
            logger.info(f"📈 성공률: {len(successful)}/30 = {len(successful)/30*100:.1f}%")
        
        # 실패한 것들 분석
        if failed:
            logger.info("\n❌ 실패한 요청들:")
            for result in failed:
                logger.info(f"  - ID {result.get('test_id')}: {result.get('duration', 0):.1f}초 - {result.get('error', '알 수 없는 오류')}")
        
        # 성공한 요청들 미리보기
        logger.info("\n✅ 성공한 요청들 샘플 (처음 5개):")
        for i, result in enumerate(successful[:5]):
            logger.info(f"📝 {i+1}. 질문: {result.get('question')[:30]}... (ID: {result.get('test_id')})")
            logger.info(f"💬 응답시간: {result.get('duration', 0):.1f}초, 청크: {result.get('chunks', 0)}개")
        
        # 결과 저장
        result_data = {
            "test_info": {
                "total_tests": 30,
                "successful": len(successful),
                "failed": len(failed),
                "success_rate": len(successful)/30*100,
                "total_duration": total_duration,
                "average_response_time": sum([r["duration"] for r in successful]) / len(successful) if successful else 0,
                "completion_signal_fix": "completed"
            },
            "results": all_results
        }
        
        with open("mcp_30_concurrent_results.json", "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2, default=str)
        logger.info("💾 결과가 mcp_30_concurrent_results.json에 저장되었습니다")
        
        return all_results

if __name__ == "__main__":
    asyncio.run(run_mcp_30_concurrent_tests())
