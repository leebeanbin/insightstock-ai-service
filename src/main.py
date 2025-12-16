"""
AI Service Main Server
InsightStock AI Service - LLM/SLM integration with multiple providers (Python)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from loguru import logger

# 환경 변수 로드 (config/env.py에서 중앙 관리)
from src.config.env import EnvConfig
from src.config.managers import get_redis_manager

# Import controllers
from src.controllers.chat_controller import router as chat_router
from src.controllers.search_controller import router as search_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    import asyncio
    from src.workers.chat_storage_worker import ChatStorageWorker

    # Startup
    logger.info("🚀 AI Service starting up...")

    # 사용 가능한 Provider 확인
    from src.providers import ProviderFactory

    available_providers = ProviderFactory.get_available_providers()
    logger.info(f"Available LLM providers: {available_providers}")

    if not available_providers:
        logger.warning("⚠️  No LLM providers available! Please set at least one API key.")
    else:
        # 기본 Provider 확인
        try:
            default_provider = ProviderFactory.get_default_provider()
            logger.info(f"✅ Default provider: {default_provider.name}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize default provider: {e}")

    # 워커 시작 (백그라운드 태스크, 배치 처리 지원)
    from src.config.env import EnvConfig
    
    worker = ChatStorageWorker()
    worker_task = None
    
    try:
        batch_size = EnvConfig.WORKER_BATCH_SIZE
        worker_task = asyncio.create_task(worker.run(batch_size=batch_size))
        logger.info(f"✅ Chat storage worker started (batch_size={batch_size})")
    except Exception as e:
        logger.warning(f"⚠️  Failed to start chat storage worker: {e}")

    yield

    # Shutdown
    logger.info("🛑 AI Service shutting down...")
    
    # 워커 중지
    if worker_task:
        try:
            worker.stop()
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass
            logger.info("✅ Chat storage worker stopped")
        except Exception as e:
            logger.warning(f"⚠️  Error stopping worker: {e}")
    
    ProviderFactory.clear_cache()
    redis_manager = get_redis_manager()
    redis_manager.close()  # Redis 연결 종료


# Initialize FastAPI app
app = FastAPI(
    title="InsightStock AI Service",
    description="AI Service for LLM/SLM integration with multiple providers (OpenAI, Claude, Ollama, Gemini)",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(chat_router, prefix="/api", tags=["chat"])
app.include_router(search_router, prefix="/api", tags=["search"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from src.providers import ProviderFactory

    available_providers = ProviderFactory.get_available_providers()

    return {
        "status": "ok",
        "service": "ai-service",
        "version": "1.0.0",
        "available_providers": available_providers,
    }


if __name__ == "__main__":
    # 환경 변수 검증
    missing = EnvConfig.validate()
    if missing:
        logger.warning(f"⚠️  Missing environment variables: {', '.join(missing)}")
        logger.warning("Service will start but may not function correctly.")

    logger.info(f"🚀 Starting server on {EnvConfig.HOST}:{EnvConfig.PORT}")
    logger.info(f"📖 API Documentation: http://{EnvConfig.HOST}:{EnvConfig.PORT}/docs")

    uvicorn.run(
        "src.main:app",
        host=EnvConfig.HOST,
        port=EnvConfig.PORT,
        reload=True,
        log_level=EnvConfig.LOG_LEVEL.lower(),
    )
