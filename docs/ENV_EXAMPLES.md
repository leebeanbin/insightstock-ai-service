# 환경 변수 예시값 가이드

**작성일**: 2025년 12월 15일

---

## 📋 AI 서비스 환경 변수

### `.env.example` 파일 내용

```env
# ============================================
# Server Configuration
# ============================================
PORT=3002
HOST=0.0.0.0
NODE_ENV=development
LOG_LEVEL=INFO

# ============================================
# LLM Provider API Keys
# 최소 하나의 Provider API 키가 필요합니다
# ============================================

# OpenAI (우선순위 1)
OPENAI_API_KEY=sk-proj-your-openai-api-key-here-example-1234567890abcdef

# Anthropic Claude (우선순위 2)
ANTHROPIC_API_KEY=sk-ant-api03-your-anthropic-api-key-here-example-1234567890abcdef

# Google Gemini (우선순위 3)
GEMINI_API_KEY=AIzaSy-your-gemini-api-key-here-example-1234567890abcdef

# Ollama (우선순위 4, 로컬 서버)
OLLAMA_HOST=http://localhost:11434

# ============================================
# Vector Database (Pinecone)
# ============================================
PINECONE_API_KEY=your-pinecone-api-key-here-example-1234567890abcdef
PINECONE_INDEX_NAME=insightstock

# ============================================
# Cache (Redis)
# ============================================
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=  # 선택사항
REDIS_DB=0  # AI 서비스 전용 DB (기본값: 0)
```

---

## 📋 메인 백엔드 환경 변수

### `.env.example` 파일에 추가할 내용

```env
# ============================================
# AI Service Integration (새로 추가)
# ============================================
AI_SERVICE_URL=http://localhost:3002
```

### 전체 `.env.example` 예시

```env
# ============================================
# Server Configuration
# ============================================
PORT=3001
NODE_ENV=development

# ============================================
# Database
# ============================================
DATABASE_URL="postgresql://user:password@localhost:5432/insightstock?schema=public"

# ============================================
# Authentication
# ============================================
JWT_SECRET=your_jwt_secret_key_here_change_in_production_min_32_chars
JWT_EXPIRES_IN=7d

# ============================================
# AI Service Integration (새로 추가)
# ============================================
AI_SERVICE_URL=http://localhost:3002

# ============================================
# OpenAI (기존, AI 서비스로 이동 예정)
# ============================================
OPENAI_API_KEY=sk-proj-your-openai-api-key-here-example-1234567890abcdef

# ============================================
# Vector Database (Pinecone)
# ============================================
PINECONE_API_KEY=your-pinecone-api-key-here-example-1234567890abcdef
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=insightstock

# ============================================
# Cache (Redis)
# ============================================
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=  # 선택사항
REDIS_DB=0  # AI 서비스 전용 DB (기본값: 0)

# ============================================
# KIS API (한국투자증권)
# ============================================
KIS_APP_KEY=your-kis-app-key-here-example-1234567890abcdef
KIS_APP_SECRET=your-kis-app-secret-here-example-1234567890abcdef
KIS_ACCOUNT_NO=your-kis-account-no-here-example-1234567890

# ============================================
# CORS
# ============================================
CORS_ORIGIN=http://localhost:3000
```

---

## 🔑 API 키 획득 방법

### OpenAI
1. https://platform.openai.com/api-keys 접속
2. "Create new secret key" 클릭
3. 키 복사 (형식: `sk-proj-...`)

### Anthropic Claude
1. https://console.anthropic.com/settings/keys 접속
2. "Create Key" 클릭
3. 키 복사 (형식: `sk-ant-api03-...`)

### Google Gemini
1. https://aistudio.google.com/app/apikey 접속
2. "Create API Key" 클릭
3. 키 복사 (형식: `AIzaSy...`)

### Pinecone
1. https://www.pinecone.io/ 접속
2. 회원가입 및 로그인
3. API Keys 섹션에서 키 복사

**무료 티어**:
- ✅ 2GB 스토리지
- ✅ 월 2백만 Write Units
- ✅ 월 1백만 Read Units
- ✅ 5개 인덱스
- ⚠️ 3주 비활성 시 일시정지 (재활성화 가능)

### Ollama
- 로컬 설치 필요: https://ollama.ai/
- API 키 불필요 (로컬 서버)

---

## 🚀 설정 방법

### AI 서비스

```bash
cd insightstock-ai-service
cp .env.example .env
# .env 파일을 열고 실제 API 키로 변경
```

### 메인 백엔드

```bash
cd insightstock-backend
# .env 파일에 AI_SERVICE_URL 추가
echo "AI_SERVICE_URL=http://localhost:3002" >> .env
```

---

## ✅ 검증

### AI 서비스

```bash
cd insightstock-ai-service
python -c "from src.config.env import EnvConfig; print(EnvConfig.PORT)"
# 출력: 3002
```

### 메인 백엔드

```bash
cd insightstock-backend
node -e "console.log(process.env.AI_SERVICE_URL || 'http://localhost:3002')"
# 출력: http://localhost:3002
```

---

## 🚨 주의사항

1. **보안**: `.env` 파일은 절대 Git에 커밋하지 마세요
2. **프로덕션**: 프로덕션 환경에서는 실제 API 키 사용
3. **기본값**: 예시값은 실제로 작동하지 않습니다. 반드시 실제 키로 변경하세요

---

**작성자**: AI Assistant  
**프로젝트**: InsightStock
