"""
Embedding Service
OpenAI Embeddings를 사용한 텍스트 임베딩 생성
"""

from typing import List
from openai import OpenAI
from loguru import logger
import hashlib

from src.config.env import EnvConfig
from src.config.cost_optimization import CostOptimizationConfig  # 비용 최적화
from src.exceptions import EmbeddingError
from src.utils.retry import retry
from src.utils.cache import cache  # Redis 캐시 (폴백: 인메모리)
from src.utils.concurrency import distributed_lock, semaphore  # 동시성 제어


class EmbeddingService:
    """임베딩 서비스 (인메모리 캐싱 포함)"""

    def __init__(self):
        """초기화"""
        api_key = EnvConfig.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for EmbeddingService")

        self.client = OpenAI(api_key=api_key)
        # 비용 최적화: text-embedding-3-small 사용
        # - 비용: $0.01/1M tokens (배치), $0.02/1M tokens (일반)
        # - text-embedding-3-large 대비 6.5배 저렴, 성능 차이 미미
        self.default_model = CostOptimizationConfig.get_embedding_model()
        self.cache = cache  # Redis 캐시 (폴백: 인메모리)
        self.cache_ttl = CostOptimizationConfig.EMBEDDING_CACHE_TTL
        
        # 비용 최적화 설정
        self.batch_size = CostOptimizationConfig.EMBEDDING_BATCH_SIZE  # 배치 처리로 비용 50% 절감
        self.max_retries = 3  # 재시도 횟수

    def _get_cache_key(self, text: str, model: str) -> str:
        """캐시 키 생성"""
        content = f"{text}:{model or self.default_model}"
        return f"embedding:{hashlib.md5(content.encode()).hexdigest()}"

    @retry(max_attempts=3, exceptions=(Exception,))
    def create_embedding(
        self, text: str, model: str = None, use_cache: bool = True
    ) -> List[float]:
        """
        단일 텍스트 임베딩 생성 (재시도 로직 및 캐싱 포함)

        Args:
            text: 임베딩할 텍스트
            model: 사용할 모델 (기본값: text-embedding-3-small)
            use_cache: 캐시 사용 여부 (기본값: True)

        Returns:
            임베딩 벡터

        Raises:
            EmbeddingError: 임베딩 생성 실패 시
        """
        # 캐시 확인
        if use_cache:
            cache_key = self._get_cache_key(text, model)
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Embedding cache hit: {cache_key[:16]}...")
                return cached

        # 동일 텍스트 동시 생성 방지 (분산 락)
        lock_key = f"embedding_lock:{hashlib.md5((text + (model or self.default_model)).encode()).hexdigest()}"
        
        with distributed_lock(lock_key, timeout=60, blocking=True):
            # 락 획득 후 다시 캐시 확인 (다른 프로세스가 생성했을 수 있음)
            if use_cache:
                cache_key = self._get_cache_key(text, model)
                cached = self.cache.get(cache_key)
                if cached is not None:
                    logger.debug(f"Embedding cache hit (after lock): {cache_key[:16]}...")
                    return cached

            try:
                response = self.client.embeddings.create(
                    model=model or self.default_model, input=text
                )
                embedding = response.data[0].embedding

                # 캐시 저장
                if use_cache:
                    cache_key = self._get_cache_key(text, model)
                    self.cache.set(cache_key, embedding, self.cache_ttl)
                    logger.debug(f"Embedding cached: {cache_key[:16]}...")

                return embedding
            except Exception as e:
                logger.error(f"Create embedding error: {e}")
                raise EmbeddingError(f"Failed to create embedding: {str(e)}") from e

    @retry(max_attempts=3, exceptions=(Exception,))
    def create_embeddings_batch(
        self, texts: List[str], model: str = None
    ) -> List[List[float]]:
        """
        텍스트 리스트에 대한 배치 임베딩 생성 (재시도 로직 포함)

        Args:
            texts: 임베딩할 텍스트 리스트
            model: 사용할 모델 (기본값: text-embedding-3-small)

        Returns:
            임베딩 벡터 리스트

        Raises:
            EmbeddingError: 임베딩 생성 실패 시
        """
        if not texts:
            return []

        embeddings = []
        # 비용 최적화: 배치 처리로 비용 50% 절감 ($0.02 → $0.01 per 1M tokens)
        batch_size = self.batch_size

        # 배치 처리 시 동시 실행 수 제한 (세마포어)
        with semaphore("embedding_batch", limit=3, timeout=300):
            try:
                for i in range(0, len(texts), batch_size):
                    batch = texts[i : i + batch_size]

                    # 배치 임베딩 생성 (비용 50% 절감)
                    response = self.client.embeddings.create(
                        model=model or self.default_model, input=batch
                    )

                    for embedding in response.data:
                        embeddings.append(embedding.embedding)
                    
                    # 비용 최적화: 배치 간 짧은 지연 (API 제한 고려)
                    import time
                    if i + batch_size < len(texts):
                        time.sleep(CostOptimizationConfig.EMBEDDING_BATCH_DELAY)

                logger.info(f"Created {len(embeddings)} embeddings in batch (cost optimized)")
                return embeddings
            except Exception as e:
                logger.error(f"Create embeddings batch error: {e}")
                raise EmbeddingError(f"Failed to create embeddings batch: {str(e)}") from e
