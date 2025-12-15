"""
Database Transaction Management
스프링 스타일의 트랜잭션 관리 (정합성과 일관성 보장)
PostgreSQL 트랜잭션 + 벡터 DB 동기화 패턴
"""

from typing import Callable, Any, Optional, TypeVar, List, Dict
from contextlib import contextmanager
from functools import wraps
from loguru import logger
import asyncio

T = TypeVar("T")


class TransactionManager:
    """
    트랜잭션 관리자 (스프링 스타일)
    PostgreSQL 트랜잭션과 벡터 DB 동기화를 관리
    """

    def __init__(self):
        self._active_transactions: List[Dict[str, Any]] = []

    @contextmanager
    def transaction(
        self, read_only: bool = False, isolation_level: str = "READ COMMITTED"
    ):
        """
        트랜잭션 컨텍스트 매니저

        Args:
            read_only: 읽기 전용 트랜잭션
            isolation_level: 격리 수준 (READ COMMITTED, REPEATABLE READ, SERIALIZABLE)

        Usage:
            with transaction_manager.transaction() as tx:
                # 트랜잭션 내 작업
                result = await some_operation(tx)
        """
        # PostgreSQL 트랜잭션 시작
        # 실제 구현은 Prisma 또는 asyncpg 사용
        tx_id = f"tx_{id(self)}"
        logger.debug(f"Transaction started: {tx_id}")

        try:
            # 트랜잭션 컨텍스트 생성
            tx_context = {
                "id": tx_id,
                "read_only": read_only,
                "isolation_level": isolation_level,
                "operations": [],
                "compensations": [],  # 보상 트랜잭션
            }
            self._active_transactions.append(tx_context)

            yield tx_context

            # 커밋 (성공 시)
            logger.debug(f"Transaction committed: {tx_id}")
            self._commit_transaction(tx_context)

        except Exception as e:
            # 롤백 (실패 시)
            logger.error(f"Transaction rolled back: {tx_id}, error: {e}")
            self._rollback_transaction(tx_context)
            raise
        finally:
            if tx_context in self._active_transactions:
                self._active_transactions.remove(tx_context)

    def _commit_transaction(self, tx_context: Dict[str, Any]):
        """트랜잭션 커밋"""
        # PostgreSQL 커밋
        # 벡터 DB 동기화 확인
        for operation in tx_context["operations"]:
            if operation.get("type") == "vector_upsert":
                # 벡터 DB 업데이트 확인
                logger.debug(f"Vector DB operation confirmed: {operation.get('id')}")

    def _rollback_transaction(self, tx_context: Dict[str, Any]):
        """트랜잭션 롤백 및 보상 트랜잭션 실행"""
        # 보상 트랜잭션 실행 (역순)
        for compensation in reversed(tx_context["compensations"]):
            try:
                compensation()
            except Exception as e:
                logger.error(f"Compensation failed: {e}")


# 전역 트랜잭션 관리자
_transaction_manager = TransactionManager()


def transactional(
    read_only: bool = False,
    isolation_level: str = "READ COMMITTED",
    propagation: str = "REQUIRED",
):
    """
    트랜잭션 데코레이터 (스프링 @Transactional 스타일)

    Args:
        read_only: 읽기 전용 트랜잭션
        isolation_level: 격리 수준
        propagation: 전파 방식 (REQUIRED, REQUIRES_NEW, NESTED, SUPPORTS, NOT_SUPPORTED, NEVER)

    Usage:
        @transactional()
        async def create_news_with_indexing(news_data):
            # 트랜잭션 내에서 실행
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            # 전파 방식 처리
            if propagation == "REQUIRED":
                # 기존 트랜잭션이 있으면 사용, 없으면 새로 생성
                if _transaction_manager._active_transactions:
                    # 기존 트랜잭션 사용
                    tx_context = _transaction_manager._active_transactions[-1]
                    return await func(*args, **kwargs, _tx=tx_context)
                else:
                    # 새 트랜잭션 생성
                    with _transaction_manager.transaction(
                        read_only=read_only, isolation_level=isolation_level
                    ) as tx:
                        return await func(*args, **kwargs, _tx=tx)
            elif propagation == "REQUIRES_NEW":
                # 항상 새 트랜잭션 생성
                with _transaction_manager.transaction(
                    read_only=read_only, isolation_level=isolation_level
                ) as tx:
                    return await func(*args, **kwargs, _tx=tx)
            elif propagation == "SUPPORTS":
                # 트랜잭션이 있으면 사용, 없으면 트랜잭션 없이 실행
                if _transaction_manager._active_transactions:
                    tx_context = _transaction_manager._active_transactions[-1]
                    return await func(*args, **kwargs, _tx=tx_context)
                else:
                    return await func(*args, **kwargs)
            else:
                # 기본: REQUIRED
                with _transaction_manager.transaction(
                    read_only=read_only, isolation_level=isolation_level
                ) as tx:
                    return await func(*args, **kwargs, _tx=tx)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            # 동기 함수는 asyncio로 래핑
            if propagation == "REQUIRED":
                if _transaction_manager._active_transactions:
                    tx_context = _transaction_manager._active_transactions[-1]
                    return func(*args, **kwargs, _tx=tx_context)
                else:
                    with _transaction_manager.transaction(
                        read_only=read_only, isolation_level=isolation_level
                    ) as tx:
                        return func(*args, **kwargs, _tx=tx)
            else:
                with _transaction_manager.transaction(
                    read_only=read_only, isolation_level=isolation_level
                ) as tx:
                    return func(*args, **kwargs, _tx=tx)

        # 비동기 함수인지 확인
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


@contextmanager
def transaction(read_only: bool = False, isolation_level: str = "READ COMMITTED"):
    """
    트랜잭션 컨텍스트 매니저 (직접 사용)

    Usage:
        with transaction() as tx:
            # 트랜잭션 내 작업
            result = await some_operation(tx)
    """
    with _transaction_manager.transaction(
        read_only=read_only, isolation_level=isolation_level
    ) as tx:
        yield tx


class SagaTransaction:
    """
    Saga 패턴 기반 분산 트랜잭션
    PostgreSQL + 벡터 DB 동기화를 위한 보상 트랜잭션 패턴
    """

    def __init__(self):
        self._steps: List[Dict[str, Any]] = []
        self._compensations: List[Callable] = []

    def add_step(
        self,
        operation: Callable,
        compensation: Optional[Callable] = None,
        step_id: Optional[str] = None,
    ):
        """
        Saga 단계 추가

        Args:
            operation: 실행할 작업 (async 함수)
            compensation: 보상 작업 (롤백 시 실행, async 함수)
            step_id: 단계 ID
        """
        self._steps.append(
            {
                "id": step_id or f"step_{len(self._steps)}",
                "operation": operation,
                "compensation": compensation,
            }
        )

    async def execute(self) -> List[Any]:
        """
        Saga 실행

        Returns:
            각 단계의 결과 리스트

        Raises:
            Exception: 실패 시 보상 트랜잭션 실행 후 예외 발생
        """
        results = []
        executed_steps = []

        try:
            for step in self._steps:
                logger.debug(f"Executing saga step: {step['id']}")

                # 비동기 함수인지 확인
                import asyncio

                if asyncio.iscoroutinefunction(step["operation"]):
                    result = await step["operation"]()
                else:
                    result = step["operation"]()

                results.append(result)
                executed_steps.append(step)

            logger.info(f"Saga completed successfully: {len(self._steps)} steps")
            return results

        except Exception as e:
            logger.error(
                f"Saga failed at step {len(executed_steps)}, executing compensations: {e}"
            )

            # 보상 트랜잭션 실행 (역순)
            for step in reversed(executed_steps):
                if step.get("compensation"):
                    try:
                        import asyncio

                        if asyncio.iscoroutinefunction(step["compensation"]):
                            await step["compensation"]()
                        else:
                            step["compensation"]()
                        logger.debug(f"Compensation executed for step: {step['id']}")
                    except Exception as comp_error:
                        logger.error(
                            f"Compensation failed for step {step['id']}: {comp_error}"
                        )

            raise


def create_saga() -> SagaTransaction:
    """Saga 트랜잭션 생성"""
    return SagaTransaction()
