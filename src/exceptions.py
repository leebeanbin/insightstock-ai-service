"""
Custom Exceptions
AI 서비스 전용 예외 클래스
"""


class AIServiceError(Exception):
    """AI 서비스 기본 예외"""
    pass


class ProviderError(AIServiceError):
    """Provider 관련 예외"""
    pass


class ProviderUnavailableError(ProviderError):
    """Provider 사용 불가 예외"""
    pass


class ModelNotFoundError(AIServiceError):
    """모델을 찾을 수 없음 예외"""
    pass


class EmbeddingError(AIServiceError):
    """임베딩 생성 실패 예외"""
    pass


class VectorSearchError(AIServiceError):
    """벡터 검색 실패 예외"""
    pass


class ConfigurationError(AIServiceError):
    """설정 오류 예외"""
    pass

