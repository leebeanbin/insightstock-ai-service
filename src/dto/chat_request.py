"""
Chat Request DTO
채팅 API 요청 데이터 모델
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """채팅 요청 DTO"""
    
    query: str = Field(..., description="사용자 질문", min_length=1)
    messages: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="대화 히스토리 (선택적)"
    )
    system: Optional[str] = Field(
        default=None,
        description="시스템 메시지 (선택적)"
    )
    force_model: Optional[str] = Field(
        default=None,
        description="강제 사용할 모델 (선택적, 없으면 자동 선택)"
    )
    userId: Optional[str] = Field(
        default=None,
        description="사용자 ID (선택적, 개인화용)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "삼성전자 주가 분석해줘",
                "messages": [
                    {"role": "user", "content": "안녕하세요"},
                    {"role": "assistant", "content": "안녕하세요! 무엇을 도와드릴까요?"}
                ],
                "system": "You are a helpful financial advisor.",
                "force_model": "gpt-4o-mini"
            }
        }
