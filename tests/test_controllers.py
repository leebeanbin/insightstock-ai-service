"""
Controller 테스트
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, Mock
from src.main import app


class TestChatController:
    """ChatController 테스트"""

    @pytest.fixture
    def client(self):
        """TestClient Fixture"""
        return TestClient(app)

    @patch("src.controllers.chat_controller.ModelRouterService")
    def test_stream_chat_endpoint(self, mock_router_class, client):
        """스트리밍 채팅 엔드포인트 테스트"""
        # Mock 설정
        mock_router = Mock()
        mock_router.route_and_stream = AsyncMock(
            return_value=iter(["chunk1", "chunk2"])
        )
        mock_router.close = AsyncMock()
        mock_router_class.return_value = mock_router

        response = client.post(
            "/api/chat/stream",
            json={
                "query": "안녕하세요",
                "messages": [],
            },
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    @patch("src.controllers.chat_controller.ModelRouterService")
    def test_chat_endpoint(self, mock_router_class, client):
        """일반 채팅 엔드포인트 테스트"""
        # Mock 설정
        mock_router = Mock()
        mock_router.route_and_chat = AsyncMock(return_value="Test response")
        mock_router.close = AsyncMock()
        mock_router_class.return_value = mock_router

        response = client.post(
            "/api/chat",
            json={
                "query": "안녕하세요",
                "messages": [],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "content" in data

    def test_get_models_endpoint(self, client):
        """모델 목록 조회 엔드포인트 테스트"""
        response = client.get("/api/models")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "models" in data
        assert "available_providers" in data


class TestSearchController:
    """SearchController 테스트"""

    @pytest.fixture
    def client(self):
        """TestClient Fixture"""
        return TestClient(app)

    @patch("src.controllers.search_controller.VectorSearchService")
    def test_vector_search_endpoint(self, mock_service_class, client):
        """벡터 검색 엔드포인트 테스트"""
        # Mock 설정
        mock_service = Mock()
        mock_service.search = Mock(
            return_value=[{"id": "1", "score": 0.95, "metadata": {"type": "news"}}]
        )
        mock_service_class.return_value = mock_service

        response = client.post(
            "/api/search/vector",
            json={
                "query": "삼성전자 주가",
                "top_k": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "results" in data

    @patch("src.controllers.search_controller.VectorSearchService")
    def test_get_index_stats_endpoint(self, mock_service_class, client):
        """인덱스 통계 조회 엔드포인트 테스트"""
        # Mock 설정
        mock_service = Mock()
        mock_service.get_stats = Mock(
            return_value={
                "total_vectors": 1000,
                "dimension": 1536,
            }
        )
        mock_service.index_name = "test-index"
        mock_service_class.return_value = mock_service

        response = client.get("/api/search/index/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "stats" in data
