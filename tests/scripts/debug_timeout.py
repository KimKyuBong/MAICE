#!/usr/bin/env python3
"""
타임아웃 디버깅 스크립트
정확한 타임아웃 원인 분석
"""

import asyncio
import aiohttp
import json
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def debug_single_request():
    """단일 요청으로 타임아웃 분석"""
    logger.info("🔍 단일 요청 타임아웃 분석 시작")
    
    # aiohttp 타임아웃 설정 (120초)
    timeout = aiohttp.ClientTimeout(total=120, connect=10)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        start_time = time.time()
        
        try:
            async with session.post(
                "http://localhost:8000/api/maice/test/chat",
                json={"message": "시그마 k 공식 알려줘"}, # 타임아웃이 발생하던 질문
                headers={"Accept": "text/event-stream"}
            ) as response:
                
                logger.info(f"📡 HTTP 응답 상태: {response.status}")
                logger.info(f"📡 응답 헤더: {dict(response.headers)}")
                
                if response.status != 200:
                    logger.error(f"❌ 요청 실패: {response.status}")
                    return
                
                chunks = []
                chunk_count = 0
                is_complete = False
                
                async for line in response.content:
                    current_time = time.time() - start_time
                    
                    if line:
                        line_str = line.decode('utf-8').strip()
                        logger.info(f"📥 [{current_time:.2f}s] 라인: {line_str[:100]}...")
                        
                        if line_str.startswith('data: '):
                            try:
                                data = json.loads(line_str[6:])
                                chunks.append(data)
                                chunk_count += 1
                                
                                msg_type = data.get("type")
                                logger.info(f"📦 [{current_time:.2f}s] 청크 {chunk_count}: type={msg_type}")
                                
                                # 완료 신호 확인
                                if msg_type == "answer_complete":
                                    duration = time.time() - start_time
                                    logger.info(f"✅ [{duration:.2f}s] 완료 신호 감지!")
                                    is_complete = True
                                    break
                                    
                            except json.JSONDecodeError as e:
                                logger.warning(f"⚠️ JSON 파싱 실패: {e}")
                                continue
                
                if is_complete:
                    logger.info(f"✅ 성공: {time.time() - start_time:.2f}초, 청크: {len(chunks)}개")
                else:
                    logger.warning(f"⏰ 완료 신호 미수신: {time.time() - start_time:.2f}초, 청크: {len(chunks)}개")
        
        except asyncio.TimeoutError:
            logger.error(f"❌ aiohttp 타임아웃: {time.time() - start_time:.2f}초")
        except Exception as e:
            logger.error(f"❌ 예외 발생: {e}, 소요시간: {time.time() - start_time:.2f}초")

if __name__ == "__main__":
    asyncio.run(debug_single_request())
