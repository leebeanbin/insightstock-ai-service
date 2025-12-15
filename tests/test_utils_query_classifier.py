"""
Query Classifier 테스트
"""

import pytest
from src.utils.query_classifier import QueryClassifier


class TestQueryClassifier:
    """QueryClassifier 테스트"""

    def test_classify_simple_query(self):
        """간단한 질문 분류"""
        result = QueryClassifier.classify_complexity("PER이 뭐야?")
        assert result == "simple"

    def test_classify_moderate_query(self):
        """중간 복잡도 질문 분류"""
        result = QueryClassifier.classify_complexity("삼성전자 주가를 분석해주세요")
        assert result in ["moderate", "complex"]

    def test_classify_complex_query(self):
        """복잡한 질문 분류"""
        result = QueryClassifier.classify_complexity(
            "삼성전자와 애플의 재무제표를 비교 분석하고, 향후 투자 전략을 추천해주세요"
        )
        assert result == "complex"

    def test_needs_context(self):
        """컨텍스트 필요 여부 판단"""
        assert QueryClassifier.needs_context("최근 삼성전자 주가") == True
        assert QueryClassifier.needs_context("내 포트폴리오 분석") == True
        assert QueryClassifier.needs_context("PER이 무엇인가요?") == False

    def test_is_financial(self):
        """금융 관련 질문 판단"""
        assert QueryClassifier.is_financial("삼성전자 주가 분석") == True
        assert QueryClassifier.is_financial("PER과 PBR의 차이") == True
        assert QueryClassifier.is_financial("오늘 날씨는?") == False

    def test_classify_comprehensive(self):
        """종합 분류 테스트"""
        result = QueryClassifier.classify("최근 삼성전자 주가 분석해줘")
        assert "complexity" in result
        assert "needs_context" in result
        assert "is_financial" in result
        assert result["is_financial"] == True
        assert result["needs_context"] == True
