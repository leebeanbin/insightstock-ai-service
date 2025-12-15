"""
Search Request DTO
벡터 검색 API 요청 데이터 모델
"""

from typing import Dict, Optional
from pydantic import BaseModel, Field


class VectorSearchRequest(BaseModel):
    """벡터 검색 요청 DTO"""
    
    query: str = Field(..., description="검색 쿼리", min_length=1)
    top_k: int = Field(
        default=5,
        description="반환할 결과 수",
        ge=1,
        le=100
    )
    filter: Optional[Dict] = Field(
        default=None,
        description="메타데이터 필터 (선택적)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "삼성전자 주가 상승",
                "top_k": 5,
                "filter": {
                    "type": "news"
                }
            }
        }
