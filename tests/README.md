# 테스트 가이드

**작성일**: 2025년 12월 15일

---

## 📋 테스트 구조

```
tests/
├── __init__.py
├── conftest.py                    # 공통 Fixtures
├── test_utils_query_classifier.py # Query Classifier 테스트
├── test_utils_parsers.py         # Parsers 테스트
├── test_providers.py              # Provider 테스트
├── test_services.py                # Service 테스트
├── test_controllers.py             # Controller 테스트
└── test_integration.py            # 통합 테스트
```

---

## 🚀 테스트 실행

### 전체 테스트 실행

```bash
# 프로젝트 루트에서
pytest

# 상세 출력
pytest -v

# 커버리지 포함
pytest --cov=src --cov-report=html
```

### 특정 테스트 실행

```bash
# 특정 파일
pytest tests/test_utils_query_classifier.py

# 특정 클래스
pytest tests/test_services.py::TestLLMService

# 특정 함수
pytest tests/test_utils_query_classifier.py::TestQueryClassifier::test_classify_simple_query
```

### 비동기 테스트

```bash
# 비동기 테스트는 pytest-asyncio가 자동으로 처리
pytest tests/test_services.py -v
```

---

## 📊 테스트 커버리지

### 커버리지 리포트 생성

```bash
# HTML 리포트
pytest --cov=src --cov-report=html

# 터미널 리포트
pytest --cov=src --cov-report=term

# 상세 리포트
pytest --cov=src --cov-report=term-missing
```

### 커버리지 확인

```bash
# HTML 리포트 열기
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

---

## 🧪 테스트 작성 가이드

### 1. 단위 테스트

각 모듈의 독립적인 기능 테스트:

```python
def test_function_name():
    """테스트 설명"""
    # Arrange
    input_data = "test"
    
    # Act
    result = function_to_test(input_data)
    
    # Assert
    assert result == expected_output
```

### 2. 비동기 테스트

```python
@pytest.mark.asyncio
async def test_async_function():
    """비동기 함수 테스트"""
    result = await async_function()
    assert result is not None
```

### 3. Mock 사용

```python
@patch("module.Class.method")
def test_with_mock(mock_method):
    """Mock을 사용한 테스트"""
    mock_method.return_value = "mocked_value"
    result = function_under_test()
    assert result == "mocked_value"
```

---

## 📝 테스트 Fixtures

`conftest.py`에 정의된 공통 Fixtures:

- `mock_provider`: Mock Provider 인스턴스
- `sample_messages`: 샘플 메시지 리스트
- `sample_news_data`: 샘플 뉴스 데이터
- `sample_stock_data`: 샘플 주식 데이터
- `sample_learning_data`: 샘플 학습 데이터

---

## ✅ 테스트 체크리스트

- [x] Query Classifier 테스트
- [x] Parsers 테스트
- [x] Provider 테스트
- [x] Service 테스트
- [x] Controller 테스트
- [x] 통합 테스트

---

## 🐛 문제 해결

### Import 에러

```bash
# 프로젝트 루트에서 실행
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
pytest
```

### 환경 변수 에러

```bash
# 테스트용 환경 변수 설정
export OPENAI_API_KEY=test-key
export ANTHROPIC_API_KEY=test-key
pytest
```

---

**작성자**: AI Assistant  
**프로젝트**: InsightStock AI Service
