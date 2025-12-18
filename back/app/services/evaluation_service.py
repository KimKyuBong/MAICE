"""
대화 세션 평가 서비스 - LLM을 통한 자동 평가
"""
import logging
import os
import json
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import google.generativeai as genai
from datetime import datetime

from app.models.models import ConversationSession, SessionMessage, ConversationEvaluation, UserModel, UserRole

logger = logging.getLogger(__name__)


class EvaluationService:
    """대화 세션 평가 서비스"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.model_name = "gemini-2.5-flash"
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
        else:
            logger.warning("GOOGLE_API_KEY가 설정되지 않았습니다")
            self.model = None
    
    async def evaluate_session_without_db(
        self,
        session_id: int,
        session: ConversationSession,
        messages: List[SessionMessage],
        evaluated_by: int
    ) -> Optional[Dict[str, Any]]:
        """DB 세션 없이 평가 수행 (결과만 반환)"""
        try:
            # 대화 내용 생성
            conversation_text = self._build_conversation_text(messages)
            
            # LLM을 통한 평가 수행
            evaluation_result = await self._evaluate_with_llm(conversation_text)
            
            # 평가 결과 딕셔너리로 반환
            scores = [
                evaluation_result.get("question_total_score"),
                evaluation_result.get("answer_total_score"),
            ]
            valid_scores = [s for s in scores if s is not None]
            overall_score = sum(valid_scores) if valid_scores else None
            
            return {
                "session_id": session_id,
                "student_id": session.user_id,
                "evaluated_by": evaluated_by,
                "question_professionalism_score": evaluation_result.get("question_professionalism_score"),
                "question_structuring_score": evaluation_result.get("question_structuring_score"),
                "question_context_application_score": evaluation_result.get("question_context_application_score"),
                "question_level_feedback": evaluation_result.get("question_feedback"),
                "answer_customization_score": evaluation_result.get("answer_customization_score"),
                "answer_systematicity_score": evaluation_result.get("answer_systematicity_score"),
                "answer_expandability_score": evaluation_result.get("answer_expandability_score"),
                "response_appropriateness_feedback": evaluation_result.get("answer_feedback"),
                "question_total_score": evaluation_result.get("question_total_score"),
                "response_total_score": evaluation_result.get("answer_total_score"),
                "overall_assessment": evaluation_result.get("overall_assessment"),
                "overall_score": overall_score
            }
            
        except Exception as e:
            logger.error(f"❌ 세션 {session_id} 평가 실패: {str(e)}")
            return None
    
    async def evaluate_session(
        self,
        session_id: int,
        evaluated_by: int,
        db: AsyncSession = None,
        preloaded_session: ConversationSession = None,
        preloaded_messages: List[SessionMessage] = None
    ) -> ConversationEvaluation:
        """
        특정 세션에 대한 평가를 수행
        
        Args:
            session_id: 평가할 세션 ID
            evaluated_by: 평가를 실행한 교사 ID
            db: 사용할 DB 세션 (결과 저장용)
            preloaded_session: 미리 로드된 세션 정보 (선택사항)
            preloaded_messages: 미리 로드된 메시지 목록 (선택사항)
            
        Returns:
            ConversationEvaluation: 평가 결과
        """
        # 병렬 처리 시 독립 DB 세션 사용
        use_db = db or self.db
        is_external_session = db is not None
        
        try:
            # 세션 정보 조회 (미리 로드된 것이 없으면 DB에서 조회)
            if preloaded_session:
                session = preloaded_session
            else:
                session = await use_db.get(ConversationSession, session_id)
                if not session:
                    raise ValueError(f"세션 {session_id}를 찾을 수 없습니다")
            
            # 세션 메시지 조회 (미리 로드된 것이 없으면 DB에서 조회)
            if preloaded_messages is not None:
                messages = preloaded_messages
            else:
                messages_query = (
                    select(SessionMessage)
                    .where(SessionMessage.conversation_session_id == session_id)
                    .order_by(SessionMessage.created_at.asc())
                )
                messages_result = await use_db.execute(messages_query)
                messages = messages_result.scalars().all()
            
            # 메시지가 없으면 평가 불가 (에러를 발생시키지 않고 조용히 건너뜀)
            if not messages:
                logger.warning(f"⚠️ 세션 {session_id}에 메시지가 없어 평가를 건너뜁니다")
                return None
            
            # 세션 소유자가 student 역할인지 확인
            user = await use_db.get(UserModel, session.user_id)
            if not user:
                logger.warning(f"⚠️ 세션 {session_id}의 사용자를 찾을 수 없어 평가를 건너뜁니다")
                return None
            if user.role != UserRole.STUDENT:
                logger.info(f"ℹ️ 세션 {session_id}의 사용자(user_id={session.user_id}, role={user.role})는 student가 아니어서 평가를 건너뜁니다")
                return None
            
            # 기존 pending 평가가 있으면 삭제 (강제 재평가)
            from sqlalchemy import delete as sql_delete
            
            delete_stmt = (
                sql_delete(ConversationEvaluation)
                .where(ConversationEvaluation.conversation_session_id == session_id)
                .where(ConversationEvaluation.evaluation_status == 'pending')
            )
            await use_db.execute(delete_stmt)
            await use_db.flush()
            
            # 평가 레코드 생성 (상태: pending)
            evaluation = ConversationEvaluation(
                conversation_session_id=session_id,
                student_id=session.user_id,
                evaluated_by=evaluated_by,
                evaluation_status="pending"
            )
            use_db.add(evaluation)
            await use_db.flush()
            
            # 대화 내용 생성
            conversation_text = self._build_conversation_text(messages)
            
            # LLM을 통한 평가 수행
            evaluation_result = await self._evaluate_with_llm(conversation_text)
            
            # 평가 결과 저장 (3+3, 각 5점 만점 체계)
            # 질문 세부 점수
            evaluation.question_professionalism_score = evaluation_result.get("question_professionalism_score")
            evaluation.question_structuring_score = evaluation_result.get("question_structuring_score")
            evaluation.question_context_application_score = evaluation_result.get("question_context_application_score")
            evaluation.question_level_feedback = evaluation_result.get("question_feedback")

            # 답변 세부 점수
            evaluation.answer_customization_score = evaluation_result.get("answer_customization_score")
            evaluation.answer_systematicity_score = evaluation_result.get("answer_systematicity_score")
            evaluation.answer_expandability_score = evaluation_result.get("answer_expandability_score")
            evaluation.response_appropriateness_feedback = evaluation_result.get("answer_feedback")

            # 합계 점수
            evaluation.question_total_score = evaluation_result.get("question_total_score")
            evaluation.response_total_score = evaluation_result.get("answer_total_score")
            evaluation.overall_assessment = evaluation_result.get("overall_assessment")
            
            # 종합 점수 계산
            scores = [
                evaluation_result.get("question_total_score"),
                evaluation_result.get("answer_total_score"),
            ]
            valid_scores = [s for s in scores if s is not None]
            if valid_scores:
                # 전체 합계(0~30)를 overall_score에 저장
                evaluation.overall_score = sum(valid_scores)
            
            evaluation.evaluation_status = "completed"
            evaluation.updated_at = datetime.utcnow()
            
            await use_db.commit()
            
            logger.info(f"✅ 세션 {session_id} 평가 완료: overall_score={evaluation.overall_score:.2f}")
            return evaluation
            
        except Exception as e:
            logger.error(f"❌ 세션 {session_id} 평가 실패: {str(e)}")
            
            # 평가 실패 상태 저장
            try:
                if 'evaluation' in locals():
                    evaluation.evaluation_status = "failed"
                    evaluation.error_message = str(e)
                    evaluation.updated_at = datetime.utcnow()
                    await use_db.commit()
            except:
                pass
            finally:
                # 외부 세션을 사용한 경우 닫기
                if is_external_session and use_db:
                    await use_db.close()
            
            raise
    
    def _build_conversation_text(self, messages: List[SessionMessage]) -> str:
        """세션 메시지를 텍스트로 변환 (전체 대화)"""
        conversation_lines = []

        def get_speaker_label(sender: str) -> str:
            sender_normalized = (sender or "").strip().lower()
            if sender_normalized == "user":
                return "사용자"
            if sender_normalized == "maice":
                return "MAICE"
            return sender  # 알 수 없는 값은 그대로 노출

        for msg in messages:
            speaker = get_speaker_label(getattr(msg, "sender", ""))
            msg_type = getattr(msg, "message_type", None) or "message"

            # 형식: [사용자|user_question] 내용 (시간 정보 제외)
            line_prefix = f"[{speaker}|{msg_type}]"
            content = getattr(msg, "content", "") or ""
            conversation_lines.append(f"{line_prefix} {content}")

        return "\n".join(conversation_lines)
    
    def _build_user_questions_text(self, messages: List[SessionMessage]) -> str:
        """사용자의 모든 질문을 모아서 텍스트로 변환"""
        user_messages = []
        
        for msg in messages:
            sender = getattr(msg, "sender", "").strip().lower()
            if sender == "user":
                content = getattr(msg, "content", "") or ""
                if content.strip():  # 빈 메시지 제외
                    user_messages.append(content)
        
        return "\n---\n".join(user_messages) if user_messages else ""
    
    def _build_maice_answers_text(self, messages: List[SessionMessage]) -> str:
        """MAICE의 모든 답변을 모아서 텍스트로 변환"""
        maice_messages = []
        
        for msg in messages:
            sender = getattr(msg, "sender", "").strip().lower()
            if sender == "maice":
                content = getattr(msg, "content", "") or ""
                if content.strip():  # 빈 메시지 제외
                    maice_messages.append(content)
        
        return "\n---\n".join(maice_messages) if maice_messages else ""
    
    async def _evaluate_with_llm(self, conversation_text: str) -> Dict[str, Any]:
        """LLM을 사용하여 대화 내용을 평가 (비동기 실행)"""
        if not self.model:
            raise ValueError("LLM 모델이 초기화되지 않았습니다")
        
        prompt = f"""
다음은 학생과 MAICE AI 수학 교육 시스템 간의 대화 내용입니다.
**이 평가는 수학 과제를 해결하는 과정에서 이루어진 대화를 기준으로 합니다.**

**중요: 수학 과제 해결과 관련없는 질문과 응답이 진행된 경우, 해당 항목에 대해 0점을 부여해야 합니다.**
예를 들어, 수학 과제와 무관한 일반적인 대화, 시스템 사용법 문의, 인사말 등은 평가 대상이 아닙니다.

**평가 방법 (반드시 준수):**
- **질문 평가 척도 (1) 평가**: 대화 내용에서 [사용자|user] 또는 [사용자]로 표시된 모든 사용자 입력(질문)을 찾아 종합적으로 평가하세요. 
  - **중요**: 첫 질문에 중점을 두지 말고, 학생이 말한 **모든 대화(질문)를 전체적인 맥락으로 종합**하여 평가하세요.
  - 학생의 모든 질문들이 함께 만들어내는 전체적인 질문 맥락, 질문의 발전 과정, 그리고 대화 전반에 걸친 학습 목적과 어려움을 종합적으로 파악하여 평가하세요.
  - 예를 들어, 초기 질문이 불완전하더라도 후속 질문들을 통해 보완되거나 발전된 경우, 전체적인 질문의 맥락과 목적을 종합적으로 평가해야 합니다.
- **답변 평가 척도 (2) 평가**: 대화 내용에서 [MAICE|maice] 또는 [MAICE]로 표시된 모든 MAICE 응답을 찾아 종합적으로 평가하세요.
  - **중요**: 첫 답변이나 개별 답변에 중점을 두지 말고, MAICE가 제시한 **모든 답변을 전체적인 맥락으로 종합**하여 평가하세요.
  - MAICE의 모든 답변들이 함께 만들어내는 전체적인 설명의 일관성, 설명의 발전 과정, 학습자에 대한 이해의 심화 과정을 종합적으로 파악하여 평가하세요.
  - 예를 들어, 초기 답변이 불완전하거나 부족하더라도 후속 답변들을 통해 보완되거나 심화된 경우, 전체적인 답변의 맥락과 품질을 종합적으로 평가해야 합니다.

이 대화를 다음과 같은 기준으로 평가해주세요:

## 평가 기준 (각 항목 0~5점, 정수만 허용)

### 1) 질문 평가 척도 (Question Evaluation Criteria) - 총 15점 (3개 × 5점)

**⚠️ 중요한 평가 원칙: 질문 평가 시 학생의 모든 대화를 전체 맥락으로 종합 평가**
- 첫 번째 질문이나 개별 질문의 완전성에 중점을 두지 마세요.
- 학생이 대화 중에 한 모든 질문들이 함께 만들어내는 전체적인 맥락, 질문의 발전 과정, 학습 목적의 일관성을 종합적으로 파악하여 평가하세요.
- 예를 들어, 초기 질문에서 부족한 정보가 후속 질문들에서 보완되거나, 여러 질문을 통해 점진적으로 문제를 명확히 하는 경우, 전체 대화 맥락을 종합하여 긍정적으로 평가하세요.

**A. 수학적 전문성 (Mathematical Professionalism) - 5점 만점 (엄격한 요소 유무 기반 채점)**
**평가 방법: 학생의 모든 질문을 통합하여 전체적인 수학적 전문성을 평가하세요.**
다음 4가지 요소가 모두 있어야 합니다. 요소가 없으면 엄격하게 감점하세요:
- 수학적 개념/원리의 정확성: 질문에 포함된 수학적 개념이나 원리의 정확성
- 교과과정 내 위계성 파악: 해당 개념의 선수 학습, 심화 학습 등 위계 이해
- 수학적 용어 사용의 적절성: 사용된 수학적 용어의 적절성과 정확성
- 문제해결 방향의 구체성: 문제 해결을 위한 구체적인 방향 제시 여부

**채점 기준 (엄격 적용):**
- 4개 요소 모두 있음: 5점
- 3개 요소만 있음: 3점
- 2개 요소만 있음: 2점
- 1개 요소만 있음: 1점
- 0개 요소: 0점

**B. 질문 구조화 (Question Structuring) - 5점 만점 (엄격한 요소 유무 기반 채점)**
**평가 방법: 학생의 모든 질문을 통합하여 전체적인 질문 구조화 능력을 평가하세요. 개별 질문의 완전성보다는 여러 질문들이 함께 만들어내는 전체적인 질문의 구조와 발전 과정을 평가하세요.**
다음 4가지 요소가 모두 있어야 합니다. 요소가 없으면 엄격하게 감점하세요:
- 핵심 질문의 단일성: 핵심 내용이 명확하고 단일한지
- 조건 제시의 완결성: 필요한 모든 조건이 완전하게 제시되었는지
- 문장 구조의 논리성: 문장 구조가 논리적이고 이해하기 쉬운지
- 질문 의도의 명시성: 무엇을 알고 싶어 하는지 의도가 명확한지

**채점 기준 (엄격 적용):**
- 4개 요소 모두 있음: 5점
- 3개 요소만 있음: 3점
- 2개 요소만 있음: 2점
- 1개 요소만 있음: 1점
- 0개 요소: 0점

**C. 학습 맥락 적용 (Application of Learning Context) - 5점 만점 (엄격한 요소 유무 기반 채점)**
**평가 방법: 학생의 모든 질문을 통합하여 전체 대화에서 드러나는 학습 맥락 적용 능력을 평가하세요. 대화 전반에 걸쳐 학습 맥락이 어떻게 발전하고 응용되는지를 종합적으로 평가하세요.**
다음 4가지 요소가 모두 있어야 합니다. 요소가 없으면 엄격하게 감점하세요:
- 현재 학습 단계 설명: 현재 학습 단계와의 관련성
- 선수학습 내용 언급: 선수 학습 내용과의 연결성
- 구체적 어려움 명시: 겪고 있는 구체적인 어려움의 명확성
- 학습 목표 제시: 어떤 학습 목표를 가지고 있는지

**채점 기준 (엄격 적용):**
- 4개 요소 모두 있음: 5점
- 3개 요소만 있음: 3점
- 2개 요소만 있음: 2점
- 1개 요소만 있음: 1점
- 0개 요소: 0점

### 2) 답변 평가 척도 (Answer Evaluation Criteria) - 총 15점 (3개 × 5점)

**⚠️ 중요한 평가 원칙: 답변 평가 시 MAICE의 모든 답변을 전체 맥락으로 종합 평가**
- 첫 번째 답변이나 개별 답변의 완전성에 중점을 두지 마세요.
- MAICE가 대화 중에 제공한 모든 답변들이 함께 만들어내는 전체적인 설명의 맥락, 답변의 발전 과정, 학습자에 대한 이해와 맞춤의 일관성을 종합적으로 파악하여 평가하세요.
- 예를 들어, 초기 답변에서 부족한 부분이 후속 답변들에서 보완되거나, 여러 답변을 통해 점진적으로 개념을 설명하고 심화하는 경우, 전체 대화 맥락을 종합하여 긍정적으로 평가하세요.

**A. 학습자 맞춤도 (Learner Customization) - 5점 만점 (엄격한 요소 유무 기반 채점)**
**평가 방법: MAICE의 모든 답변을 통합하여 전체적으로 학습자에 대한 맞춤도를 평가하세요.**
다음 4가지 요소가 모두 있어야 합니다. 요소가 없으면 엄격하게 감점하세요:
- 학습자 수준별 접근: 답변이 학습자 수준에 맞는지
- 선수지식 연계성: 학습자의 선수 지식과의 효과적 연결
- 학습 난이도 조절: 내용이나 설명 방식의 난이도 적절성
- 개인화된 피드백: 학습자에게 개인화된 피드백 제공 여부

**채점 기준 (엄격 적용):**
- 4개 요소 모두 있음: 5점
- 3개 요소만 있음: 3점
- 2개 요소만 있음: 2점
- 1개 요소만 있음: 1점
- 0개 요소: 0점

**B. 설명의 체계성 (Systematicity of Explanation) - 5점 만점 (엄격한 요소 유무 기반 채점)**
**평가 방법: MAICE의 모든 답변을 통합하여 전체적인 설명의 체계성을 평가하세요. 개별 답변의 완전성보다는 여러 답변들이 함께 만들어내는 전체적인 설명의 체계와 논리적 전개 과정을 평가하세요.**
다음 4가지 요소가 모두 있어야 합니다. 요소가 없으면 엄격하게 감점하세요:
- 개념 설명의 위계화: 개념 설명의 체계적이고 위계적 구성
- 단계별 논리 전개: 단계별로 논리적인 전개
- 핵심 요소 강조: 설명에서 핵심 요소의 명확한 강조
- 예시 활용의 적절성: 예시가 적절하게 활용되어 개념 이해를 돕는지

**채점 기준 (엄격 적용):**
- 4개 요소 모두 있음: 5점
- 3개 요소만 있음: 3점
- 2개 요소만 있음: 2점
- 1개 요소만 있음: 1점
- 0개 요소: 0점

**C. 학습 내용 확장성 (Expandability of Learning Content) - 5점 만점 (엄격한 요소 유무 기반 채점)**
**평가 방법: MAICE의 모든 답변을 통합하여 전체 대화에서 드러나는 학습 내용 확장성을 평가하세요. 대화 전반에 걸쳐 학습 내용이 어떻게 확장되고 심화되는지를 종합적으로 평가하세요.**
다음 4가지 요소가 모두 있어야 합니다. 요소가 없으면 엄격하게 감점하세요:
- 심화학습 방향 제시: 심화 학습으로 나아갈 수 있는 방향 제시
- 응용문제 연계성: 관련 응용 문제와 연결 가능성 제시
- 오개념 교정 전략: 학습자의 오개념 교정을 위한 효과적 전략 포함
- 자기주도 학습 유도: 학습자의 자기주도 학습 유도 여부

**채점 기준 (엄격 적용):**
- 4개 요소 모두 있음: 5점
- 3개 요소만 있음: 3점
- 2개 요소만 있음: 2점
- 1개 요소만 있음: 1점
- 0개 요소: 0점

## 응답 형식 (반드시 아래 JSON 키를 그대로 사용, 모든 점수는 정수)

각 점수의 근거를 피드백에 명확히 개별적으로 포함해야 합니다.

{{
  "question_professionalism_score": 3,
  "question_structuring_score": 3,
  "question_context_application_score": 2,
  "question_total_score": 8,
  "question_feedback": "【수학적 전문성 3점】\n- 수학적 개념/원리의 정확성: 있음\n- 교과과정 내 위계성 파악: 있음\n- 수학적 용어 사용의 적절성: 있음\n- 문제해결 방향의 구체성: 없음 (감점)\n【질문 구조화 3점】\n- 핵심 질문의 단일성: 있음\n- 조건 제시의 완결성: 있음\n- 문장 구조의 논리성: 있음\n- 질문 의도의 명시성: 없음 (감점)\n【학습 맥락 적용 2점】\n- 현재 학습 단계 설명: 있음\n- 선수학습 내용 언급: 있음\n- 구체적 어려움 명시: 없음 (감점)\n- 학습 목표 제시: 없음 (감점)",
  "answer_customization_score": 3,
  "answer_systematicity_score": 5,
  "answer_expandability_score": 2,
  "answer_total_score": 10,
  "answer_feedback": "【학습자 맞춤도 3점】\n- 학습자 수준별 접근: 있음\n- 선수지식 연계성: 있음\n- 학습 난이도 조절: 있음\n- 개인화된 피드백: 없음 (감점)\n【설명의 체계성 5점】\n- 개념 설명의 위계화: 있음\n- 단계별 논리 전개: 있음\n- 핵심 요소 강조: 있음\n- 예시 활용의 적절성: 있음\n【학습 내용 확장성 2점】\n- 심화학습 방향 제시: 있음\n- 응용문제 연계성: 있음\n- 오개념 교정 전략: 없음 (감점)\n- 자기주도 학습 유도: 없음 (감점)",
  "overall_assessment": "질문과 답변 모두 교육적으로 적절하며 학습에 도움이 됩니다."
}}

## 대화 내용

{conversation_text}

---

**중요 지침 (엄격한 요소 유무 기반 채점):**
0. **평가 대상 분리 (필수)**: 
   - 질문 평가 척도(1) 평가: 대화 내용 전체를 보면서, [사용자] 또는 [사용자|user]로 표시된 **모든 사용자 질문을 찾아 모아서 종합적으로 평가**하세요.
     - **반드시 준수**: 첫 질문에 중점을 두지 말고, 학생이 말한 **모든 대화를 전체 맥락으로 종합**하여 평가하세요.
     - 개별 질문의 완전성보다는, 모든 질문들이 함께 만들어내는 **전체적인 질문 맥락, 학습 목적, 어려움의 발전 과정**을 종합적으로 파악하여 평가하세요.
     - 초기 질문이 불완전하거나 부족해도, 후속 질문들을 통해 보완되거나 발전된 경우, 전체 대화의 맥락을 종합적으로 고려하여 평가하세요.
   - 답변 평가 척도(2) 평가: 대화 내용 전체를 보면서, [MAICE] 또는 [MAICE|maice]로 표시된 **모든 MAICE 답변을 찾아 모아서 종합적으로 평가**하세요.
     - **반드시 준수**: 첫 답변에 중점을 두지 말고, MAICE가 제공한 **모든 답변을 전체 맥락으로 종합**하여 평가하세요.
     - 개별 답변의 완전성보다는, 모든 답변들이 함께 만들어내는 **전체적인 설명의 일관성, 설명의 발전 과정, 학습자 맞춤의 심화**를 종합적으로 파악하여 평가하세요.
     - 초기 답변이 불완전하거나 부족해도, 후속 답변들을 통해 보완되거나 심화된 경우, 전체 대화의 맥락을 종합적으로 고려하여 평가하세요.
0-1. **수학 과제 해결 관련성 필수 체크**: 
   - 대화 내용이 수학 과제를 해결하는 과정과 관련이 있는지 먼저 확인하세요.
   - 질문이 수학 과제 해결과 무관한 경우(일반 대화, 인사말, 시스템 사용법 문의 등): 질문 관련 모든 항목(question_professionalism_score, question_structuring_score, question_context_application_score)에 0점 부여
   - 응답이 수학 과제 해결과 무관한 경우: 응답 관련 모든 항목(answer_customization_score, answer_systematicity_score, answer_expandability_score)에 0점 부여
   - 관련성이 없는 경우 피드백에 "수학 과제 해결과 무관한 내용이므로 0점을 부여합니다"라고 명시하세요.
1. 각 항목은 4가지 요소의 존재 여부를 엄격하게 확인하여 채점하세요. 요소가 없으면 감점해야 합니다. 모든 점수는 정수(0,1,2,3,4,5)만 사용하세요. 소수점 금지.
2. 채점 기준을 정확히 따르세요:
   - 4개 요소 모두 있음: 5점
   - 3개 요소만 있음: 3점
   - 2개 요소만 있음: 2점
   - 1개 요소만 있음: 1점
   - 0개 요소: 0점
3. 각 항목의 4가지 세부 요소를 하나씩 확인하고, 있으면 "있음", 없으면 "없음 (감점)"이라고 명시하세요. 감점이 발생한 이유를 명확히 기술하세요.
4. 피드백 형식: 각 항목별로 【항목명 점수】로 시작하고, 그 아래에 각 요소를 체크리스트 형식으로 "- 요소명: 있음/없음 (감점)"으로 기술하세요. 줄바꿈(\n)으로 구분하세요.
5. question_feedback에는 3개 항목(수학적 전문성, 질문 구조화, 학습 맥락 적용)의 평가 근거를 모두 포함하세요.
6. answer_feedback에는 3개 항목(학습자 맞춤도, 설명의 체계성, 학습 내용 확장성)의 평가 근거를 모두 포함하세요.
7. 정확히 위의 JSON 형식으로만 응답하세요. 추가 텍스트는 금지합니다. 점수 필드는 모두 정수여야 하며, 피드백은 줄바꿈으로 항목별 근거를 분리해야 합니다.
8. 너그럽게 점수를 주지 마세요. 요소가 없으면 반드시 감점하고, 그 근거를 피드백에 명확히 명시하세요.
9. 수학 과제 해결과 무관한 내용은 반드시 0점을 부여하고, 피드백에 그 이유를 명시하세요.
"""

        try:
            # 동기 LLM 호출을 비동기 스레드에서 실행하여 병렬 처리 가능
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: self.model.generate_content(prompt))
            
            # JSON 응답 추출
            response_text = response.text
            
            # 제어 문자 제거 (JSON 파싱 오류 방지)
            import re
            def clean_json_text(text: str) -> str:
                """제어 문자와 잘못된 이스케이프 시퀀스를 정리"""
                # 제어 문자 제거 (탭, 줄바꿈, 캐리지 리턴 제외) - JSON 문자열 내부 제외하고 처리
                # JSON 문자열 밖의 제어 문자만 제거하는 것이 안전하지만, 복잡하므로
                # 전체에서 제어 문자 제거 (유효한 줄바꿈/탭은 유지)
                # ASCII 제어 문자 제거 (0x00-0x1F 중 \n, \r, \t 제외)
                text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
                return text
            
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("JSON 응답을 찾을 수 없습니다")
            
            json_text = response_text[json_start:json_end]
            # JSON 파싱 전 텍스트 정리
            json_text = clean_json_text(json_text)
            
            try:
                evaluation_result = json.loads(json_text)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON 파싱 1차 실패: {str(e)} - 텍스트 일부: {json_text[:200]}")
                # 재시도: 더 공격적인 정리
                # 원본에서 다시 추출하고 더 강력하게 정리
                original_json = response_text[json_start:json_end]
                # 모든 제어 문자 제거 (줄바꿈/탭 포함, 하지만 JSON 내부 \n은 유지되어야 함)
                # 대신 잘못된 이스케이프만 수정: JSON 문자열 외부의 단독 백슬래시
                cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', original_json)
                # 인코딩 문제 해결
                cleaned = cleaned.encode('utf-8', errors='ignore').decode('utf-8')
                try:
                    evaluation_result = json.loads(cleaned)
                    logger.info("JSON 파싱 재시도 성공")
                except json.JSONDecodeError as e2:
                    logger.error(f"JSON 파싱 재시도 실패: {str(e2)}")
                    # 마지막 시도: 잘못된 이스케이프 시퀀스 수정
                    # \ 뒤에 유효하지 않은 문자가 오면 제거
                    final_cleaned = re.sub(r'\\(?!["\\/bfnrt])', '', cleaned)
                    try:
                        evaluation_result = json.loads(final_cleaned)
                        logger.info("JSON 파싱 3차 시도 성공")
                    except json.JSONDecodeError as e3:
                        logger.error(f"JSON 파싱 모든 시도 실패. 원본 시작: {original_json[:300]}")
                        raise ValueError(f"JSON 파싱 실패 (1차: {str(e)}, 2차: {str(e2)}, 3차: {str(e3)})")

            # 점수 정규화: 0~5 정수로 강제, 합계 재계산
            def to_int_score(value: Any) -> int:
                try:
                    num = float(value)
                except Exception:
                    return 0
                int_val = int(round(num))
                if int_val < 0:
                    return 0
                if int_val > 5:
                    return 5
                return int_val

            q_keys = [
                "question_professionalism_score",
                "question_structuring_score",
                "question_context_application_score",
            ]
            a_keys = [
                "answer_customization_score",
                "answer_systematicity_score",
                "answer_expandability_score",
            ]

            for k in q_keys + a_keys:
                if k in evaluation_result:
                    evaluation_result[k] = to_int_score(evaluation_result.get(k))

            # 합계 재계산 (정수 합)
            evaluation_result["question_total_score"] = sum(
                to_int_score(evaluation_result.get(k)) for k in q_keys
            )
            evaluation_result["answer_total_score"] = sum(
                to_int_score(evaluation_result.get(k)) for k in a_keys
            )
            
            return evaluation_result
            
        except Exception as e:
            logger.error(f"LLM 평가 중 오류: {str(e)}")
            raise
    
    async def batch_evaluate_sessions(
        self,
        session_ids: List[int],
        evaluated_by: int,
        max_concurrent: Optional[int] = None,
        batch_size: Optional[int] = None
    ) -> List[ConversationEvaluation]:
        """
        여러 세션에 대한 배치 단위 병렬 일괄 평가
        
        Args:
            session_ids: 평가할 세션 ID 목록
            evaluated_by: 평가를 실행한 교사 ID
            max_concurrent: 배치 내 최대 동시 실행 수 (기본값: 환경변수 또는 50)
            batch_size: 배치 크기 (기본값: 환경변수 또는 100)
            
        Returns:
            List[ConversationEvaluation]: 평가 결과 목록
        """
        import asyncio
        from app.core.db.session import async_session
        
        # 배치 크기 결정: 파라미터 > 환경변수 > 기본값(100)
        if batch_size is None:
            batch_size = int(os.getenv("EVALUATION_BATCH_SIZE", "100"))
        
        # 동시 실행 수 결정: 파라미터 > 환경변수 > 기본값(배치 크기와 동일)
        if max_concurrent is None:
            max_concurrent = int(os.getenv("EVALUATION_MAX_CONCURRENT", str(batch_size)))
        
        # 세션 ID 중복 제거 (안전장치)
        unique_session_ids = list(set(session_ids))
        if len(unique_session_ids) != len(session_ids):
            logger.warning(f"⚠️ 중복된 세션 ID 제거: {len(session_ids)} → {len(unique_session_ids)}개")
        
        total_count = len(unique_session_ids)
        logger.info(f"📊 일괄 평가 시작: 총 {total_count}개 세션, 배치 크기: {batch_size}개, 배치당 동시 실행 수: {max_concurrent}개")
        
        all_results = []
        
        # 배치별로 처리
        for batch_start in range(0, total_count, batch_size):
            batch_end = min(batch_start + batch_size, total_count)
            batch_ids = unique_session_ids[batch_start:batch_end]
            batch_num = (batch_start // batch_size) + 1
            total_batches = (total_count + batch_size - 1) // batch_size
            
            logger.info(f"📦 배치 {batch_num}/{total_batches} 처리 시작: {len(batch_ids)}개 세션")
            
            # 배치 데이터 미리 로드 (한 DB 세션에서)
            batch_db = async_session()
            try:
                # 세션 정보 일괄 조회
                sessions_query = (
                    select(ConversationSession)
                    .where(ConversationSession.id.in_(batch_ids))
                )
                sessions_result = await batch_db.execute(sessions_query)
                all_sessions = sessions_result.scalars().all()
                
                # 사용자 정보 일괄 조회 (student 역할 필터링)
                user_ids = list(set(s.user_id for s in all_sessions))
                users_query = (
                    select(UserModel)
                    .where(UserModel.id.in_(user_ids))
                    .where(UserModel.role == UserRole.STUDENT)
                )
                users_result = await batch_db.execute(users_query)
                student_user_ids = {u.id for u in users_result.scalars().all()}
                
                # student 역할 사용자의 세션만 필터링
                sessions_dict = {s.id: s for s in all_sessions if s.user_id in student_user_ids}
                filtered_out = len(all_sessions) - len(sessions_dict)
                if filtered_out > 0:
                    logger.info(f"🔍 배치 {batch_num}: student가 아닌 사용자의 세션 {filtered_out}개 제외")
                
                # 메시지 일괄 조회
                messages_query = (
                    select(SessionMessage)
                    .where(SessionMessage.conversation_session_id.in_(batch_ids))
                    .order_by(SessionMessage.conversation_session_id, SessionMessage.created_at.asc())
                )
                messages_result = await batch_db.execute(messages_query)
                all_messages = messages_result.scalars().all()
                
                # 세션별로 메시지 그룹화
                messages_dict: Dict[int, List[SessionMessage]] = {}
                for msg in all_messages:
                    if msg.conversation_session_id not in messages_dict:
                        messages_dict[msg.conversation_session_id] = []
                    messages_dict[msg.conversation_session_id].append(msg)
                
                logger.info(f"📥 배치 {batch_num} 데이터 로드 완료: {len(sessions_dict)}개 세션, {len(all_messages)}개 메시지")
            finally:
                await batch_db.close()
            
            # 동시 실행 수 제한을 위한 Semaphore
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def evaluate_single_session(session_id: int) -> Optional[Dict[str, Any]]:
                """단일 세션 평가 (DB 세션 없이 결과만 반환)"""
                # Semaphore를 먼저 획득 (병렬 실행 제한)
                async with semaphore:
                    logger.info(f"🚀 세션 {session_id} 평가 시작 (병렬)")
                    
                    # 미리 로드된 데이터 사용
                    session = sessions_dict.get(session_id)
                    messages = messages_dict.get(session_id, [])
                    
                    if not session:
                        logger.warning(f"⚠️ 세션 {session_id} 정보를 찾을 수 없어 건너뜁니다")
                        return None
                    
                    if not messages:
                        logger.warning(f"⚠️ 세션 {session_id}에 메시지가 없어 건너뜁니다")
                        return None
                    
                    # DB 세션 없이 평가 수행 (LLM 호출만)
                    try:
                        result = await self.evaluate_session_without_db(
                            session_id,
                            session,
                            messages,
                            evaluated_by
                        )
                        if result:
                            logger.info(f"✅ 세션 {session_id} 평가 완료")
                        return result
                    except Exception as e:
                        logger.error(f"❌ 세션 {session_id} 평가 실패: {str(e)}")
                        return None
            
            # 배치 내 병렬 평가 실행 (모든 태스크를 동시에 시작)
            logger.info(f"🚀 배치 {batch_num} 평가 태스크 시작: {len(batch_ids)}개 동시 실행")
            tasks = [evaluate_single_session(session_id) for session_id in batch_ids]
            
            # 모든 태스크를 병렬로 실행
            batch_evaluation_results = await asyncio.gather(*tasks, return_exceptions=False)
            
            # 평가 결과를 한 DB 세션에서 일괄 저장
            batch_db = async_session()
            try:
                from sqlalchemy import delete as sql_delete
                
                saved_evaluations = []
                for eval_data in batch_evaluation_results:
                    if not eval_data:
                        continue
                    
                    session_id = eval_data["session_id"]
                    
                    # 기존 pending 평가 삭제
                    delete_stmt = (
                        sql_delete(ConversationEvaluation)
                        .where(ConversationEvaluation.conversation_session_id == session_id)
                        .where(ConversationEvaluation.evaluation_status == 'pending')
                    )
                    await batch_db.execute(delete_stmt)
                    
                    # 평가 결과 저장
                    evaluation = ConversationEvaluation(
                        conversation_session_id=session_id,
                        student_id=eval_data["student_id"],
                        evaluated_by=eval_data["evaluated_by"],
                        evaluation_status="completed",
                        question_professionalism_score=eval_data.get("question_professionalism_score"),
                        question_structuring_score=eval_data.get("question_structuring_score"),
                        question_context_application_score=eval_data.get("question_context_application_score"),
                        question_level_feedback=eval_data.get("question_level_feedback"),
                        answer_customization_score=eval_data.get("answer_customization_score"),
                        answer_systematicity_score=eval_data.get("answer_systematicity_score"),
                        answer_expandability_score=eval_data.get("answer_expandability_score"),
                        response_appropriateness_feedback=eval_data.get("response_appropriateness_feedback"),
                        question_total_score=eval_data.get("question_total_score"),
                        response_total_score=eval_data.get("response_total_score"),
                        overall_assessment=eval_data.get("overall_assessment"),
                        overall_score=eval_data.get("overall_score"),
                        updated_at=datetime.utcnow()
                    )
                    batch_db.add(evaluation)
                    saved_evaluations.append(evaluation)
                
                await batch_db.commit()
                logger.info(f"💾 배치 {batch_num} 평가 결과 일괄 저장 완료: {len(saved_evaluations)}개")
                
            except Exception as e:
                await batch_db.rollback()
                logger.error(f"❌ 배치 {batch_num} 결과 저장 실패: {str(e)}", exc_info=True)
                saved_evaluations = []
            finally:
                await batch_db.close()
            
            # 결과 반환 (세션 ID별로 매핑하여 순서 유지)
            saved_evaluations_dict = {e.conversation_session_id: e for e in saved_evaluations}
            batch_results = [saved_evaluations_dict.get(sid) for sid in batch_ids]
            all_results.extend(batch_results)
            
            successful_in_batch = sum(1 for r in batch_results if r is not None)
            logger.info(f"✅ 배치 {batch_num}/{total_batches} 완료: {successful_in_batch}/{len(batch_ids)}개 성공")
        
        successful_count = sum(1 for r in all_results if r is not None)
        failed_count = len(all_results) - successful_count
        logger.info(f"📊 전체 일괄 평가 완료: 성공 {successful_count}개, 실패 {failed_count}개")
        
        return all_results
    
    async def get_evaluation(self, evaluation_id: int) -> Optional[ConversationEvaluation]:
        """평가 결과 조회"""
        return await self.db.get(ConversationEvaluation, evaluation_id)
    
    async def get_session_evaluations(
        self,
        session_id: int
    ) -> List[ConversationEvaluation]:
        """특정 세션의 모든 평가 결과 조회"""
        query = (
            select(ConversationEvaluation)
            .where(ConversationEvaluation.conversation_session_id == session_id)
            .order_by(ConversationEvaluation.created_at.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_student_evaluations(
        self,
        student_id: int,
        limit: int = 10
    ) -> List[ConversationEvaluation]:
        """특정 학생의 평가 결과 조회"""
        query = (
            select(ConversationEvaluation)
            .where(ConversationEvaluation.student_id == student_id)
            .order_by(ConversationEvaluation.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

