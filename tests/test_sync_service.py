"""
Sync Service 테스트
백엔드 DB와 벡터 DB 동기화 테스트
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.services.sync_service import SyncService
from src.exceptions import VectorSearchError


class TestSyncService:
    """SyncService 테스트"""

    @pytest.fixture
    def sync_service(self):
        """SyncService Fixture"""
        return SyncService()

    @pytest.fixture
    def sample_news_data(self):
        """샘플 뉴스 데이터"""
        return {
            "id": "news_1",
            "title": "삼성전자 주가 상승",
            "content": "삼성전자 주가가 전일 대비 2% 상승했습니다.",
            "summary": "삼성전자 주가 상승",
            "source": "한국경제",
            "publishedAt": "2025-12-15T10:00:00Z",
            "stockCodes": ["005930"],
            "sentiment": "positive",
        }

    @pytest.fixture
    def sample_stock_data(self):
        """샘플 주식 데이터"""
        return {
            "code": "005930",
            "name": "삼성전자",
            "sector": "반도체",
            "market": "KOSPI",
            "description": "삼성전자는 세계 최대 반도체 제조사입니다.",
        }

    @pytest.mark.asyncio
    @patch("src.services.sync_service.httpx.AsyncClient")
    async def test_sync_news_to_vector_db(
        self, mock_client_class, sync_service, sample_news_data
    ):
        """뉴스 동기화 테스트"""
        # Mock HTTP 클라이언트 설정
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=sample_news_data)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        # Mock IndexingService
        with patch.object(
            sync_service.indexing_service, "index_news", new_callable=AsyncMock
        ) as mock_index:
            mock_index.return_value = ["vector_1", "vector_2"]

            vector_ids = await sync_service.sync_news_to_vector_db("news_1")

            assert len(vector_ids) == 2
            mock_index.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.sync_service.httpx.AsyncClient")
    async def test_sync_stock_to_vector_db(
        self, mock_client_class, sync_service, sample_stock_data
    ):
        """주식 동기화 테스트"""
        # Mock HTTP 클라이언트 설정
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=sample_stock_data)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        # Mock IndexingService
        with patch.object(
            sync_service.indexing_service, "index_stock", new_callable=AsyncMock
        ) as mock_index:
            mock_index.return_value = "vector_1"

            vector_id = await sync_service.sync_stock_to_vector_db("005930")

            assert vector_id == "vector_1"
            mock_index.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.sync_service.httpx.AsyncClient")
    async def test_sync_news_batch(
        self, mock_client_class, sync_service, sample_news_data
    ):
        """뉴스 배치 동기화 테스트"""
        # Mock HTTP 클라이언트 설정
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=sample_news_data)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        # Mock IndexingService
        with patch.object(
            sync_service.indexing_service, "index_news", new_callable=AsyncMock
        ) as mock_index:
            mock_index.return_value = ["vector_1"]

            results = await sync_service.sync_news_batch(["news_1", "news_2"])

            assert len(results) == 2
            assert mock_index.call_count == 2

    @pytest.mark.asyncio
    @patch("src.services.sync_service.httpx.AsyncClient")
    async def test_sync_news_error_handling(self, mock_client_class, sync_service):
        """뉴스 동기화 에러 처리 테스트"""
        # Mock HTTP 클라이언트 설정 (404 에러)
        mock_response = Mock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        with pytest.raises(VectorSearchError):
            await sync_service.sync_news_to_vector_db("invalid_id")

    @pytest.mark.asyncio
    async def test_close(self, sync_service):
        """리소스 정리 테스트"""
        await sync_service.close()
        # 정상 종료 확인 (에러 없이 실행)
