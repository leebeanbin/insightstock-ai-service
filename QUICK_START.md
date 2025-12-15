# 빠른 시작 가이드

**작성일**: 2025년 12월 15일

---

## 🚀 서버 실행 방법

### 1. 환경 변수 설정

```bash
cd insightstock-ai-service

# .env 파일 생성 (없는 경우)
cp .env.example .env

# .env 파일 수정 (최소 필수 항목)
# - OPENAI_API_KEY (필수)
# - PINECONE_API_KEY (필수)
```

### 2. 의존성 설치

```bash
# 가상 환경 생성 (선택사항)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 3. 서버 실행

#### 방법 1: Python 직접 실행 (권장)

```bash
cd src
python main.py
```

#### 방법 2: uvicorn 직접 실행

```bash
uvicorn src.main:app --reload --port 3002 --host 0.0.0.0
```

#### 방법 3: Makefile 사용

```bash
make run
```

### 4. 서버 확인

서버가 정상적으로 실행되면:

```bash
# Health Check
curl http://localhost:3002/health
```

**예상 응답**:
```json
{
  "status": "ok",
  "service": "ai-service",
  "version": "1.0.0",
  "available_providers": ["ollama", "openai"]
}
```

---

## 💬 챗 기능 테스트

### 1. 스트리밍 챗 테스트 (SSE)

```bash
curl -X POST http://localhost:3002/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "안녕하세요",
    "messages": []
  }'
```

**스트리밍 응답 예시**:
```
data: {"content":"안녕","done":false}
data: {"content":"하세요","done":false}
data: {"content":"!","done":false}
data: {"done":true}
```

### 2. 일반 챗 테스트 (비스트리밍)

```bash
curl -X POST http://localhost:3002/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "삼성전자 주가에 대해 설명해줘",
    "messages": []
  }'
```

**응답 예시**:
```json
{
  "response": "삼성전자는 한국의 대표적인 반도체 제조사입니다...",
  "model": "phi3.5",
  "usage": {
    "tokens": 150
  }
}
```

### 3. 대화 히스토리 포함 테스트

```bash
curl -X POST http://localhost:3002/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "그럼 애플은?",
    "messages": [
      {"role": "user", "content": "삼성전자에 대해 설명해줘"},
      {"role": "assistant", "content": "삼성전자는..."}
    ]
  }'
```

### 4. 특정 모델 강제 사용

```bash
curl -X POST http://localhost:3002/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "복잡한 투자 전략을 분석해줘",
    "force_model": "claude-3-5-sonnet-20241022"
  }'
```

---

## 🧪 테스트 스크립트

### Python 테스트 스크립트

`test_chat.py` 파일 생성:

```python
import requests
import json

# 스트리밍 챗 테스트
def test_stream_chat():
    url = "http://localhost:3002/api/chat/stream"
    data = {
        "query": "안녕하세요! 주식 투자에 대해 알려주세요.",
        "messages": []
    }
    
    response = requests.post(url, json=data, stream=True)
    
    print("스트리밍 응답:")
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                data_str = line_str[6:]  # 'data: ' 제거
                try:
                    data_json = json.loads(data_str)
                    if data_json.get('done'):
                        print("\n✅ 완료")
                        break
                    else:
                        print(data_json.get('content', ''), end='', flush=True)
                except:
                    pass

# 일반 챗 테스트
def test_chat():
    url = "http://localhost:3002/api/chat"
    data = {
        "query": "삼성전자 주가 분석",
        "messages": []
    }
    
    response = requests.post(url, json=data)
    result = response.json()
    
    print("\n응답:")
    print(result.get('response', ''))
    print(f"\n사용된 모델: {result.get('model', '')}")

if __name__ == "__main__":
    print("=" * 60)
    print("챗 기능 테스트")
    print("=" * 60)
    
    print("\n1. 스트리밍 챗 테스트")
    print("-" * 60)
    test_stream_chat()
    
    print("\n\n2. 일반 챗 테스트")
    print("-" * 60)
    test_chat()
```

**실행**:
```bash
python test_chat.py
```

---

## 📋 API 엔드포인트 목록

### Health Check
```bash
GET /health
```

### 챗 API

#### 스트리밍 챗
```bash
POST /api/chat/stream
Content-Type: application/json

{
  "query": "사용자 질문",
  "messages": [],  # 선택사항
  "system": "",    # 선택사항
  "force_model": ""  # 선택사항
}
```

#### 일반 챗
```bash
POST /api/chat
Content-Type: application/json

{
  "query": "사용자 질문",
  "messages": [],  # 선택사항
  "system": "",    # 선택사항
  "force_model": ""  # 선택사항
}
```

#### 사용 가능한 모델 조회
```bash
GET /api/models
```

### 검색 API

#### 벡터 검색
```bash
POST /api/search/vector
Content-Type: application/json

{
  "query": "검색어",
  "top_k": 5,  # 선택사항
  "filter": {}  # 선택사항
}
```

#### 인덱스 통계
```bash
GET /api/search/index/stats
```

---

## 🔍 문제 해결

### 1. 서버가 시작되지 않을 때

```bash
# 포트 확인
lsof -i :3002

# 다른 포트로 실행
uvicorn src.main:app --port 3003
```

### 2. API 키 오류

```bash
# 환경 변수 확인
python -c "from src.config.env import EnvConfig; print(f'OpenAI: {bool(EnvConfig.OPENAI_API_KEY)}')"
```

### 3. Ollama 연결 오류

```bash
# Ollama 서버 확인
curl http://localhost:11434/api/tags

# Ollama 서버 시작
ollama serve
```

### 4. Redis 연결 오류

```bash
# Redis 서버 확인
redis-cli ping

# Redis 서버 시작
redis-server
# 또는
brew services start redis
```

**참고**: Redis가 없어도 인메모리 캐시로 자동 폴백됩니다.

---

## ✅ 테스트 체크리스트

- [ ] 서버 실행 확인 (`/health` 엔드포인트)
- [ ] OpenAI API 키 설정 확인
- [ ] Ollama 서버 실행 확인 (선택사항)
- [ ] 스트리밍 챗 테스트
- [ ] 일반 챗 테스트
- [ ] 모델 목록 조회 테스트

---

**작성자**: AI Assistant  
**프로젝트**: InsightStock AI Service
