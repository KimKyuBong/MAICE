"""
MAICE 에이전트 워커 - 멀티프로세스 방식으로 각 에이전트 독립 실행
"""

import uvloop
import asyncio
import logging
import signal
import sys
import multiprocessing as mp
from typing import List, Dict
import time
import os

# uvloop 이벤트 루프 최적화 적용
uvloop.install()

from agents.question_classifier.agent import QuestionClassifierAgent
from agents.question_improvement.agent import QuestionImprovementAgent
from agents.answer_generator.agent import AnswerGeneratorAgent
from agents.observer.agent import ObserverAgent
from agents.freetalker.agent import FreeTalkerAgent

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def run_agent_process(agent_class, agent_name: str):
    """개별 에이전트를 별도 프로세스에서 실행"""

    async def agent_runner():
        # 프로세스별 로깅 설정
        logger = logging.getLogger(f"agent.{agent_name}")
        logger.info(f"🚀 {agent_name} 프로세스 시작 (PID: {os.getpid()})")

        agent = None
        try:
            # 에이전트 생성 및 초기화
            agent = agent_class()
            await agent.initialize()
            logger.info(f"✅ {agent_name} 초기화 완료")

            # 구독자 실행 (무한 루프)
            await agent.run_subscriber()

        except Exception as e:
            logger.error(f"❌ {agent_name} 실행 오류: {e}")
        finally:
            if agent:
                try:
                    await agent.cleanup()
                    logger.info(f"✅ {agent_name} 정리 완료")
                except Exception as e:
                    logger.error(f"❌ {agent_name} 정리 실패: {e}")

    # 각 프로세스에서 asyncio 실행
    try:
        asyncio.run(agent_runner())
    except KeyboardInterrupt:
        logger = logging.getLogger(f"agent.{agent_name}")
        logger.info(f"🛑 {agent_name} 키보드 인터럽트로 종료")
    except Exception as e:
        logger = logging.getLogger(f"agent.{agent_name}")
        logger.error(f"❌ {agent_name} 프로세스 오류: {e}")


class AgentWorker:
    """MAICE 에이전트 워커 - 멀티프로세스 방식"""

    def __init__(self):
        self.processes: Dict[str, mp.Process] = {}
        self.is_running = False
        self._shutdown_event = asyncio.Event()

        # 에이전트 설정
        self.agent_configs = [
            (QuestionClassifierAgent, "QuestionClassifier"),
            (QuestionImprovementAgent, "QuestionImprovement"),
            (AnswerGeneratorAgent, "AnswerGenerator"),
            (ObserverAgent, "Observer"),
            (FreeTalkerAgent, "FreeTalker"),
        ]

        # 시그널 핸들러 설정
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """시그널 핸들러"""
        logger.info(f"🛑 시그널 수신: {signum}")
        self._shutdown_event.set()

    def start_agent_processes(self):
        """에이전트 프로세스들 시작"""
        try:
            logger.info("🚀 에이전트 프로세스 시작...")

            for agent_class, agent_name in self.agent_configs:
                try:
                    # 각 에이전트를 별도 프로세스에서 실행
                    process = mp.Process(
                        target=run_agent_process,
                        args=(agent_class, agent_name),
                        name=f"agent_{agent_name}",
                    )
                    process.start()
                    self.processes[agent_name] = process

                    logger.info(
                        f"✅ {agent_name} 프로세스 시작 완료 (PID: {process.pid})"
                    )

                except Exception as e:
                    logger.error(f"❌ {agent_name} 프로세스 시작 실패: {e}")
                    raise

            self.is_running = True
            logger.info("✅ 모든 에이전트 프로세스 시작 완료")

        except Exception as e:
            logger.error(f"❌ 에이전트 프로세스 시작 실패: {e}")
            raise

    def stop_agent_processes(self):
        """에이전트 프로세스들 중지"""
        try:
            logger.info("🛑 에이전트 프로세스 중지 시작...")

            for agent_name, process in self.processes.items():
                try:
                    if process.is_alive():
                        logger.info(
                            f"🛑 {agent_name} 프로세스 종료 중 (PID: {process.pid})"
                        )
                        process.terminate()

                        # 최대 5초 대기
                        process.join(timeout=5)

                        if process.is_alive():
                            logger.warning(
                                f"⚠️ {agent_name} 강제 종료 (PID: {process.pid})"
                            )
                            process.kill()
                            process.join(timeout=2)

                        logger.info(f"✅ {agent_name} 프로세스 정리 완료")
                    else:
                        logger.info(f"ℹ️ {agent_name} 프로세스 이미 종료됨")

                except Exception as e:
                    logger.warning(f"⚠️ {agent_name} 프로세스 정리 실패: {e}")

            self.processes.clear()
            self.is_running = False
            logger.info("✅ 모든 에이전트 프로세스 중지 완료")

        except Exception as e:
            logger.error(f"❌ 에이전트 프로세스 중지 실패: {e}")

    async def monitor_processes(self):
        """프로세스 상태 모니터링"""
        while self.is_running:
            try:
                dead_processes = []

                for agent_name, process in self.processes.items():
                    if not process.is_alive():
                        logger.warning(
                            f"⚠️ {agent_name} 프로세스 죽음 감지 (PID: {process.pid})"
                        )
                        dead_processes.append(agent_name)

                # 죽은 프로세스 재시작 (옵션)
                for agent_name in dead_processes:
                    logger.info(f"🔄 {agent_name} 프로세스 재시작 시도...")

                    # 기존 프로세스 정리
                    old_process = self.processes.pop(agent_name)
                    old_process.join(timeout=1)

                    # 새 프로세스 시작
                    agent_class = next(
                        cls for cls, name in self.agent_configs if name == agent_name
                    )
                    new_process = mp.Process(
                        target=run_agent_process,
                        args=(agent_class, agent_name),
                        name=f"agent_{agent_name}",
                    )
                    new_process.start()
                    self.processes[agent_name] = new_process

                    logger.info(
                        f"✅ {agent_name} 프로세스 재시작 완료 (PID: {new_process.pid})"
                    )

                # 5초마다 체크
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"❌ 프로세스 모니터링 오류: {e}")
                await asyncio.sleep(5)

    async def run(self):
        """워커 실행"""
        try:
            logger.info("🚀 MAICE 에이전트 워커 시작 (멀티프로세스 모드)")

            # 에이전트 프로세스들 시작
            self.start_agent_processes()

            # 프로세스 모니터링 시작
            monitor_task = asyncio.create_task(self.monitor_processes())

            # 종료 신호 대기
            await self._shutdown_event.wait()

            logger.info("🛑 종료 신호 수신, 워커 종료 시작")

            # 모니터링 중지
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

        except Exception as e:
            logger.error(f"❌ 워커 실행 오류: {e}")
            raise

        finally:
            # 에이전트 프로세스들 정리
            self.stop_agent_processes()
            logger.info("🛑 워커 종료")


async def main():
    """메인 함수"""
    # 환경변수 확인 및 로깅
    llm_provider = os.getenv("LLM_PROVIDER", "openai")
    openai_model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4")
    anthropic_model = os.getenv("ANTHROPIC_CHAT_MODEL", "claude-3-sonnet")
    google_model = os.getenv("GOOGLE_CHAT_MODEL", "gemini-pro")
    mcp_model = os.getenv("MCP_MODEL", "penGPT")

    logger.info("=" * 80)
    logger.info("🤖 MAICE 에이전트 시스템 시작")
    logger.info("=" * 80)
    logger.info(f"📊 LLM 설정:")
    logger.info(f"   ├─ 프로바이더: {llm_provider.upper()}")

    if llm_provider.lower() == "openai":
        logger.info(f"   ├─ OpenAI 모델: {openai_model}")
        logger.info(
            f"   └─ API 키: {'✅ 설정됨' if os.getenv('OPENAI_API_KEY') else '❌ 미설정'}"
        )
    elif llm_provider.lower() == "anthropic":
        logger.info(f"   ├─ Anthropic 모델: {anthropic_model}")
        logger.info(
            f"   └─ API 키: {'✅ 설정됨' if os.getenv('ANTHROPIC_API_KEY') else '❌ 미설정'}"
        )
    elif llm_provider.lower() == "google":
        logger.info(f"   ├─ Google 모델: {google_model}")
        logger.info(
            f"   └─ API 키: {'✅ 설정됨' if os.getenv('GEMINI_API_KEY') else '❌ 미설정'}"
        )
    elif llm_provider.lower() == "mcp":
        logger.info(f"   ├─ MCP 모델: {mcp_model}")
        logger.info(
            f"   └─ 서버 URL: {os.getenv('MCP_SERVER_URL', 'http://192.168.1.105:5555')}"
        )

    logger.info("=" * 80)

    worker = AgentWorker()

    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("🛑 키보드 인터럽트로 종료")
    except Exception as e:
        logger.error(f"❌ 메인 함수 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 멀티프로세싱을 위한 설정
    mp.set_start_method("spawn", force=True)  # Docker 환경에서 안전한 방법

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 키보드 인터럽트로 종료")
    except Exception as e:
        logger.error(f"❌ 메인 실행 오류: {e}")
        sys.exit(1)
