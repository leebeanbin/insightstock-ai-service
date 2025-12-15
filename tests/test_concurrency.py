"""
Concurrency Control 테스트
분산 락, 세마포어, 레이트 리미터 테스트
"""

import pytest
import time
from unittest.mock import Mock, patch
from src.utils.concurrency import (
    DistributedLock,
    Semaphore,
    RateLimiter,
    redis_transaction,
)


class TestDistributedLock:
    """DistributedLock 테스트"""

    @patch("src.utils.concurrency.get_redis_client")
    def test_lock_acquire_release(self, mock_redis):
        """락 획득 및 해제 테스트"""
        mock_client = Mock()
        mock_client.set = Mock(return_value=True)
        mock_client.delete = Mock(return_value=1)
        mock_redis.return_value = mock_client

        lock = DistributedLock("test_lock", timeout=10)

        # 락 획득
        result = lock.acquire()
        assert result is True
        assert mock_client.set.called

        # 락 해제
        lock.release()
        assert mock_client.delete.called

    @patch("src.utils.concurrency.get_redis_client")
    def test_lock_context_manager(self, mock_redis):
        """락 컨텍스트 매니저 테스트"""
        mock_client = Mock()
        mock_client.set = Mock(return_value=True)
        mock_client.delete = Mock(return_value=1)
        mock_redis.return_value = mock_client

        with DistributedLock("test_lock", timeout=10):
            assert mock_client.set.called

        assert mock_client.delete.called


class TestSemaphore:
    """Semaphore 테스트"""

    @patch("src.utils.concurrency.get_redis_client")
    def test_semaphore_acquire_release(self, mock_redis):
        """세마포어 획득 및 해제 테스트"""
        mock_client = Mock()
        mock_client.incr = Mock(return_value=1)
        mock_client.decr = Mock(return_value=0)
        mock_redis.return_value = mock_client

        semaphore = Semaphore("test_semaphore", limit=3)

        # 세마포어 획득
        result = semaphore.acquire()
        assert result is True
        assert mock_client.incr.called

        # 세마포어 해제
        semaphore.release()
        assert mock_client.decr.called

    @patch("src.utils.concurrency.get_redis_client")
    def test_semaphore_limit(self, mock_redis):
        """세마포어 제한 테스트"""
        mock_client = Mock()
        # 제한 초과 시 False 반환
        mock_client.incr = Mock(return_value=4)  # limit=3 초과
        mock_redis.return_value = mock_client

        semaphore = Semaphore("test_semaphore", limit=3)
        result = semaphore.acquire()

        # 제한 초과 시 False 반환
        assert result is False


class TestRateLimiter:
    """RateLimiter 테스트"""

    @patch("src.utils.concurrency.get_redis_client")
    def test_rate_limiter_allow(self, mock_redis):
        """레이트 리미터 허용 테스트"""
        mock_client = Mock()
        mock_client.zcard = Mock(return_value=5)  # 현재 요청 수
        mock_client.zremrangebyscore = Mock(return_value=0)
        mock_client.zadd = Mock(return_value=1)
        mock_redis.return_value = mock_client

        limiter = RateLimiter("test_limiter", max_requests=10, window=60)
        result = limiter.is_allowed("user_1")

        assert result is True

    @patch("src.utils.concurrency.get_redis_client")
    def test_rate_limiter_block(self, mock_redis):
        """레이트 리미터 차단 테스트"""
        mock_client = Mock()
        mock_client.zcard = Mock(return_value=10)  # 제한 초과
        mock_client.zremrangebyscore = Mock(return_value=0)
        mock_redis.return_value = mock_client

        limiter = RateLimiter("test_limiter", max_requests=10, window=60)
        result = limiter.is_allowed("user_1")

        assert result is False


class TestRedisTransaction:
    """RedisTransaction 테스트"""

    @patch("src.utils.concurrency.get_redis_client")
    def test_redis_transaction(self, mock_redis):
        """Redis 트랜잭션 테스트"""
        mock_client = Mock()
        mock_pipeline = Mock()
        mock_pipeline.set = Mock(return_value=mock_pipeline)
        mock_pipeline.execute = Mock(return_value=[True])
        mock_client.pipeline = Mock(return_value=mock_pipeline)
        mock_redis.return_value = mock_client

        with redis_transaction() as tx:
            tx.set("key", "value", ttl=60)

        assert mock_pipeline.set.called
        assert mock_pipeline.execute.called
