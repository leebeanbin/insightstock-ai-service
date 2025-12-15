"""
Cost Optimization Configuration
비용 친화적인 AI 서비스 설정 (최신 연구 기반)
"""

from typing import Optional
from src.config.env import EnvConfig


class CostOptimizationConfig:
    """
    비용 최적화 설정

    최적화 전략:
    1. 배치 처리로 비용 50% 절감
    2. 캐싱으로 중복 호출 방지
    3. 적응형 청킹으로 청크 수 최소화
    4. 비용 효율적인 모델 선택
    """

    # ============================================
    # 임베딩 모델 비용 (OpenAI 기준, 2024-2025)
    # ============================================
    # text-embedding-3-small: $0.02/1M tokens (일반), $0.01/1M tokens (배치) ✅ 비용 효율적
    # text-embedding-3-large: $0.13/1M tokens (일반), $0.065/1M tokens (배치)
    # 배치 처리 시 비용 50% 절감!

    # 기본 임베딩 모델 (비용 효율적)
    EMBEDDING_MODEL = "text-embedding-3-small"  # 1536차원, 비용 효율적

    # 배치 처리 설정
    EMBEDDING_BATCH_SIZE = 100  # OpenAI 최대 배치 크기 (비용 50% 절감)
    EMBEDDING_BATCH_DELAY = 0.1  # 배치 간 지연 (초)

    # ============================================
    # 청킹 최적화 (비용 절감)
    # ============================================
    # 청크 수를 최소화하면 임베딩 생성 비용 절감

    # 최적 청크 크기 (512 토큰 = 약 2000자)
    CHUNK_SIZE_TOKENS = 512  # 토큰 기준
    CHUNK_SIZE_CHARS = 2000  # 문자 기준 (대략적)
    CHUNK_OVERLAP_RATIO = 0.15  # 15% 오버랩

    # 적응형 청킹 설정
    MIN_CHUNK_SIZE = 256  # 최소 청크 크기 (토큰)
    MAX_CHUNK_SIZE = 1024  # 최대 청크 크기 (토큰)

    # ============================================
    # 캐싱 전략 (비용 절감)
    # ============================================
    # 캐시 히트율이 높을수록 API 호출 감소 = 비용 절감

    EMBEDDING_CACHE_TTL = 3600  # 1시간 (임베딩은 변경되지 않음)
    SEARCH_CACHE_TTL = 1800  # 30분 (검색 결과는 더 짧게)
    CLASSIFICATION_CACHE_TTL = 3600  # 1시간 (분류 결과는 변경되지 않음)

    # ============================================
    # LLM 모델 선택 (비용 최적화)
    # ============================================
    # 간단한 질문은 SLM 사용 (로컬, 무료)
    # 복잡한 질문만 LLM 사용 (유료)

    USE_SLM_FOR_SIMPLE_QUERIES = True  # 간단한 질문은 SLM 사용
    SLM_THRESHOLD = 0.7  # 복잡도 임계값 (0.7 이하는 SLM)

    # ============================================
    # 벡터 검색 최적화
    # ============================================
    DEFAULT_TOP_K = 5  # 기본 검색 결과 수 (적절한 밸런스)
    MAX_TOP_K = 20  # 최대 검색 결과 수
    SIMILARITY_THRESHOLD = 0.7  # 유사도 임계값 (필터링)

    # ============================================
    # 배치 인덱싱 최적화
    # ============================================
    INDEXING_BATCH_SIZE = 100  # 배치 인덱싱 크기
    INDEXING_DELAY_BETWEEN_BATCHES = 1.0  # 배치 간 지연 (초, API 제한 고려)

    @classmethod
    def get_embedding_model(cls) -> str:
        """임베딩 모델 반환 (환경 변수 우선)"""
        return getattr(EnvConfig, "EMBEDDING_MODEL", cls.EMBEDDING_MODEL)

    @classmethod
    def should_use_batch(cls, count: int) -> bool:
        """배치 처리 여부 판단"""
        return count >= 2  # 2개 이상이면 배치 처리

    @classmethod
    def estimate_cost(cls, tokens: int, use_batch: bool = True) -> float:
        """
        비용 추정 (USD)

        Args:
            tokens: 토큰 수
            use_batch: 배치 처리 여부

        Returns:
            예상 비용 (USD)
        """
        model = cls.get_embedding_model()

        if model == "text-embedding-3-small":
            price_per_million = 0.01 if use_batch else 0.02
        elif model == "text-embedding-3-large":
            price_per_million = 0.065 if use_batch else 0.13
        else:
            price_per_million = 0.02  # 기본값

        return (tokens / 1_000_000) * price_per_million

    @classmethod
    def get_optimal_chunk_size(cls, text_length: int) -> int:
        """
        텍스트 길이에 따른 최적 청크 크기

        Args:
            text_length: 텍스트 길이 (문자 수)

        Returns:
            최적 청크 크기 (문자 수)
        """
        # 짧은 텍스트는 작은 청크, 긴 텍스트는 큰 청크
        if text_length < 1000:
            return 500
        elif text_length < 5000:
            return cls.CHUNK_SIZE_CHARS
        else:
            return min(cls.CHUNK_SIZE_CHARS * 2, 4000)
