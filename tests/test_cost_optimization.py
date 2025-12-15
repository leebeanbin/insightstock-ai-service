"""
Cost Optimization 테스트
비용 최적화 설정 및 로직 테스트
"""

import pytest
from src.config.cost_optimization import CostOptimizationConfig


class TestCostOptimizationConfig:
    """CostOptimizationConfig 테스트"""

    def test_get_embedding_model(self):
        """임베딩 모델 반환 테스트"""
        model = CostOptimizationConfig.get_embedding_model()
        assert model == "text-embedding-3-small"

    def test_should_use_batch(self):
        """배치 처리 여부 판단 테스트"""
        assert CostOptimizationConfig.should_use_batch(2) is True
        assert CostOptimizationConfig.should_use_batch(100) is True
        assert CostOptimizationConfig.should_use_batch(1) is False

    def test_estimate_cost_batch(self):
        """배치 처리 비용 추정 테스트"""
        # 배치 처리: $0.01/1M tokens
        cost = CostOptimizationConfig.estimate_cost(1_000_000, use_batch=True)
        assert cost == 0.01

    def test_estimate_cost_non_batch(self):
        """일반 처리 비용 추정 테스트"""
        # 일반 처리: $0.02/1M tokens
        cost = CostOptimizationConfig.estimate_cost(1_000_000, use_batch=False)
        assert cost == 0.02

    def test_get_optimal_chunk_size_short(self):
        """짧은 텍스트 최적 청크 크기 테스트"""
        size = CostOptimizationConfig.get_optimal_chunk_size(500)
        assert size == 500

    def test_get_optimal_chunk_size_medium(self):
        """중간 텍스트 최적 청크 크기 테스트"""
        size = CostOptimizationConfig.get_optimal_chunk_size(2000)
        assert size == 2000

    def test_get_optimal_chunk_size_long(self):
        """긴 텍스트 최적 청크 크기 테스트"""
        size = CostOptimizationConfig.get_optimal_chunk_size(10000)
        assert size == 4000  # 최대 4000자

    def test_cost_savings_batch(self):
        """배치 처리 비용 절감 확인"""
        tokens = 1_000_000
        batch_cost = CostOptimizationConfig.estimate_cost(tokens, use_batch=True)
        non_batch_cost = CostOptimizationConfig.estimate_cost(tokens, use_batch=False)

        # 배치 처리 시 50% 절감
        assert batch_cost == non_batch_cost / 2
