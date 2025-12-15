# 🤖 InsightStock AI Service

AI Service for InsightStock - LLM/SLM integration with Ollama (Python)

## 📋 개요

이 서비스는 InsightStock의 AI 기능을 제공하는 별도 마이크로서비스입니다.

### 주요 기능
- **LLM/SLM 통합**: Ollama 기반 오픈소스 모델 사용
- **벡터 검색**: Pinecone을 통한 RAG 구현
- **모델 라우팅**: 쿼리 복잡도에 따른 자동 모델 선택
- **Jupyter Notebook**: AI 파싱 및 벡터 DB 작업용

## 🏗️ 구조

```
insightstock-ai-service/
├── src/
│   ├── services/          # 비즈니스 로직
│   │   ├── llm_service.py
│   │   ├── slm_service.py
│   │   ├── model_router.py
│   │   └── vector_search_service.py
│   ├── models/             # 모델 클라이언트
│   │   ├── ollama_client.py
│   │   └── model_config.py
│   ├── controllers/       # API 컨트롤러
│   │   ├── chat_controller.py
│   │   └── search_controller.py
│   ├── utils/             # 유틸리티
│   │   └── query_classifier.py
│   └── main.py            # FastAPI 서버
│
├── notebooks/             # Jupyter Notebooks
│   ├── embeddings.ipynb          # 임베딩 생성
│   ├── vector_search.ipynb       # 벡터 검색 실험
│   ├── indexing.ipynb            # 인덱싱 작업
│   ├── parse_news.ipynb          # 뉴스 데이터 파싱
│   ├── parse_stocks.ipynb        # 주식 데이터 파싱
│   └── parse_learnings.ipynb     # 학습 콘텐츠 파싱
│
├── tests/                 # 테스트
├── requirements.txt
├── pyproject.toml
└── README.md
```

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 가상 환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일 수정
```

### 2. Ollama 설치 및 모델 다운로드

```bash
# Ollama 설치 (https://ollama.com)
# macOS
brew install ollama

# 모델 다운로드
ollama pull phi3.5
ollama pull qwen2.5:7b
ollama pull llama3.1:70b
```

### 3. 서버 실행

```bash
# 개발 모드 (권장)
cd src
python main.py

# 또는 uvicorn 직접 사용
uvicorn src.main:app --reload --port 3002

# 또는 Makefile 사용
make run
```

서버가 실행되면:
- API 서버: http://localhost:3002
- API 문서: http://localhost:3002/docs (Swagger UI)
- Health Check: http://localhost:3002/health

### 4. 챗 기능 테스트

```bash
# 테스트 스크립트 실행
python test_chat.py

# 또는 curl로 직접 테스트
curl -X POST http://localhost:3002/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "안녕하세요"}'
```

자세한 테스트 방법은 [QUICK_START.md](./QUICK_START.md)를 참조하세요.

### 4. Jupyter Notebook 실행

```bash
# Jupyter Lab 실행
jupyter lab

# 또는 Jupyter Notebook
jupyter notebook
```

## 📚 주요 모듈

### Jupyter Notebooks

#### `notebooks/embeddings.ipynb`
- OpenAI Embeddings를 사용한 텍스트 임베딩 생성
- 벡터 변환 실험 및 테스트

#### `notebooks/vector_search.ipynb`
- Pinecone 벡터 검색 실험
- 유사도 검색 테스트

#### `notebooks/indexing.ipynb`
- 데이터 인덱싱 작업
- 배치 인덱싱 스크립트

#### `notebooks/parse_*.ipynb`
- 뉴스, 주식, 학습 콘텐츠 파싱
- 데이터 전처리 및 정제

### Python 모듈

#### `src/services/llm_service.py`
- Ollama 기반 LLM 통합
- 스트리밍 지원

#### `src/services/vector_search_service.py`
- Pinecone 벡터 검색
- Jupyter에서 실험한 로직을 모듈화

## 🔧 환경 변수

### 필수 설정

```bash
# OpenAI (임베딩 생성 필수)
OPENAI_API_KEY=your_key_here

# Pinecone (벡터 DB - 무료 티어 사용 가능)
PINECONE_API_KEY=your_key_here
PINECONE_INDEX_NAME=insightstock

# Redis (캐싱 - 선택사항, 권장)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Backend API (동기화용)
BACKEND_API_URL=http://localhost:3001
```

### 선택 설정

```bash
# Ollama (로컬 LLM/SLM - 무료)
OLLAMA_HOST=http://localhost:11434

# Anthropic Claude (선택사항)
ANTHROPIC_API_KEY=your_key_here

# Google Gemini (선택사항)
GEMINI_API_KEY=your_key_here

# Server
PORT=3002
HOST=0.0.0.0
LOG_LEVEL=INFO

# 비용 최적화
EMBEDDING_MODEL=text-embedding-3-small
```

### 상세 가이드

자세한 설정 방법은 [ENV_SETUP_GUIDE.md](./ENV_SETUP_GUIDE.md)를 참조하세요.

## 🐳 Docker

```bash
# 빌드
docker build -t insightstock-ai-service .

# 실행
docker-compose up
```

## 📝 개발 워크플로우

1. **Jupyter에서 실험**: `notebooks/`에서 AI 파싱, 벡터 검색 등 실험
2. **Python 모듈화**: 실험 결과를 `src/services/`에 모듈로 구현
3. **API 통합**: FastAPI 컨트롤러에서 사용
4. **테스트**: `tests/`에서 단위/통합 테스트

## 🔗 메인 백엔드 연동

메인 백엔드(insightstock-backend)에서 이 서비스를 호출:

```typescript
// ChatService.ts
const response = await fetch(`${AI_SERVICE_URL}/chat/stream`, {
  method: 'POST',
  body: JSON.stringify({ query, messages }),
});
```

## 📊 모델 선택 전략

- **간단한 질문**: Phi-3.5 (SLM, 빠름)
- **일반 대화**: Qwen2.5 7B (LLM, 균형)
- **복잡한 분석**: Llama 3.1 70B (LLM, 정확)

## 📄 라이선스

ISC
