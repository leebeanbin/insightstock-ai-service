"""
Ollama Client
Ollama API를 통한 LLM/SLM 모델 통합
"""

from typing import AsyncGenerator, List, Dict, Optional
import httpx
from loguru import logger
from src.config.env import EnvConfig


class OllamaClient:
    """Ollama API 클라이언트"""

    def __init__(self, host: Optional[str] = None):
        self.host = host or EnvConfig.OLLAMA_HOST
        self.base_url = f"{self.host}/api"
        self.client = httpx.AsyncClient(timeout=300.0)

    async def check_connection(self) -> bool:
        """Ollama 서버 연결 확인"""
        try:
            response = await self.client.get(f"{self.base_url}/tags")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama connection check failed: {e}")
            return False

    async def list_models(self) -> List[Dict]:
        """설치된 모델 목록 조회"""
        try:
            response = await self.client.get(f"{self.base_url}/tags")
            if response.status_code == 200:
                data = response.json()
                return data.get("models", [])
            return []
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    async def pull_model(self, model_name: str) -> bool:
        """모델 다운로드"""
        try:
            async with self.client.stream(
                "POST", f"{self.base_url}/pull", json={"name": model_name}
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        logger.debug(f"Pull progress: {line}")
            return True
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False

    async def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """스트리밍 채팅"""
        try:
            payload = {
                "model": model,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": temperature,
                },
            }

            if system:
                payload["system"] = system

            if max_tokens:
                payload["options"]["num_predict"] = max_tokens

            async with self.client.stream(
                "POST",
                f"{self.base_url}/chat",
                json=payload,
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error(f"Ollama API error: {error_text}")
                    yield f"[Error: {response.status_code}]"
                    return

                async for line in response.aiter_lines():
                    if line:
                        try:
                            import json

                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                content = data["message"]["content"]
                                if content:
                                    yield content
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Stream chat error: {e}")
            yield f"[Error: {str(e)}]"

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        """일반 채팅 (비스트리밍)"""
        try:
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                },
            }

            if system:
                payload["system"] = system

            response = await self.client.post(
                f"{self.base_url}/chat",
                json=payload,
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("message", {}).get("content", "")
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return f"[Error: {response.status_code}]"
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return f"[Error: {str(e)}]"

    async def close(self):
        """클라이언트 종료"""
        await self.client.aclose()
