"""
Transaction 테스트
트랜잭션 및 Saga 패턴 테스트
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.utils.transaction import (
    TransactionManager,
    transactional,
    create_saga,
    SagaTransaction,
)


class TestTransactionManager:
    """TransactionManager 테스트"""

    def test_transaction_context(self):
        """트랜잭션 컨텍스트 테스트"""
        manager = TransactionManager()

        with manager.transaction() as tx:
            assert tx is not None
            assert "id" in tx
            assert "operations" in tx
            assert "compensations" in tx

    def test_transaction_read_only(self):
        """읽기 전용 트랜잭션 테스트"""
        manager = TransactionManager()

        with manager.transaction(read_only=True) as tx:
            assert tx["read_only"] is True


class TestTransactionalDecorator:
    """@transactional 데코레이터 테스트"""

    @transactional()
    async def async_function(self, _tx=None):
        """비동기 함수"""
        return "result"

    @transactional()
    def sync_function(self, _tx=None):
        """동기 함수"""
        return "result"

    @pytest.mark.asyncio
    async def test_async_transactional(self):
        """비동기 트랜잭션 데코레이터 테스트"""
        result = await self.async_function()
        assert result == "result"

    def test_sync_transactional(self):
        """동기 트랜잭션 데코레이터 테스트"""
        result = self.sync_function()
        assert result == "result"


class TestSagaTransaction:
    """SagaTransaction 테스트"""

    @pytest.fixture
    def saga(self):
        """SagaTransaction Fixture"""
        return create_saga()

    @pytest.mark.asyncio
    async def test_saga_success(self, saga):
        """Saga 성공 시나리오 테스트"""
        step1_result = None
        step2_result = None

        async def operation1():
            nonlocal step1_result
            step1_result = "step1"
            return step1_result

        async def operation2():
            nonlocal step2_result
            step2_result = "step2"
            return step2_result

        saga.add_step(operation=operation1, step_id="step1")
        saga.add_step(operation=operation2, step_id="step2")

        results = await saga.execute()

        assert len(results) == 2
        assert step1_result == "step1"
        assert step2_result == "step2"

    @pytest.mark.asyncio
    async def test_saga_compensation(self, saga):
        """Saga 보상 트랜잭션 테스트"""
        compensation_called = False

        # 첫 번째 step은 성공, 두 번째 step은 실패
        async def operation1():
            return "step1"

        async def operation2():
            raise Exception("Operation failed")

        async def compensation():
            nonlocal compensation_called
            compensation_called = True

        saga.add_step(operation=operation1, compensation=compensation, step_id="step1")
        saga.add_step(operation=operation2, step_id="step2")

        with pytest.raises(Exception):
            await saga.execute()

        # 첫 번째 step은 성공했으므로 보상 트랜잭션이 실행되어야 함
        assert compensation_called is True

    @pytest.mark.asyncio
    async def test_saga_multiple_steps_compensation(self, saga):
        """Saga 다중 단계 보상 테스트"""
        compensation1_called = False
        compensation2_called = False

        async def operation1():
            return "step1"

        async def operation2():
            raise Exception("Step2 failed")

        async def compensation1():
            nonlocal compensation1_called
            compensation1_called = True

        async def compensation2():
            nonlocal compensation2_called
            compensation2_called = True

        saga.add_step(operation=operation1, compensation=compensation1, step_id="step1")
        saga.add_step(operation=operation2, compensation=compensation2, step_id="step2")

        with pytest.raises(Exception):
            await saga.execute()

        # operation1은 성공했으므로 compensation1 실행
        assert compensation1_called is True
        # operation2는 실패했으므로 compensation2는 실행되지 않아야 함
        # (Saga 패턴: 실패한 step의 compensation은 실행되지 않음)
        assert compensation2_called is False
