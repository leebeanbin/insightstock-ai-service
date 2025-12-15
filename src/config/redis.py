"""
Redis Configuration
캐싱을 위한 Redis 클라이언트 설정
"""

import redis
from loguru import logger
from src.config.env import EnvConfig

_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    """
    Redis 클라이언트 인스턴스 반환 (싱글톤)
    
    Returns:
        Redis 클라이언트 인스턴스
    """
    global _redis_client
    
    if _redis_client is not None:
        return _redis_client
    
    try:
        # Redis 연결 파라미터 구성
        redis_params = {
            "host": EnvConfig.REDIS_HOST,
            "port": EnvConfig.REDIS_PORT,
            "db": EnvConfig.REDIS_DB,
            "decode_responses": False,  # 바이너리 데이터 지원
            "socket_connect_timeout": 5,
            "socket_timeout": 5,
            "retry_on_timeout": True,
            "health_check_interval": 30,
        }
        
        # 비밀번호가 설정된 경우에만 추가
        if EnvConfig.REDIS_PASSWORD:
            redis_params["password"] = EnvConfig.REDIS_PASSWORD
        
        _redis_client = redis.Redis(**redis_params)
        
        # 연결 테스트
        _redis_client.ping()
        logger.info(
            f"Redis connected: {EnvConfig.REDIS_HOST}:{EnvConfig.REDIS_PORT}"
            + (f" (with password)" if EnvConfig.REDIS_PASSWORD else " (no password)")
        )
        
        return _redis_client
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        logger.warning("Falling back to in-memory cache")
        raise


def close_redis():
    """Redis 연결 종료"""
    global _redis_client
    if _redis_client:
        try:
            _redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")
        finally:
            _redis_client = None

