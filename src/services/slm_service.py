"""
SLM Service
Small Language Model 서비스 (빠른 응답용, Provider 추상화 사용)
"""

from typing import AsyncGenerator, List, Dict, Optional
from src.providers import ProviderFactory, BaseLLMProvider
from src.models.model_config import ModelConfigManager
from loguru import logger


class SLMService:
    """SLM 서비스 (빠른 응답용, Provider 추상화 사용)"""
    
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        """
        SLM 서비스 초기화
        
        Args:
            provider: LLM 제공자 (None이면 자동 선택, Ollama 우선)
        """
        # Ollama를 우선적으로 사용 (로컬 SLM 모델)
        try:
            ollama_provider = ProviderFactory.get_provider("ollama", fallback=False)
            self.provider = ollama_provider
            logger.info(f"SLMService initialized with Ollama provider: {self.provider.name}")
        except:
            # Ollama가 없으면 기본 Provider 사용
            self.provider = provider or ProviderFactory.get_default_provider()
            logger.info(f"SLMService initialized with provider: {self.provider.name}")
    
    async def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> AsyncGenerator[str, None]:
        """
        스트리밍 채팅 (SLM 모델 사용)
        
        Args:
            model: 사용할 모델 (기본값: phi3.5)
            messages: 대화 메시지 리스트
            system: 시스템 메시지
            temperature: 온도
        
        Yields:
            응답 청크
        """
        # SLM 모델 기본값
        if not model:
            model = "phi3.5"
        
        # 모델 설정 조회
        config = ModelConfigManager.get_model_config(model)
        if not config:
            logger.warning(f"Model {model} not found in config, using defaults")
            config = ModelConfigManager.get_model_config("phi3.5")
        
        temp = temperature if temperature is not None else config.temperature
        
        # 모델에 맞는 provider 선택
        provider = self._get_provider_for_model(config.provider)
        
        # Provider를 통한 스트리밍
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
        일반 채팅 (비스트리밍, SLM 모델 사용)
        
        Args:
            model: 사용할 모델 (기본값: phi3.5)
            messages: 대화 메시지 리스트
            system: 시스템 메시지
            temperature: 온도
        
        Returns:
            응답 텍스트
        """
        # SLM 모델 기본값
        if not model:
            model = "phi3.5"
        
        config = ModelConfigManager.get_model_config(model)
        if not config:
            config = ModelConfigManager.get_model_config("phi3.5")
        
        temp = temperature if temperature is not None else config.temperature
        
        # 모델에 맞는 provider 선택
        provider = self._get_provider_for_model(config.provider)
        
        # Provider를 통한 채팅
        response = await provider.chat(
            messages=messages,
            model=model,
            system=system,
            temperature=temp,
        )
        
        # LLMResponse 객체에서 content만 반환 (간단한 챗용)
        return response.content if hasattr(response, 'content') else str(response)
    
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
                return ProviderFactory.get_provider("ollama")
        except Exception as e:
            logger.warning(f"Failed to get provider for {model_provider}, using default: {e}")
            return self.provider
        
        return self.provider

    async def close(self):
        """리소스 정리"""
        if hasattr(self.provider, "close"):
            await self.provider.close()
