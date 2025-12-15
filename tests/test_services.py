"""
Service 테스트
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from src.services.llm_service import LLMService
from src.services.slm_service import SLMService
from src.services.model_router import ModelRouterService
from src.services.embedding_service import EmbeddingService
from src.services.vector_search_service import VectorSearchService


class TestLLMService:
    """LLMService 테스트"""

    @pytest.mark.asyncio
    async def test_stream_chat(self, mock_provider):
        """LLM 스트리밍 테스트"""
        with patch(
            "src.services.llm_service.ProviderFactory.get_default_provider",
            return_value=mock_provider,
        ):
            service = LLMService()
            chunks = []
            async for chunk in service.stream_chat(
                model="test-model",
                messages=[{"role": "user", "content": "test"}],
            ):
                chunks.append(chunk)

            assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_chat(self, mock_provider):
        """LLM 일반 채팅 테스트"""
        with patch(
            "src.services.llm_service.ProviderFactory.get_default_provider",
            return_value=mock_provider,
        ):
            service = LLMService()
            response = await service.chat(
                model="test-model",
                messages=[{"role": "user", "content": "test"}],
            )

            assert response is not None
            assert isinstance(response, str)


class TestSLMService:
    """SLMService 테스트"""

    @pytest.mark.asyncio
    async def test_stream_chat(self, mock_provider):
        """SLM 스트리밍 테스트"""
        with patch(
            "src.services.slm_service.ProviderFactory.get_provider",
            return_value=mock_provider,
        ):
            service = SLMService()
            chunks = []
            async for chunk in service.stream_chat(
                model="phi3.5",
                messages=[{"role": "user", "content": "test"}],
            ):
                chunks.append(chunk)

            assert len(chunks) > 0


class TestModelRouterService:
    """ModelRouterService 테스트"""

    @pytest.mark.asyncio
    async def test_route_and_stream_simple(self):
        """간단한 쿼리 라우팅 테스트"""
        with patch("src.services.model_router.SLMService") as mock_slm:
            mock_service = Mock()
            mock_service.stream_chat = AsyncMock(return_value=iter(["response"]))
            mock_slm.return_value = mock_service

            router = ModelRouterService()
            chunks = []
            async for chunk in router.route_and_stream(query="안녕"):
                chunks.append(chunk)

            assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_route_and_chat(self):
        """일반 채팅 라우팅 테스트"""
        with patch("src.services.model_router.LLMService") as mock_llm:
            mock_service = Mock()
            mock_service.chat = AsyncMock(return_value="response")
            mock_llm.return_value = mock_service

            router = ModelRouterService()
            response = await router.route_and_chat(query="분석해줘")

            assert response is not None


class TestEmbeddingService:
    """EmbeddingService 테스트"""

    @patch("src.services.embedding_service.OpenAI")
    def test_create_embedding(self, mock_openai):
        """단일 임베딩 생성 테스트"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_client.embeddings.create = Mock(return_value=mock_response)
        mock_openai.return_value = mock_client

        service = EmbeddingService()
        embedding = service.create_embedding("test text")

        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)

    @patch("src.services.embedding_service.OpenAI")
    def test_create_embeddings_batch(self, mock_openai):
        """배치 임베딩 생성 테스트"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536) for _ in range(3)]
        mock_client.embeddings.create = Mock(return_value=mock_response)
        mock_openai.return_value = mock_client

        service = EmbeddingService()
        embeddings = service.create_embeddings_batch(["text1", "text2", "text3"])

        assert len(embeddings) == 3
        assert all(len(emb) == 1536 for emb in embeddings)


class TestVectorSearchService:
    """VectorSearchService 테스트"""

    @patch("src.services.vector_search_service.Pinecone")
    @patch("src.services.vector_search_service.EmbeddingService")
    def test_search(self, mock_embedding, mock_pinecone):
        """벡터 검색 테스트"""
        # Mock 설정
        mock_embedding_service = Mock()
        mock_embedding_service.create_embedding = Mock(return_value=[0.1] * 1536)

        mock_index = Mock()
        mock_match = Mock()
        mock_match.id = "1"
        mock_match.score = 0.95
        mock_match.metadata = {"type": "news"}
        mock_index.query = Mock(return_value=Mock(matches=[mock_match]))

        mock_pc = Mock()
        mock_pc.Index = Mock(return_value=mock_index)
        mock_pinecone.return_value = mock_pc

        service = VectorSearchService()
        service.embedding_service = mock_embedding_service
        service._index = mock_index

        results = service.search("test query", top_k=5)

        assert len(results) > 0
        assert results[0]["id"] == "1"
        assert results[0]["score"] == 0.95

    @patch("src.services.vector_search_service.Pinecone")
    def test_get_stats(self, mock_pinecone):
        """인덱스 통계 조회 테스트"""
        mock_index = Mock()
        mock_index.describe_index_stats = Mock(
            return_value=Mock(
                total_vector_count=1000,
                dimension=1536,
                index_fullness=0.5,
            )
        )

        mock_pc = Mock()
        mock_pc.Index = Mock(return_value=mock_index)
        mock_pinecone.return_value = mock_pc

        service = VectorSearchService()
        service._index = mock_index

        stats = service.get_stats()

        assert stats["total_vectors"] == 1000
        assert stats["dimension"] == 1536


class TestIndexingService:
    """IndexingService 테스트"""

    @patch("src.services.indexing_service.EmbeddingService")
    @patch("src.services.indexing_service.VectorSearchService")
    def test_adaptive_chunk(self, mock_vector, mock_embedding):
        """적응형 청킹 테스트"""
        from src.services.indexing_service import IndexingService

        service = IndexingService()
        text = "문장 1. 문장 2. 문장 3. 문장 4. 문장 5."

        chunks = service._adaptive_chunk(text)

        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)

    @patch("src.services.indexing_service.EmbeddingService")
    @patch("src.services.indexing_service.VectorSearchService")
    @pytest.mark.asyncio
    async def test_index_news_batch_embedding(self, mock_vector, mock_embedding):
        """뉴스 인덱싱 배치 임베딩 테스트"""
        from src.services.indexing_service import IndexingService

        # Mock 설정
        mock_embedding_service = Mock()
        mock_embedding_service.create_embeddings_batch = Mock(
            return_value=[[0.1] * 1536, [0.2] * 1536]
        )
        mock_embedding_service.create_embedding = Mock(return_value=[0.1] * 1536)

        mock_vector_service = Mock()
        mock_vector_service.upsert = Mock()

        service = IndexingService()
        service.embedding_service = mock_embedding_service
        service.vector_search_service = mock_vector_service

        news_data = {
            "id": "news_1",
            "title": "테스트 뉴스",
            "content": "긴 내용입니다. " * 100,  # 여러 청크 생성
            "summary": "요약",
            "source": "테스트",
            "publishedAt": "2025-12-15T10:00:00Z",
            "stockCodes": ["005930"],
        }

        # 배치 임베딩이 호출되는지 확인
        with patch.object(
            service, "_adaptive_chunk", return_value=["chunk1", "chunk2"]
        ):
            vector_ids = await service.index_news(news_data)

            # 배치 임베딩이 호출되었는지 확인 (청크가 2개 이상일 때)
            assert mock_embedding_service.create_embeddings_batch.called
