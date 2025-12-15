"""
Environment Configuration 테스트
"""

import pytest
import os
from src.config.env import EnvConfig


class TestEnvConfig:
    """EnvConfig 테스트"""

    def test_ollama_host_default(self):
        """OLLAMA_HOST 기본값 테스트"""
        # 환경 변수가 없으면 기본값 사용
        if "OLLAMA_HOST" not in os.environ:
            assert EnvConfig.OLLAMA_HOST == "http://localhost:11434"

    def test_port_default(self):
        """PORT 기본값 테스트"""
        # 환경 변수가 없으면 기본값 사용
        if "PORT" not in os.environ:
            assert EnvConfig.PORT == 3002

    def test_host_default(self):
        """HOST 기본값 테스트"""
        # 환경 변수가 없으면 기본값 사용
        if "HOST" not in os.environ:
            assert EnvConfig.HOST == "0.0.0.0"

    def test_validate(self):
        """환경 변수 검증 테스트"""
        missing = EnvConfig.validate()
        # 최소 하나의 Provider API 키가 없으면 missing 리스트에 포함
        assert isinstance(missing, list)
