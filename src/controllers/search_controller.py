"""
Search Controller
벡터 검색 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException
from loguru import logger

from src.dto.search_request import VectorSearchRequest
from src.services.vector_search_service import VectorSearchService
from src.exceptions import VectorSearchError, EmbeddingError
from src.utils.concurrency import RateLimiter  # Rate Limiting

router = APIRouter()

# Rate Limiter 인스턴스
_search_rate_limiter = RateLimiter(
    "search:vector", max_requests=100, window=60
)  # 분당 100회


@router.post("/search/vector")
async def vector_search(request: VectorSearchRequest):
    """
    벡터 검색 API
    """
    try:
        service = VectorSearchService()

        results = service.search(
            query=request.query,
            top_k=request.top_k,
            filter=request.filter,
        )

        return {
            "success": True,
            "query": request.query,
            "top_k": request.top_k,
            "filter": request.filter,
            "results": results,
            "count": len(results),
        }

    except (VectorSearchError, EmbeddingError) as e:
        logger.error(f"Vector search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search service error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected vector search error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to process search request: {str(e)}"
        )


@router.get("/search/index/stats")
async def get_index_stats():
    """
    Pinecone 인덱스 통계 조회
    """
    try:
        service = VectorSearchService()
        stats = service.get_stats()

        return {
            "success": True,
            "index_name": service.index_name,
            "stats": stats,
        }

    except VectorSearchError as e:
        logger.error(f"Get index stats error: {e}")
        raise HTTPException(status_code=500, detail=f"Index stats error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected get index stats error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get index stats: {str(e)}"
        )
