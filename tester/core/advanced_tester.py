#!/usr/bin/env python3
"""
고급 테스터 클래스 - 분리된 모듈들을 사용하여 테스트 실행
"""

import asyncio
import json
import logging
import random
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor

import redis.asyncio as redis
import aiohttp
from openai import AsyncOpenAI

from tester.core.base_tester import BaseTester
from tester.handlers.message_handler import MessageHandler
from tester.handlers.clarification_handler import ClarificationHandler
from tester.personas.persona_manager import PersonaManager
from tester.utils.question_generator import QuestionGenerator
from tester.utils.data_loader import load_questions_from_dataset, load_answers_from_dataset

logger = logging.getLogger(__name__)

# Redis 채널 상수
USER_QUESTION = "user.question"
USER_CLARIFICATION = "user.clarification"

class AdvancedTester(BaseTester):
    """고급 테스터 - 다양한 학생 페르소나와 명료화 과정 테스트"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        super().__init__(redis_url)
        
        # 모듈 초기화
        self.persona_manager = PersonaManager()
        self.question_generator = QuestionGenerator()
        self.message_handler: Optional[MessageHandler] = None
        self.clarification_handler: Optional[ClarificationHandler] = None
        
        # 테스트 상태
        self.test_sessions: Dict[str, Dict[str, Any]] = {}
        self.current_session_id: Optional[str] = None
        self.test_mode = "combined"
        self.num_questions = 5
        
    async def initialize(self) -> bool:
        """테스터 초기화 - 현재 백엔드 API 구조에 맞춤"""
        try:
            logger.info("🚀 AdvancedTester 초기화 시작...")
            
            # 현재 백엔드 API 설정
            self.api_base_url = "http://localhost:8000"
            self.api_endpoints = {
                "login": "/api/auth/login",
                "chat": "/api/student/maice/chat",
                "sessions": "/api/student/maice/sessions", 
                "health": "/health"
            }
            
            # HTTP 클라이언트 초기화
            import aiohttp
            self.http_session = aiohttp.ClientSession()
            
            # 테스트 사용자 로그인
            await self._authenticate_test_user()
            
            # Redis 연결 (현재 백엔드와 동일한 방식)
            self.redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
            await self.redis_client.ping()
            logger.info("✅ Redis 연결 성공")
            
            # MessageHandler 초기화 (현재 백엔드 메시지 형식에 맞춤)
            self.message_handler = MessageHandler(self.redis_client)
            logger.info("✅ MessageHandler 초기화 완료")
            
            # MessageHandler 시작 (백그라운드에서 단일 구독자로 작동)
            asyncio.create_task(self.message_handler.start_listening())
            logger.info("✅ MessageHandler 백그라운드 시작 완료")
            
            # 페르소나 및 명료화 핸들러 초기화
            self.persona_manager = PersonaManager()
            self.clarification_handler = ClarificationHandler(self.persona_manager)
            
            logger.info("✅ AdvancedTester 초기화 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ 초기화 실패: {e}")
            return False
    
    async def _authenticate_test_user(self):
        """테스트 사용자 인증 (Google OAuth 시뮬레이션)"""
        try:
            # 현재 백엔드는 Google OAuth만 지원하므로 테스트 토큰 사용
            # 실제 환경에서는 테스트용 JWT 토큰을 환경변수로 설정
            test_token = os.getenv("TEST_JWT_TOKEN")

            # 공개 저장소에 기본/샘플 토큰을 넣지 않기 위해,
            # 환경변수가 없으면 Authorization 헤더 없이 진행합니다.
            self.auth_headers = {"Content-Type": "application/json"}
            if test_token:
                self.auth_headers["Authorization"] = f"Bearer {test_token}"
            else:
                logger.warning("⚠️ TEST_JWT_TOKEN이 설정되지 않았습니다. Authorization 없이 테스트를 진행합니다.")
            
            # 헬스 체크로 연결 확인
            async with self.http_session.get(
                f"{self.api_base_url}{self.api_endpoints['health']}"
            ) as response:
                if response.status == 200:
                    logger.info("✅ 백엔드 서버 연결 확인")
                else:
                    logger.warning(f"⚠️ 백엔드 서버 응답: {response.status}")
                    
        except Exception as e:
            logger.error(f"❌ 테스트 사용자 인증 실패: {e}")
            # 인증 실패해도 계속 진행 (토큰 없이 테스트)
            self.auth_headers = {"Content-Type": "application/json"}
    
    async def _send_question_to_backend(self, question: str, use_agents: bool = True) -> Dict[str, Any]:
        """현재 백엔드 API로 질문 전송"""
        try:
            payload = {
                "question": question,
                "use_agents": use_agents,
                "session_id": None,  # 새 세션 생성
                "request_id": str(uuid.uuid4())
            }
            
            async with self.http_session.post(
                f"{self.api_base_url}{self.api_endpoints['chat']}",
                json=payload,
                headers=self.auth_headers
            ) as response:
                if response.status == 200:
                    # SSE 스트림 처리
                    result_data = {"chunks": [], "complete": False}
                    
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])  # 'data: ' 제거
                                result_data["chunks"].append(data)
                                
                                if data.get("type") == "answer_complete":
                                    result_data["complete"] = True
                                    result_data["session_id"] = data.get("session_id")
                                    result_data["answer"] = data.get("answer", "")
                                    
                            except json.JSONDecodeError:
                                continue
                    
                    return {
                        "success": True,
                        "data": result_data
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: {error_text}"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def run_test(self, mode: str = "combined", question_count: int = 5) -> Dict[str, Any]:
        """테스트 실행"""
        try:
            logger.info(f"🎯 테스트 시작 - 모드: {mode}, 질문 수: {question_count}")
            
            if mode == "combined":
                # 원문 질문 준비
                original_questions = self._prepare_original_questions()
                
                # 페르소나 기반 질문 준비
                persona_questions = self._prepare_persona_questions(question_count)
                
                # 병렬 처리로 실행
                return await self._run_combined_test(original_questions, persona_questions)
                
            elif mode == "original":
                return await self._run_original_questions_test()
                
            elif mode == "persona":
                return await self._run_persona_questions_test(question_count)
                
            elif mode == "interactive":
                return await self._run_interactive_test(question_count)
                
            else:
                raise ValueError(f"지원하지 않는 테스트 모드: {mode}")
                
        except Exception as e:
            logger.error(f"❌ 테스트 실행 실패: {e}")
            return {"error": str(e)}
    
    def _prepare_original_questions(self) -> List[Dict[str, Any]]:
        """원문 질문 준비"""
        questions = []
        
        # 실제 질문 데이터 로드
        try:
            from tester.utils.data_loader import load_questions_from_dataset
            real_questions = load_questions_from_dataset()
            if real_questions:
                for q in real_questions[:2]:  # 최대 2개
                    questions.append({
                        'question': q,
                        'description': '실제 학생 질문',
                        'persona': None
                    })
                    logger.info(f"📚 실제 학생 질문 로드: {q[:50]}...")
        except Exception as e:
            logger.warning(f"⚠️ 실제 학생 질문 데이터를 찾을 수 없습니다.")
            
        # 기본 질문 추가
        default_questions = [
            "등차수열의 일반항을 구하는 방법이 뭔가요?",
            "등비수열의 합을 구하는 공식이 뭔가요?"
        ]
        
        for q in default_questions:
            questions.append({
                'question': q,
                'description': '원문 질문',
                'persona': None
            })
            
        return questions
    
    def _prepare_persona_questions(self, count: int) -> List[Dict[str, Any]]:
        """페르소나 기반 질문 준비"""
        questions = []
        
        logger.info(f"🎭 {count}개 페르소나 기반 질문 준비 중...")
        
        for i in range(count):
            try:
                # 페르소나와 수학 주제 조합
                combination = self.persona_manager.get_persona_combination()
                persona = combination['persona']
                topic = combination['topic']
                difficulty = combination['difficulty']
                
                logger.info(f"   🎭 페르소나 {i+1}: {persona['name']} - {topic} ({difficulty})")
                
                # 질문 생성
                question = self.question_generator.generate_question(topic, difficulty)
                
                # 페르소나 스타일 적용
                styled_question = self.persona_manager.apply_persona_style(question, persona)
                
                question_data = {
                    'question': styled_question,
                    'description': f"{persona['name']} - {topic} ({difficulty})",
                    'persona': persona
                }
                
                questions.append(question_data)
                logger.info(f"   📝 질문 생성 완료: {styled_question[:50]}...")
                
            except Exception as e:
                logger.error(f"❌ 페르소나 질문 {i+1} 생성 실패: {e}")
                # 기본 질문으로 대체
                default_question = {
                    'question': f"수학 질문 {i+1}",
                    'description': f"기본 질문 {i+1}",
                    'persona': None
                }
                questions.append(default_question)
                
        logger.info(f"✅ {len(questions)}개 페르소나 질문 준비 완료")
        return questions
        
    async def _run_combined_test(self, questions: List[Dict[str, Any]], persona_questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """종합 테스트 실행 (원문 + 페르소나) - 병렬 처리"""
        logger.info("🔄 종합 테스트 시작 (원문 + 페르소나)...")
        
        all_questions = questions + persona_questions
        logger.info(f"📚 총 {len(all_questions)}개 질문 병렬 처리 시작")
        
        # 모든 질문을 병렬로 처리
        tasks = []
        for question_data in all_questions:
            task = asyncio.create_task(
                self._test_single_question(
                    question_data['question'], 
                    question_data.get('persona', None)
                )
            )
            tasks.append(task)
        
        # 모든 질문이 완료될 때까지 대기
        logger.info(f"🚀 {len(tasks)}개 질문 동시 실행 중...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 집계
        success_count = 0
        failed_count = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ 질문 {i+1} 처리 실패: {result}")
                failed_count += 1
            elif isinstance(result, dict) and result.get('status') == 'answer_completed':
                success_count += 1
            else:
                failed_count += 1
                
        logger.info(f"📊 병렬 처리 완료: 성공 {success_count}개, 실패 {failed_count}개")
        
        return {
            "mode": "combined_parallel",
            "total_questions": len(all_questions),
            "success_count": success_count,
            "failed_count": failed_count,
            "results": results
        }
        
    async def _run_original_questions_test(self) -> Dict[str, Any]:
        """원문 질문 테스트 실행"""
        logger.info("📚 실제 학생 질문 테스트...")
        
        # 실제 질문 데이터 로드
        try:
            from tester.utils.data_loader import load_questions_from_dataset
            questions = load_questions_from_dataset()
            if questions:
                for q in questions[:2]:  # 최대 2개
                    questions.append({
                        'question': q,
                        'description': '실제 학생 질문',
                        'persona': None
                    })
                    logger.info(f"📚 실제 학생 질문 로드: {q[:50]}...")
        except Exception as e:
            logger.warning(f"⚠️ 실제 학생 질문 데이터를 찾을 수 없습니다.")
            
        # 기본 질문 추가
        default_questions = [
            "등차수열의 일반항을 구하는 방법이 뭔가요?",
            "등비수열의 합을 구하는 공식이 뭔가요?"
        ]
        
        for q in default_questions:
            questions.append({
                'question': q,
                'description': '원문 질문',
                'persona': None
            })
            
        return questions
        
    async def _run_persona_questions_test(self, num_questions: int) -> Dict[str, Any]:
        """페르소나 기반 질문 테스트 실행"""
        logger.info("🎭 페르소나 기반 질문 테스트...")
        
        # 페르소나별 질문 생성
        results = []
        for i in range(3):  # 3개 질문
            # 페르소나와 수학 주제 조합
            combination = self.persona_manager.get_persona_combination()
            persona = combination['persona']
            topic = combination['topic']
            difficulty = combination['difficulty']
            
            # 질문 생성
            question = self.question_generator.generate_question(topic, difficulty)
            
            # 페르소나 스타일 적용
            styled_question = self.persona_manager.apply_persona_style(question, persona)
            
            # 테스트 실행
            result = await self._test_single_question(
                styled_question, 
                persona
            )
            results.append(result)
            
        return {
            "mode": "persona",
            "questions": results,
            "success_count": len([r for r in results if r.get("status") == "answer_completed"]),
            "failure_count": len([r for r in results if r.get("status") != "answer_completed"])
        }
        
    async def _test_single_question(self, question: str, persona: Dict[str, Any]) -> Dict[str, Any]:
        """단일 질문 테스트 (병렬 처리 지원)"""
        try:
            # 현재 페르소나 설정
            if not persona:
                # 기본 페르소나 가드
                persona = {"name": "default", "style": "neutral"}
            self.current_persona = persona
            logger.info(f"🎭 페르소나 설정: {persona.get('name', 'Unknown')}")
            
            # 요청 ID 및 세션 ID 생성
            request_id = f"test_{int(datetime.now().timestamp() * 1000000)}_{random.randint(100000, 999999)}"
            session_id = f"session_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}"
            
            logger.info(f"📝 질문 테스트 시작:")
            logger.info(f"   질문: {question}")
            logger.info(f"   요청 ID: {request_id}")
            logger.info(f"   세션 ID: {session_id}")
            
            # 질문 데이터 준비
            question_data = {
                "request_id": request_id,
                "session_id": session_id,
                "question": question,
                "context": "",
                "timestamp": datetime.now().isoformat()
            }
            
            # 질문 발행 (MessageHandler를 통한 단일 구독자 방식)
            json_data = json.dumps(question_data, ensure_ascii=False)
            logger.info(f"📤 Redis로 전송할 데이터: {json_data}")
            result = await self.redis_client.publish(USER_QUESTION, json_data)
            logger.info(f"📤 Redis 발행 결과: {result}")
            
            if result > 0:
                logger.info(f"✅ 질문 전송 완료: {question}")
                logger.info(f"   요청 ID: {request_id}")
                logger.info(f"   채널: {USER_QUESTION}")
                
                # MessageHandler를 통해 응답 대기 (병렬 처리 지원)
                response = await self._wait_for_complete_response_single(request_id, session_id)
                
                if response:
                    logger.info(f"✅ 응답 수신 완료: {request_id}")
                    return response
                else:
                    logger.warning(f"⚠️ 응답 수신 실패: {request_id}")
                    return {"status": "error", "message": "응답 수신 실패"}
            else:
                logger.error(f"❌ 질문 전송 실패: {question}")
                return {"status": "error", "message": "질문 전송 실패"}
                
        except Exception as e:
            logger.error(f"❌ 질문 테스트 중 오류: {e}")
            return {"status": "error", "message": str(e)}
            
    async def _wait_for_complete_response_single(self, request_id: str, session_id: Optional[str] = None, timeout: float = 120.0) -> Optional[Dict[str, Any]]:
        """MessageHandler를 통한 응답 대기 (단일 구독자 방식)"""
        try:
            logger.info(f"🔄 응답 대기 시작: {request_id}")
            logger.info(f"   📡 MessageHandler를 통한 응답 대기 중...")
            logger.info(f"   ⏰ 타임아웃: {timeout}초")
            
            # MessageHandler를 통해 응답 대기
            response = await self.message_handler.get_response(request_id, timeout)
            
            if response:
                logger.info(f"📨 응답 수신: {response.get('status', 'unknown')}")
                
                # 명료화가 필요한 경우 자동 처리
                if response.get('status') == 'clarification_required':
                    logger.info(f"❓ 명료화 질문 수신, 자동 응답 처리 중...")
                    return await self._handle_automated_clarification_single(response, request_id)
                
                # 답변 완료인 경우
                elif response.get('status') == 'answer_completed':
                    logger.info(f"🎉 답변 완료!")
                    return await self._handle_automated_answer_single(response)
                
                else:
                    logger.warning(f"⚠️ 예상치 못한 응답 상태: {response.get('status')}")
                    return response
            
            else:
                logger.warning(f"⏰ 타임아웃: {timeout}초 내에 응답을 받지 못했습니다.")
                return None
                
        except Exception as e:
            logger.error(f"❌ 응답 대기 중 오류: {e}")
            return None
    
    async def _handle_automated_clarification_single(self, clarification_data: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """자동화 명료화 응답 처리 (여러 단계 명료화 루프)"""
        try:
            next_data = clarification_data
            while True:
                question = next_data.get('question', '')
                field = next_data.get('field', '')
                logger.info(f"❓ 자동화 명료화 질문 수신:")
                logger.info(f"   질문: {question}")
                logger.info(f"   필드: {field}")

                # 페르소나 기반 응답 생성
                if self.current_persona:
                    user_response = self.clarification_handler.generate_clarification_response(
                        next_data, self.current_persona
                    )
                else:
                    user_response = "이 부분에 대해 더 자세히 알고 싶습니다."

                logger.info(f"💬 자동화 응답: {user_response}")

                # 명료화 응답 전송
                clarification_response = {
                    "request_id": request_id,
                    "response": user_response,
                    "field": field,
                    "timestamp": datetime.now().isoformat()
                }

                await self.redis_client.publish(USER_CLARIFICATION, json.dumps(clarification_response, ensure_ascii=False))
                logger.info(f"✅ 자동화 명료화 응답 전송 완료")

                # 다음 이벤트 대기 (다음 명료화 질문 또는 최종 답변)
                logger.info(f"⏳ 명료화 후 다음 이벤트 대기 중...")
                next_event = await self.message_handler.get_response(request_id, timeout=120.0)
                if not next_event:
                    return {"status": "timeout", "message": "명료화 후 응답 타임아웃"}

                if next_event.get('status') == 'clarification_required':
                    # 다음 명료화 라운드 진행
                    next_data = {
                        'question': next_event.get('question', ''),
                        'field': next_event.get('field', ''),
                        'request_id': request_id
                    }
                    continue

                if next_event.get('status') == 'answer_completed':
                    return await self._handle_automated_answer_single(next_event)

                # 기타 이벤트는 계속 대기
                await asyncio.sleep(0.2)

        except Exception as e:
            logger.error(f"❌ 자동화 명료화 처리 실패: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _handle_automated_answer_single(self, answer_data: Dict[str, Any]) -> Dict[str, Any]:
        """자동화 답변 처리 (단일 구독자 방식)"""
        try:
            answer = answer_data.get('answer', '')
            request_id = answer_data.get('request_id', '')
            
            logger.info(f"🎉 자동화 답변 완료!")
            logger.info(f"   요청 ID: {request_id}")
            logger.info(f"   답변 길이: {len(answer)} 문자")
            
            return {
                "status": "answer_completed",
                "request_id": request_id,
                "answer": answer,
                "answer_length": len(answer),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ 자동화 답변 처리 실패: {e}")
            return {"status": "error", "message": str(e)}
        
    async def _wait_for_complete_response(self, request_id: str, session_id: Optional[str] = None, timeout: float = 60.0) -> Optional[Dict[str, Any]]:
        """응답 대기 (기존 메서드 - 호환성 유지)"""
        return await self._wait_for_complete_response_single(request_id, session_id, timeout)
        
    def _is_response_for_request(self, message: Dict[str, Any], request_id: str) -> bool:
        """메시지가 특정 요청에 대한 응답인지 확인"""
        data = message.get('data', {})
        return data.get('request_id') == request_id
        
    async def _handle_clarification_question(self, data: Dict[str, Any]) -> None:
        """명료화 질문에 대한 자동 응답 처리 (기존 메서드 - 호환성 유지)"""
        try:
            request_id = data.get('request_id', '')
            field = data.get('field', '')
            question = data.get('question', '')
            
            logger.info(f"❓ 명료화 질문 처리 시작: {field} - {question[:50]}...")
            logger.info(f"   🆔 요청 ID: {request_id}")
            logger.info(f"   🏷️ 필드: {field}")
            logger.info(f"   📝 질문: {question}")
            
            # Redis 연결 상태 확인
            if not self.redis_client:
                logger.error(f"❌ Redis 클라이언트가 연결되지 않음")
                return
                
            logger.info(f"✅ Redis 연결 상태 확인 완료")
            
            # 페르소나 기반 응답 생성
            if self.current_persona:
                user_response = self.clarification_handler.generate_clarification_response(
                    data, self.current_persona
                )
            else:
                user_response = "이 부분에 대해 더 자세히 알고 싶습니다."
            
            logger.info(f"💬 생성된 응답: {user_response}")
            
            # 명료화 응답 전송
            clarification_response = {
                "request_id": request_id,
                "response": user_response,
                "field": field,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.redis_client.publish(USER_CLARIFICATION, json.dumps(clarification_response, ensure_ascii=False))
            logger.info(f"✅ 명료화 응답 전송 완료: {field}")
            
        except Exception as e:
            logger.error(f"❌ 명료화 질문 처리 실패: {e}")
            
    async def _generate_clarification_response(self, question: str, field: str) -> str:
        """명료화 질문에 대한 자연스러운 응답 생성"""
        try:
            logger.info(f"🔄 명료화 응답 생성 시작: field={field}, question={question[:50]}...")
            
            # 현재 페르소나 정보 가져오기
            current_persona = getattr(self, 'current_persona', None)
            logger.info(f"🎭 현재 페르소나: {current_persona}")
            
            # 원래 질문 정보 가져오기 (가능한 경우)
            original_question = getattr(self, 'current_question', '알 수 없음')
            logger.info(f"📝 원래 질문: {original_question[:50]}...")
            
            # 필드별 기본 응답 템플릿
            field_responses = {
                '질문_1': [
                    "아, 그런 거였군요! 제가 잘못 이해했네요.",
                    "아, 맞습니다! 그 부분을 놓쳤어요.",
                    "아, 그렇구나! 이제 이해했어요."
                ],
                '질문_2': [
                    "그 부분은 아직 제대로 모르겠어요.",
                    "그건 좀 어려워서 잘 모르겠어요.",
                    "그 부분은 배우지 못했어요."
                ],
                '질문_3': [
                    "결과는 공식 형태로 알고 싶어요.",
                    "단계별로 설명해주시면 좋겠어요.",
                    "예시와 함께 설명해주세요."
                ]
            }
            
            # 기본 응답 선택
            base_responses = field_responses.get(field, [
                "아, 그렇구나! 이제 이해했어요.",
                "그 부분은 잘 모르겠어요.",
                "더 자세히 설명해주세요."
            ])
            
            logger.info(f"📝 기본 응답 템플릿 선택: {field} -> {len(base_responses)}개")
            
            # 질문 내용에 따른 구체적 응답 생성
            prompt = f"""
            명료화 질문에 대한 학생 응답을 생성해주세요:

            학생: {current_persona.get('name', '학생') if current_persona else '학생'}
            원래 질문: {original_question[:100] if len(original_question) > 100 else original_question}
            명료화 질문: {question}
            
            요구사항:
            1. 자연스러운 학생 톤
            2. 구체적이고 명확한 내용
            3. 20-50자 정도의 길이
            
            응답:
            """
            
            logger.info(f"🤖 OpenAI API 호출 시작...")
            logger.info(f"    📝 프롬프트 길이: {len(prompt)}자")
            logger.info(f"    🎭 페르소나: {current_persona}")
            logger.info(f"    📝 원래 질문: {original_question[:50]}...")
            logger.info(f"    ❓ 명료화 질문: {question[:50]}...")
            
            # OpenAI API 호출
            response = await self.openai_client.chat.completions.create(
                model="gpt-5-mini",  # gpt-5-mini 모델 사용
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 수학을 배우는 학생입니다. 명료화 질문에 대해 자연스럽고 솔직하게 답변해주세요."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_completion_tokens=1500,  # 토큰 제한 증가 (500 → 1500)
            )
            
            logger.info(f"✅ OpenAI API 응답 수신 완료")
            logger.info(f"    📊 응답 타입: {type(response)}")
            logger.info(f"    📊 응답 속성: {dir(response)}")
            
            # 응답 내용 확인
            if hasattr(response, 'choices') and response.choices:
                choice = response.choices[0]
                logger.info(f"    📊 첫 번째 선택지: {choice}")
                if hasattr(choice, 'message'):
                    message = choice.message
                    logger.info(f"    📊 메시지 객체: {message}")
                    if hasattr(message, 'content'):
                        content = message.content
                        logger.info(f"    📊 원본 콘텐츠: {repr(content)}")
                        logger.info(f"    📊 콘텐츠 길이: {len(content) if content else 0}")
                    else:
                        logger.error(f"    ❌ message.content 속성 없음")
                else:
                    logger.error(f"    ❌ choice.message 속성 없음")
            else:
                logger.error(f"    ❌ response.choices가 비어있거나 없음")
            
            generated_response = response.choices[0].message.content.strip()
            logger.info(f"✅ LLM 응답 생성 완료: {generated_response[:50]}...")
            logger.info(f"    📊 최종 응답 길이: {len(generated_response)}")
            logger.info(f"    📊 최종 응답 내용: {repr(generated_response)}")
            
            # 응답 검증 - 빈 응답이나 부적절한 응답 방지
            if not generated_response or generated_response.strip() == "" or len(generated_response.strip()) < 5:
                logger.warning(f"⚠️ LLM이 빈 응답을 생성했습니다. 기본 응답으로 대체합니다.")
                logger.warning(f"    📊 검증 실패: generated_response='{repr(generated_response)}'")
                logger.warning(f"    📊 길이: {len(generated_response)}")
                fallback_responses = [
                    "아, 그렇구나! 이제 이해했어요.",
                    "그 부분은 잘 모르겠어요.",
                    "더 자세히 설명해주세요.",
                    "네, 이해했습니다.",
                    "그런 거였군요!"
                ]
                generated_response = random.choice(fallback_responses)
                logger.info(f"🔄 기본 응답으로 대체: {generated_response}")
            
            return generated_response
            
        except Exception as e:
            logger.error(f"❌ 명료화 응답 생성 실패: {e}")
            logger.error(f"   📍 상세 오류: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"   📍 스택 트레이스: {traceback.format_exc()}")
            
            # 에러 발생 시 기본 응답 반환
            fallback_responses = [
                "아, 그렇구나! 이제 이해했어요.",
                "그 부분은 잘 모르겠어요.",
                "더 자세히 설명해주세요."
            ]
            fallback_response = random.choice(fallback_responses)
            logger.info(f"🔄 기본 응답으로 대체: {fallback_response}")
            return fallback_response
            
    async def _log_clarification_requested(self, data: Dict[str, Any]) -> None:
        """명료화 요청 로깅"""
        try:
            request_id = data.get('request_id', 'N/A')
            question = data.get('question', 'N/A')
            missing_fields = data.get('missing_fields', [])
            
            logger.info(f"📋 명료화 요청 수신:")
            logger.info(f"   🆔 요청 ID: {request_id}")
            logger.info(f"   📝 원본 질문: {question[:100]}...")
            logger.info(f"   🏷️ 누락 필드: {missing_fields}")
            
        except Exception as e:
            logger.error(f"❌ 명료화 요청 로깅 실패: {e}")
            
    async def _run_interactive_test(self, question_count: int) -> Dict[str, Any]:
        """인터랙티브 테스트 실행 - 성공한 로직 기반"""
        logger.info(f"🎮 인터랙티브 테스트 시작: {question_count}개 질문")
        
        results = {
            "mode": "interactive",
            "total_questions": question_count,
            "success_count": 0,
            "failed_count": 0,
            "sessions": [],
            "start_time": datetime.now().isoformat(),
            "end_time": None
        }
        
        try:
            for i in range(question_count):
                logger.info(f"\n{'='*60}")
                logger.info(f"📝 질문 {i+1}/{question_count}")
                logger.info(f"{'='*60}")
                
                # 사용자 입력 받기
                question = input(f"\n💬 질문 {i+1}을 입력하세요 (또는 'skip' 입력): ").strip()
                
                if question.lower() == 'skip':
                    logger.info("⏭️ 질문을 건너뜁니다.")
                    continue
                    
                if not question:
                    logger.warning("⚠️ 질문을 입력해주세요.")
                    continue
                
                # 세션 시작
                session_id = f"interactive_{datetime.now().strftime('%H%M%S')}_{i}"
                session = {
                    "id": session_id,
                    "question": question,
                    "start_time": datetime.now().isoformat(),
                    "status": "running"
                }
                
                results["sessions"].append(session)
                
                try:
                    # 질문 전송 및 응답 대기
                    success = await self._process_interactive_question(question, session)
                    
                    if success:
                        session["status"] = "completed"
                        session["success"] = True
                        results["success_count"] += 1
                        logger.info(f"✅ 질문 {i+1} 완료")
                    else:
                        session["status"] = "failed"
                        session["success"] = False
                        results["failed_count"] += 1
                        logger.warning(f"❌ 질문 {i+1} 실패")
                        
                except Exception as e:
                    logger.error(f"❌ 질문 {i+1} 처리 중 오류: {e}")
                    session["status"] = "error"
                    session["error"] = str(e)
                    results["failed_count"] += 1
                
                # 다음 질문 전 잠시 대기
                if i < question_count - 1:
                    logger.info("⏳ 다음 질문을 준비 중...")
                    await asyncio.sleep(2)
                    
        except Exception as e:
            logger.error(f"❌ 인터랙티브 테스트 실행 중 오류: {e}")
            results["error"] = str(e)
            
        finally:
            results["end_time"] = datetime.now().isoformat()
            
        return results
        
    async def _process_interactive_question(self, question: str, session: Dict[str, Any]) -> bool:
        """인터랙티브 질문 처리 - 성공한 로직 기반"""
        try:
            # 1. 질문 전송
            request_id = f"interactive_{datetime.now().strftime('%H%M%S')}"
            question_payload = {
                "request_id": request_id,
                "question": question,  # 에이전트가 기대하는 필드명
                "context": "",
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"📤 질문 전송: {question[:50]}...")
            logger.info(f"   요청 ID: {request_id}")
            
            # Redis로 질문 발행
            await self.redis_client.publish(USER_QUESTION, json.dumps(question_payload, ensure_ascii=False))
            
            # 2. 응답 대기 및 처리
            timeout = 120  # 2분 타임아웃
            start_time = datetime.now()
            clarification_completed = False
            
            while (datetime.now() - start_time).seconds < timeout:
                try:
                    # 메시지 핸들러에서 응답 확인
                    if self.message_handler:
                        # 명료화 질문 처리
                        if hasattr(self.message_handler, 'last_clarification_question'):
                            clarification_data = self.message_handler.last_clarification_question
                            if clarification_data and clarification_data.get('request_id') == request_id:
                                await self._handle_interactive_clarification(clarification_data, session)
                                clarification_completed = True
                                break
                        
                        # 답변 완료 확인
                        if hasattr(self.message_handler, 'last_answer_completed'):
                            answer_data = self.message_handler.last_answer_completed
                            if answer_data and answer_data.get('request_id') == request_id:
                                await self._handle_interactive_answer(answer_data, session)
                                return True
                    
                    # 잠시 대기
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"❌ 응답 처리 중 오류: {e}")
                    break
            
            # 타임아웃 처리
            if not clarification_completed:
                logger.warning(f"⏰ 타임아웃: {timeout}초 내에 응답을 받지 못했습니다.")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"❌ 인터랙티브 질문 처리 실패: {e}")
            return False
            
    async def _handle_interactive_clarification(self, clarification_data: Dict[str, Any], session: Dict[str, Any]):
        """인터랙티브 명료화 처리"""
        try:
            question = clarification_data.get('question', '')
            field = clarification_data.get('field', '')
            
            logger.info(f"❓ 명료화 질문 수신:")
            logger.info(f"   질문: {question}")
            logger.info(f"   필드: {field}")
            
            # 사용자 입력 받기
            user_response = input(f"💬 명료화 응답 ({field}): ").strip()
            
            if not user_response:
                logger.warning("⚠️ 응답을 입력해주세요.")
                return
            
            # 명료화 응답 전송
            clarification_response = {
                "request_id": clarification_data.get('request_id'),
                "message": user_response,  # 에이전트가 기대하는 파라미터명
                "field": field,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.redis_client.publish(USER_CLARIFICATION, 
                                         json.dumps(clarification_response, ensure_ascii=False))
            
            logger.info(f"✅ 명료화 응답 전송 완료: {user_response}")
            
        except Exception as e:
            logger.error(f"❌ 명료화 처리 실패: {e}")
            
    async def _handle_interactive_answer(self, answer_data: Dict[str, Any], session: Dict[str, Any]):
        """인터랙티브 답변 처리"""
        try:
            answer = answer_data.get('answer', '')
            
            logger.info(f"🎉 답변 완료!")
            logger.info(f"   답변 길이: {len(answer)} 문자")
            
            # 세션에 답변 저장
            session["answer"] = answer
            session["answer_length"] = len(answer)
            
            logger.info(f"✅ 답변 처리 완료")
            
        except Exception as e:
            logger.error(f"❌ 답변 처리 실패: {e}")
            
    async def _handle_automated_clarification(self, clarification_data: Dict[str, Any], request_id: str):
        """자동화된 명료화 처리 - 성공한 심플 테스터 로직"""
        try:
            question = clarification_data.get('question', '')
            field = clarification_data.get('field', '')
            
            logger.info(f"❓ 자동화 명료화 질문 수신:")
            logger.info(f"   질문: {question}")
            logger.info(f"   필드: {field}")
            
            # 자동화된 명료화 응답 생성 (페르소나 기반)
            if self.current_persona:
                user_response = self.clarification_handler.generate_clarification_response(
                    clarification_data, self.current_persona
                )
            else:
                # 기본 응답
                user_response = "이 부분에 대해 더 자세히 알고 싶습니다."
            
            logger.info(f"💬 자동화 응답: {user_response}")
            
            # 명료화 응답 전송
            clarification_response = {
                "request_id": request_id,
                "message": user_response,  # 에이전트가 기대하는 파라미터명
                "field": field,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.redis_client.publish(USER_CLARIFICATION, 
                                         json.dumps(clarification_response, ensure_ascii=False))
            
            logger.info(f"✅ 자동화 명료화 응답 전송 완료: {user_response}")
            
        except Exception as e:
            logger.error(f"❌ 자동화 명료화 처리 실패: {e}")
            
    async def _handle_automated_answer(self, answer_data: Dict[str, Any]) -> Dict[str, Any]:
        """자동화된 답변 처리 - 성공한 심플 테스터 로직"""
        try:
            answer = answer_data.get('answer', '')
            
            logger.info(f"🎉 자동화 답변 완료!")
            logger.info(f"   답변 길이: {len(answer)} 문자")
            
            return {
                "status": "answer_completed",
                "answer": answer,
                "answer_length": len(answer)
            }
            
        except Exception as e:
            logger.error(f"❌ 자동화 답변 처리 실패: {e}")
            return {"status": "error", "error": str(e)}
            
    async def cleanup(self):
        """리소스 정리 - 현재 백엔드 API 구조에 맞춤"""
        try:
            # HTTP 세션 정리
            if hasattr(self, 'http_session') and self.http_session:
                await self.http_session.close()
                logger.info("✅ HTTP 세션 정리 완료")
            
            # Redis 연결 정리
            if hasattr(self, 'redis_client') and self.redis_client:
                await self.redis_client.close()
                logger.info("✅ Redis 연결 정리 완료")
            
            # 메시지 핸들러 정리
            if self.message_handler:
                await self.message_handler.cleanup()
                logger.info("✅ 메시지 핸들러 정리 완료")
            
            # 명료화 핸들러 정리
            if self.clarification_handler:
                # 명료화 핸들러 정리
                pass
            
            # 부모 클래스 정리
            await super().cleanup()
            logger.info("✅ 고급 테스터 정리 완료")
            
        except Exception as e:
            logger.error(f"❌ 테스터 정리 실패: {e}")
            
    def get_test_summary(self) -> Dict[str, Any]:
        """테스트 요약 반환"""
        total_sessions = len(self.test_sessions)
        completed_sessions = len([s for s in self.test_sessions.values() if s.get("status") == "completed"])
        successful_sessions = len([s for s in self.test_sessions.values() if s.get("success", False)])
        
        return {
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "successful_sessions": successful_sessions,
            "success_rate": (successful_sessions / completed_sessions * 100) if completed_sessions > 0 else 0,
            "test_mode": self.test_mode,
            "num_questions": self.num_questions
        }
