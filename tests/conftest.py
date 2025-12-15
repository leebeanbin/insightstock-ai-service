"""
Pytest Configuration
테스트 공통 설정 및 Fixtures
"""

import pytest
import os
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# 테스트 환경 변수 설정
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("OLLAMA_HOST", "http://localhost:11434")
os.environ.setdefault("PINECONE_API_KEY", "test-pinecone-key")
os.environ.setdefault("PINECONE_INDEX_NAME", "test-index")
os.environ.setdefault("PORT", "3002")
os.environ.setdefault("HOST", "0.0.0.0")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("REDIS_DB", "1")  # 테스트용 DB
os.environ.setdefault("BACKEND_API_URL", "http://localhost:3001")
os.environ.setdefault("EMBEDDING_MODEL", "text-embedding-3-small")


@pytest.fixture
def mock_provider():
    """Mock Provider Fixture"""
    provider = Mock()
    provider.name = "MockProvider"
    provider.stream_chat = AsyncMock(return_value=iter(["chunk1", "chunk2", "chunk3"]))
    provider.chat = AsyncMock(return_value=Mock(content="Test response"))
    provider.list_models = AsyncMock(return_value=["model1", "model2"])
    provider.is_available = Mock(return_value=True)
    provider.health_check = AsyncMock(return_value=True)
    return provider


@pytest.fixture
def sample_messages():
    """샘플 메시지 리스트"""
    return [
        {"role": "user", "content": "안녕하세요"},
        {"role": "assistant", "content": "안녕하세요! 무엇을 도와드릴까요?"},
    ]


@pytest.fixture
def sample_news_data():
    """샘플 뉴스 데이터"""
    return {
        "id": "1",
        "title": "삼성전자 주가 상승",
        "summary": "삼성전자 주가가 전일 대비 2% 상승했습니다.",
        "content": "삼성전자 주가가...",
        "source": "한국경제",
        "publishedAt": "2025-12-15T10:00:00Z",
        "stockCodes": ["005930"],
        "sentiment": "positive",
        "url": "https://example.com/news/1",
    }


@pytest.fixture
def sample_stock_data():
    """샘플 주식 데이터"""
    return {
        "code": "005930",
        "name": "삼성전자",
        "sector": "반도체",
        "market": "KOSPI",
        "description": "삼성전자는 세계 최대 반도체 제조사입니다...",
    }


@pytest.fixture
def sample_learning_data():
    """샘플 학습 데이터"""
    return {
        "id": "1",
        "concept": "PER",
        "question": "PER이 무엇인가요?",
        "answer": "PER은 주가수익비율입니다...",
        "tags": ["재무", "주식"],
    }
