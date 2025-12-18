#!/usr/bin/env python3
"""
MCP 서버 실제 병렬 테스트 - 동시 질문 후 답변 확인
"""
import asyncio
import httpx
import json
import logging
import time
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def send_mcp_request(client: httpx.AsyncClient, question: str, test_id: int) -> Dict[str, Any]:
    """단일 MCP 요청 전송"""
    start_time = time.time()
    mcp_data = {
        "jsonrpc": "2.0",
        "id": test_id,
        "method": "tools/call",
        "params": {
            "name": "gpt5_chat",
            "arguments": {
                "message": f"User: {question}",
                "assistant_id": "142729"
            }
        }
    }
    
    try:
        logger.info(f"🚀 요청 {test_id} 시작: {question}")
        
        response = await client.post(
            "http://192.168.1.105:5555/mcp",
            json=mcp_data,
            timeout=30.0
        )
        
        duration = time.time() - start_time
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                if "error" in response_data:
                    logger.error(f"❌ 요청 {test_id} MCP 에러: {response_data['error']}")
                    return {
                        "test_id": test_id,
                        "question": question,
                        "success": False,
                        "duration": duration,
                        "error": response_data['error'].get('message', 'MCP 에러')
                    }
                else:
                    # 실제 답변 내용 추출
                    result_content = ""
                    if "result" in response_data and "content" in response_data["result"]:
                        content = response_data["result"]["content"]
                        if isinstance(content, list) and len(content) > 0 and "text" in content[0]:
                            result_content = content[0]["text"]
                        else:
                            result_content = str(content)[:100] + "..."
                    
                    logger.info(f"✅ 요청 {test_id} 성공: {duration:.2f}초")
                    if result_content:
                        logger.info(f"📝 답변 내용: {result_content[:150]}...")
                    
                    return {
                        "test_id": test_id,
                        "question": question,
                        "success": True,
                        "duration": duration,
                        "content": result_content
                    }
            except json.JSONDecodeError:
                logger.error(f"❌ 요청 {test_id} JSON 파싱 실패")
                return {
                    "test_id": test_id,
                    "question": question,
                    "success": False,
                    "duration": duration,
                    "error": "JSON 파싱 실패"
                }
        else:
            logger.error(f"❌ 요청 {test_id} HTTP 에러: {response.status_code}")
            return {
                "test_id": test_id,
                "question": question,
                "success": False,
                "duration": duration,
                "error": f"HTTP {response.status_code}"
            }
            
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"❌ 요청 {test_id} 예외: {e}")
        return {
            "test_id": test_id,
            "question": question,
            "success": False,
            "duration": duration,
            "error": str(e)
        }

async def test_mcp_parallel(num_requests=30):
    """MCP 병렬 테스트 실행"""
    test_questions = [
        "등차수열의 정의 알려줘",
        "미분의 정의 알려줘", 
        "삼각함수의 정의 알려줘",
        "적분의 정의 알려줘",
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
        "방정식의 해 구하는법 알려줘"
    ]
    
    # 질문을 반복해서 30개 생성
    questions = []
    for i in range(num_requests):
        questions.append(f"{test_questions[i % len(test_questions)]} ({i+1})")
    
    logger.info(f"🚀 MCP 병렬 테스트 시작 - {num_requests}개 질문 동시 처리")
    start_time = time.time()
    
    async with httpx.AsyncClient() as client:
        # 모든 요청을 동시에 시작
        tasks = []
        for i, question in enumerate(questions, 1):
            tasks.append(send_mcp_request(client, question, i))
        
        # 결과 수집
        logger.info("⚡ 모든 요청 동시 시작!")
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    total_duration = time.time() - start_time
    
    # 결과 분석
    successful = [r for r in results if isinstance(r, dict) and r.get("success")]
    failed = [r for r in results if isinstance(r, dict) and not r.get("success")]
    exceptions = [r for r in results if isinstance(r, Exception)]
    
    logger.info(f"\n📊 테스트 결과:")
    logger.info(f"✅ 성공: {len(successful)}개")
    logger.info(f"❌ 실패: {len(failed)}개") 
    logger.info(f"💥 예외: {len(exceptions)}개")
    logger.info(f"⏱️ 총 소요시간: {total_duration:.2f}초")
    
    if successful:
        durations = [r["duration"] for r in successful]
        logger.info(f"📈 성공 평균 응답시간: {sum(durations) / len(durations):.2f}초")
        logger.info(f"📈 최단 응답시간: {min(durations):.2f}초")
        logger.info(f"📈 최장 응답시간: {max(durations):.2f}초")
        
        logger.info(f"\n📋 성공 요청 샘플 (처음 5개):")
        for i, result in enumerate(successful[:5]):
            content = result.get("content", "")
            if content:
                logger.info(f"📝 {i+1}. 질문: {result['question']}")
                logger.info(f"💬 답변: {content[:100]}...")
                logger.info("---")
    
    # 결과를 JSON 파일로 저장
    with open("mcp_parallel_results.json", "w", encoding="utf-8") as f:
        import json
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    logger.info(f"💾 결과가 mcp_parallel_results.json에 저장되었습니다")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_mcp_parallel(30))
