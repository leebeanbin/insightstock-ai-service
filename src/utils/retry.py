"""
Retry Utility
재시도 로직 및 백오프 전략
"""

import asyncio
from typing import Callable, TypeVar, Any
from functools import wraps
from loguru import logger

T = TypeVar('T')


def exponential_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
    """
    지수 백오프 계산
    
    Args:
        attempt: 시도 횟수 (1부터 시작)
        base_delay: 기본 지연 시간 (초)
        max_delay: 최대 지연 시간 (초)
    
    Returns:
        지연 시간 (초)
    """
    delay = base_delay * (2 ** (attempt - 1))
    return min(delay, max_delay)


def retry(
    max_attempts: int = 3,
    backoff: Callable[[int], float] = exponential_backoff,
    exceptions: tuple = (Exception,),
    on_retry: Callable[[Exception, int], None] = None,
):
    """
    재시도 데코레이터
    
    Args:
        max_attempts: 최대 시도 횟수
        backoff: 백오프 함수
        exceptions: 재시도할 예외 타입
        on_retry: 재시도 시 호출할 콜백
    
    Usage:
        @retry(max_attempts=3)
        async def my_function():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts:
                        delay = backoff(attempt)
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay}s..."
                        )
                        
                        if on_retry:
                            on_retry(e, attempt)
                        
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {e}"
                        )
                        raise
            
            # 이 코드는 도달하지 않지만 타입 체커를 위해 필요
            if last_exception:
                raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts:
                        delay = backoff(attempt)
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay}s..."
                        )
                        
                        if on_retry:
                            on_retry(e, attempt)
                        
                        import time
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {e}"
                        )
                        raise
            
            if last_exception:
                raise last_exception
        
        # 비동기 함수인지 확인
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

