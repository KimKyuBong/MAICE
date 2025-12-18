#!/usr/bin/env python3
"""
단일 명료화 테스트 - 명료화 과정을 단계별로 진행
"""

import asyncio
import aiohttp
import time
import json
import logging
from typing import Dict, Any

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
USER_ID = 21

async def send_question(session: aiohttp.ClientSession, message: str, session_id: int = None) -> Dict[str, Any]:
    """질문 전송 및 응답 수신"""
    payload = {
        "message": message,
        "message_type": "question",
        "use_agents": True
    }
    
    if session_id:
        payload["session_id"] = session_id
    
    logger.info(f"🚀 질문 전송: {message[:30]}... (세션: {session_id})")
    
    async with session.post(
        f"{BASE_URL}{TEST_ENDPOINT}?user_id={USER_ID}",
        json=payload,
        timeout=aiohttp.ClientTimeout(total=TIMEOUT),
        headers={"Content-Type": "application/json"}
    ) as response:
        if response.status != 200:
            logger.error(f"❌ HTTP 오류 {response.status}")
            return {"error": f"HTTP {response.status}"}
        
        # SSE 스트림 처리
        result = {
            "session_id": None,
            "clarification_questions": [],
            "answers": [],
            "success": False
        }
        
        async for line in response.content:
            line = line.decode('utf-8').strip()
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    logger.info(f"📨 수신: {data.get('type', 'unknown')} - {str(data)[:100]}...")
                    
                    # 세션 ID 저장
                    if data.get("session_id") and not result["session_id"]:
                        result["session_id"] = data.get("session_id")
                        logger.info(f"📌 세션 ID 저장: {result['session_id']}")
                    
                    # 명료화 질문 수신
                    if data.get("type") == "clarification_question":
                        clar_question = {
                            "message": data.get("message", ""),
                            "question_index": data.get("question_index", "1"),
                            "total_questions": data.get("total_questions", "1")
                        }
                        result["clarification_questions"].append(clar_question)
                        logger.info(f"❓ 명료화 질문: {clar_question['message'][:50]}...")
                    
                    # 답변 청크 수신
                    elif data.get("type") == "streaming_chunk":
                        chunk_content = data.get("content", "")
                        if chunk_content:
                            result["answers"].append(chunk_content)
                            logger.info(f"📝 답변 청크: {chunk_content[:50]}...")
                    
                    # 완료 신호
                    elif data.get("type") in ["answer_complete", "summary_complete"]:
                        logger.info(f"✅ 완료: {data.get('type')}")
                        result["success"] = True
                        break
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ JSON 파싱 오류: {e}")
                    continue
        
        return result

async def clarification_test():
    """명료화 테스트 실행"""
    logger.info("🎯 단일 명료화 테스트 시작")
    
    async with aiohttp.ClientSession() as session:
        # 1단계: 초기 질문 전송
        logger.info("📋 1단계: 초기 질문 전송")
        result1 = await send_question(session, "이차함수 알려줘")
        
        if not result1["session_id"]:
            logger.error("❌ 세션 ID를 받지 못했습니다")
            return
        
        session_id = result1["session_id"]
        
        # 명료화 질문이 있는지 확인
        if result1["clarification_questions"]:
            clar_question = result1["clarification_questions"][0]
            logger.info(f"✅ 명료화 질문 수신: {clar_question['message']}")
            
            # 2단계: 명료화 답변 전송
            logger.info("📋 2단계: 명료화 답변 전송")
            clar_answer = "그래프에 대해서 알려주세요"
            logger.info(f"📝 명료화 답변: {clar_answer}")
            
            result2 = await send_question(session, clar_answer, session_id)
            
            if result2["success"]:
                logger.info("🎉 명료화 과정 성공!")
                
                # 최종 답변 출력
                full_answer = "".join(result2["answers"])
                logger.info(f"📄 최종 답변:\n{full_answer[:500]}...")
                
                # 결과 요약
                logger.info("📊 테스트 결과:")
                logger.info(f"   - 세션 ID: {session_id}")
                logger.info(f"   - 명료화 질문 수: {len(result1['clarification_questions'])}")
                logger.info(f"   - 답변 청크 수: {len(result2['answers'])}")
                logger.info(f"   - 성공 여부: {result2['success']}")
                
            else:
                logger.error("❌ 명료화 답변 처리 실패")
                
        else:
            logger.info("ℹ️ 명료화 질문 없이 바로 답변 생성됨")
            if result1["success"]:
                full_answer = "".join(result1["answers"])
                logger.info(f"📄 답변:\n{full_answer[:500]}...")

if __name__ == "__main__":
    asyncio.run(clarification_test())
