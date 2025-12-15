"""
LLM Service
Large Language Model 서비스 (Provider 추상화 사용)
"""

from typing import AsyncGenerator, List, Dict, Optional
from src.providers import ProviderFactory, BaseLLMProvider
from src.models.model_config import ModelConfigManager
from loguru import logger


class LLMService:
    """LLM 서비스 (Provider 추상화 사용)"""

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        """
        LLM 서비스 초기화

        Args:
            provider: LLM 제공자 (None이면 자동 선택)
        """
        self.provider = provider or ProviderFactory.get_default_provider()
        logger.info(f"LLMService initialized with provider: {self.provider.name}")

    async def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> AsyncGenerator[str, None]:
        """
        스트리밍 채팅

        Args:
            model: 사용할 모델
            messages: 대화 메시지 리스트
            system: 시스템 메시지
            temperature: 온도

        Yields:
            응답 청크
        """
        # 모델 설정 조회
        config = ModelConfigManager.get_model_config(model)
        if not config:
            logger.warning(f"Model {model} not found in config, using defaults")
            config = ModelConfigManager.get_model_config("qwen2.5:7b")

        temp = temperature if temperature is not None else config.temperature

        # 모델에 맞는 provider 선택
        provider = self._get_provider_for_model(config.provider)
        
        # Provider를 통한 스트리밍 (에러는 Provider 내부에서 처리)
        async for chunk in provider.stream_chat(
            messages=messages,
            model=model,
            system=system,
            temperature=temp,
            max_tokens=config.max_tokens,
        ):
            yield chunk

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        일반 채팅 (비스트리밍)

        Args:
            model: 사용할 모델
            messages: 대화 메시지 리스트
            system: 시스템 메시지
            temperature: 온도

        Returns:
            응답 텍스트
        """
        config = ModelConfigManager.get_model_config(model)
        if not config:
            config = ModelConfigManager.get_model_config("qwen2.5:7b")

        temp = temperature if temperature is not None else config.temperature

        # 모델에 맞는 provider 선택
        provider = self._get_provider_for_model(config.provider)

        # Provider를 통한 채팅 (에러는 Provider 내부에서 처리)
        response = await provider.chat(
            messages=messages,
            model=model,
            system=system,
            temperature=temp,
        )

        # LLMResponse 객체에서 content만 반환 (간단한 챗용)
        if hasattr(response, 'content'):
            content = response.content or ""
            if not content:
                logger.warning(f"Empty response from model {model}")
            return content
        else:
            logger.warning(f"Unexpected response type from provider: {type(response)}")
            return str(response) if response else ""

    async def check_models(self) -> Dict[str, bool]:
        """사용 가능한 모델 확인"""
        try:
            available_models = await self.provider.list_models()
            # 모델 설정과 비교
            result = {}
            for model_name in ModelConfigManager.MODELS.keys():
                # 모델 이름 매칭 (간단한 체크)
                result[model_name] = any(
                    model_name.lower() in m.lower() or m.lower() in model_name.lower()
                    for m in available_models
                )
            return result
        except Exception as e:
            logger.error(f"Check models error: {e}")
            return {}

    def _get_provider_for_model(self, model_provider):
        """모델에 맞는 provider 반환"""
        from src.models.llm_provider import LLMProvider
        
        # 모델의 provider와 현재 provider가 같으면 현재 provider 사용
        if model_provider == LLMProvider.OPENAI and self.provider.name == "openai":
            return self.provider
        elif model_provider == LLMProvider.ANTHROPIC and self.provider.name == "claude":
            return self.provider
        elif model_provider == LLMProvider.GOOGLE and self.provider.name == "gemini":
            return self.provider
        elif model_provider == LLMProvider.OLLAMA and self.provider.name == "ollama":
            return self.provider
        
        # 다른 provider가 필요하면 동적으로 가져오기
        try:
            if model_provider == LLMProvider.OPENAI:
                return ProviderFactory.get_provider("openai")
            elif model_provider == LLMProvider.ANTHROPIC:
                return ProviderFactory.get_provider("claude")
            elif model_provider == LLMProvider.GOOGLE:
                return ProviderFactory.get_provider("gemini")
            elif model_provider == LLMProvider.OLLAMA:
                # Ollama는 선택적이므로 실패해도 조용히 처리
                try:
                    return ProviderFactory.get_provider("ollama")
                except:
                    logger.debug(f"Ollama provider not available, using default")
                    return self.provider
        except Exception as e:
            logger.debug(f"Failed to get provider for {model_provider}, using default: {e}")
            return self.provider
        
        return self.provider

    async def close(self):
        """리소스 정리"""
        if hasattr(self.provider, "close"):
            await self.provider.close()
