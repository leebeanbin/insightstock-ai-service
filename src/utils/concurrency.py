"""
Concurrency Control Utilities
Redis 기반 동시성 제어 (분산 락, Rate Limiting, 트랜잭션)
AI 서비스 특성에 맞게 최적화
"""

import time
import uuid
from typing import Optional, Callable, Any, List, Dict
from contextlib import contextmanager
from loguru import logger

try:
    from src.config.redis import get_redis_client

    REDIS_AVAILABLE = True
except Exception as e:
    logger.warning(f"Redis not available for concurrency control: {e}")
    REDIS_AVAILABLE = False


class DistributedLock:
    """Redis 기반 분산 락 (AI 서비스 최적화)"""

    def __init__(self, key: str, timeout: int = 30, retry_interval: float = 0.1):
        """
        분산 락 초기화

        Args:
            key: 락 키
            timeout: 락 타임아웃 (초)
            retry_interval: 재시도 간격 (초)
        """
        self.key = f"lock:{key}"
        self.timeout = timeout
        self.retry_interval = retry_interval
        self.identifier = str(uuid.uuid4())
        self._client = None

    @property
    def client(self):
        """Redis 클라이언트 (지연 로딩)"""
        if self._client is None and REDIS_AVAILABLE:
            try:
                self._client = get_redis_client()
            except Exception as e:
                logger.warning(f"Redis unavailable for lock: {e}")
        return self._client

    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        락 획득

        Args:
            blocking: 블로킹 모드 (기본값: True)
            timeout: 타임아웃 (초, None이면 무한 대기)

        Returns:
            락 획득 성공 여부
        """
        if not self.client:
            logger.warning("Redis unavailable, lock acquisition skipped")
            return False

        end_time = time.time() + (timeout or float("inf"))

        while True:
            # SET NX EX: 키가 없으면 설정하고 만료 시간 설정
            if self.client.set(
                self.key,
                self.identifier,
                nx=True,  # 키가 없을 때만 설정
                ex=self.timeout,  # 만료 시간
            ):
                logger.debug(f"Lock acquired: {self.key}")
                return True

            if not blocking or time.time() >= end_time:
                return False

            time.sleep(self.retry_interval)

    def release(self) -> bool:
        """
        락 해제

        Returns:
            락 해제 성공 여부
        """
        if not self.client:
            return False

        try:
            # Lua 스크립트로 원자적 연산: 자신의 락만 해제
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            result = self.client.eval(lua_script, 1, self.key, self.identifier)
            if result:
                logger.debug(f"Lock released: {self.key}")
                return True
            else:
                logger.warning(f"Lock release failed (not owner): {self.key}")
                return False
        except Exception as e:
            logger.error(f"Lock release error: {e}")
            return False

    def __enter__(self):
        """Context manager 진입"""
        if not self.acquire():
            raise RuntimeError(f"Failed to acquire lock: {self.key}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 종료"""
        self.release()


@contextmanager
def distributed_lock(key: str, timeout: int = 30, blocking: bool = True):
    """
    분산 락 컨텍스트 매니저

    Args:
        key: 락 키
        timeout: 락 타임아웃 (초)
        blocking: 블로킹 모드

    Usage:
        with distributed_lock("embedding:abc123"):
            # 동시에 하나의 프로세스만 실행
            do_something()
    """
    lock = DistributedLock(key, timeout)
    try:
        if lock.acquire(blocking=blocking):
            yield lock
        else:
            raise RuntimeError(f"Failed to acquire lock: {key}")
    finally:
        lock.release()


class RateLimiter:
    """Redis 기반 Rate Limiter (토큰 버킷 알고리즘)"""

    def __init__(self, key: str, max_requests: int = 100, window: int = 60):
        """
        Rate Limiter 초기화

        Args:
            key: Rate limit 키
            max_requests: 최대 요청 수
            window: 시간 윈도우 (초)
        """
        self.key = f"ratelimit:{key}"
        self.max_requests = max_requests
        self.window = window
        self._client = None

    @property
    def client(self):
        """Redis 클라이언트 (지연 로딩)"""
        if self._client is None and REDIS_AVAILABLE:
            try:
                self._client = get_redis_client()
            except Exception as e:
                logger.warning(f"Redis unavailable for rate limiting: {e}")
        return self._client

    def is_allowed(self) -> tuple[bool, Optional[int]]:
        """
        요청 허용 여부 확인

        Returns:
            (허용 여부, 남은 요청 수)
        """
        if not self.client:
            # Redis 없으면 항상 허용
            return True, None

        try:
            # Lua 스크립트로 원자적 연산
            lua_script = """
            local key = KEYS[1]
            local window = tonumber(ARGV[1])
            local max_requests = tonumber(ARGV[2])
            local current_time = tonumber(ARGV[3])
            
            -- 현재 윈도우의 시작 시간
            local window_start = current_time - (current_time % window)
            local window_key = key .. ":" .. window_start
            
            -- 현재 요청 수 확인
            local count = redis.call("INCR", window_key)
            redis.call("EXPIRE", window_key, window)
            
            if count <= max_requests then
                return {1, max_requests - count}
            else
                return {0, 0}
            end
            """

            current_time = int(time.time())
            result = self.client.eval(
                lua_script,
                1,
                self.key,
                str(self.window),
                str(self.max_requests),
                str(current_time),
            )

            is_allowed = bool(result[0])
            remaining = result[1] if len(result) > 1 else None

            return is_allowed, remaining
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # 에러 시 허용 (fail-open)
            return True, None

    def check(self) -> bool:
        """
        요청 허용 여부만 확인 (간단 버전)

        Returns:
            허용 여부
        """
        allowed, _ = self.is_allowed()
        return allowed


class RedisTransaction:
    """Redis 트랜잭션 래퍼 (MULTI/EXEC)"""

    def __init__(self):
        self._client = None
        self._pipeline = None

    @property
    def client(self):
        """Redis 클라이언트 (지연 로딩)"""
        if self._client is None and REDIS_AVAILABLE:
            try:
                self._client = get_redis_client()
            except Exception as e:
                logger.warning(f"Redis unavailable for transaction: {e}")
        return self._client

    def __enter__(self):
        """트랜잭션 시작"""
        if not self.client:
            logger.warning("Redis unavailable, transaction skipped")
            return self

        self._pipeline = self.client.pipeline()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """트랜잭션 커밋 또는 롤백"""
        if not self._pipeline:
            return

        try:
            if exc_type is None:
                # 성공 시 실행
                self._pipeline.execute()
                logger.debug("Transaction committed")
            else:
                # 에러 시 롤백 (Redis는 DISCARD)
                self._pipeline.reset()
                logger.debug("Transaction rolled back")
        except Exception as e:
            logger.error(f"Transaction error: {e}")
            self._pipeline.reset()

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """트랜잭션 내에서 SET 명령 추가"""
        if not self._pipeline:
            if self.client:
                if ttl:
                    self.client.setex(key, ttl, value)
                else:
                    self.client.set(key, value)
            return

        if ttl:
            self._pipeline.setex(key, ttl, value)
        else:
            self._pipeline.set(key, value)

    def setex(self, key: str, ttl: int, value: Any):
        """트랜잭션 내에서 SETEX 명령 추가 (별칭)"""
        self.set(key, value, ttl)

    def get(self, key: str):
        """트랜잭션 내에서 GET 명령 추가"""
        if not self._pipeline:
            if self.client:
                return self.client.get(key)
            return None

        self._pipeline.get(key)

    def delete(self, key: str):
        """트랜잭션 내에서 DELETE 명령 추가"""
        if not self._pipeline:
            if self.client:
                self.client.delete(key)
            return

        self._pipeline.delete(key)

    def incr(self, key: str):
        """트랜잭션 내에서 INCR 명령 추가"""
        if not self._pipeline:
            if self.client:
                return self.client.incr(key)
            return None

        self._pipeline.incr(key)

    def execute(self) -> List[Any]:
        """트랜잭션 실행 (수동 실행 시)"""
        if not self._pipeline:
            return []

        try:
            results = self._pipeline.execute()
            return results
        except Exception as e:
            logger.error(f"Transaction execute error: {e}")
            return []


@contextmanager
def redis_transaction():
    """
    Redis 트랜잭션 컨텍스트 매니저

    Usage:
        with redis_transaction() as tx:
            tx.set("key1", "value1")
            tx.set("key2", "value2")
            # 자동으로 커밋 또는 롤백
    """
    tx = RedisTransaction()
    try:
        yield tx
    except Exception as e:
        logger.error(f"Transaction error: {e}")
        raise


class Semaphore:
    """Redis 기반 세마포어 (동시 실행 수 제한)"""

    def __init__(self, key: str, limit: int = 10):
        """
        세마포어 초기화

        Args:
            key: 세마포어 키
            limit: 최대 동시 실행 수
        """
        self.key = f"semaphore:{key}"
        self.limit = limit
        self.identifier = str(uuid.uuid4())
        self._client = None

    @property
    def client(self):
        """Redis 클라이언트 (지연 로딩)"""
        if self._client is None and REDIS_AVAILABLE:
            try:
                self._client = get_redis_client()
            except Exception as e:
                logger.warning(f"Redis unavailable for semaphore: {e}")
        return self._client

    def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        세마포어 획득

        Args:
            timeout: 타임아웃 (초)

        Returns:
            획득 성공 여부
        """
        if not self.client:
            logger.warning("Redis unavailable, semaphore acquisition skipped")
            return False

        end_time = time.time() + (timeout or float("inf"))

        while True:
            try:
                # 현재 카운트 확인
                current = self.client.zcard(self.key)

                if current < self.limit:
                    # 세마포어 획득
                    now = time.time()
                    self.client.zadd(self.key, {self.identifier: now})
                    # 만료 시간 설정 (10분)
                    self.client.expire(self.key, 600)

                    logger.debug(
                        f"Semaphore acquired: {self.key} ({current + 1}/{self.limit})"
                    )
                    return True

                if time.time() >= end_time:
                    return False

                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Semaphore acquire error: {e}")
                return False

    def release(self) -> bool:
        """
        세마포어 해제

        Returns:
            해제 성공 여부
        """
        if not self.client:
            return False

        try:
            removed = self.client.zrem(self.key, self.identifier)
            if removed:
                logger.debug(f"Semaphore released: {self.key}")
            return bool(removed)
        except Exception as e:
            logger.error(f"Semaphore release error: {e}")
            return False

    def __enter__(self):
        """Context manager 진입"""
        if not self.acquire():
            raise RuntimeError(f"Failed to acquire semaphore: {self.key}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 종료"""
        self.release()


@contextmanager
def semaphore(key: str, limit: int = 10, timeout: Optional[float] = None):
    """
    세마포어 컨텍스트 매니저

    Args:
        key: 세마포어 키
        limit: 최대 동시 실행 수
        timeout: 타임아웃 (초)

    Usage:
        with semaphore("embedding_batch", limit=5):
            # 최대 5개까지 동시 실행
            do_something()
    """
    sem = Semaphore(key, limit)
    try:
        if sem.acquire(timeout=timeout):
            yield sem
        else:
            raise RuntimeError(f"Failed to acquire semaphore: {key}")
    finally:
        sem.release()

