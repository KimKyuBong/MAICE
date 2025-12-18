#!/usr/bin/env python3
"""
MAICE 명료화 시뮬레이션 테스트
명료화 과정을 포함한 질문 처리 테스트
"""

import asyncio
import aiohttp
import time
import json
import logging
from typing import List, Dict, Any
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 테스트 설정
BASE_URL = "http://localhost:8000"
TEST_ENDPOINT = "/api/student/chat-test"
TIMEOUT = 300  # 5분 타임아웃

# 명료화 테스트 질문 (5개만)
TEST_QUESTIONS = [
    "삼각함수의 그래프를 그리는 방법을 알려줘",
    "적분의 기본정리를 증명해줘", 
    "행렬의 곱셈을 계산하는 방법을 알려줘",
    "미분의 정의 알려줘",
    "등차수열의 정의 알려줘"
]

class ClarificationTester:
    """명료화 시뮬레이션 테스트 클래스"""
    
    def __init__(self):
        self.results = []
    
    async def handle_clarification_responses(self, session: aiohttp.ClientSession, clarification_questions: List[Dict], clarification_answers: List[Dict], chunks: List[Dict], user_id: int, question: str, start_time: float, current_session_id: int = None) -> Dict[str, Any]:
        """명료화 답변 처리"""
        try:
            # 명료화 질문들에 대한 답변 시뮬레이션
            for i, clar_q in enumerate(clarification_questions):
                # 간단한 답변 시뮬레이션
                if "어떤 그래프" in clar_q["message"]:
                    answer = "사인 그래프"
                elif "직관적" in clar_q["message"]:
                    answer = "직관적인 설명"
                elif "어떤 방법" in clar_q["message"]:
                    answer = "단계별로"
                else:
                    answer = "네, 알겠습니다"
                
                clarification_answers.append({
                    "question": clar_q["message"],
                    "answer": answer
                })
                
                # 명료화 답변 전송 (기존 세션 ID 유지)
                clarification_payload = {
                    "message": answer,
                    "message_type": "clarification_response",
                    "session_id": current_session_id,  # 기존 세션 ID 유지
                    "use_agents": True,
                    "conversation_history": None
                }
                
                logger.info(f"📝 명료화 답변 {i+1}: {answer}")
                
                # 명료화 답변 전송 (동일한 세션으로)
                async with session.post(
                    f"{BASE_URL}{TEST_ENDPOINT}?user_id={user_id}",
                    json=clarification_payload,
                    timeout=aiohttp.ClientTimeout(total=TIMEOUT),
                    headers={"Content-Type": "application/json"}
                ) as clar_response:
                    if clar_response.status == 200:
                        async for clar_line in clar_response.content:
                            clar_line = clar_line.decode('utf-8').strip()
                            if clar_line.startswith('data: '):
                                try:
                                    clar_data = json.loads(clar_line[6:])
                                    chunks.append(clar_data)
                                    
                                    # 최종 답변 완료 확인
                                    if clar_data.get("type") in ["answer_complete", "freepass_complete"]:
                                        duration = time.time() - start_time
                                        logger.info(f"✅ 완료: {question[:30]}... ({duration:.2f}초)")
                                        
                                        # 전체 답변 수집
                                        full_response = ""
                                        for chunk in chunks:
                                            if chunk.get("type") in ["answer_chunk", "freepass_chunk"]:
                                                chunk_content = chunk.get("content", "")
                                                if chunk_content:
                                                    full_response += chunk_content
                                        
                                        return {
                                            "question": question,
                                            "success": True,
                                            "chunks": len(chunks),
                                            "duration": duration,
                                            "clarification_questions": len(clarification_questions),
                                            "clarification_answers": clarification_answers,
                                            "full_response": full_response,
                                            "chunk_details": chunks
                                        }
                                except json.JSONDecodeError:
                                    continue
            
            # 명료화 완료 후 타임아웃
            duration = time.time() - start_time
            logger.warning(f"⏰ 명료화 후 타임아웃: {duration:.2f}초")
            
            return {
                "question": question,
                "success": False,
                "error": "clarification_timeout",
                "duration": duration,
                "chunks": len(chunks),
                "clarification_questions": len(clarification_questions),
                "clarification_answers": clarification_answers,
                "partial_response": "",
                "chunk_details": chunks
            }
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"💥 명료화 처리 중 예외: {str(e)}")
            return {
                "question": question,
                "success": False,
                "error": str(e),
                "duration": duration,
                "chunks": len(chunks),
                "clarification_questions": len(clarification_questions),
                "partial_response": "",
                "chunk_details": chunks
            }

    async def send_question_with_clarification(self, session: aiohttp.ClientSession, question: str, user_id: int) -> Dict[str, Any]:
        """명료화 과정을 포함한 질문 처리"""
        start_time = time.time()
        chunks = []
        clarification_answers = []
        current_session_id = None
        
        try:
            # 첫 번째 질문 전송
            payload = {
                "message": question,
                "message_type": "question",
                "use_agents": True,
                "conversation_history": None
            }
            
            logger.info(f"🚀 요청 시작: {question[:30]}... (사용자 {user_id})")
            
            async with session.post(
                f"{BASE_URL}{TEST_ENDPOINT}?user_id={user_id}",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=TIMEOUT),
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status != 200:
                    logger.error(f"❌ HTTP 오류 {response.status}: {question[:30]}...")
                    return {
                        "question": question,
                        "success": False,
                        "error": f"HTTP {response.status}",
                        "duration": time.time() - start_time
                    }
                
                clarification_questions = []
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])
                            chunks.append(data)
                            
                            # 세션 ID 추적
                            if data.get("session_id"):
                                current_session_id = data.get("session_id")
                            
                            # 명료화 질문 수집
                            if data.get("type") == "clarification_question":
                                clarification_questions.append({
                                    "message": data.get("message"),
                                    "question_index": data.get("question_index"),
                                    "total_questions": data.get("total_questions")
                                })
                                logger.info(f"❓ 명료화 질문 {data.get('question_index')}/{data.get('total_questions')}: {data.get('message')[:50]}...")
                                logger.info(f"🔍 현재 세션 ID: {current_session_id}")
                                
                                # 명료화 질문이 나오면 바로 답변 시뮬레이션 시작 (첫 번째 질문만)
                                if clarification_questions:
                                    logger.info(f"✅ 명료화 시작: 첫 번째 질문만 처리")
                                    result = await self.handle_clarification_responses(session, clarification_questions, clarification_answers, chunks, user_id, question, start_time, current_session_id)
                                    if result:
                                        return result
                            
                            # 명료화 완료 신호 (사용하지 않음 - 이미 위에서 처리됨)
                            elif data.get("type") == "clarification_complete":
                                logger.info(f"✅ 명료화 완료: {len(clarification_questions)}개 질문")
                                break
                            
                            # 일반 완료 신호 (명료화 없이 바로 답변)
                            elif data.get("type") in ["answer_complete", "freepass_complete"]:
                                duration = time.time() - start_time
                                logger.info(f"✅ 완료 (명료화 없음): {question[:30]}... ({duration:.2f}초)")
                                
                                # 전체 답변 수집
                                full_response = ""
                                for chunk in chunks:
                                    if chunk.get("type") in ["answer_chunk", "freepass_chunk"]:
                                        chunk_content = chunk.get("content", "")
                                        if chunk_content:
                                            full_response += chunk_content
                                
                                return {
                                    "question": question,
                                    "success": True,
                                    "chunks": len(chunks),
                                    "duration": duration,
                                    "clarification_questions": 0,
                                    "clarification_answers": [],
                                    "full_response": full_response,
                                    "chunk_details": chunks
                                }
                                
                        except json.JSONDecodeError:
                            continue
                
                # 타임아웃으로 종료된 경우
                duration = time.time() - start_time
                logger.warning(f"⏰ 타임아웃: {duration:.2f}초")
                
                # 부분 답변 수집
                partial_response = ""
                for chunk in chunks:
                    if chunk.get("type") in ["answer_chunk", "freepass_chunk"]:
                        chunk_content = chunk.get("content", "")
                        if chunk_content:
                            partial_response += chunk_content
                
                return {
                    "question": question,
                    "success": False,
                    "error": "timeout",
                    "duration": duration,
                    "chunks": len(chunks),
                    "clarification_questions": len(clarification_questions),
                    "partial_response": partial_response,
                    "chunk_details": chunks
                }
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"💥 예외 발생: {question[:30]}... - {str(e)}")
            return {
                "question": question,
                "success": False,
                "error": str(e),
                "duration": duration,
                "chunks": len(chunks) if 'chunks' in locals() else 0,
                "clarification_questions": 0,
                "partial_response": "",
                "chunk_details": chunks if 'chunks' in locals() else []
            }
    
    async def test_question(self, question: str, user_id: int) -> Dict[str, Any]:
        """단일 질문 테스트"""
        async with aiohttp.ClientSession() as session:
            result = await self.send_question_with_clarification(session, question, user_id)
            result["user_id"] = user_id
            return result
    
    async def run_clarification_test(self):
        """명료화 시뮬레이션 테스트 실행"""
        logger.info("🎯 MAICE 명료화 시뮬레이션 테스트 시작")
        logger.info(f"📝 테스트 질문 수: {len(TEST_QUESTIONS)}")
        
        # 테스트 사용자 ID (에이전트 모드와 프리패스 모드)
        user_ids = [18, 28, 19, 29, 20]  # 5개 질문에 대응
        
        tasks = []
        for i, question in enumerate(TEST_QUESTIONS):
            user_id = user_ids[i]
            logger.info(f"📋 질문 {i+1}: {question[:50]}... (사용자 {user_id})")
            task = self.test_question(question, user_id)
            tasks.append(task)
        
        logger.info("⚡ 5개 질문 동시 시작")
        start_time = time.time()
        
        # 모든 요청 동시 실행
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        self.results = results
        
        # 결과 분석
        self.analyze_results(end_time - start_time)
    
    def analyze_results(self, total_time):
        """테스트 결과 분석"""
        successful = [r for r in self.results if isinstance(r, dict) and r.get("success", False)]
        failed = [r for r in self.results if isinstance(r, dict) and not r.get("success", False)]
        exceptions = [r for r in self.results if not isinstance(r, dict)]
        
        logger.info("📊 테스트 결과 분석")
        logger.info(f"✅ 성공: {len(successful)}개")
        logger.info(f"❌ 실패: {len(failed)}개")
        logger.info(f"💥 예외: {len(exceptions)}개")
        logger.info(f"⏱️ 총 소요시간: {total_time:.2f}초")
        
        if successful:
            avg_response_time = sum(r["duration"] for r in successful) / len(successful)
            logger.info(f"📈 평균 응답시간: {avg_response_time:.2f}초")
            
            # 명료화 통계
            with_clarification = [r for r in successful if r.get("clarification_questions", 0) > 0]
            without_clarification = [r for r in successful if r.get("clarification_questions", 0) == 0]
            
            logger.info(f"📊 명료화 통계:")
            logger.info(f"   - 명료화 있음: {len(with_clarification)}개")
            logger.info(f"   - 명료화 없음: {len(without_clarification)}개")
        
        logger.info("\n📋 상세 결과:")
        for i, result in enumerate(self.results):
            if isinstance(result, dict):
                status = "✅" if result.get("success", False) else "❌"
                duration = result.get("duration", 0)
                question = result.get("question", "알 수 없음")
                clar_questions = result.get("clarification_questions", 0)
                clar_answers = result.get("clarification_answers", [])
                
                clar_info = f" (명료화: {clar_questions}개)" if clar_questions > 0 else ""
                logger.info(f"{status} 질문 {i+1}: {question[:50]}... ({duration:.2f}초){clar_info}")
                
                # 명료화 과정 상세 로그
                if clar_answers:
                    for j, clar in enumerate(clar_answers):
                        logger.info(f"  ❓ 명료화 질문 {j+1}: {clar['question'][:50]}...")
                        logger.info(f"  📝 명료화 답변 {j+1}: {clar['answer']}")
            else:
                logger.info(f"💥 질문 {i+1}: 예외 발생 - {str(result)}")
        
        # 결과 저장 (예외 객체를 문자열로 변환)
        serializable_results = []
        for result in self.results:
            if isinstance(result, Exception):
                serializable_results.append({
                    "error": str(result),
                    "type": "exception"
                })
            else:
                serializable_results.append(result)
        
        results_data = {
            "test_type": "clarification_simulation",
            "total_questions": len(TEST_QUESTIONS),
            "successful": len(successful),
            "failed": len(failed),
            "exceptions": len(exceptions),
            "total_time": total_time,
            "test_timestamp": datetime.now().isoformat(),
            "results": serializable_results
        }
        
        with open("clarification_test_results.json", "w", encoding="utf-8") as f:
            json.dump(results_data, f, ensure_ascii=False, indent=2)
        
        logger.info("💾 결과가 clarification_test_results.json에 저장되었습니다")

async def main():
    """메인 함수"""
    tester = ClarificationTester()
    await tester.run_clarification_test()

if __name__ == "__main__":
    asyncio.run(main())
