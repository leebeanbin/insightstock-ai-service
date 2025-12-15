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
_chat_user_rate_limiter = RateLimiter(
    "chat:user", max_requests=30, window=60
)  # 사용자당 분당 30회


@router.post("/chat/stream")
async def stream_chat(request: ChatRequest):
    """
    스트리밍 채팅 API

    컨트롤러는 큰 흐름만 담당:
    1. 요청 받기
    2. 서비스 호출
    3. 응답 스트리밍

    에러 처리는 서비스 단에서 처리됨
    """
    try:
        model_router = ModelRouterService()

        async def generate() -> AsyncGenerator[str, None]:
            """SSE 스트리밍 생성기 (버퍼링 적용)"""
            buffer = ""
            buffer_size = 50  # 최소 버퍼 크기 (문자 수)
            
            try:
                async for chunk in model_router.route_and_stream(
                    query=request.query,
                    messages=request.messages,
                    system=request.system,
                    force_model=request.force_model,
                ):
                    if chunk:
                        buffer += chunk
                        
                        # 버퍼가 충분히 크면 전송
                        if len(buffer) >= buffer_size:
                            data = json.dumps(
                                {"content": buffer, "done": False}, ensure_ascii=False
                            )
                            yield f"data: {data}\n\n"
                            buffer = ""
                
                # 남은 버퍼 전송
                if buffer:
                    data = json.dumps(
                        {"content": buffer, "done": False}, ensure_ascii=False
                    )
                    yield f"data: {data}\n\n"

                # 완료 신호
                done_data = json.dumps({"content": "", "done": True}, ensure_ascii=False)
                yield f"data: {done_data}\n\n"

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
        raise HTTPException(
            status_code=500, detail=f"Failed to process chat request: {str(e)}"
        )


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    일반 채팅 API (비스트리밍)
    """
    try:
        model_router = ModelRouterService()

        try:
            # 채팅 실행
            response = await model_router.route_and_chat(
                query=request.query,
                messages=request.messages,
                system=request.system,
                force_model=request.force_model,
            )

            # 간단한 챗이므로 content만 반환 (경량 모델 사용 전략)
            return {
                "success": True,
                "content": response,
            }
        finally:
            # 리소스 정리
            await model_router.close()

    except Exception as e:
        logger.error(f"Chat controller error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to process chat request: {str(e)}"
        )


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
                    "provider": (
                        config.provider.value
                        if hasattr(config.provider, "value")
                        else str(config.provider)
                    ),
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
