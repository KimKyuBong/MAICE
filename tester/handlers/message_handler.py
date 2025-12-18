"""
메시지 처리 핸들러 - Redis 이벤트 처리 및 로깅
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class MessageHandler:
	"""Redis 메시지 수신 및 라우팅을 담당하는 단일 구독자"""
	
	def __init__(self, redis_client: redis.Redis):
		self.redis_client = redis_client
		self.pubsub = None
		self.is_listening = False
		
		# 요청별 응답 저장 (병렬 처리용)
		self.request_responses: Dict[str, Dict[str, Any]] = {}
		self.session_states: Dict[str, Dict[str, Any]] = {}
		
		# 구독할 채널 목록
		self.subscribed_channels = [
			'user.question',
			'question.submitted', 
			'question.classified',
			'clarification.requested',
			'clarification.question',
			'user.clarification',
			'answer.requested',
			'answer.completed',
			'student.status_updated',
			'session.title_updated',
			'conversation.summary_updated'
		]
		
		logger.info(f"📡 MessageHandler 초기화 완료: {len(self.subscribed_channels)}개 채널 구독 준비")
	
	async def start_listening(self):
		"""Redis 채널 구독 시작 (단일 구독자)"""
		if self.is_listening:
			logger.warning("⚠️ 이미 수신 중입니다.")
			return
			
		try:
			logger.info("🚀 Redis 채널 구독 시작...")
			self.pubsub = self.redis_client.pubsub()
			
			# 모든 채널 구독
			for channel in self.subscribed_channels:
				await self.pubsub.subscribe(channel)
				logger.debug(f"📡 채널 구독: {channel}")
			
			logger.info(f"✅ {len(self.subscribed_channels)}개 채널 구독 완료")
			self.is_listening = True
			
			# 메시지 수신 루프 시작
			await self._listen_for_messages()
			
		except Exception as e:
			logger.error(f"❌ 채널 구독 실패: {e}")
			self.is_listening = False
			raise
	
	async def _listen_for_messages(self):
		"""Redis 메시지 수신 루프 (단일 구독자)"""
		logger.info("👂 메시지 수신 루프 시작...")
		
		try:
			while self.is_listening:
				try:
					# 메시지 수신 (타임아웃 1초)
					message = await self.pubsub.get_message(timeout=1.0)
					
					if message and message["type"] == "message":
						await self._process_message(message)
						
				except Exception as e:
					logger.error(f"❌ 메시지 수신 중 오류: {e}")
					await asyncio.sleep(1)
					
		except Exception as e:
			logger.error(f"❌ 메시지 수신 루프 오류: {e}")
		finally:
			self.is_listening = False
			logger.info("🛑 메시지 수신 루프 종료")
	
	async def _process_message(self, message):
		"""수신된 메시지 처리 및 저장"""
		try:
			channel = message["channel"].decode("utf-8")
			data = json.loads(message["data"].decode("utf-8"))
			
			request_id = data.get('request_id', 'unknown')
			session_id = data.get('session_id')
			
			logger.debug(f"📨 메시지 수신: {channel} (요청: {request_id})")
			
			# 요청별 응답 저장 (병렬 처리용)
			if request_id != 'unknown':
				if request_id not in self.request_responses:
					self.request_responses[request_id] = {}
				# 메타 상태 초기화
				if '_meta' not in self.request_responses[request_id]:
					self.request_responses[request_id]['_meta'] = {
						'clarification_dispatched': False
					}
				
				# 채널별 응답 저장
				self.request_responses[request_id][channel] = {
					'data': data,
					'timestamp': datetime.now().isoformat(),
					'channel': channel
				}
				
				logger.debug(f"💾 응답 저장: {request_id} -> {channel}")
			
			# 세션 상태 업데이트
			if session_id:
				if session_id not in self.session_states:
					self.session_states[session_id] = {}
				self.session_states[session_id].update({
					'last_activity': datetime.now().isoformat(),
					'last_channel': channel
				})
				
		except Exception as e:
			logger.error(f"❌ 메시지 처리 실패: {e}")
	
	async def get_response(self, request_id: str, timeout: float = 120.0) -> Optional[Dict[str, Any]]:
		"""특정 요청의 응답 대기 (병렬 처리용)
		- clarification.question이 도착하면 즉시 반환 (early return)
		- 그 후 answer.completed를 기다려 최종 응답 반환
		"""
		start_time = datetime.now()
		logger.info(f"⏳ 응답 대기 시작: {request_id} (타임아웃: {timeout}초)")
		
		while (datetime.now() - start_time).total_seconds() < timeout:
			try:
				responses = self.request_responses.get(request_id)
				if responses:
					meta = responses.get('_meta', {'clarification_dispatched': False})
					
					# 1) 명료화 질문 도착 시 즉시 반환 (한 번만)
					if 'clarification.question' in responses and not meta.get('clarification_dispatched', False):
						clarification = responses['clarification.question']['data']
						meta['clarification_dispatched'] = True
						responses['_meta'] = meta
						logger.info(f"✅ 응답 완료: {request_id}")
						logger.info(f"📨 응답 수신: clarification_required")
						return {
							'status': 'clarification_required',
							'type': 'clarification_question',
							'question': clarification.get('question', ''),
							'field': clarification.get('field', ''),
							'request_id': clarification.get('request_id')
						}
					
					# 2) 최종 답변 완료 시 반환
					if 'answer.completed' in responses:
						result = self._extract_complete_response(responses)
						# 메모리 정리
						try:
							del self.request_responses[request_id]
						except Exception:
							pass
						logger.info(f"✅ 응답 완료: {request_id}")
						logger.info(f"📨 응답 수신: answer_completed")
						return result
				
				await asyncio.sleep(0.1)
				
			except Exception as e:
				logger.error(f"❌ 응답 대기 중 오류: {e}")
				break
		
		logger.warning(f"⏰ 타임아웃: {request_id} (타임아웃: {timeout}초)")
		return None
	
	def _is_response_complete(self, responses: Dict[str, Any]) -> bool:
		"""응답이 완료되었는지 확인"""
		# 명료화 질문이 있으면 명료화 응답 대기 (기존 로직 - 현재는 사용 안 함)
		if 'clarification.question' in responses:
			return 'user.clarification' in responses
		# 답변 완료 확인
		if 'answer.completed' in responses:
			return True
		return False
	
	def _extract_complete_response(self, responses: Dict[str, Any]) -> Dict[str, Any]:
		"""완성된 응답 데이터 추출"""
		result = {
			'status': 'unknown',
			'request_id': None,
			'timestamp': datetime.now().isoformat()
		}
		
		# 답변 완료 처리
		if 'answer.completed' in responses:
			answer_data = responses['answer.completed']['data']
			result.update({
				'status': 'answer_completed',
				'type': 'answer',
				'answer': answer_data.get('answer', ''),
				'request_id': answer_data.get('request_id'),
				'session_id': answer_data.get('session_id')
			})
		return result
	
	async def stop_listening(self):
		"""메시지 수신 중지"""
		self.is_listening = False
		if self.pubsub:
			await self.pubsub.close()
			logger.info("🛑 메시지 수신 중지")
	
	async def cleanup(self):
		"""외부 정리를 위한 헬퍼"""
		await self.stop_listening()
	
	def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
		"""특정 요청의 현재 상태 조회"""
		if request_id in self.request_responses:
			return {
				'request_id': request_id,
				'channels': list(self.request_responses[request_id].keys()),
				'timestamp': datetime.now().isoformat()
			}
		return None
	
	def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
		"""특정 세션의 현재 상태 조회"""
		if session_id in self.session_states:
			return self.session_states[session_id]
		return None
