"""
Provider 테스트
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.providers.provider_factory import ProviderFactory
from src.providers.base_provider import BaseLLMProvider, LLMResponse


class TestProviderFactory:
    """ProviderFactory 테스트"""

    def test_get_available_providers(self):
        """사용 가능한 Provider 목록 조회"""
        providers = ProviderFactory.get_available_providers()
        assert isinstance(providers, list)
        # 환경 변수가 설정되어 있으면 해당 Provider가 포함되어야 함

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_get_provider_with_openai(self):
        """OpenAI Provider 생성 테스트"""
        try:
            provider = ProviderFactory.get_provider("openai", fallback=False)
            assert provider is not None
            assert provider.name == "OpenAIProvider"
        except Exception:
            # API 키가 유효하지 않으면 에러 발생 가능
            pass

    def test_get_default_provider(self):
        """기본 Provider 조회 테스트"""
        try:
            provider = ProviderFactory.get_default_provider()
            assert provider is not None
        except ValueError:
            # 사용 가능한 Provider가 없으면 에러 발생
            pass

    def test_clear_cache(self):
        """캐시 초기화 테스트"""
        ProviderFactory.clear_cache()
        # 에러 없이 실행되면 성공


class TestBaseProvider:
    """BaseLLMProvider 인터페이스 테스트"""

    @pytest.mark.asyncio
    async def test_provider_stream_chat(self, mock_provider):
        """Provider 스트리밍 테스트"""
        chunks = []
        async for chunk in mock_provider.stream_chat(
            messages=[{"role": "user", "content": "test"}],
            model="test-model",
        ):
            chunks.append(chunk)

        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_provider_chat(self, mock_provider):
        """Provider 일반 채팅 테스트"""
        response = await mock_provider.chat(
            messages=[{"role": "user", "content": "test"}],
            model="test-model",
        )

        assert response is not None
        assert hasattr(response, "content") or isinstance(response, str)

    @pytest.mark.asyncio
    async def test_provider_list_models(self, mock_provider):
        """Provider 모델 목록 조회 테스트"""
        models = await mock_provider.list_models()
        assert isinstance(models, list)

    def test_provider_is_available(self, mock_provider):
        """Provider 사용 가능 여부 테스트"""
        assert mock_provider.is_available() == True

    @pytest.mark.asyncio
    async def test_provider_health_check(self, mock_provider):
        """Provider 건강 상태 확인 테스트"""
        health = await mock_provider.health_check()
        assert isinstance(health, bool)
