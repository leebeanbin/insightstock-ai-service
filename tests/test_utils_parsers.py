"""
Parsers 테스트
"""

import pytest
from src.utils.parsers import (
    parse_news_for_indexing,
    parse_stock_for_indexing,
    parse_learning_for_indexing,
    chunk_text,
)


class TestParsers:
    """Parsers 테스트"""

    def test_parse_news_for_indexing(self, sample_news_data):
        """뉴스 파싱 테스트"""
        result = parse_news_for_indexing(sample_news_data)

        assert result["id"] == "news_1"
        assert "text" in result
        assert "metadata" in result
        assert result["metadata"]["type"] == "news"
        assert result["metadata"]["title"] == sample_news_data["title"]
        assert result["metadata"]["stock_codes"] == ["005930"]

    def test_parse_stock_for_indexing(self, sample_stock_data):
        """주식 파싱 테스트"""
        result = parse_stock_for_indexing(sample_stock_data)

        assert result["id"] == "stock_005930"
        assert "text" in result
        assert "metadata" in result
        assert result["metadata"]["type"] == "stock"
        assert result["metadata"]["code"] == "005930"
        assert result["metadata"]["name"] == "삼성전자"

    def test_parse_learning_for_indexing(self, sample_learning_data):
        """학습 콘텐츠 파싱 테스트"""
        result = parse_learning_for_indexing(sample_learning_data)

        assert result["id"] == "learning_1"
        assert "text" in result
        assert "metadata" in result
        assert result["metadata"]["type"] == "learning"
        assert result["metadata"]["concept"] == "PER"

    def test_chunk_text(self):
        """텍스트 청킹 테스트"""
        text = "a" * 1000  # 1000자 텍스트
        chunks = chunk_text(text, chunk_size=200, overlap=50)

        assert len(chunks) > 1
        assert all(len(chunk) <= 200 for chunk in chunks)

        # 첫 번째와 두 번째 청크가 overlap만큼 겹치는지 확인
        if len(chunks) > 1:
            # overlap이 50이므로, 두 번째 청크의 시작이 첫 번째 청크의 끝에서 50자 전부터 시작
            assert chunks[1][:50] == chunks[0][-50:]

    def test_chunk_text_empty(self):
        """빈 텍스트 청킹 테스트"""
        chunks = chunk_text("", chunk_size=100, overlap=10)
        assert chunks == []

    def test_chunk_text_small(self):
        """작은 텍스트 청킹 테스트"""
        chunks = chunk_text("short text", chunk_size=100, overlap=10)
        assert len(chunks) == 1
        assert chunks[0] == "short text"
