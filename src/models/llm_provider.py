"""
LLM Provider Abstraction
여러 LLM 제공자를 통합하는 추상화 레이어
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict, Optional
from enum import Enum
import os
from loguru import logger


class LLMProvider(str, Enum):
    """지원하는 LLM 제공자"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"  # Claude
    GOOGLE = "google"  # Gemini
    OLLAMA = "ollama"
    AUTO = "auto"  # 자동 선택


class BaseLLMProvider(ABC):
    """LLM 제공자 기본 클래스"""
    
    @abstractmethod
    async def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """스트리밍 채팅"""
        pass
    
    @abstractmethod
    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        """일반 채팅 (비스트리밍)"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """제공자 사용 가능 여부"""
        pass
    
    @abstractmethod
    def get_default_model(self) -> str:
        """기본 모델 반환"""
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI 제공자"""
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required")
        
        import openai
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.default_model = "gpt-4o-mini"
    
    async def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        openai_messages = messages.copy()
        if system:
            openai_messages.insert(0, {"role": "system", "content": system})
        
        stream = await self.client.chat.completions.create(
            model=model or self.default_model,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        openai_messages = messages.copy()
        if system:
            openai_messages.insert(0, {"role": "system", "content": system})
        
        response = await self.client.chat.completions.create(
            model=model or self.default_model,
            messages=openai_messages,
            temperature=temperature,
        )
        
        return response.choices[0].message.content or ""
    
    def is_available(self) -> bool:
        return os.getenv("OPENAI_API_KEY") is not None
    
    def get_default_model(self) -> str:
        return self.default_model


class AnthropicProvider(BaseLLMProvider):
    """Anthropic (Claude) 제공자"""
    
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")
        
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(api_key=api_key)
        self.default_model = "claude-3-5-sonnet-20241022"
    
    async def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        # Claude 메시지 형식 변환
        claude_messages = []
        for msg in messages:
            if msg["role"] == "user":
                claude_messages.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                claude_messages.append({"role": "assistant", "content": msg["content"]})
        
        async with self.client.messages.stream(
            model=model or self.default_model,
            max_tokens=max_tokens or 4096,
            system=system,
            messages=claude_messages,
            temperature=temperature,
        ) as stream:
            async for text in stream.text_stream:
                yield text
    
    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        claude_messages = []
        for msg in messages:
            if msg["role"] == "user":
                claude_messages.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                claude_messages.append({"role": "assistant", "content": msg["content"]})
        
        response = await self.client.messages.create(
            model=model or self.default_model,
            max_tokens=4096,
            system=system,
            messages=claude_messages,
            temperature=temperature,
        )
        
        return response.content[0].text
    
    def is_available(self) -> bool:
        return os.getenv("ANTHROPIC_API_KEY") is not None
    
    def get_default_model(self) -> str:
        return self.default_model


class GoogleProvider(BaseLLMProvider):
    """Google (Gemini) 제공자"""
    
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is required")
        
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.client = genai
        self.default_model = "gemini-1.5-pro"
    
    async def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        model_instance = self.client.GenerativeModel(
            model_name=model or self.default_model,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens or 4096,
            }
        )
        
        # Gemini 메시지 형식 변환
        chat = model_instance.start_chat(history=[])
        
        # 시스템 메시지가 있으면 첫 메시지에 포함
        if system:
            prompt = f"{system}\n\n{messages[-1]['content']}"
        else:
            prompt = messages[-1]['content']
        
        response = await model_instance.generate_content_async(
            prompt,
            stream=True,
        )
        
        async for chunk in response:
            if chunk.text:
                yield chunk.text
    
    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        model_instance = self.client.GenerativeModel(
            model_name=model or self.default_model,
            generation_config={"temperature": temperature}
        )
        
        prompt = messages[-1]['content']
        if system:
            prompt = f"{system}\n\n{prompt}"
        
        response = await model_instance.generate_content_async(prompt)
        return response.text
    
    def is_available(self) -> bool:
        return os.getenv("GOOGLE_API_KEY") is not None
    
    def get_default_model(self) -> str:
        return self.default_model


class OllamaProvider(BaseLLMProvider):
    """Ollama 제공자"""
    
    def __init__(self):
        from models.ollama_client import OllamaClient
        self.client = OllamaClient()
        self.default_model = "qwen2.5:7b"
    
    async def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        async for chunk in self.client.stream_chat(
            model=model or self.default_model,
            messages=messages,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            yield chunk
    
    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        return await self.client.chat(
            model=model or self.default_model,
            messages=messages,
            system=system,
            temperature=temperature,
        )
    
    def is_available(self) -> bool:
        # Ollama는 항상 사용 가능 (로컬)
        return True
    
    def get_default_model(self) -> str:
        return self.default_model


class LLMProviderFactory:
    """LLM 제공자 팩토리"""
    
    @staticmethod
    def create_provider(provider: Optional[LLMProvider] = None) -> BaseLLMProvider:
        """
        제공자 생성
        
        Args:
            provider: 제공자 타입 (None이면 자동 선택)
        
        Returns:
            LLM 제공자 인스턴스
        """
        if provider is None or provider == LLMProvider.AUTO:
            provider = LLMProviderFactory._auto_select_provider()
        
        if provider == LLMProvider.OPENAI:
            return OpenAIProvider()
        elif provider == LLMProvider.ANTHROPIC:
            return AnthropicProvider()
        elif provider == LLMProvider.GOOGLE:
            return GoogleProvider()
        elif provider == LLMProvider.OLLAMA:
            return OllamaProvider()
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    @staticmethod
    def _auto_select_provider() -> LLMProvider:
        """
        환경 변수를 기반으로 자동 제공자 선택
        
        우선순위:
        1. ANTHROPIC_API_KEY (Claude)
        2. OPENAI_API_KEY (OpenAI)
        3. GOOGLE_API_KEY (Gemini)
        4. Ollama (기본값)
        """
        if os.getenv("ANTHROPIC_API_KEY"):
            logger.info("Auto-selected provider: Anthropic (Claude)")
            return LLMProvider.ANTHROPIC
        elif os.getenv("OPENAI_API_KEY"):
            logger.info("Auto-selected provider: OpenAI")
            return LLMProvider.OPENAI
        elif os.getenv("GOOGLE_API_KEY"):
            logger.info("Auto-selected provider: Google (Gemini)")
            return LLMProvider.GOOGLE
        else:
            logger.info("Auto-selected provider: Ollama (default)")
            return LLMProvider.OLLAMA
    
    @staticmethod
    def get_available_providers() -> List[LLMProvider]:
        """사용 가능한 제공자 목록"""
        available = []
        
        if os.getenv("ANTHROPIC_API_KEY"):
            available.append(LLMProvider.ANTHROPIC)
        if os.getenv("OPENAI_API_KEY"):
            available.append(LLMProvider.OPENAI)
        if os.getenv("GOOGLE_API_KEY"):
            available.append(LLMProvider.GOOGLE)
        # Ollama는 항상 사용 가능
        available.append(LLMProvider.OLLAMA)
        
        return available

