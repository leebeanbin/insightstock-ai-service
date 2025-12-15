"""
Model Router Service
쿼리 복잡도에 따른 모델 라우팅
"""

from typing import AsyncGenerator, List, Dict, Optional
from loguru import logger
import hashlib

from src.utils.query_classifier import QueryClassifier
from src.services.llm_service import LLMService
from src.services.slm_service import SLMService
from src.models.model_config import ModelConfigManager
from src.exceptions import AIServiceError, ModelNotFoundError
from src.utils.cache import cache  # Redis 캐시 (폴백: 인메모리)
from src.config.cost_optimization import CostOptimizationConfig  # 비용 최적화


class ModelRouterService:
    """모델 라우팅 서비스"""

    def __init__(self):
        """초기화"""
        self.llm_service = LLMService()
        self.slm_service = SLMService()
        self.classifier = QueryClassifier()
        self.classification_cache = cache  # Redis 캐시 (폴백: 인메모리)
        self.classification_cache_ttl = 3600  # 1시간

    async def route_and_stream(
        self,
        query: str,
        messages: Optional[List[Dict[str, str]]] = None,
        system: Optional[str] = None,
        force_model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        쿼리 분류 후 적절한 모델로 라우팅하여 스트리밍

        Args:
            query: 사용자 쿼리
            messages: 대화 히스토리
            system: 시스템 메시지
            force_model: 강제 사용할 모델

        Yields:
            응답 청크
        """
        try:
            # 강제 모델이 있으면 사용
            if force_model:
                model = force_model
                service = self._get_service_for_model(model)
            else:
                # 쿼리 분류 (캐싱)
                cache_key = f"classification:{hashlib.md5(query.encode()).hexdigest()}"
                classification = self.classification_cache.get(cache_key)

                if classification is None:
                    classification = self.classifier.classify(query)
                    self.classification_cache.set(
                        cache_key, classification, self.classification_cache_ttl
                    )

                complexity = classification["complexity"]

                # 모델 선택
                model, service = await self._select_model(complexity, classification)
                logger.info(f"Query classified as {complexity}, using model: {model}")

            # 메시지 구성
            if not messages:
                messages = [{"role": "user", "content": query}]
            else:
                # 마지막 메시지가 사용자 메시지가 아니면 query 추가
                if not messages or messages[-1].get("role") != "user":
                    messages.append({"role": "user", "content": query})

            # 스트리밍 실행
            async for chunk in service.stream_chat(
                model=model,
                messages=messages,
                system=system,
            ):
                yield chunk

        except Exception as e:
            logger.error(f"Model router error: {e}")
            raise AIServiceError(f"Model routing failed: {str(e)}") from e

    async def route_and_chat(
        self,
        query: str,
        messages: Optional[List[Dict[str, str]]] = None,
        system: Optional[str] = None,
        force_model: Optional[str] = None,
    ) -> str:
        """
        쿼리 분류 후 적절한 모델로 라우팅하여 채팅 (비스트리밍)

        Args:
            query: 사용자 쿼리
            messages: 대화 히스토리
            system: 시스템 메시지
            force_model: 강제 사용할 모델

        Returns:
            응답 텍스트
        """
        try:
            # 강제 모델이 있으면 사용
            if force_model:
                model = force_model
                service = self._get_service_for_model(model)
            else:
                # 쿼리 분류 (캐싱)
                cache_key = f"classification:{hashlib.md5(query.encode()).hexdigest()}"
                classification = self.classification_cache.get(cache_key)

                if classification is None:
                    classification = self.classifier.classify(query)
                    self.classification_cache.set(
                        cache_key, classification, self.classification_cache_ttl
                    )

                complexity = classification["complexity"]

                # 모델 선택
                model, service = await self._select_model(complexity, classification)
                logger.info(f"Query classified as {complexity}, using model: {model}")

            # 메시지 구성
            if not messages:
                messages = [{"role": "user", "content": query}]
            else:
                if not messages or messages[-1].get("role") != "user":
                    messages.append({"role": "user", "content": query})

            # 채팅 실행
            response = await service.chat(
                model=model,
                messages=messages,
                system=system,
            )

            return response

        except Exception as e:
            logger.error(f"Model router error: {e}")
            raise AIServiceError(f"Model routing failed: {str(e)}") from e

    async def _select_model(
        self, complexity: str, classification: dict
    ) -> tuple[str, object]:
        """
        복잡도에 따라 모델 및 서비스 선택 (환경 변수 기반 자동 선택)

        Args:
            complexity: "simple", "moderate", "complex"
            classification: 분류 결과

        Returns:
            (model_name, service_instance)
        """
        if complexity == "simple":
            # 간단한 질문: SLM 사용 (사용 가능한 provider에 맞는 모델 선택)
            model = await self._get_available_slm_model()
            service = self.slm_service
        elif complexity == "complex":
            # 복잡한 질문: 고성능 LLM 사용
            model = await self._get_best_llm_model()
            service = self.llm_service
        else:
            # 중간 복잡도: 균형잡힌 LLM 사용 (사용 가능한 provider에 맞는 모델 선택)
            model = await self._get_moderate_llm_model()
            service = self.llm_service

        return model, service

    def _get_service_for_model(self, model: str) -> object:
        """
        모델에 맞는 서비스 반환

        Args:
            model: 모델 이름

        Returns:
            LLMService 또는 SLMService 인스턴스
        """
        config = ModelConfigManager.get_model_config(model)
        if config and config.type == "slm":
            return self.slm_service
        else:
            return self.llm_service

    async def _get_best_llm_model(self) -> str:
        """
        사용 가능한 최고 성능 LLM 모델 반환 (환경 변수 기반)
        경량 모델을 우선적으로 선택

        Returns:
            모델 이름
        """
        # 먼저 경량 모델을 찾음
        mini_model = await self._find_mini_model()
        if mini_model:
            return mini_model

        # "mini"가 없으면 우선순위: Claude > OpenAI > Gemini > Ollama
        from src.config.env import EnvConfig

        if EnvConfig.ANTHROPIC_API_KEY:
            return "claude-3-5-sonnet-20241022"
        elif EnvConfig.OPENAI_API_KEY:
            return "gpt-4o"
        elif EnvConfig.GEMINI_API_KEY:
            return "gemini-1.5-pro"
        else:
            return "llama3.1:70b"  # Ollama 기본

    async def _get_moderate_llm_model(self) -> str:
        """
        중간 복잡도용 LLM 모델 반환 (환경 변수 기반)
        경량 모델을 우선적으로 선택

        Returns:
            모델 이름
        """
        # 먼저 경량 모델을 찾음
        mini_model = await self._find_mini_model()
        if mini_model:
            return mini_model

        # "mini"가 없으면 우선순위: OpenAI > Claude > Gemini > Ollama
        from src.config.env import EnvConfig

        if EnvConfig.OPENAI_API_KEY:
            return "gpt-4o-mini"  # 이미 위에서 체크했지만 안전장치
        elif EnvConfig.ANTHROPIC_API_KEY:
            return "claude-3-haiku-20240307"
        elif EnvConfig.GEMINI_API_KEY:
            return "gemini-1.5-flash"
        else:
            return "qwen2.5:7b"  # Ollama 기본

    async def _get_available_slm_model(self) -> str:
        """
        사용 가능한 SLM 모델 반환 (환경 변수 기반)
        경량 모델을 우선적으로 선택

        Returns:
            모델 이름
        """
        # 먼저 경량 모델을 찾음
        mini_model = await self._find_mini_model()
        if mini_model:
            return mini_model

        # "mini"가 없으면 기본 SLM 모델 사용
        from src.config.env import EnvConfig

        if EnvConfig.OPENAI_API_KEY:
            return "gpt-4o-mini"  # 이미 위에서 체크했지만 안전장치
        elif EnvConfig.ANTHROPIC_API_KEY:
            return "claude-3-haiku-20240307"
        elif EnvConfig.GEMINI_API_KEY:
            return "gemini-1.5-flash"
        else:
            return "phi3.5"  # Ollama 기본

    def __init__(self):
        """초기화"""
        self.llm_service = LLMService()
        self.slm_service = SLMService()
        self.classifier = QueryClassifier()
        self.classification_cache = cache  # Redis 캐시 (폴백: 인메모리)
        self.classification_cache_ttl = 3600  # 1시간

        # 경량 모델 캐싱 (성능 최적화)
        self._lightweight_model_cache = None
        self._lightweight_model_cache_time = None
        self._lightweight_model_cache_ttl = 3600  # 1시간

    async def _find_mini_model(self) -> Optional[str]:
        """
        사용 가능한 provider 중에서 경량 모델을 찾음
        OpenAI API에서 실제 모델 목록을 가져와서 경량 모델을 자동 탐색 (캐싱 적용)

        Returns:
            모델 이름 또는 None
        """
        import time
        from src.config.env import EnvConfig
        from src.models.model_config import ModelConfigManager
        from src.models.llm_provider import LLMProvider
        from src.providers import ProviderFactory

        # 캐시 확인
        current_time = time.time()
        if (
            self._lightweight_model_cache is not None
            and self._lightweight_model_cache_time is not None
            and (current_time - self._lightweight_model_cache_time)
            < self._lightweight_model_cache_ttl
        ):
            logger.debug(
                f"Using cached lightweight model: {self._lightweight_model_cache}"
            )
            return self._lightweight_model_cache

        # 사용 가능한 provider 확인
        available_providers = []
        if EnvConfig.OPENAI_API_KEY:
            available_providers.append(LLMProvider.OPENAI)
        if EnvConfig.ANTHROPIC_API_KEY:
            available_providers.append(LLMProvider.ANTHROPIC)
        if EnvConfig.GEMINI_API_KEY:
            available_providers.append(LLMProvider.GOOGLE)
        # Ollama는 선택적 (실패해도 계속 진행)

        # OpenAI: API에서 실제 모델 목록 가져와서 경량 모델 찾기
        if LLMProvider.OPENAI in available_providers:
            try:
                openai_provider = ProviderFactory.get_provider("openai")
                available_models = await openai_provider.list_models()

                # OpenAI provider의 find_lightweight_model 메서드 사용
                if hasattr(openai_provider, "find_lightweight_model"):
                    lightweight_model = openai_provider.find_lightweight_model(
                        available_models
                    )
                    if lightweight_model:
                        # 캐시 저장
                        self._lightweight_model_cache = lightweight_model
                        self._lightweight_model_cache_time = current_time

                        logger.info(
                            f"Found OpenAI lightweight model from API: {lightweight_model}"
                        )
                        return lightweight_model
            except Exception as e:
                logger.debug(f"Failed to get OpenAI models from API: {e}")

        # 다른 provider: 하드코딩된 모델 목록에서 경량 모델 찾기
        # 1단계: "mini", "haiku", "flash" 등 명확한 경량 키워드 찾기
        for keyword in ["mini", "haiku", "flash"]:
            for model_name, config in ModelConfigManager.MODELS.items():
                if (
                    keyword in model_name.lower()
                    and config.provider in available_providers
                ):
                    logger.info(
                        f"Found lightweight model: {model_name} (provider: {config.provider}, keyword: {keyword})"
                    )
                    return model_name

        # 2단계: "phi", "lite" 등 다른 경량 키워드 찾기
        for keyword in ["phi", "lite"]:
            for model_name, config in ModelConfigManager.MODELS.items():
                if (
                    keyword in model_name.lower()
                    and config.provider in available_providers
                ):
                    logger.info(
                        f"Found lightweight model: {model_name} (provider: {config.provider}, keyword: {keyword})"
                    )
                    return model_name

        # 3단계: provider별 기본 경량 모델 (모델 목록에 없을 경우)
        if LLMProvider.OPENAI in available_providers:
            return "gpt-4o-mini"
        elif LLMProvider.ANTHROPIC in available_providers:
            return "claude-3-haiku-20240307"
        elif LLMProvider.GOOGLE in available_providers:
            return "gemini-1.5-flash"
        elif LLMProvider.OLLAMA in available_providers:
            return "phi3.5"

        return None

    async def close(self):
        """리소스 정리"""
        if hasattr(self.llm_service, "close"):
            await self.llm_service.close()
        if hasattr(self.slm_service, "close"):
            await self.slm_service.close()
