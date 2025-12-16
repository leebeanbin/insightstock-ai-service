"""
Chat Request DTO
채팅 API 요청 데이터 모델
"""

from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """채팅 요청 DTO"""

    query: str = Field(..., description="사용자 질문", min_length=1)
    messages: Optional[List[Dict[str, str]]] = Field(default=None, description="대화 히스토리 (선택적)")
    system: Optional[str] = Field(default=None, description="시스템 메시지 (선택적)")
    force_model: Optional[str] = Field(default=None, description="강제 사용할 모델 (선택적, 없으면 자동 선택)")
    userId: Optional[str] = Field(default=None, description="사용자 ID (선택적, 개인화용)")
    # 구조화된 응답 옵션
    response_type: Optional[Literal["stock_analysis", "news_summary", "market_analysis", "portfolio_recommendation", "simple"]] = Field(
        default=None, description="구조화된 응답 타입 (선택적, None이면 일반 텍스트 응답)"
    )
    stock_code: Optional[str] = Field(default=None, description="종목 코드 (stock_analysis일 때 필요)")
    news_text: Optional[str] = Field(default=None, description="뉴스 텍스트 (news_summary일 때 필요)")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "삼성전자 주가 분석해줘",
                "messages": [
                    {"role": "user", "content": "안녕하세요"},
                    {"role": "assistant", "content": "안녕하세요! 무엇을 도와드릴까요?"},
                ],
                "system": "You are a helpful financial advisor.",
                "force_model": "gpt-4o-mini",
                "response_type": "stock_analysis",
                "stock_code": "005930",
            }
        }
