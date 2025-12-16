"""
Chat Controller
채팅 API 엔드포인트 (스트리밍 및 비스트리밍)
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import json
from loguru import logger

from src.dto.chat_request import ChatRequest
from src.services.model_router import ModelRouterService
from src.exceptions import AIServiceError, ProviderError
from src.utils.concurrency import RateLimiter  # Rate Limiting

router = APIRouter()

# Rate Limiter 인스턴스 (사용자별, 엔드포인트별)
_chat_rate_limiter = RateLimiter("chat:stream", max_requests=60, window=60)  # 분당 60회
_chat_user_rate_limiter = RateLimiter("chat:user", max_requests=30, window=60)  # 사용자당 분당 30회


@router.post("/chat/stream")
async def stream_chat(
    request: ChatRequest,
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    """
    스트리밍 채팅 API
    구조화된 응답 지원: response_type이 있으면 스트리밍 완료 후 구조화된 응답 반환

    컨트롤러는 큰 흐름만 담당:
    1. 요청 받기
    2. 서비스 호출
    3. 응답 스트리밍

    에러 처리는 서비스 단에서 처리됨
    """
    try:
        model_router = ModelRouterService()

        async def generate() -> AsyncGenerator[str, None]:
            """SSE 스트리밍 생성기 (개선된 버퍼링)"""
            import asyncio
            
            buffer = ""
            buffer_size = 10  # 버퍼 크기 감소 (더 빠른 스트리밍)
            buffer_timeout = 0.05  # 50ms 타임아웃 (버퍼가 작아도 일정 시간 후 전송)
            full_response = ""  # 전체 응답 수집 (백엔드 저장 및 구조화용)
            last_send_time = asyncio.get_event_loop().time()

            try:
                async for chunk in model_router.route_and_stream(
                    query=request.query,
                    messages=request.messages,
                    system=request.system,
                    force_model=request.force_model,
                ):
                    if chunk:
                        buffer += chunk
                        full_response += chunk  # 전체 응답 수집
                        current_time = asyncio.get_event_loop().time()

                        # 버퍼가 충분히 크거나 타임아웃이 지났으면 전송
                        should_send = (
                            len(buffer) >= buffer_size or
                            (buffer and (current_time - last_send_time) >= buffer_timeout)
                        )

                        if should_send:
                            data = json.dumps({"content": buffer, "done": False}, ensure_ascii=False)
                            yield f"data: {data}\n\n"
                            buffer = ""
                            last_send_time = current_time

                # 남은 버퍼 전송
                if buffer:
                    data = json.dumps({"content": buffer, "done": False}, ensure_ascii=False)
                    yield f"data: {data}\n\n"

                # 구조화된 응답이 요청된 경우, 스트리밍 완료 후 구조화된 형식으로 변환
                if request.response_type and full_response:
                    try:
                        from src.services.structured_llm_service import StructuredLLMService
                        from src.dto.llm_responses import (
                            StockAnalysis,
                            NewsSummary,
                            MarketAnalysis,
                            PortfolioRecommendation,
                            SimpleResponse,
                        )

                        structured_service = StructuredLLMService()
                        structured_result = None

                        # 응답 타입에 따라 적절한 스키마로 변환
                        if request.response_type == "stock_analysis":
                            if request.stock_code:
                                # 전체 응답을 기반으로 구조화된 분석 생성
                                query_with_response = f"{request.query}\n\n응답: {full_response}"
                                structured_result = await structured_service.analyze_stock(
                                    stock_code=request.stock_code,
                                    model=request.force_model,
                                )
                        elif request.response_type == "news_summary":
                            if request.news_text:
                                structured_result = await structured_service.summarize_news(
                                    news_text=request.news_text,
                                    model=request.force_model,
                                )
                        elif request.response_type == "market_analysis":
                            structured_result = await structured_service.analyze_market(
                                query=request.query,
                                model=request.force_model,
                            )
                        elif request.response_type == "portfolio_recommendation":
                            structured_result = await structured_service.recommend_portfolio(
                                query=request.query,
                                model=request.force_model,
                            )
                        else:  # simple
                            structured_result = await structured_service.generate_structured(
                                query=request.query,
                                response_schema=SimpleResponse,
                                model=request.force_model,
                            )

                        # 구조화된 응답을 최종 데이터로 전송
                        if structured_result:
                            structured_data = json.dumps(
                                {
                                    "content": "",
                                    "done": False,
                                    "structured": True,
                                    "data": structured_result.model_dump() if hasattr(structured_result, 'model_dump') else structured_result.dict(),
                                },
                                ensure_ascii=False,
                            )
                            yield f"data: {structured_data}\n\n"
                            # 구조화된 응답을 백엔드 저장용으로 사용
                            full_response = structured_result.model_dump_json() if hasattr(structured_result, 'model_dump_json') else str(structured_result)

                    except Exception as e:
                        logger.warning(f"Failed to generate structured response: {e}")
                        # 구조화 실패 시 일반 텍스트 응답 유지

                # 완료 신호
                done_data = json.dumps({"content": "", "done": True}, ensure_ascii=False)
                yield f"data: {done_data}\n\n"

                # 스트리밍 완료 후 백엔드에 저장 (비동기 큐 사용)
                if request.userId and full_response:
                    try:
                        from src.services.chat_storage_queue import ChatStorageQueue

                        storage_queue = ChatStorageQueue()
                        await storage_queue.enqueue_chat(
                            userId=request.userId,
                            question=request.query,
                            answer=full_response,
                            messages=request.messages,
                        )
                        # 큐에 추가만 하고 즉시 반환 (워커가 백그라운드에서 처리)
                    except Exception as e:
                        # 저장 실패는 챗 응답에 영향을 주지 않도록 에러만 로깅
                        logger.warning(f"Failed to enqueue chat storage: {e}")

            except (AIServiceError, ProviderError) as e:
                logger.error(f"Stream chat error: {e}")
                error_data = json.dumps(
                    {"content": f"[Error: {str(e)}]", "done": True, "error": True},
                    ensure_ascii=False,
                )
                yield f"data: {error_data}\n\n"
            except Exception as e:
                logger.error(f"Unexpected stream chat error: {e}")
                error_data = json.dumps(
                    {
                        "content": f"[Unexpected Error: {str(e)}]",
                        "done": True,
                        "error": True,
                    },
                    ensure_ascii=False,
                )
                yield f"data: {error_data}\n\n"
            finally:
                # 리소스 정리
                await model_router.close()

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Nginx 버퍼링 비활성화
            },
        )

    except Exception as e:
        logger.error(f"Chat controller error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process chat request: {str(e)}")


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    일반 채팅 API (비스트리밍)
    구조화된 응답 지원: response_type이 있으면 구조화된 응답 반환
    """
    try:
        # 구조화된 응답 요청인 경우
        if request.response_type:
            try:
                from src.services.structured_llm_service import StructuredLLMService
                from src.dto.llm_responses import (
                    StockAnalysis,
                    NewsSummary,
                    MarketAnalysis,
                    PortfolioRecommendation,
                    SimpleResponse,
                )

                structured_service = StructuredLLMService()

                # 응답 타입에 따라 적절한 스키마 선택
                if request.response_type == "stock_analysis":
                    if not request.stock_code:
                        raise HTTPException(
                            status_code=400,
                            detail="stock_code is required for stock_analysis"
                        )
                    result = await structured_service.analyze_stock(
                        stock_code=request.stock_code,
                        model=request.force_model,
                    )
                elif request.response_type == "news_summary":
                    if not request.news_text:
                        raise HTTPException(
                            status_code=400,
                            detail="news_text is required for news_summary"
                        )
                    result = await structured_service.summarize_news(
                        news_text=request.news_text,
                        model=request.force_model,
                    )
                elif request.response_type == "market_analysis":
                    result = await structured_service.analyze_market(
                        query=request.query,
                        model=request.force_model,
                    )
                elif request.response_type == "portfolio_recommendation":
                    result = await structured_service.recommend_portfolio(
                        query=request.query,
                        model=request.force_model,
                    )
                else:  # simple
                    result = await structured_service.generate_structured(
                        query=request.query,
                        response_schema=SimpleResponse,
                        model=request.force_model,
                    )

                # 백엔드에 저장 (비동기 큐)
                if request.userId:
                    try:
                        from src.services.chat_storage_queue import ChatStorageQueue

                        storage_queue = ChatStorageQueue()
                        await storage_queue.enqueue_chat(
                            userId=request.userId,
                            question=request.query,
                            answer=result.model_dump_json() if hasattr(result, 'model_dump_json') else str(result),
                            messages=request.messages,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to enqueue chat storage: {e}")

                return {
                    "success": True,
                    "data": result.model_dump() if hasattr(result, 'model_dump') else result.dict(),
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Structured chat error: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to process structured chat request: {str(e)}"
                )

        # 일반 텍스트 응답
        model_router = ModelRouterService()

        try:
            # 채팅 실행
            response = await model_router.route_and_chat(
                query=request.query,
                messages=request.messages,
                system=request.system,
                force_model=request.force_model,
            )

            # 백엔드에 저장 (비동기 큐 사용)
            if request.userId and response:
                try:
                    from src.services.chat_storage_queue import ChatStorageQueue

                    storage_queue = ChatStorageQueue()
                    await storage_queue.enqueue_chat(
                        userId=request.userId,
                        question=request.query,
                        answer=response,
                        messages=request.messages,
                    )
                    # 큐에 추가만 하고 즉시 반환 (워커가 백그라운드에서 처리)
                except Exception as e:
                    # 저장 실패는 챗 응답에 영향을 주지 않도록 에러만 로깅
                    logger.warning(f"Failed to enqueue chat storage: {e}")

            # 간단한 챗이므로 content만 반환 (경량 모델 사용 전략)
            return {
                "success": True,
                "content": response,
            }
        finally:
            # 리소스 정리
            await model_router.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat controller error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process chat request: {str(e)}")


@router.get("/models")
async def get_models():
    """
    사용 가능한 모델 목록 조회
    """
    try:
        from src.providers import ProviderFactory
        from src.models.model_config import ModelConfigManager

        available_providers = ProviderFactory.get_available_providers()

        # 모델 목록 구성
        models = []
        for model_name, config in ModelConfigManager.MODELS.items():
            models.append(
                {
                    "name": model_name,
                    "display_name": config.display_name,
                    "type": config.type,
                    "provider": (config.provider.value if hasattr(config.provider, "value") else str(config.provider)),
                    "description": config.description,
                    "use_case": config.use_case,
                }
            )

        return {
            "success": True,
            "available_providers": available_providers,
            "models": models,
        }

    except Exception as e:
        logger.error(f"Get models error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get models: {str(e)}")


@router.get("/queue/stats")
async def get_queue_stats():
    """
    Redis 메시지 큐 통계 조회 (모니터링)
    """
    try:
        from src.services.redis_message_queue import RedisMessageQueue
        from src.services.dlq_handler import DLQHandler
        from src.config.env import EnvConfig
        
        queue = RedisMessageQueue()
        dlq_handler = DLQHandler(
            use_file_system=EnvConfig.USE_FILE_DLQ,
            dlq_dir=EnvConfig.DLQ_DIR,
        )
        
        # 주요 큐들의 길이 조회
        chat_storage_queue_length = queue.get_queue_length("chat:storage")
        chat_storage_dlq_count = dlq_handler.get_dlq_count("chat:storage")
        
        # 백프레셔 상태
        max_queue_length = EnvConfig.MAX_QUEUE_LENGTH
        queue_usage_percent = (chat_storage_queue_length / max_queue_length * 100) if max_queue_length > 0 else 0
        
        return {
            "success": True,
            "queues": {
                "chat:storage": {
                    "length": chat_storage_queue_length,
                    "max_length": max_queue_length,
                    "usage_percent": round(queue_usage_percent, 2),
                    "status": "active" if chat_storage_queue_length > 0 else "empty",
                    "backpressure": queue_usage_percent >= 90,
                },
                "chat:storage:dlq": {
                    "count": chat_storage_dlq_count,
                    "type": "file" if EnvConfig.USE_FILE_DLQ else "redis",
                    "status": "active" if chat_storage_dlq_count > 0 else "empty",
                },
            },
            "config": {
                "compression_enabled": EnvConfig.ENABLE_MESSAGE_COMPRESSION,
                "batch_size": EnvConfig.WORKER_BATCH_SIZE,
            },
        }
        
    except Exception as e:
        logger.error(f"Get queue stats error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get queue stats: {str(e)}")


@router.get("/chat/history")
async def get_chat_history(
    userId: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    concept: Optional[str] = None,
    stockCode: Optional[str] = None,
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    """
    챗 히스토리 조회 (캐싱 포함)
    
    Args:
        userId: 사용자 ID (선택적, 없으면 Authorization 헤더에서 추출)
        page: 페이지 번호 (기본값: 1)
        limit: 페이지당 항목 수 (기본값: 20, 최대: 100)
        concept: 개념 필터 (선택적)
        stockCode: 종목 코드 필터 (선택적)
        authorization: Authorization 헤더 (JWT 토큰)
    
    Returns:
        챗 히스토리 리스트
    """
    # userId가 없으면 Authorization 헤더에서 추출
    if not userId and authorization:
        extracted_user_id = get_user_id_from_token(authorization)
        if extracted_user_id:
            userId = extracted_user_id
            logger.debug(f"Extracted userId from token: {extracted_user_id}")
    
    if not userId:
        raise HTTPException(status_code=400, detail="userId is required (provide userId parameter or Authorization header)")
    
    if limit > 100:
        limit = 100  # 최대 제한
    
    try:
        from src.services.chat_storage_service import ChatStorageService
        from src.utils.cache import cache
        import hashlib
        
        # 캐시 키 생성
        cache_key_parts = [userId, str(page), str(limit)]
        if concept:
            cache_key_parts.append(f"concept:{concept}")
        if stockCode:
            cache_key_parts.append(f"stock:{stockCode}")
        
        cache_key = f"chat_history:{hashlib.md5(':'.join(cache_key_parts).encode()).hexdigest()}"
        
        # 캐시 확인
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"Chat history cache hit: {userId}")
            return {
                "success": True,
                "data": cached,
                "cached": True,
            }
        
        # 백엔드 API 호출
        storage_service = ChatStorageService()
        
        # 쿼리 파라미터 구성 (백엔드 API는 offset 기반 페이지네이션 사용)
        offset = (page - 1) * limit
        params = {
            "userId": userId,
            "offset": offset,
            "limit": limit,
        }
        if concept:
            params["concept"] = concept
        if stockCode:
            params["stockCode"] = stockCode
        
        response = await storage_service.client.get(
            f"{storage_service.backend_url}/api/learning",
            params=params,
        )
        
        if response.status_code == 200:
            backend_data = response.json()
            
            # 백엔드 응답 형식: { success: true, data: [...], meta: {...} }
            # 프론트엔드 호환성을 위해 동일한 형식으로 반환
            chat_history = backend_data.get("data", [])
            meta = backend_data.get("meta", {})
            
            # 캐시 저장 (5분 TTL)
            cache_data = {
                "data": chat_history,
                "meta": meta,
            }
            cache.set(cache_key, cache_data, ttl=300)
            
            return {
                "success": True,
                "data": chat_history,
                "meta": meta,
                "cached": False,
            }
        else:
            logger.error(
                f"Failed to get chat history: {response.status_code} - {response.text}"
            )
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to get chat history: {response.text}",
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get chat history error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get chat history: {str(e)}")
