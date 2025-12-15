"""
Indexing Service
뉴스, 주식 데이터를 벡터 DB에 인덱싱 (최신 RAG 패턴 적용)
트랜잭션 기반 정합성 보장
"""

from typing import List, Dict, Optional
from loguru import logger

from src.services.embedding_service import EmbeddingService
from src.services.vector_search_service import VectorSearchService
from src.utils.parsers import (
    parse_news_for_indexing,
    parse_stock_for_indexing,
    parse_learning_for_indexing,
    chunk_text,
)
from src.utils.transaction import transactional, SagaTransaction, create_saga
from src.exceptions import VectorSearchError, EmbeddingError
from src.config.cost_optimization import CostOptimizationConfig  # 비용 최적화


class IndexingService:
    """
    인덱싱 서비스 (최신 RAG 패턴 적용)

    최적화 사항:
    - 적응형 청킹 (Recursive Chunking)
    - 최적 청크 크기 (512 토큰 기준)
    - 청크 오버랩 (10-20%)
    - Parent-Child 청킹
    - 메타데이터 강화
    - 배치 처리 최적화
    """

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_search_service = VectorSearchService()

        # 비용 최적화된 청킹 설정 (최신 연구 기반)
        # 청크 수를 최소화하면 임베딩 생성 비용 절감
        self.chunk_size = CostOptimizationConfig.CHUNK_SIZE_CHARS  # 2000자 (512 토큰)
        self.chunk_overlap = CostOptimizationConfig.CHUNK_OVERLAP_RATIO  # 15% 오버랩
        self.batch_size = CostOptimizationConfig.INDEXING_BATCH_SIZE  # 100개 배치

    def _adaptive_chunk(
        self,
        text: str,
        min_chunk_size: Optional[int] = None,
        max_chunk_size: Optional[int] = None,
    ) -> List[str]:
        """
        적응형 청킹 (Recursive Chunking) - 비용 최적화
        문장/단락 경계를 고려한 스마트 청킹으로 청크 수 최소화 = 비용 절감

        Args:
            text: 원본 텍스트
            min_chunk_size: 최소 청크 크기 (문자 수, 기본값: 설정값 사용)
            max_chunk_size: 최대 청크 크기 (문자 수, 기본값: 설정값 사용)

        Returns:
            청크 리스트 (최소화됨)
        """
        # 비용 최적화: 동적 청크 크기 결정
        if min_chunk_size is None:
            min_chunk_size = (
                CostOptimizationConfig.get_optimal_chunk_size(len(text)) // 4
            )
        if max_chunk_size is None:
            max_chunk_size = CostOptimizationConfig.get_optimal_chunk_size(len(text))

        # 문장 단위로 분할
        sentences = text.split(". ")
        chunks = []
        current_chunk = []
        current_size = 0

        for sentence in sentences:
            sentence_size = len(sentence)

            if current_size + sentence_size > max_chunk_size and current_chunk:
                # 현재 청크 저장
                chunks.append(". ".join(current_chunk) + ".")
                # 오버랩을 위해 마지막 문장 유지
                overlap_sentences = current_chunk[-1:] if len(current_chunk) > 1 else []
                current_chunk = overlap_sentences + [sentence]
                current_size = sum(len(s) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_size += sentence_size

        # 마지막 청크 추가
        if current_chunk:
            chunks.append(". ".join(current_chunk) + ".")

        # 최소 크기 미만 청크는 이전 청크와 병합 (청크 수 최소화 = 비용 절감)
        filtered_chunks = []
        for chunk in chunks:
            if len(chunk) < min_chunk_size and filtered_chunks:
                filtered_chunks[-1] += " " + chunk
            else:
                filtered_chunks.append(chunk)

        logger.debug(
            f"Adaptive chunking: {len(text)} chars → {len(filtered_chunks)} chunks (cost optimized)"
        )
        return filtered_chunks

    def _enrich_metadata(
        self, base_metadata: Dict, content_type: str, parent_id: Optional[str] = None
    ) -> Dict:
        """
        메타데이터 강화 (LLM 생성 메타데이터 패턴)

        Args:
            base_metadata: 기본 메타데이터
            content_type: 콘텐츠 타입 (news, stock, learning)
            parent_id: 부모 문서 ID (Parent-Child 청킹용)

        Returns:
            강화된 메타데이터
        """
        enriched = base_metadata.copy()

        # 타임스탬프 추가
        from datetime import datetime

        enriched["indexed_at"] = datetime.now().isoformat()

        # Parent-Child 관계
        if parent_id:
            enriched["parent_id"] = parent_id
            enriched["chunk_type"] = "child"
        else:
            enriched["chunk_type"] = "parent"

        # 검색 최적화를 위한 추가 필드
        enriched["content_type"] = content_type
        enriched["version"] = "1.0"  # 스키마 버전

        return enriched

    @transactional()
    async def index_news(
        self,
        news_data: Dict,
        use_adaptive_chunking: bool = True,
        _tx: Optional[Dict] = None,
    ) -> List[str]:
        """
        뉴스 인덱싱 (트랜잭션 기반)

        Args:
            news_data: 뉴스 데이터
            use_adaptive_chunking: 적응형 청킹 사용 여부
            _tx: 트랜잭션 컨텍스트

        Returns:
            인덱싱된 벡터 ID 리스트
        """
        try:
            # 파싱
            parsed = parse_news_for_indexing(news_data)

            # 청킹
            if use_adaptive_chunking:
                chunks = self._adaptive_chunk(parsed["text"])
            else:
                chunks = chunk_text(
                    parsed["text"],
                    chunk_size=self.chunk_size * 4,
                    overlap=int(self.chunk_size * 4 * self.chunk_overlap),
                )

            # 벡터 생성 및 인덱싱 (비용 최적화: 배치 처리)
            vectors = []
            parent_id = parsed["id"]

            # 비용 최적화: 청크가 많으면 배치 임베딩 생성
            if len(chunks) >= 2:
                # 배치 임베딩 생성 (비용 50% 절감)
                chunk_texts = [chunk for chunk in chunks]
                embeddings = self.embedding_service.create_embeddings_batch(chunk_texts)
            else:
                # 단일 임베딩 생성
                embeddings = (
                    [self.embedding_service.create_embedding(chunks[0])]
                    if chunks
                    else []
                )

            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):

                # 메타데이터 강화
                chunk_metadata = self._enrich_metadata(
                    parsed["metadata"],
                    content_type="news",
                    parent_id=parent_id if i > 0 else None,
                )
                chunk_metadata["chunk_index"] = i
                chunk_metadata["total_chunks"] = len(chunks)

                # 벡터 구성
                vector_id = f"{parent_id}_chunk_{i}"
                vectors.append(
                    {
                        "id": vector_id,
                        "values": embedding,
                        "metadata": chunk_metadata,
                    }
                )

            # Saga 패턴으로 벡터 DB 업로드 (보상 트랜잭션 지원)
            saga = create_saga()

            async def upsert_vectors():
                """벡터 업로드 작업"""
                self.vector_search_service.upsert(vectors, batch_size=self.batch_size)
                return vectors

            async def rollback_vectors():
                """보상 작업: 벡터 삭제"""
                vector_ids = [v["id"] for v in vectors]
                self.vector_search_service.delete(vector_ids)
                logger.info(f"Compensated: deleted {len(vector_ids)} vectors")

            saga.add_step(
                operation=upsert_vectors,
                compensation=rollback_vectors,
                step_id=f"index_news_{news_data.get('id')}",
            )

            # 트랜잭션 컨텍스트에 기록
            if _tx:
                _tx["operations"].append(
                    {
                        "type": "vector_upsert",
                        "id": parent_id,
                        "vector_count": len(vectors),
                    }
                )
                _tx["compensations"].append(rollback_vectors)

            # Saga 실행
            await saga.execute()

            logger.info(f"Indexed news: {parent_id} ({len(vectors)} chunks)")
            return [v["id"] for v in vectors]

        except Exception as e:
            logger.error(f"Failed to index news: {e}")
            raise VectorSearchError(f"News indexing failed: {str(e)}") from e

    @transactional()
    async def index_stock(self, stock_data: Dict, _tx: Optional[Dict] = None) -> str:
        """
        주식 인덱싱 (트랜잭션 기반)

        Args:
            stock_data: 주식 데이터
            _tx: 트랜잭션 컨텍스트

        Returns:
            인덱싱된 벡터 ID
        """
        try:
            # 파싱
            parsed = parse_stock_for_indexing(stock_data)

            # 임베딩 생성
            embedding = self.embedding_service.create_embedding(parsed["text"])

            # 메타데이터 강화
            metadata = self._enrich_metadata(parsed["metadata"], content_type="stock")

            # 벡터 구성
            vector = {
                "id": parsed["id"],
                "values": embedding,
                "metadata": metadata,
            }

            # Saga 패턴으로 업로드
            saga = create_saga()

            async def upsert_vector():
                self.vector_search_service.upsert([vector], batch_size=1)
                return vector["id"]

            async def rollback_vector():
                self.vector_search_service.delete([vector["id"]])
                logger.info(f"Compensated: deleted vector {vector['id']}")

            saga.add_step(
                operation=upsert_vector,
                compensation=rollback_vector,
                step_id=f"index_stock_{stock_data.get('code')}",
            )

            if _tx:
                _tx["operations"].append(
                    {
                        "type": "vector_upsert",
                        "id": vector["id"],
                        "vector_count": 1,
                    }
                )
                _tx["compensations"].append(rollback_vector)

            await saga.execute()

            logger.info(f"Indexed stock: {vector['id']}")
            return vector["id"]

        except Exception as e:
            logger.error(f"Failed to index stock: {e}")
            raise VectorSearchError(f"Stock indexing failed: {str(e)}") from e

    @transactional()
    async def batch_index_news(
        self, news_list: List[Dict], _tx: Optional[Dict] = None
    ) -> Dict[str, List[str]]:
        """
        뉴스 배치 인덱싱 (트랜잭션 기반)

        Args:
            news_list: 뉴스 데이터 리스트
            _tx: 트랜잭션 컨텍스트

        Returns:
            {news_id: [vector_ids]} 딕셔너리
        """
        results = {}

        for news_data in news_list:
            try:
                vector_ids = await self.index_news(news_data, _tx=_tx)
                results[news_data["id"]] = vector_ids
            except Exception as e:
                logger.error(f"Failed to index news {news_data.get('id')}: {e}")
                # 개별 실패는 기록만 하고 계속 진행

        logger.info(f"Batch indexed {len(results)} news items")
        return results
