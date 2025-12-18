#!/usr/bin/env python3
"""
MCP 서버 스트림 엔드포인트 디버깅
실제로 어떤 타입의 메시지들이 오는지 확인
"""

import asyncio
import httpx
import json
import time
import logging
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MCP_SERVER_URL = "http://192.168.1.105:5555"

async def debug_mcp_stream():
    """MCP 서버 스트림 디버깅"""
    question = "시그마 k 공식 알려줘"
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as session:
        logger.info(f"🚀 MCP 스트림 디버깅 시작: {question}")
        
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
            logger.error(f"❌ 요청 실패: {response.status_code}")
            return
        
        logger.info("✅ 스트림 연결 성공, 메시지 분석 시작...")
        
        # SSE 스트리밍 응답 처리
        chunks = []
        message_types = set()
        
        try:
            async for line in response.aiter_lines():
                if line:
                    line_str = line.strip()
                    logger.info(f"📥 원본 라인: {line_str}")
                    
                    if line_str.startswith('data: '):
                        try:
                            data = json.loads(line_str[6:])
                            chunks.append(data)
                            
                            # 메시지 타입 수집
                            msg_type = data.get("type", "unknown")
                            message_types.add(msg_type)
                            
                            logger.info(f"📦 청크 {len(chunks)}: type={msg_type}, content={str(data.get('text', data.get('content', '')))[:50]}...")
                            
                            # 완료 신호 확인
                            if msg_type in ["done", "complete", "finished", "end"]:
                                logger.info(f"✅ 완료 신호 발견: {msg_type}")
                                break
                                
                        except json.JSONDecodeError as e:
                            logger.warning(f"⚠️ JSON 파싱 실패: {e}, 라인: {line_str}")
                            continue
                    else:
                        logger.info(f"📄 일반 라인: {line_str}")
        
        except Exception as e:
            logger.error(f"❌ 스트림 처리 오류: {e}")
        
        logger.info(f"\n📊 분석 결과:")
        logger.info(f"📈 총 청크 수: {len(chunks)}")
        logger.info(f"📋 발견된 메시지 타입들: {sorted(message_types)}")
        
        # 마지막 몇 개 청크 확인
        logger.info(f"\n🔍 마지막 5개 청크:")
        for i, chunk in enumerate(chunks[-5:]):
            logger.info(f"  {len(chunks)-5+i+1}. type={chunk.get('type')}, content={str(chunk.get('text', chunk.get('content', '')))[:30]}...")

if __name__ == "__main__":
    asyncio.run(debug_mcp_stream())
