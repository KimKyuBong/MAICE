#!/usr/bin/env python3
"""
MAICE 시스템 병렬 처리 테스트 스크립트
동시 접속 10개로 다양한 수학 질문을 테스트
"""

import asyncio
import aiohttp
import json
import time
import uuid
from typing import List, Dict, Any
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 테스트 질문들 (20개 - 10개 프리패스, 10개 에이전트)
TEST_QUESTIONS = [
    # 프리패스 모드 질문들 (0-9)
    "등차수열의 정의 알려줘",
    "등비수열의 정의 알려줘", 
    "\\sum_{k=1}^n k 공식 알려줘",
    "\\sum_{k=1}^n k^2 공식 알려줘",
    "수열의 극한 정의 알려줘",
    "미분의 정의 알려줘",
    "정적분의 정의와 기본 이론 알려줘",
    "삼각함수 sine cosine 정의 알려줘",
    "로그함수의 정의 알려줘",
    "지수함수의 정의 알려줘",
    
    # 에이전트 모드 질문들 (10-19)
    "이차방정식의 해를 구하는 방법을 단계별로 설명해줘",
    "삼각함수의 그래프를 그리는 방법을 알려줘",
    "적분의 기본정리를 증명해줘",
    "수열의 수렴성을 판단하는 방법을 알려줘",
    "복소수의 사칙연산을 예시와 함께 설명해줘",
    "행렬의 곱셈을 계산하는 방법을 알려줘",
    "확률의 기본 개념과 조건부 확률을 설명해줘",
    "함수의 연속성을 판단하는 방법을 알려줘",
    "벡터의 내적과 외적을 계산하는 방법을 설명해줘",
    "극좌표계에서의 적분을 계산하는 방법을 알려줘"
]

class ParallelTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def send_question_stream(self, question: str, user_id: int) -> Dict[str, Any]:
        """질문 전송 및 스트리밍 응답 수신"""
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        try:
            logger.info(f"🚀 요청 시작: {question[:30]}... (사용자 {user_id})")
            async with self.session.post(
                f"{self.base_url}/api/maice/test/chat",
                json={
                    "message": question
                },
                headers={"Accept": "text/event-stream"}
            ) as response:
                
                if response.status != 200:
                    logger.error(f"❌ 요청 실패: {response.status}")
                    return {
                        "question": question,
                        "success": False,
                        "error": f"HTTP {response.status}",
                        "duration": time.time() - start_time
                    }
                
                # SSE 스트리밍 응답 처리
                chunks = []
                async for line in response.content:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            try:
                                data = json.loads(line_str[6:])
                                chunks.append(data)
                                
                                # 완료 신호 확인 (프리패스 모드와 에이전트 모드 모두 지원)
                                if data.get("type") in ["answer_complete", "freepass_complete"]:
                                    duration = time.time() - start_time
                                    logger.info(f"✅ 완료: {question[:30]}... ({duration:.2f}초)")
                                    return {
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
                logger.warning(f"⏰ 타임아웃: {duration:.2f}초")
                return {
                    "question": question,
                    "success": False,
                    "error": "timeout",
                    "chunks": len(chunks),
                    "duration": duration
                }
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ 오류: {e}")
            return {
                "question": question,
                "success": False,
                "error": str(e),
                "duration": duration
            }
    
    async def test_single_session(self, user_id: int, question: str, mode: str = "알 수 없음") -> Dict[str, Any]:
        """단일 세션 테스트"""
        # 질문 전송 및 응답 수신 (세션은 백엔드에서 자동 생성)
        result = await self.send_question_stream(question, user_id)
        result["mode"] = mode  # 모드 정보 추가
        return result
    
    async def run_parallel_test(self) -> List[Dict[str, Any]]:
        """병렬 처리 테스트 실행 - 20개 (10개 프리패스, 10개 에이전트)"""
        logger.info("🚀 병렬 처리 테스트 시작")
        logger.info(f"📝 테스트 질문 수: {len(TEST_QUESTIONS)}")
        logger.info("🎯 10개 프리패스 + 10개 에이전트 모드 동시 테스트")
        
        start_time = time.time()
        
        # 동시에 20개 세션 테스트 (실제 DB 사용자 ID 사용)
        # 로컬/테스트 DB에 존재하는 사용자 ID 예시(환경에 따라 다를 수 있음)
        db_user_ids = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 2, 3, 4, 5, 6, 7, 8, 9]  # 20개 (일부 중복 사용)
        
        tasks = []
        for i, question in enumerate(TEST_QUESTIONS):
            user_id = db_user_ids[i]
            # 0-9: 프리패스 모드로 예상
            # 10-19: 에이전트 모드로 예상
            if i < 10:
                mode = "프리패스"
            else:
                mode = "에이전트"
            
            logger.info(f"📋 질문 {i+1}: {mode} 모드 (사용자 {user_id}) - {question[:30]}...")
            task = self.test_single_session(user_id, question, mode)
            tasks.append(task)
        
        # 모든 테스트 동시 실행
        logger.info("⚡ 모든 세션 동시 시작")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_duration = time.time() - start_time
        
        # 결과 분석
        successful = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed = [r for r in results if isinstance(r, dict) and not r.get("success")]
        exceptions = [r for r in results if isinstance(r, Exception)]
        
        # 모드별 분석
        freepass_successful = [r for r in successful if r.get("mode") == "프리패스"]
        agent_successful = [r for r in successful if r.get("mode") == "에이전트"]
        
        logger.info("📊 테스트 결과 분석")
        logger.info(f"✅ 성공: {len(successful)}개")
        logger.info(f"   - 프리패스: {len(freepass_successful)}개")
        logger.info(f"   - 에이전트: {len(agent_successful)}개")
        logger.info(f"❌ 실패: {len(failed)}개")
        logger.info(f"💥 예외: {len(exceptions)}개")
        logger.info(f"⏱️ 총 소요시간: {total_duration:.2f}초")
        
        if successful:
            durations = [r["duration"] for r in successful]
            logger.info(f"📈 성공 세션 평균 응답시간: {sum(durations)/len(durations):.2f}초")
            logger.info(f"📈 최단 응답시간: {min(durations):.2f}초")
            logger.info(f"📈 최장 응답시간: {max(durations):.2f}초")
            
            if freepass_successful:
                freepass_durations = [r["duration"] for r in freepass_successful]
                logger.info(f"📈 프리패스 평균 응답시간: {sum(freepass_durations)/len(freepass_durations):.2f}초")
            
            if agent_successful:
                agent_durations = [r["duration"] for r in agent_successful]
                logger.info(f"📈 에이전트 평균 응답시간: {sum(agent_durations)/len(agent_durations):.2f}초")
        
        # 상세 결과 출력
        logger.info("\n📋 상세 결과:")
        for i, result in enumerate(results):
            if isinstance(result, dict):
                status = "✅" if result.get("success") else "❌"
                mode = result.get("mode", "알 수 없음")
                logger.info(f"{status} 질문 {i+1} ({mode}): {result.get('question', 'N/A')[:30]}... ({result.get('duration', 0):.2f}초)")
            else:
                logger.info(f"💥 예외 {i}: {result}")
        
        return results

async def main():
    """메인 실행 함수"""
    logger.info("🎯 MAICE 병렬 처리 테스트 시작")
    
    async with ParallelTester() as tester:
        results = await tester.run_parallel_test()
        
        # 결과를 JSON 파일로 저장
        with open("parallel_test_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info("💾 결과가 parallel_test_results.json에 저장되었습니다")

if __name__ == "__main__":
    asyncio.run(main())
