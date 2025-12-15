"""
Data Parsers
뉴스, 주식, 학습 콘텐츠를 벡터 DB 인덱싱용으로 파싱
"""

from typing import List, Dict


def parse_news_for_indexing(news_data: Dict) -> Dict:
    """
    뉴스 데이터를 인덱싱용으로 파싱

    Args:
        news_data: 뉴스 데이터 딕셔너리
            - id: 뉴스 ID
            - title: 제목
            - summary: 요약 (선택)
            - content: 본문 (선택)
            - source: 출처
            - publishedAt: 발행일
            - stockCodes: 관련 주식 코드 리스트
            - sentiment: 감정 분석 결과
            - url: URL

    Returns:
        인덱싱용 데이터
            - id: "news_{id}" 형식
            - text: 인덱싱할 텍스트
            - metadata: 메타데이터
    """
    # 텍스트 구성 (제목 + 요약 또는 본문 일부)
    text_parts = [news_data.get("title", "")]

    if news_data.get("summary"):
        text_parts.append(news_data["summary"])
    elif news_data.get("content"):
        # 본문의 처음 500자만 사용
        text_parts.append(news_data["content"][:500])

    text = "\n".join(text_parts)

    return {
        "id": f"news_{news_data['id']}",
        "text": text,
        "metadata": {
            "type": "news",
            "title": news_data.get("title", ""),
            "source": news_data.get("source", ""),
            "published_at": news_data.get("publishedAt", ""),
            "stock_codes": news_data.get("stockCodes", []),
            "sentiment": news_data.get("sentiment"),
            "url": news_data.get("url"),
        },
    }


def parse_stock_for_indexing(stock_data: Dict) -> Dict:
    """
    주식 데이터를 인덱싱용으로 파싱

    Args:
        stock_data: 주식 데이터 딕셔너리
            - code: 주식 코드
            - name: 종목명
            - sector: 섹터
            - market: 시장 (KOSPI, KOSDAQ 등)
            - description: 설명 (선택)

    Returns:
        인덱싱용 데이터
            - id: "stock_{code}" 형식
            - text: 인덱싱할 텍스트
            - metadata: 메타데이터
    """
    # 텍스트 구성
    text_parts = [
        stock_data.get("name", ""),
        stock_data.get("code", ""),
        stock_data.get("sector", ""),
        stock_data.get("market", ""),
    ]

    if stock_data.get("description"):
        text_parts.append(stock_data["description"][:500])

    text = " ".join(filter(None, text_parts))

    return {
        "id": f"stock_{stock_data['code']}",
        "text": text,
        "metadata": {
            "type": "stock",
            "code": stock_data.get("code", ""),
            "name": stock_data.get("name", ""),
            "sector": stock_data.get("sector", ""),
            "market": stock_data.get("market", ""),
        },
    }


def parse_learning_for_indexing(learning_data: Dict) -> Dict:
    """
    학습 콘텐츠를 인덱싱용으로 파싱

    Args:
        learning_data: 학습 데이터 딕셔너리
            - id: 학습 ID
            - concept: 개념
            - question: 질문
            - answer: 답변 (선택)
            - tags: 태그 리스트

    Returns:
        인덱싱용 데이터
            - id: "learning_{id}" 형식
            - text: 인덱싱할 텍스트
            - metadata: 메타데이터
    """
    # 텍스트 구성
    text_parts = [
        learning_data.get("concept", ""),
        learning_data.get("question", ""),
    ]

    if learning_data.get("answer"):
        text_parts.append(learning_data["answer"][:500])

    text = "\n".join(filter(None, text_parts))

    return {
        "id": f"learning_{learning_data['id']}",
        "text": text,
        "metadata": {
            "type": "learning",
            "concept": learning_data.get("concept", ""),
            "question": learning_data.get("question", ""),
            "tags": learning_data.get("tags", []),
        },
    }


def chunk_text(
    text: str,
    chunk_size: int = 512,  # 최적화: 512 토큰 기준 (약 2000자)
    overlap: float = 0.15,  # 최적화: 15% 오버랩 (최신 연구 기반)
) -> List[str]:
    """
    텍스트를 청크로 분할 (최신 RAG 패턴 적용)

    최적화 사항:
    - 청크 크기: 512 토큰 (약 2000자) - 최적 밸런스
    - 오버랩: 15% - 컨텍스트 손실 최소화
    - 문장 경계 고려

    Args:
        text: 원본 텍스트
        chunk_size: 청크 크기 (문자 수, 기본값: 2000)
        overlap: 겹치는 비율 (0.0-1.0, 기본값: 0.15)

    Returns:
        청크 리스트
    """
    if not text:
        return []

    # 오버랩을 문자 수로 변환
    overlap_chars = int(chunk_size * overlap)

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # 문장 경계 찾기 (컨텍스트 보존)
        if end < len(text):
            # 마지막 문장 끝 찾기
            last_period = chunk.rfind(".")
            last_newline = chunk.rfind("\n")
            boundary = max(last_period, last_newline)

            if boundary > chunk_size * 0.7:  # 70% 이상이면 경계 사용
                chunk = chunk[: boundary + 1]
                end = start + boundary + 1

        chunks.append(chunk.strip())
        start = end - overlap_chars

    return chunks
