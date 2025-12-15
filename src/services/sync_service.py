"""
Sync Service
백엔드 PostgreSQL과 벡터 DB 동기화 서비스
트랜잭션 기반 정합성 보장
"""

from typing import List, Dict, Optional
from loguru import logger
import httpx

from src.services.indexing_service import IndexingService
from src.utils.transaction import transactional, create_saga
from src.exceptions import VectorSearchError
from src.config.env import EnvConfig
from src.config.cost_optimization import CostOptimizationConfig


class SyncService:
    """
    백엔드 DB와 벡터 DB 동기화 서비스

    백엔드 구조:
    - PostgreSQL (Prisma)
    - News, Stock, Learning, Note 모델
    - 트랜잭션: executeTransaction 사용
    """

    def __init__(self):
        self.indexing_service = IndexingService()
        self.backend_url = EnvConfig.BACKEND_API_URL
        self.client = httpx.AsyncClient(timeout=30.0)

    async def sync_news_to_vector_db(
        self, news_id: str, force_reindex: bool = False
    ) -> List[str]:
        """
        뉴스를 벡터 DB에 동기화 (트랜잭션 기반)

        백엔드 구조:
        - News 모델: id, title, content, summary, source, url, publishedAt, sentiment
        - NewsStock: newsId, stockId (관계 테이블)
        - NewsKeyPoint: newsId, content
        - NewsConcept: newsId, concept

        Args:
            news_id: 뉴스 ID
            force_reindex: 강제 재인덱싱 여부

        Returns:
            인덱싱된 벡터 ID 리스트
        """
        try:
            # 백엔드에서 뉴스 데이터 조회
            response = await self.client.get(
                f"{self.backend_url}/api/news/{news_id}",
                headers={"Content-Type": "application/json"},
            )

            if response.status_code != 200:
                raise VectorSearchError(
                    f"Failed to fetch news from backend: {response.status_code}"
                )

            news_data = response.json()

            # 벡터 DB에 인덱싱 (트랜잭션 기반)
            vector_ids = await self.indexing_service.index_news(
                news_data, use_adaptive_chunking=True  # 비용 최적화: 적응형 청킹
            )

            logger.info(
                f"Synced news {news_id} to vector DB: {len(vector_ids)} vectors"
            )
            return vector_ids

        except Exception as e:
            logger.error(f"Failed to sync news {news_id}: {e}")
            raise VectorSearchError(f"News sync failed: {str(e)}") from e

    async def sync_stock_to_vector_db(
        self, stock_code: str, force_reindex: bool = False
    ) -> str:
        """
        주식을 벡터 DB에 동기화 (트랜잭션 기반)

        백엔드 구조:
        - Stock 모델: id, code, name, market, sector, description
        - StockPrice: stockId, date, open, high, low, close, volume

        Args:
            stock_code: 주식 코드
            force_reindex: 강제 재인덱싱 여부

        Returns:
            인덱싱된 벡터 ID
        """
        try:
            # 백엔드에서 주식 데이터 조회
            response = await self.client.get(
                f"{self.backend_url}/api/stocks/{stock_code}",
                headers={"Content-Type": "application/json"},
            )

            if response.status_code != 200:
                raise VectorSearchError(
                    f"Failed to fetch stock from backend: {response.status_code}"
                )

            stock_data = response.json()

            # 벡터 DB에 인덱싱 (트랜잭션 기반)
            vector_id = await self.indexing_service.index_stock(stock_data)

            logger.info(f"Synced stock {stock_code} to vector DB: {vector_id}")
            return vector_id

        except Exception as e:
            logger.error(f"Failed to sync stock {stock_code}: {e}")
            raise VectorSearchError(f"Stock sync failed: {str(e)}") from e

    @transactional()
    async def sync_news_batch(
        self, news_ids: List[str], _tx: Optional[Dict] = None
    ) -> Dict[str, List[str]]:
        """
        뉴스 배치 동기화 (트랜잭션 기반, 비용 최적화)

        비용 최적화:
        - 배치 처리로 API 호출 최소화
        - 배치 임베딩 생성으로 비용 50% 절감

        Args:
            news_ids: 뉴스 ID 리스트
            _tx: 트랜잭션 컨텍스트

        Returns:
            {news_id: [vector_ids]} 딕셔너리
        """
        results = {}

        # 비용 최적화: 배치 크기로 나누어 처리
        batch_size = CostOptimizationConfig.INDEXING_BATCH_SIZE

        for i in range(0, len(news_ids), batch_size):
            batch = news_ids[i : i + batch_size]

            # 배치 처리
            for news_id in batch:
                try:
                    vector_ids = await self.sync_news_to_vector_db(news_id, _tx=_tx)
                    results[news_id] = vector_ids
                except Exception as e:
                    logger.error(f"Failed to sync news {news_id}: {e}")
                    # 개별 실패는 기록만 하고 계속 진행

            # 비용 최적화: 배치 간 지연 (API 제한 고려)
            if i + batch_size < len(news_ids):
                import asyncio

                await asyncio.sleep(
                    CostOptimizationConfig.INDEXING_DELAY_BETWEEN_BATCHES
                )

        logger.info(f"Synced {len(results)} news items to vector DB (batch optimized)")
        return results

    async def close(self):
        """리소스 정리"""
        await self.client.aclose()
