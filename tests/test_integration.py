"""
통합 테스트
AI 서비스와 메인 백엔드 연동 테스트
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from src.main import app


class TestIntegration:
    """통합 테스트"""

    @pytest.fixture
    def client(self):
        """TestClient Fixture"""
        return TestClient(app)

    def test_health_check(self, client):
        """Health check 엔드포인트 테스트"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "ai-service"

    @patch("src.controllers.chat_controller.ModelRouterService")
    def test_chat_flow(self, mock_router_class, client):
        """전체 채팅 플로우 테스트"""
        # Mock 설정
        mock_router = Mock()
        mock_router.route_and_stream = AsyncMock(return_value=iter(["응답", "입니다"]))
        mock_router.close = AsyncMock()
        mock_router_class.return_value = mock_router

        # 스트리밍 요청
        response = client.post(
            "/api/chat/stream",
            json={
                "query": "삼성전자 주가 분석",
                "messages": [],
            },
        )

        assert response.status_code == 200

        # SSE 응답 파싱
        content = response.text
        assert "data: " in content

    @patch("src.controllers.search_controller.VectorSearchService")
    def test_search_flow(self, mock_service_class, client):
        """전체 검색 플로우 테스트"""
        # Mock 설정
        mock_service = Mock()
        mock_service.search = Mock(
            return_value=[
                {
                    "id": "news_1",
                    "score": 0.92,
                    "metadata": {
                        "type": "news",
                        "title": "삼성전자 주가 상승",
                    },
                }
            ]
        )
        mock_service_class.return_value = mock_service

        # 검색 요청
        response = client.post(
            "/api/search/vector",
            json={
                "query": "삼성전자",
                "top_k": 5,
                "filter": {"type": "news"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert len(data["results"]) > 0
