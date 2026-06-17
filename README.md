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

```bash
cp .env.example .env
```

```env
# ============================================
# Server
# ============================================
PORT=3002
HOST=0.0.0.0
NODE_ENV=development
LOG_LEVEL=INFO

# ============================================
# LLM Providers — 최소 하나의 API 키 필요
# ============================================
OPENAI_API_KEY=sk-proj-...          # OpenAI (우선순위 1)
ANTHROPIC_API_KEY=sk-ant-api03-...  # Claude  (우선순위 2)
GEMINI_API_KEY=AIzaSy-...           # Gemini  (우선순위 3)
OLLAMA_HOST=http://localhost:11434  # Ollama  (우선순위 4, 로컬 무료)

# ============================================
# Vector Database (Pinecone)
# ============================================
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INDEX_NAME=insightstock

# ============================================
# Cache (Redis)
# ============================================
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=          # 선택사항
REDIS_DB=0

# ============================================
# Backend Integration
# ============================================
BACKEND_API_URL=http://localhost:3001

# ============================================
# 비용 최적화 (선택사항)
# ============================================
EMBEDDING_MODEL=text-embedding-3-small
```

**API 키 발급 링크**:
- OpenAI → https://platform.openai.com/api-keys
- Anthropic → https://console.anthropic.com/settings/keys
- Gemini → https://aistudio.google.com/app/apikey
- Pinecone → https://www.pinecone.io/

자세한 설정 방법은 [docs/ENV_SETUP_GUIDE.md](./docs/ENV_SETUP_GUIDE.md)를 참조하세요.

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

## 🤖 지원 모델 전체 목록

`GET /api/models` 로 런타임에 사용 가능한 모델 목록을 조회할 수 있습니다.

### Ollama (로컬 — 무료)

| 모델 | 타입 | Max Tokens | 용도 |
|------|------|-----------|------|
| `phi3.5` | SLM | 2,048 | 간단한 질문, 검색 제안, 자동완성 |
| `qwen2.5:7b` | LLM | 4,096 | 일반 대화, 설명, 분석 |
| `llama3.1:70b` | LLM | 8,192 | 복잡한 분석, 전략 수립, 심층 추론 |
| `ax:3.1-lite` | LLM | 4,096 | 한국어 금융 질문, 한국 시장 분석 |

### OpenAI

| 모델 | Max Tokens | 용도 |
|------|-----------|------|
| `gpt-4o-mini` | 16,384 | 일반 대화, 빠른 응답 |
| `gpt-4o` | 128,000 | 복잡한 분석, 정확한 답변 |
| `gpt-4.1` | 128,000 | 복잡한 분석, 긴 컨텍스트 |
| `gpt-5-mini` | 16,384 | 경량 최신 모델 |
| `gpt-5` | 128,000 | 최신 고성능 |
| `o3-mini` / `o4-mini` | 16,384 | 수학·과학 추론 |

### Anthropic

| 모델 | Max Tokens | 용도 |
|------|-----------|------|
| `claude-3-5-sonnet-20241022` | 8,192 | 복잡한 추론, 정확한 분석 |
| `claude-3-opus-20240229` | 4,096 | 최고 수준의 추론 |
| `claude-3-haiku-20240307` | 4,096 | 빠른 응답, 간단한 작업 |

### Google Gemini

| 모델 | Max Tokens | 용도 |
|------|-----------|------|
| `gemini-1.5-pro` | 8,192 | 복잡한 분석, 멀티모달 |
| `gemini-1.5-flash` | 8,192 | 빠른 응답, 일반 작업 |

> **자동 선택 우선순위**: Anthropic → OpenAI → Gemini → Ollama (설정된 API 키 기준)

---

## 🌐 API 레퍼런스

서버 실행 후 **[Swagger UI](http://localhost:3002/docs)** 에서 인터랙티브 문서를 확인하세요.

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | 서비스 상태 및 사용 가능한 프로바이더 확인 |
| `POST` | `/api/chat` | 일반 채팅 (단일 응답, 구조화 응답 지원) |
| `POST` | `/api/chat/stream` | 스트리밍 채팅 (SSE, `text/event-stream`) |
| `GET` | `/api/models` | 지원 모델 및 프로바이더 목록 |
| `GET` | `/api/chat/history` | 챗 히스토리 조회 (페이지네이션, 캐싱) |
| `GET` | `/api/queue/stats` | Redis 메시지 큐 상태 모니터링 |

### Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/search/vector` | Pinecone 벡터 유사도 검색 |
| `GET` | `/api/search/index/stats` | Pinecone 인덱스 통계 |

#### POST `/api/chat` — 요청 예시

```bash
# 일반 텍스트 응답
curl -X POST http://localhost:3002/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "삼성전자 주가 전망을 분석해줘",
    "force_model": "gpt-4o-mini",
    "userId": "user123"
  }'

# 구조화된 주식 분석 응답
curl -X POST http://localhost:3002/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "삼성전자 분석",
    "response_type": "stock_analysis",
    "stock_code": "005930",
    "force_model": "claude-3-5-sonnet-20241022"
  }'
```

`response_type` 옵션: `stock_analysis` · `news_summary` · `market_analysis` · `portfolio_recommendation` · `simple`

#### POST `/api/chat/stream` — SSE 스트리밍 예시

```bash
curl -X POST http://localhost:3002/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "시장 현황 요약"}' \
  --no-buffer
# data: {"content": "현재 시장은", "done": false}
# data: {"content": " 상승세를 보이고 있습니다", "done": false}
# data: {"content": "", "done": true}
```

---

## 🚀 배포 가이드

### 개발 환경

```bash
# 1. 환경 변수 설정
cp .env.example .env  # API 키 입력

# 2. 가상환경 + 의존성
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. 서버 실행 (포트 3002)
uvicorn src.main:app --reload --host 0.0.0.0 --port 3002
```

### 프로덕션 환경

```bash
# 환경 변수를 직접 주입하거나 .env 사용
NODE_ENV=production uvicorn src.main:app \
  --host 0.0.0.0 \
  --port 3002 \
  --workers 4 \
  --log-level warning
```

### Docker

```bash
# 이미지 빌드
docker build -t insightstock-ai-service .

# 컨테이너 실행 (환경 변수 파일 사용)
docker run -d \
  --name is-ai \
  --env-file .env \
  -p 3002:3002 \
  insightstock-ai-service

# Docker Compose (Redis 포함)
docker-compose up -d
```

> Ollama를 로컬에서 사용할 경우 Docker 컨테이너 내에서 `OLLAMA_HOST=http://host.docker.internal:11434` 로 설정합니다.

---

## 📄 라이선스

ISC
