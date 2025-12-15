"""
Environment Configuration
환경 변수 중앙 관리 (dotenv 사용)
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# .env 파일 로드 (프로젝트 루트에서)
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class EnvConfig:
    """환경 변수 설정 클래스"""

    # Ollama
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # Anthropic Claude
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

    # Google Gemini
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # Pinecone
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "insightstock")

    # Redis
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))  # AI 서비스 전용 DB

    # Server
    PORT = int(os.getenv("PORT", 3002))
    HOST = os.getenv("HOST", "0.0.0.0")
    NODE_ENV = os.getenv("NODE_ENV", "development")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # Backend API (동기화용)
    BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:3001")

    # 비용 최적화 설정 (선택사항)
    EMBEDDING_MODEL = os.getenv(
        "EMBEDDING_MODEL", "text-embedding-3-small"
    )  # 비용 효율적

    @classmethod
    def validate(cls) -> list[str]:
        """필수 환경 변수 검증"""
        missing = []

        # 최소 하나의 LLM Provider API 키가 필요
        has_provider = any(
            [
                cls.OPENAI_API_KEY,
                cls.ANTHROPIC_API_KEY,
                cls.GEMINI_API_KEY,
                cls.OLLAMA_HOST != "http://localhost:11434",  # Ollama는 로컬 서버
            ]
        )

        if not has_provider:
            missing.append(
                "At least one LLM provider API key (OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, or OLLAMA_HOST)"
            )

        return missing
