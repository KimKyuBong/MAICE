"""
MAICE 에이전트 메트릭 수집 시스템

에이전트별 성능 메트릭을 수집하고 Redis에 저장하여
실시간 모니터링을 지원합니다.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
from enum import Enum

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """메트릭 타입"""
    COUNTER = "counter"  # 누적 카운터 (요청 수, 에러 수)
    GAUGE = "gauge"  # 현재 값 (메모리 사용량, 활성 세션)
    HISTOGRAM = "histogram"  # 분포 (응답 시간)
    TIMER = "timer"  # 시간 측정


@dataclass
class MetricData:
    """메트릭 데이터 구조"""
    agent_name: str
    metric_name: str
    metric_type: str
    value: float
    timestamp: float
    labels: Dict[str, str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "agent_name": self.agent_name,
            "metric_name": self.metric_name,
            "metric_type": self.metric_type,
            "value": self.value,
            "timestamp": self.timestamp,
            "labels": self.labels or {}
        }


class AgentMetrics:
    """에이전트 메트릭 수집기"""
    
    def __init__(self, agent_name: str, redis_url: str = None):
        """
        Args:
            agent_name: 에이전트 이름
            redis_url: Redis 연결 URL
        """
        self.agent_name = agent_name
        self.redis_url = redis_url or "redis://redis:6379"
        self.redis_client: Optional[redis.Redis] = None
        
        # 메트릭 저장소 (Redis 연결 전까지 메모리에 저장)
        self._metrics: Dict[str, Any] = {
            "counters": {},  # 카운터
            "gauges": {},  # 게이지
            "histograms": {},  # 히스토그램
            "timers": {}  # 타이머
        }
        
        # Redis 키 prefix
        self.key_prefix = f"maice:metrics:{agent_name}"
        
        # 백그라운드 플러시 태스크
        self._flush_task: Optional[asyncio.Task] = None
        self._flush_interval = 5  # 5초마다 Redis에 저장
    
    async def initialize(self):
        """Redis 연결 및 백그라운드 태스크 시작"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info(f"✅ [{self.agent_name}] 메트릭 수집기 Redis 연결 완료")
            
            # 백그라운드 플러시 시작
            self._flush_task = asyncio.create_task(self._flush_loop())
            
        except Exception as e:
            logger.error(f"❌ [{self.agent_name}] 메트릭 수집기 초기화 실패: {e}")
            self.redis_client = None
    
    async def cleanup(self):
        """리소스 정리"""
        try:
            # 플러시 태스크 중지
            if self._flush_task:
                self._flush_task.cancel()
                try:
                    await self._flush_task
                except asyncio.CancelledError:
                    pass
            
            # 마지막 플러시
            await self._flush_to_redis()
            
            # Redis 연결 종료
            if self.redis_client:
                await self.redis_client.close()
                
            logger.info(f"✅ [{self.agent_name}] 메트릭 수집기 정리 완료")
            
        except Exception as e:
            logger.error(f"❌ [{self.agent_name}] 메트릭 수집기 정리 실패: {e}")
    
    # ========== 카운터 메트릭 ==========
    
    def increment_counter(self, metric_name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """카운터 증가"""
        key = self._make_key(metric_name, labels)
        self._metrics["counters"][key] = self._metrics["counters"].get(key, 0) + value
    
    def get_counter(self, metric_name: str, labels: Dict[str, str] = None) -> float:
        """카운터 조회"""
        key = self._make_key(metric_name, labels)
        return self._metrics["counters"].get(key, 0)
    
    # ========== 게이지 메트릭 ==========
    
    def set_gauge(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """게이지 설정"""
        key = self._make_key(metric_name, labels)
        self._metrics["gauges"][key] = value
    
    def get_gauge(self, metric_name: str, labels: Dict[str, str] = None) -> float:
        """게이지 조회"""
        key = self._make_key(metric_name, labels)
        return self._metrics["gauges"].get(key, 0)
    
    # ========== 히스토그램 메트릭 ==========
    
    def record_histogram(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """히스토그램 기록"""
        key = self._make_key(metric_name, labels)
        if key not in self._metrics["histograms"]:
            self._metrics["histograms"][key] = []
        self._metrics["histograms"][key].append(value)
        
        # 최근 1000개만 유지
        if len(self._metrics["histograms"][key]) > 1000:
            self._metrics["histograms"][key] = self._metrics["histograms"][key][-1000:]
    
    def get_histogram_stats(self, metric_name: str, labels: Dict[str, str] = None) -> Dict[str, float]:
        """히스토그램 통계 조회"""
        key = self._make_key(metric_name, labels)
        values = self._metrics["histograms"].get(key, [])
        
        if not values:
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}
        
        sorted_values = sorted(values)
        count = len(sorted_values)
        
        return {
            "count": count,
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "avg": sum(sorted_values) / count,
            "p50": sorted_values[int(count * 0.5)],
            "p95": sorted_values[int(count * 0.95)] if count > 20 else sorted_values[-1],
            "p99": sorted_values[int(count * 0.99)] if count > 100 else sorted_values[-1]
        }
    
    # ========== 타이머 메트릭 ==========
    
    @asynccontextmanager
    async def measure_time(self, metric_name: str, labels: Dict[str, str] = None):
        """시간 측정 컨텍스트 매니저
        
        사용 예시:
            async with metrics.measure_time("process_question"):
                await process_question()
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_histogram(metric_name, duration, labels)
            
            # 카운터도 자동 증가
            self.increment_counter(f"{metric_name}_total", 1.0, labels)
    
    # ========== 공통 메트릭 헬퍼 ==========
    
    def record_request(self, operation: str, success: bool = True, duration: float = None):
        """요청 기록 (통합 헬퍼)"""
        labels = {"operation": operation, "status": "success" if success else "error"}
        
        # 카운터
        self.increment_counter("requests_total", 1.0, labels)
        
        # 에러 카운터
        if not success:
            self.increment_counter("errors_total", 1.0, {"operation": operation})
        
        # 응답 시간
        if duration is not None:
            self.record_histogram("request_duration_seconds", duration, {"operation": operation})
    
    def record_error(self, error_type: str, operation: str = None):
        """에러 기록"""
        labels = {"error_type": error_type}
        if operation:
            labels["operation"] = operation
        
        self.increment_counter("errors_total", 1.0, labels)
    
    # ========== 내부 헬퍼 ==========
    
    def _make_key(self, metric_name: str, labels: Dict[str, str] = None) -> str:
        """메트릭 키 생성"""
        if not labels:
            return metric_name
        
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{metric_name}{{{label_str}}}"
    
    async def _flush_loop(self):
        """백그라운드 플러시 루프"""
        while True:
            try:
                await asyncio.sleep(self._flush_interval)
                await self._flush_to_redis()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ [{self.agent_name}] 메트릭 플러시 실패: {e}")
    
    async def _flush_to_redis(self):
        """Redis에 메트릭 저장"""
        if not self.redis_client:
            return
        
        try:
            timestamp = time.time()
            
            # 카운터 저장
            for key, value in self._metrics["counters"].items():
                redis_key = f"{self.key_prefix}:counter:{key}"
                await self.redis_client.set(redis_key, value, ex=3600)  # 1시간 TTL
            
            # 게이지 저장
            for key, value in self._metrics["gauges"].items():
                redis_key = f"{self.key_prefix}:gauge:{key}"
                await self.redis_client.set(redis_key, value, ex=3600)
            
            # 히스토그램 통계 저장
            for key, values in self._metrics["histograms"].items():
                if values:
                    stats = self.get_histogram_stats(key.split("{")[0], None)
                    redis_key = f"{self.key_prefix}:histogram:{key}"
                    await self.redis_client.hset(
                        redis_key,
                        mapping={k: str(v) for k, v in stats.items()}
                    )
                    await self.redis_client.expire(redis_key, 3600)
            
            # 에이전트 상태 업데이트
            status_key = f"maice:agent_status:{self.agent_name}"
            status = {
                "last_update": timestamp,
                "is_alive": "true",
                "metrics_count": len(self._metrics["counters"]) + len(self._metrics["gauges"])
            }
            await self.redis_client.hset(status_key, mapping=status)
            await self.redis_client.expire(status_key, 60)  # 1분 TTL
            
        except Exception as e:
            logger.error(f"❌ [{self.agent_name}] Redis 플러시 실패: {e}")
    
    # ========== 메트릭 조회 (Redis에서) ==========
    
    async def get_all_metrics(self) -> Dict[str, Any]:
        """전체 메트릭 조회"""
        if not self.redis_client:
            return self._get_memory_metrics()
        
        try:
            result = {
                "agent_name": self.agent_name,
                "timestamp": time.time(),
                "counters": {},
                "gauges": {},
                "histograms": {}
            }
            
            # 카운터 조회
            counter_keys = await self.redis_client.keys(f"{self.key_prefix}:counter:*")
            for key in counter_keys:
                metric_name = key.split(":")[-1]
                value = await self.redis_client.get(key)
                result["counters"][metric_name] = float(value) if value else 0
            
            # 게이지 조회
            gauge_keys = await self.redis_client.keys(f"{self.key_prefix}:gauge:*")
            for key in gauge_keys:
                metric_name = key.split(":")[-1]
                value = await self.redis_client.get(key)
                result["gauges"][metric_name] = float(value) if value else 0
            
            # 히스토그램 조회
            histogram_keys = await self.redis_client.keys(f"{self.key_prefix}:histogram:*")
            for key in histogram_keys:
                metric_name = key.split(":")[-1]
                stats = await self.redis_client.hgetall(key)
                result["histograms"][metric_name] = {
                    k: float(v) for k, v in stats.items()
                } if stats else {}
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [{self.agent_name}] 메트릭 조회 실패: {e}")
            return self._get_memory_metrics()
    
    def _get_memory_metrics(self) -> Dict[str, Any]:
        """메모리에서 메트릭 조회"""
        result = {
            "agent_name": self.agent_name,
            "timestamp": time.time(),
            "counters": dict(self._metrics["counters"]),
            "gauges": dict(self._metrics["gauges"]),
            "histograms": {}
        }
        
        # 히스토그램 통계 계산
        for key in self._metrics["histograms"]:
            result["histograms"][key] = self.get_histogram_stats(key.split("{")[0], None)
        
        return result


# ========== 전역 메트릭 조회 함수 ==========

async def get_all_agent_metrics(redis_url: str = None) -> List[Dict[str, Any]]:
    """모든 에이전트 메트릭 조회"""
    redis_url = redis_url or "redis://redis:6379"
    
    try:
        client = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        
        # 활성 에이전트 목록 조회
        agent_status_keys = await client.keys("maice:agent_status:*")
        
        results = []
        for key in agent_status_keys:
            agent_name = key.split(":")[-1]
            
            # 상태 조회
            status = await client.hgetall(key)
            if not status:
                continue
            
            # 메트릭 조회
            metrics = {
                "agent_name": agent_name,
                "timestamp": float(status.get("last_update", 0)),
                "is_alive": status.get("is_alive") == "true",
                "counters": {},
                "gauges": {},
                "histograms": {}
            }
            
            # 카운터
            counter_keys = await client.keys(f"maice:metrics:{agent_name}:counter:*")
            for ck in counter_keys:
                metric_name = ck.split(":")[-1]
                value = await client.get(ck)
                metrics["counters"][metric_name] = float(value) if value else 0
            
            # 게이지
            gauge_keys = await client.keys(f"maice:metrics:{agent_name}:gauge:*")
            for gk in gauge_keys:
                metric_name = gk.split(":")[-1]
                value = await client.get(gk)
                metrics["gauges"][metric_name] = float(value) if value else 0
            
            # 히스토그램
            histogram_keys = await client.keys(f"maice:metrics:{agent_name}:histogram:*")
            for hk in histogram_keys:
                metric_name = hk.split(":")[-1]
                stats = await client.hgetall(hk)
                metrics["histograms"][metric_name] = {
                    k: float(v) for k, v in stats.items()
                } if stats else {}
            
            results.append(metrics)
        
        await client.close()
        return results
        
    except Exception as e:
        logger.error(f"❌ 전체 에이전트 메트릭 조회 실패: {e}")
        return []


