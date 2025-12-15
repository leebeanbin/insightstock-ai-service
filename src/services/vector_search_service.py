"""
Vector Search Service
Pinecone을 사용한 벡터 검색 및 인덱싱
"""

from typing import List, Dict, Optional
from pinecone import Pinecone, Index
from loguru import logger
import hashlib

from src.config.env import EnvConfig
from src.config.cost_optimization import CostOptimizationConfig  # 비용 최적화
from src.services.embedding_service import EmbeddingService
from src.exceptions import VectorSearchError
from src.utils.retry import retry
from src.utils.cache import cache  # Redis 캐시 (폴백: 인메모리)
from src.utils.concurrency import distributed_lock, redis_transaction, semaphore  # 동시성 제어


class VectorSearchService:
    """벡터 검색 서비스"""

    def __init__(self):
        """초기화"""
        api_key = EnvConfig.PINECONE_API_KEY
        if not api_key:
            raise ValueError("PINECONE_API_KEY is required for VectorSearchService")

        self.pc = Pinecone(api_key=api_key)
        self.index_name = EnvConfig.PINECONE_INDEX_NAME
        self.embedding_service = EmbeddingService()
        self._index: Optional[Index] = None
        self.cache = cache  # Redis 캐시 (폴백: 인메모리)
        self.cache_ttl = CostOptimizationConfig.SEARCH_CACHE_TTL  # 비용 최적화: 캐싱
        
        # 비용 최적화 설정
        self.batch_size = CostOptimizationConfig.INDEXING_BATCH_SIZE  # 벡터 업로드 배치 크기
        self.top_k_default = CostOptimizationConfig.DEFAULT_TOP_K  # 기본 검색 결과 수
        self.similarity_threshold = CostOptimizationConfig.SIMILARITY_THRESHOLD  # 유사도 임계값

    @property
    def index(self) -> Index:
        """Pinecone 인덱스 인스턴스 (지연 로딩)"""
        if self._index is None:
            self._index = self.pc.Index(self.index_name)
        return self._index

    def _get_search_cache_key(
        self, query: str, top_k: int, filter: Optional[Dict]
    ) -> str:
        """검색 결과 캐시 키 생성"""
        filter_str = str(sorted(filter.items())) if filter else "no_filter"
        content = f"{query}:{top_k}:{filter_str}"
        return f"vector_search:{hashlib.md5(content.encode()).hexdigest()}"

    @retry(max_attempts=3, exceptions=(Exception,))
    def search(
        self,
        query: str,
        top_k: int = 5,
        filter: Optional[Dict] = None,
        include_metadata: bool = True,
        use_cache: bool = True,
    ) -> List[Dict]:
        """
        벡터 검색 (재시도 로직 및 캐싱 포함)

        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            filter: 메타데이터 필터
            include_metadata: 메타데이터 포함 여부
            use_cache: 캐시 사용 여부 (기본값: True)

        Returns:
            검색 결과 리스트

        Raises:
            VectorSearchError: 검색 실패 시
        """
        # 캐시 확인
        if use_cache:
            cache_key = self._get_search_cache_key(query, top_k, filter)
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Vector search cache hit: {cache_key[:16]}...")
                return cached

        # 동일 검색 동시 실행 방지 (분산 락)
        lock_key = f"search_lock:{hashlib.md5((query + str(top_k) + str(filter)).encode()).hexdigest()}"
        
        with distributed_lock(lock_key, timeout=30, blocking=True):
            # 락 획득 후 다시 캐시 확인
            if use_cache:
                cache_key = self._get_search_cache_key(query, top_k, filter)
                cached = self.cache.get(cache_key)
                if cached is not None:
                    logger.debug(f"Vector search cache hit (after lock): {cache_key[:16]}...")
                    return cached

            try:
                # 쿼리 임베딩 생성 (임베딩은 자체 캐싱 사용)
                query_embedding = self.embedding_service.create_embedding(
                    query, use_cache=True
                )

                # Pinecone 검색
                results = self.index.query(
                    vector=query_embedding,
                    top_k=top_k,
                    filter=filter,
                    include_metadata=include_metadata,
                )

                # 결과 포맷팅
                formatted_results = []
                for match in results.matches:
                    formatted_results.append(
                        {
                            "id": match.id,
                            "score": match.score,
                            "metadata": match.metadata if include_metadata else None,
                        }
                    )

                # 캐시 저장
                if use_cache:
                    cache_key = self._get_search_cache_key(query, top_k, filter)
                    # 트랜잭션으로 원자성 보장 (pickle 직렬화 필요)
                    import pickle
                    with redis_transaction() as tx:
                        tx.set(cache_key, pickle.dumps(formatted_results), self.cache_ttl)
                    logger.debug(f"Vector search cached: {cache_key[:16]}...")

                return formatted_results
            except Exception as e:
                logger.error(f"Vector search error: {e}")
                raise VectorSearchError(f"Failed to search vectors: {str(e)}") from e

    def upsert(self, vectors: List[Dict], batch_size: int = 100) -> None:
        """
        벡터 업로드 (트랜잭션 및 동시성 제어 포함)

        Args:
            vectors: 업로드할 벡터 리스트
                각 벡터는 {"id": str, "values": List[float], "metadata": Dict} 형식
            batch_size: 배치 크기
        """
        # 동시 업로드 수 제한 (세마포어)
        with semaphore("vector_upsert", limit=2, timeout=600):
            try:
                for i in range(0, len(vectors), batch_size):
                    batch = vectors[i : i + batch_size]
                    
                    # 배치 업로드 락 (동일 배치 중복 업로드 방지)
                    batch_key = f"upsert_batch:{hashlib.md5(str(batch[0]['id']).encode()).hexdigest()}"
                    with distributed_lock(batch_key, timeout=300, blocking=True):
                        self.index.upsert(vectors=batch)
                        logger.info(
                            f"Upserted batch {i//batch_size + 1} ({len(batch)} vectors)"
                        )

                logger.info(f"Total upserted: {len(vectors)} vectors")
            except Exception as e:
                logger.error(f"Upsert error: {e}")
                raise

    def delete(self, ids: List[str]) -> None:
        """
        벡터 삭제

        Args:
            ids: 삭제할 벡터 ID 리스트
        """
        try:
            self.index.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} vectors")
        except Exception as e:
            logger.error(f"Delete error: {e}")
            raise

    @retry(max_attempts=3, exceptions=(Exception,))
    def get_stats(self) -> Dict:
        """
        인덱스 통계 조회 (재시도 로직 포함)

        Returns:
            인덱스 통계 딕셔너리

        Raises:
            VectorSearchError: 통계 조회 실패 시
        """
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vectors": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "namespaces": stats.namespaces if hasattr(stats, "namespaces") else {},
            }
        except Exception as e:
            logger.error(f"Get stats error: {e}")
            raise VectorSearchError(f"Failed to get index stats: {str(e)}") from e
