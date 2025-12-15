"""
Cache Utility
Redis 기반 캐싱 (프로덕션 권장)
Redis 연결 실패 시 인메모리 캐시로 폴백
"""

import json
import pickle
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from functools import wraps
from loguru import logger

try:
    from src.config.redis import get_redis_client
    REDIS_AVAILABLE = True
except Exception as e:
    logger.warning(f"Redis not available, using in-memory cache: {e}")
    REDIS_AVAILABLE = False


class SimpleCache:
    """간단한 인메모리 캐시 (Redis 폴백용)"""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        if key not in self._cache:
            return None

        entry = self._cache[key]

        # TTL 확인
        if entry.get("expires_at") and datetime.now() > entry["expires_at"]:
            del self._cache[key]
            return None

        return entry["value"]

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """
        캐시에 값 저장

        Args:
            key: 캐시 키
            value: 저장할 값
            ttl: Time to Live (초)
        """
        expires_at = datetime.now() + timedelta(seconds=ttl)
        self._cache[key] = {
            "value": value,
            "expires_at": expires_at,
        }

    def delete(self, key: str) -> None:
        """캐시에서 값 삭제"""
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        """전체 캐시 초기화"""
        self._cache.clear()

    def size(self) -> int:
        """캐시 크기 반환"""
        return len(self._cache)


class RedisCache:
    """Redis 기반 캐시"""

    def __init__(self):
        self._client = None
        self._fallback = SimpleCache()

    @property
    def client(self):
        """Redis 클라이언트 (지연 로딩)"""
        if self._client is None:
            try:
                self._client = get_redis_client()
            except Exception as e:
                logger.warning(f"Redis unavailable, using fallback: {e}")
                return None
        return self._client

    def get(self, key: str) -> Optional[Any]:
        """
        캐시에서 값 조회
        
        Args:
            key: 캐시 키
        
        Returns:
            캐시된 값 또는 None
        """
        if not self.client:
            return self._fallback.get(key)

        try:
            data = self.client.get(key)
            if data is None:
                return None

            # Pickle로 역직렬화
            return pickle.loads(data)
        except Exception as e:
            logger.warning(f"Redis get error, using fallback: {e}")
            return self._fallback.get(key)

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """
        캐시에 값 저장

        Args:
            key: 캐시 키
            value: 저장할 값
            ttl: Time to Live (초)
        """
        if not self.client:
            self._fallback.set(key, value, ttl)
            return

        try:
            # Pickle로 직렬화
            data = pickle.dumps(value)
            self.client.setex(key, ttl, data)
        except Exception as e:
            logger.warning(f"Redis set error, using fallback: {e}")
            self._fallback.set(key, value, ttl)

    def delete(self, key: str) -> None:
        """캐시에서 값 삭제"""
        if not self.client:
            self._fallback.delete(key)
            return

        try:
            self.client.delete(key)
        except Exception as e:
            logger.warning(f"Redis delete error, using fallback: {e}")
            self._fallback.delete(key)

    def clear(self) -> None:
        """전체 캐시 초기화 (현재 DB만)"""
        if not self.client:
            self._fallback.clear()
            return

        try:
            self.client.flushdb()
        except Exception as e:
            logger.warning(f"Redis clear error, using fallback: {e}")
            self._fallback.clear()

    def size(self) -> int:
        """캐시 크기 반환"""
        if not self.client:
            return self._fallback.size()

        try:
            return self.client.dbsize()
        except Exception as e:
            logger.warning(f"Redis size error, using fallback: {e}")
            return self._fallback.size()


# 전역 캐시 인스턴스 (Redis 우선, 실패 시 인메모리)
if REDIS_AVAILABLE:
    try:
        cache = RedisCache()
        logger.info("Using Redis cache")
    except Exception as e:
        logger.warning(f"Redis initialization failed, using in-memory cache: {e}")
        cache = SimpleCache()
else:
    cache = SimpleCache()
    logger.info("Using in-memory cache (Redis not available)")


def cache_result(ttl: int = 3600, key_func: Optional[Callable] = None):
    """
    함수 결과 캐싱 데코레이터

    Args:
        ttl: 캐시 TTL (초)
        key_func: 캐시 키 생성 함수 (None이면 자동 생성)

    Usage:
        @cache_result(ttl=3600)
        async def get_embedding(text: str):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # 캐시 키 생성
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # 캐시 확인
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached

            # 함수 실행
            result = await func(*args, **kwargs)

            # 캐시 저장
            cache.set(cache_key, result, ttl)
            logger.debug(f"Cache set: {cache_key}")

            return result

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # 캐시 키 생성
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # 캐시 확인
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached

            # 함수 실행
            result = func(*args, **kwargs)

            # 캐시 저장
            cache.set(cache_key, result, ttl)
            logger.debug(f"Cache set: {cache_key}")

            return result

        # 비동기 함수인지 확인
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator

