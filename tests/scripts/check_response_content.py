#!/usr/bin/env python3
"""
답변 내용 확인 스크립트
실제로 돌아온 답변이 명확한 답변인지, 명료화 질문인지 확인
"""

import asyncio
import aiohttp
import json
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def check_response_content(question: str):
    """단일 질문으로 답변 내용 확인"""
    logger.info(f"🔍 답변 내용 확인: '{question}'")
    
    timeout = aiohttp.ClientTimeout(total=120)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.post(
                "http://localhost:8000/api/maice/test/chat",
                json={"message": question},
                headers={"Accept": "text/event-stream"}
            ) as response:
                
                if response.status != 200:
                    logger.error(f"❌ 요청 실패: {response.status}")
                    return
                
                chunks = []
                clarification_detected = False
                answer_complete_received = False
                
                async for line in response.content:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        
                        if line_str.startswith('data: '):
                            try:
                                data = json.loads(line_str[6:])
                                chunks.append(data)
                                
                                msg_type = data.get("type", "")
                                logger.info(f"📦 메시지 타입: {msg_type}")
                                
                                # 명료화 관련 메시지 검출
                                if msg_type in ["clarification_question", "clarification_needed", "need_clarification"]:
                                    clarification_detected = True
                                    logger.warning(f"⚠️ 명료화 질문 감지: {data.get('message', '')[:100]}...")
                                
                                # 완료 신호 감지
                                if msg_type == "answer_complete":
                                    answer_complete_received = True
                                    logger.info("✅ 답변 완료 신호 수신")
                                    break
                                
                                # answer_chunk 메시지에서 실제 답변 내용 보기
                                if msg_type == "answer_chunk":
                                    chunk_content = data.get("chunk", "")
                                    logger.info(f"📄 답변 청크: {chunk_content[:100]}...")
                                
                            except json.JSONDecodeError:
                                continue
                
                logger.info(f"\n📊 분석 결과:")
                logger.info(f"🔍 총 청크 수: {len(chunks)}")
                logger.info(f"⚠️ 명료화 질문 감지됨: {clarification_detected}")
                logger.info(f"✅ 완료 신호 수신: {answer_complete_received}")
                
                if clarification_detected:
                    logger.warning("❌ 여전히 명료화 질문이 발생했습니다.")
                elif answer_complete_received:
                    logger.info("✅ 정상적인 답변을 받았습니다.")
                else:
                    logger.warning("⚠️ 완료 신호를 받지 못했습니다.")
        
        except Exception as e:
            logger.error(f"❌ 오류 발생: {e}")

async def test_multiple_questions():
    """여러 질문으로 테스트"""
    test_questions = [
        "시그마 일차항 k 공식 알려줘",
        "시그마 k 제곱의 합 공식 알려줘", 
        "삼각함수 sine cosine 정의 알려줘"
    ]
    
    for question in test_questions:
        await check_response_content(question)
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(test_multiple_questions())
