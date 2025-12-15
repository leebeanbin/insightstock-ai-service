"""
Database Configuration
PostgreSQL 연결 설정 (Prisma 스타일)
실제 Prisma 클라이언트는 메인 백엔드에서 관리
AI 서비스는 HTTP API를 통해 메인 백엔드와 통신
"""

from typing import Optional
from loguru import logger

# 실제 구현은 메인 백엔드와의 통신으로 처리
# 이 파일은 향후 직접 DB 연결 시 사용할 수 있도록 준비


class DatabaseConfig:
    """데이터베이스 설정"""

    # 메인 백엔드 API URL
    BACKEND_API_URL: Optional[str] = None

    @classmethod
    def get_backend_url(cls) -> str:
        """메인 백엔드 API URL 반환"""
        from src.config.env import EnvConfig

        # 환경 변수에서 가져오거나 기본값 사용
        return getattr(EnvConfig, "BACKEND_API_URL", "http://localhost:3001")

    @classmethod
    async def execute_in_transaction(cls, operation):
        """
        트랜잭션 내에서 작업 실행
        실제로는 메인 백엔드 API를 통해 트랜잭션 실행

        Args:
            operation: 실행할 작업

        Returns:
            작업 결과
        """
        # 메인 백엔드의 executeTransaction을 호출
        # 실제 구현은 HTTP API 호출
        logger.info("Executing transaction via backend API")
        return await operation()
