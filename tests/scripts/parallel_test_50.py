#!/usr/bin/env python3
"""
MAICE 시스템 50개 동시 처리 테스트
대용량 동시 요청 처리 성능 검증
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

# 테스트 질문 (명료화 시뮬레이션용 - 5개만)
TEST_QUESTIONS = [
    "삼각함수의 그래프를 그리는 방법을 알려줘",
    "적분의 기본정리를 증명해줘", 
    "행렬의 곱셈을 계산하는 방법을 알려줘",
    "미분의 정의 알려줘",
    "등차수열의 정의 알려줘"
    "통계학의 기본 개념을 알려줘",
    "회귀분석의 원리를 설명해줘",
    "가설검정의 과정을 단계별로 알려줘",
    "신뢰구간의 개념을 설명해줘",
    "이산수학의 기본 개념을 알려줘",
    "집합론의 기본 원리를 설명해줘",
    "논리학의 기본 개념을 알려줘",
    "증명 방법의 종류를 설명해줘",
    "수학적 귀납법의 원리를 알려줘",
    "함수의 극한을 계산하는 방법을 알려줘",
    "도함수의 응용을 설명해줘",
    "부정적분을 계산하는 방법을 알려줘",
    "정적분의 응용을 설명해줘",
    "급수의 수렴성을 판단하는 방법을 알려줘",
    "멱급수의 개념을 설명해줘",
    "테일러 급수의 원리를 알려줘",
    "편미분의 개념을 설명해줘",
    "중적분을 계산하는 방법을 알려줘",
    "벡터장의 개념을 알려줘",
    "곡선의 길이를 구하는 방법을 설명해줘",
    "곡면의 넓이를 구하는 방법을 알려줘",
    "체적을 구하는 방법을 설명해줘",
    "변수분리법을 이용한 미분방정식 해법을 알려줘",
    "완전미분방정식의 해법을 설명해줘"
]

class ParallelTester:
    """50개 동시 처리 테스트 클래스"""
    
    def __init__(self):
        self.results = []
        self.start_time = None
        self.end_time = None
    
    async def send_question_with_clarification(self, session: aiohttp.ClientSession, question: str, user_id: int) -> Dict[str, Any]:
        """명료화 과정을 포함한 질문 처리 - 각 명료화 질문마다 새로운 POST 요청"""
        start_time = time.time()
        all_chunks = []
        clarification_answers = []
        current_session_id = None
        max_clarifications = 5  # 무한 루프 방지
        clarification_count = 0
        
        try:
            # 첫 번째 질문 전송
            current_message = question
            current_message_type = "question"
            
            logger.info(f"🚀 요청 시작: {question[:30]}... (사용자 {user_id})")
            
            while clarification_count < max_clarifications:
                payload = {
                    "message": current_message,
                    "message_type": current_message_type,
                    "use_agents": True,
                    "conversation_history": None
                }
                
                # 세션 ID가 있으면 포함 (명료화 연속성 유지)
                if current_session_id:
                    payload["session_id"] = current_session_id
                
                async with session.post(
                    f"{BASE_URL}{TEST_ENDPOINT}?user_id={user_id}",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=TIMEOUT),
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status != 200:
                        logger.error(f"❌ HTTP 오류 {response.status}: {current_message[:30]}...")
                        return {
                            "question": question,
                            "success": False,
                            "error": f"HTTP {response.status}",
                            "duration": time.time() - start_time
                        }
                    
                    received_clarification = False
                    received_answer = False
                    
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])
                                all_chunks.append(data)
                                
                                # 세션 ID 저장
                                if data.get("session_id") and not current_session_id:
                                    current_session_id = data.get("session_id")
                                    logger.info(f"📌 세션 ID 저장: {current_session_id}")
                                
                                # 명료화 질문 수신 (스트림은 여기서 자동 종료됨)
                                if data.get("type") == "clarification_question":
                                    clarification_count += 1
                                    question_index = data.get("question_index", "1")
                                    total_questions = data.get("total_questions", "1")
                                    clar_message = data.get("message", "")
                                    
                                    logger.info(f"❓ 명료화 질문 {question_index}/{total_questions}: {clar_message[:50]}...")
                                    
                                    # 단일 테스트에서 성공한 구체적인 답변 시뮬레이션
                                    if "정의" in clar_message and "그래프" in clar_message:
                                        answer = "그래프에 대해서 알려주세요"
                                    elif "정의" in clar_message:
                                        answer = "정의 위주로 알려주세요"
                                    elif "그래프" in clar_message or "모습" in clar_message or "성질" in clar_message:
                                        answer = "그래프에 대해서 알려주세요"
                                    elif "방법" in clar_message or "계산" in clar_message or "풀이" in clar_message:
                                        answer = "계산 방법을 알려주세요"
                                    elif "증명" in clar_message:
                                        answer = "증명 과정을 알려주세요"
                                    elif "응용" in clar_message:
                                        answer = "응용 문제를 알려주세요"
                                    elif "수준" in clar_message or "정도" in clar_message:
                                        answer = "고등학교 수준으로 알려주세요"
                                    elif "직관적" in clar_message:
                                        answer = "직관적인 설명으로 알려주세요"
                                    elif "단계별" in clar_message:
                                        answer = "단계별로 알려주세요"
                                    elif "개념" in clar_message:
                                        answer = "정의와 기본 개념을 알려주세요"
                                    elif "내용" in clar_message:
                                        answer = "핵심 내용을 알려주세요"
                                    elif "주제" in clar_message:
                                        answer = "정의와 예시를 알려주세요"
                                    else:
                                        answer = "정의 위주로 알려주세요"
                                    
                                    clarification_answers.append({
                                        "question": clar_message,
                                        "answer": answer,
                                        "index": question_index,
                                        "total": total_questions
                                    })
                                    
                                    logger.info(f"📝 명료화 답변 준비: {answer}")
                                    
                                    # 다음 루프에서 사용할 메시지 설정
                                    current_message = answer
                                    current_message_type = "question"  # 프론트엔드와 동일하게 question 타입 사용
                                    received_clarification = True
                                    logger.info(f"🔄 세션 {current_session_id} 명료화 답변 전송 준비")
                                    break  # 스트림 종료, 다음 POST 요청 준비
                                
                                # 답변 청크 수집
                                elif data.get("type") in ["answer_chunk", "freepass_chunk"]:
                                    chunk_content = data.get("content", "")
                                    if chunk_content:
                                        all_chunks.append(data)
                                
                                # 최종 답변 완료
                                elif data.get("type") in ["answer_complete", "freepass_complete"]:
                                    duration = time.time() - start_time
                                    logger.info(f"✅ 완료: {question[:30]}... ({duration:.2f}초)")
                                    
                                    # 전체 답변 수집
                                    full_response = ""
                                    for chunk in all_chunks:
                                        if chunk.get("type") in ["answer_chunk", "freepass_chunk"]:
                                            chunk_content = chunk.get("content", "")
                                            if chunk_content:
                                                full_response += chunk_content
                                    
                                    return {
                                        "question": question,
                                        "success": True,
                                        "chunks": len(all_chunks),
                                        "duration": duration,
                                        "clarification_questions": len(clarification_answers),
                                        "clarification_answers": clarification_answers,
                                        "full_response": full_response,
                                        "chunk_details": all_chunks,
                                        "session_id": current_session_id
                                    }
                                    
                            except json.JSONDecodeError:
                                continue
                
                # 명료화 질문을 받았으면 다음 루프에서 답변 전송
                if received_clarification:
                    logger.info(f"🔄 명료화 답변 전송 준비: {current_message}")
                    await asyncio.sleep(0.1)  # 짧은 대기 후 다음 요청
                    continue
                elif received_answer:
                    # 답변을 받았으면 성공적으로 완료
                    break
                else:
                    # 명료화도 답변도 없으면 타임아웃
                    logger.warning(f"⏰ 응답 없음 - 타임아웃")
                    break
            
            # 최대 명료화 횟수 초과 또는 타임아웃
            duration = time.time() - start_time
            logger.warning(f"⏰ 타임아웃 또는 최대 명료화 횟수 초과: {duration:.2f}초")
            
            # 부분 답변 수집
            partial_response = ""
            for chunk in all_chunks:
                if chunk.get("type") in ["answer_chunk", "freepass_chunk"]:
                    chunk_content = chunk.get("content", "")
                    if chunk_content:
                        partial_response += chunk_content
            
            return {
                "question": question,
                "success": False,
                "error": "timeout or max clarifications exceeded",
                "duration": duration,
                "chunks": len(all_chunks),
                "clarification_questions": len(clarification_answers),
                "clarification_answers": clarification_answers,
                "partial_response": partial_response,
                "chunk_details": all_chunks,
                "session_id": current_session_id
            }
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"💥 예외 발생: {question[:30]}... - {str(e)}")
            return {
                "question": question,
                "success": False,
                "error": str(e),
                "duration": duration,
                "chunks": len(all_chunks) if 'all_chunks' in locals() else 0,
                "clarification_questions": len(clarification_answers) if 'clarification_answers' in locals() else 0,
                "clarification_answers": clarification_answers if 'clarification_answers' in locals() else [],
                "partial_response": "",
                "chunk_details": all_chunks if 'all_chunks' in locals() else [],
                "session_id": current_session_id
            }

    async def send_question_stream(self, session: aiohttp.ClientSession, question: str, user_id: int) -> Dict[str, Any]:
        """단일 질문 스트리밍 처리"""
        start_time = time.time()
        chunks = []
        
        try:
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
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])
                            chunks.append(data)
                            
                            # 완료 신호 확인 (프리패스 모드와 에이전트 모드 모두 지원)
                            if data.get("type") in ["answer_complete", "freepass_complete"]:
                                duration = time.time() - start_time
                                logger.info(f"✅ 완료: {question[:30]}... ({duration:.2f}초)")
                                
                                # 전체 답변 원문 수집
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
                                    "first_chunk_time": chunks[0].get("timestamp") if chunks else None,
                                    "last_chunk_time": data.get("timestamp"),
                                    "full_response": full_response,
                                    "chunk_details": chunks  # 모든 청크 상세 정보
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
                "partial_response": "",
                "chunk_details": chunks if 'chunks' in locals() else []
            }
    
    async def test_single_session(self, user_id: int, question: str, mode: str) -> Dict[str, Any]:
        """단일 세션 테스트 (명료화 시뮬레이션 포함)"""
        async with aiohttp.ClientSession() as session:
            # 명료화 시뮬레이션 사용
            result = await self.send_question_with_clarification(session, question, user_id)
            result["user_id"] = user_id
            result["mode"] = mode
            return result
    
    async def run_parallel_test(self):
        """50개 동시 처리 테스트 실행"""
        logger.info("🎯 MAICE 50개 동시 처리 테스트 시작")
        logger.info("🚀 대용량 병렬 처리 테스트 시작")
        logger.info(f"📝 테스트 질문 수: {len(TEST_QUESTIONS)}")
        logger.info("🎯 50개 동시 요청 처리 성능 테스트")
        
        # 새로 생성한 테스트 계정 사용 (18-37, 총 20명)
        # 에이전트 모드: 18-27 (10명), 프리패스 모드: 28-37 (10명)
        agent_user_ids = list(range(18, 28))  # 에이전트 모드 10명
        freepass_user_ids = list(range(28, 38))  # 프리패스 모드 10명
        
        # 50개 요청을 위해 각 모드별로 25개씩 할당
        user_ids = (agent_user_ids * 3)[:25] + (freepass_user_ids * 3)[:25]
        
        # 모드 할당 (25개 프리패스, 25개 에이전트)
        modes = ["프리패스"] * 25 + ["에이전트"] * 25
        
        tasks = []
        for i, question in enumerate(TEST_QUESTIONS):
            user_id = user_ids[i]
            mode = modes[i]
            
            logger.info(f"📋 질문 {i+1}: {mode} 모드 (사용자 {user_id}) - {question[:30]}...")
            task = self.test_single_session(user_id, question, mode)
            tasks.append(task)
        
        logger.info("⚡ 50개 세션 동시 시작")
        self.start_time = time.time()
        
        # 모든 요청 동시 실행
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        self.end_time = time.time()
        self.results = results
        
        # 결과 분석
        self.analyze_results()
    
    def analyze_results(self):
        """테스트 결과 분석"""
        total_time = self.end_time - self.start_time
        
        successful = [r for r in self.results if isinstance(r, dict) and r.get("success", False)]
        failed = [r for r in self.results if isinstance(r, dict) and not r.get("success", False)]
        exceptions = [r for r in self.results if not isinstance(r, dict)]
        
        freepass_results = [r for r in successful if r.get("mode") == "프리패스"]
        agent_results = [r for r in successful if r.get("mode") == "에이전트"]
        
        logger.info("📊 테스트 결과 분석")
        logger.info(f"✅ 성공: {len(successful)}개")
        logger.info(f"   - 프리패스: {len(freepass_results)}개")
        logger.info(f"   - 에이전트: {len(agent_results)}개")
        logger.info(f"❌ 실패: {len(failed)}개")
        logger.info(f"💥 예외: {len(exceptions)}개")
        logger.info(f"⏱️ 총 소요시간: {total_time:.2f}초")
        
        if successful:
            avg_response_time = sum(r["duration"] for r in successful) / len(successful)
            min_response_time = min(r["duration"] for r in successful)
            max_response_time = max(r["duration"] for r in successful)
            
            logger.info(f"📈 성공 세션 평균 응답시간: {avg_response_time:.2f}초")
            logger.info(f"📈 최단 응답시간: {min_response_time:.2f}초")
            logger.info(f"📈 최장 응답시간: {max_response_time:.2f}초")
            
            if freepass_results:
                freepass_avg = sum(r["duration"] for r in freepass_results) / len(freepass_results)
                logger.info(f"📈 프리패스 평균 응답시간: {freepass_avg:.2f}초")
            
            if agent_results:
                agent_avg = sum(r["duration"] for r in agent_results) / len(agent_results)
                logger.info(f"📈 에이전트 평균 응답시간: {agent_avg:.2f}초")
        
        logger.info("\n📋 상세 결과:")
        for i, result in enumerate(self.results):
            if isinstance(result, dict):
                status = "✅" if result.get("success", False) else "❌"
                mode = result.get("mode", "알 수 없음")
                duration = result.get("duration", 0)
                question = result.get("question", "알 수 없음")
                clar_questions = result.get("clarification_questions", 0)
                clar_answers = result.get("clarification_answers", [])
                
                clar_info = f" (명료화: {clar_questions}개)" if clar_questions > 0 else ""
                logger.info(f"{status} 질문 {i+1} ({mode}): {question[:30]}... ({duration:.2f}초){clar_info}")
                
                # 명료화 과정 상세 로그
                if clar_answers:
                    for j, clar in enumerate(clar_answers):
                        logger.info(f"  ❓ 명료화 질문 {j+1}: {clar['question'][:50]}...")
                        logger.info(f"  📝 명료화 답변 {j+1}: {clar['answer']}")
            else:
                logger.info(f"💥 질문 {i+1}: 예외 발생 - {str(result)}")
        
        # 결과 저장 (답변 원문 포함)
        results_data = {
            "test_type": "50_concurrent_requests",
            "total_questions": len(TEST_QUESTIONS),
            "successful": len(successful),
            "failed": len(failed),
            "exceptions": len(exceptions),
            "total_time": total_time,
            "test_timestamp": datetime.now().isoformat(),
            "results": self.results
        }
        
        with open("parallel_test_50_results.json", "w", encoding="utf-8") as f:
            json.dump(results_data, f, ensure_ascii=False, indent=2)
        
        logger.info("💾 결과가 parallel_test_50_results.json에 저장되었습니다")

async def main():
    """메인 함수"""
    tester = ParallelTester()
    await tester.run_parallel_test()

if __name__ == "__main__":
    asyncio.run(main())
