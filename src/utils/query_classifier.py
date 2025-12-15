"""
Query Classifier
쿼리 복잡도 및 특성 분류
"""

import re
from typing import List
from loguru import logger


class QueryClassifier:
    """쿼리 분류기"""
    
    # 간단한 질문 키워드
    SIMPLE_KEYWORDS = [
        "뭐야", "뭐", "무엇", "어떤", "어디", "언제", "누구",
        "what", "where", "when", "who", "which",
        "정의", "의미", "개념",
    ]
    
    # 복잡한 질문 키워드
    COMPLEX_KEYWORDS = [
        "분석", "전략", "비교", "예측", "추천", "설명",
        "analyze", "strategy", "compare", "predict", "recommend", "explain",
        "투자", "포트폴리오", "리스크", "수익률",
    ]
    
    # 금융 관련 키워드
    FINANCIAL_KEYWORDS = [
        "주가", "주식", "투자", "배당", "PER", "PBR", "ROE", "ROA",
        "시가총액", "거래량", "상승", "하락", "매수", "매도",
        "포트폴리오", "리스크", "수익률", "손실", "이익",
        "삼성전자", "애플", "테슬라", "나스닥", "코스피", "코스닥",
        "stock", "price", "dividend", "portfolio", "risk", "return",
    ]
    
    # 컨텍스트 필요 키워드
    CONTEXT_KEYWORDS = [
        "최근", "요즘", "지금", "현재", "오늘", "어제",
        "recent", "current", "now", "today", "latest",
        "내", "나의", "내가", "my", "mine",
    ]
    
    @classmethod
    def classify_complexity(cls, query: str) -> str:
        """
        쿼리 복잡도 분류
        
        Args:
            query: 사용자 쿼리
        
        Returns:
            "simple", "moderate", "complex"
        """
        if not query:
            return "simple"
        
        query_lower = query.lower()
        query_length = len(query.split())
        
        # 복잡한 키워드 확인
        complex_count = sum(1 for keyword in cls.COMPLEX_KEYWORDS if keyword in query_lower)
        simple_count = sum(1 for keyword in cls.SIMPLE_KEYWORDS if keyword in query_lower)
        
        # 길이 기반 분류
        if query_length <= 5 and simple_count > 0 and complex_count == 0:
            return "simple"
        elif query_length > 20 or complex_count >= 2:
            return "complex"
        elif complex_count >= 1 or query_length > 10:
            return "moderate"
        else:
            return "simple"
    
    @classmethod
    def needs_context(cls, query: str) -> bool:
        """
        컨텍스트 필요 여부 판단
        
        Args:
            query: 사용자 쿼리
        
        Returns:
            True if context is needed
        """
        if not query:
            return False
        
        query_lower = query.lower()
        
        # 컨텍스트 키워드 확인
        context_count = sum(1 for keyword in cls.CONTEXT_KEYWORDS if keyword in query_lower)
        
        return context_count > 0
    
    @classmethod
    def is_financial(cls, query: str) -> bool:
        """
        금융 관련 질문 판단
        
        Args:
            query: 사용자 쿼리
        
        Returns:
            True if financial-related
        """
        if not query:
            return False
        
        query_lower = query.lower()
        
        # 금융 키워드 확인
        financial_count = sum(1 for keyword in cls.FINANCIAL_KEYWORDS if keyword in query_lower)
        
        return financial_count > 0
    
    @classmethod
    def classify(cls, query: str) -> dict:
        """
        종합 분류
        
        Args:
            query: 사용자 쿼리
        
        Returns:
            분류 결과 딕셔너리
        """
        return {
            "complexity": cls.classify_complexity(query),
            "needs_context": cls.needs_context(query),
            "is_financial": cls.is_financial(query),
        }
