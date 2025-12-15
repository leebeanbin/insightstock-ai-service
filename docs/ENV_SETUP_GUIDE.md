# 환경 변수 설정 가이드

**작성일**: 2025년 12월 15일

---

## 📋 필수 환경 변수

### 최소 설정 (기본 동작)

```env
# Ollama (로컬 LLM/SLM)
OLLAMA_HOST=http://localhost:11434

# OpenAI (임베딩 생성 필수)
OPENAI_API_KEY=your_openai_api_key_here

# Pinecone (벡터 DB)
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX_NAME=insightstock

# Redis (캐싱)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Server
PORT=3002
HOST=0.0.0.0
LOG_LEVEL=INFO

# Backend API
BACKEND_API_URL=http://localhost:3001
```

---

## 🔑 API 키 획득 방법

### 1. OpenAI API Key (필수)

**용도**: 텍스트 임베딩 생성

**획득 방법**:
1. https://platform.openai.com/api-keys 접속
2. "Create new secret key" 클릭
3. 키 복사 (형식: `sk-proj-...`)

**비용**: 
- Embedding: $0.01/1M tokens (배치), $0.02/1M tokens (일반)
- 무료 크레딧 제공 (신규 가입 시)

---

### 2. Pinecone API Key (필수)

**용도**: 벡터 데이터베이스

**획득 방법**:
1. https://www.pinecone.io/ 접속
2. 회원가입 및 로그인
3. API Keys 섹션에서 키 복사

**무료 티어**:
- ✅ **2GB 스토리지**
- ✅ **월 2백만 Write Units**
- ✅ **월 1백만 Read Units**
- ✅ **5개 인덱스**
- ⚠️ **3주 비활성 시 일시정지** (재활성화 가능)

**비용**: 무료 티어로 시작 가능, 유료 플랜은 사용량에 따라

---

### 3. Redis (선택사항, 권장)

**용도**: 캐싱 및 동시성 제어

**설치 방법**:
```bash
# macOS
brew install redis
brew services start redis

# 또는 Docker
docker run -d -p 6379:6379 redis:alpine
```

**설정**:
```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=  # 선택사항
REDIS_DB=0
```

**참고**: Redis가 없으면 인메모리 캐시로 자동 폴백

---

### 4. Ollama (선택사항, 권장)

**용도**: 로컬 LLM/SLM (무료)

**설치 방법**:
```bash
# macOS
brew install ollama

# 모델 다운로드
ollama pull phi3.5
ollama pull qwen2.5:7b
```

**설정**:
```env
OLLAMA_HOST=http://localhost:11434
```

---

### 5. Anthropic Claude (선택사항)

**용도**: 고성능 LLM

**획득 방법**:
1. https://console.anthropic.com/settings/keys 접속
2. "Create Key" 클릭
3. 키 복사 (형식: `sk-ant-api03-...`)

---

### 6. Google Gemini (선택사항)

**용도**: 대안 LLM

**획득 방법**:
1. https://aistudio.google.com/app/apikey 접속
2. "Create API Key" 클릭
3. 키 복사 (형식: `AIzaSy...`)

---

## 🚀 설정 방법

### 1. .env 파일 생성

```bash
cd insightstock-ai-service
cp .env.example .env
```

### 2. .env 파일 수정

```bash
# 필수 항목만 수정
OPENAI_API_KEY=sk-proj-your-actual-key-here
PINECONE_API_KEY=your-actual-pinecone-key-here
```

### 3. 환경 변수 검증

```bash
python -c "from src.config.env import EnvConfig; print('✅ 환경 변수 로드 성공')"
```

---

## 💰 비용 정보

### 무료로 시작 가능

1. **OpenAI**: 신규 가입 시 무료 크레딧 제공
2. **Pinecone**: 무료 티어 (2GB, 월 2M Write/1M Read)
3. **Ollama**: 완전 무료 (로컬)
4. **Redis**: 완전 무료 (로컬)

### 예상 비용 (소규모 사용)

- **OpenAI Embedding**: 월 $0.01-0.10 (사용량에 따라)
- **Pinecone**: 무료 티어로 충분
- **총 예상 비용**: 월 $0.01-0.10

---

## ⚠️ 주의사항

1. **보안**: `.env` 파일은 절대 Git에 커밋하지 마세요
2. **프로덕션**: 프로덕션 환경에서는 실제 API 키 사용
3. **기본값**: 예시값은 실제로 작동하지 않습니다
4. **Pinecone 무료 티어**: 3주 비활성 시 일시정지되지만 재활성화 가능

---

## ✅ 체크리스트

- [ ] OpenAI API Key 설정
- [ ] Pinecone API Key 설정
- [ ] Redis 설치 및 실행 (선택사항)
- [ ] Ollama 설치 및 모델 다운로드 (선택사항)
- [ ] Backend API URL 확인
- [ ] 환경 변수 검증

---

**작성자**: AI Assistant  
**프로젝트**: InsightStock AI Service
