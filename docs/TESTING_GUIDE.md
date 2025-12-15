# 🧪 테스트 가이드

**작성일**: 2025년 12월 15일

---

## 📋 테스트 구조

```
tests/
├── __init__.py
├── conftest.py                    # 공통 Fixtures 및 설정
├── test_config_env.py             # 환경 변수 테스트
├── test_utils_query_classifier.py # Query Classifier 테스트
├── test_utils_parsers.py          # Parsers 테스트
├── test_providers.py              # Provider 테스트
├── test_services.py               # Service 테스트
├── test_controllers.py            # Controller 테스트
└── test_integration.py            # 통합 테스트
```

---

## 🚀 빠른 시작

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 테스트 실행

```bash
# 전체 테스트
pytest

# 상세 출력
pytest -v

# 특정 테스트만
pytest tests/test_utils_query_classifier.py
```

### 3. 커버리지 확인

```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html  # macOS
```

---

## 📊 테스트 카테고리

### 1. 단위 테스트 (Unit Tests)

#### Utils 테스트
- `test_utils_query_classifier.py`: 쿼리 분류 로직
- `test_utils_parsers.py`: 데이터 파싱 로직

#### Provider 테스트
- `test_providers.py`: LLM Provider 추상화

#### Service 테스트
- `test_services.py`: LLM/SLM Service, Model Router, Embedding, Vector Search

### 2. 통합 테스트 (Integration Tests)

#### Controller 테스트
- `test_controllers.py`: FastAPI 엔드포인트

#### 전체 플로우 테스트
- `test_integration.py`: AI 서비스 전체 플로우

---

## 🧪 테스트 작성 예시

### 단위 테스트

```python
def test_classify_simple_query():
    """간단한 질문 분류 테스트"""
    result = QueryClassifier.classify_complexity("PER이 뭐야?")
    assert result == "simple"
```

### 비동기 테스트

```python
@pytest.mark.asyncio
async def test_stream_chat():
    """스트리밍 채팅 테스트"""
    service = LLMService()
    chunks = []
    async for chunk in service.stream_chat(
        model="test-model",
        messages=[{"role": "user", "content": "test"}],
    ):
        chunks.append(chunk)
    assert len(chunks) > 0
```

### Mock 사용 테스트

```python
@patch("src.services.llm_service.ProviderFactory.get_default_provider")
async def test_llm_service(mock_provider):
    """Mock을 사용한 LLM Service 테스트"""
    mock_provider.return_value = mock_provider_instance
    service = LLMService()
    # 테스트 진행
```

---

## 🔧 테스트 설정

### pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
```

### conftest.py

공통 Fixtures:
- `mock_provider`: Mock Provider
- `sample_messages`: 샘플 메시지
- `sample_news_data`: 샘플 뉴스 데이터
- `sample_stock_data`: 샘플 주식 데이터
- `sample_learning_data`: 샘플 학습 데이터

---

## 📈 커버리지 목표

- **현재 목표**: 70% 이상
- **이상적 목표**: 80% 이상

### 커버리지 확인

```bash
# HTML 리포트
pytest --cov=src --cov-report=html

# 터미널 리포트
pytest --cov=src --cov-report=term-missing
```

---

## 🐛 문제 해결

### Import 에러

```bash
# PYTHONPATH 설정
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
pytest
```

### 환경 변수 에러

테스트는 `conftest.py`에서 자동으로 테스트용 환경 변수를 설정합니다.

### 비동기 테스트 에러

`pytest-asyncio`가 설치되어 있는지 확인:

```bash
pip install pytest-asyncio
```

---

## ✅ 테스트 체크리스트

- [x] 환경 변수 테스트
- [x] Query Classifier 테스트
- [x] Parsers 테스트
- [x] Provider 테스트
- [x] Service 테스트
- [x] Controller 테스트
- [x] 통합 테스트

---

## 📝 테스트 실행 명령어

```bash
# 전체 테스트
make test

# 커버리지 포함
make test-cov

# 특정 카테고리
pytest tests/test_utils_*.py  # Utils만
pytest tests/test_services.py  # Services만
pytest tests/test_controllers.py  # Controllers만
```

---

**작성자**: AI Assistant  
**프로젝트**: InsightStock AI Service
