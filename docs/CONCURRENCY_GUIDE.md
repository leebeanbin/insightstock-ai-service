# 동시성 제어 가이드

**작성일**: 2025년 12월 15일

---

## ✅ 적용된 동시성 제어

### 1. 분산 락 (Distributed Lock)

#### 적용 위치

1. **EmbeddingService.create_embedding()**
   - 동일 텍스트 동시 생성 방지
   - 락 키: `embedding_lock:{md5(text:model)}`
   - 타임아웃: 60초

2. **VectorSearchService.search()**
   - 동일 검색 쿼리 동시 실행 방지
   - 락 키: `search_lock:{md5(query:top_k:filter)}`
   - 타임아웃: 30초

3. **VectorSearchService.upsert()**
   - 동일 배치 중복 업로드 방지
   - 락 키: `upsert_batch:{md5(batch_id)}`
   - 타임아웃: 300초

#### 사용 예시

```python
from utils.concurrency import distributed_lock

with distributed_lock("my_resource", timeout=30):
    # 동시에 하나의 프로세스만 실행
    do_something()
```

---

### 2. 세마포어 (Semaphore)

#### 적용 위치

1. **EmbeddingService.create_embeddings_batch()**
   - 배치 임베딩 생성 동시 실행 수 제한
   - 세마포어: `embedding_batch`
   - 제한: 최대 3개 동시 실행

2. **VectorSearchService.upsert()**
   - 벡터 업로드 동시 실행 수 제한
   - 세마포어: `vector_upsert`
   - 제한: 최대 2개 동시 실행

#### 사용 예시

```python
from utils.concurrency import semaphore

with semaphore("my_resource", limit=5, timeout=300):
    # 최대 5개까지 동시 실행
    do_something()
```

---

### 3. Rate Limiting

#### 적용 위치

1. **ChatController.stream_chat()**
   - 전체: 분당 60회
   - 사용자별: 분당 30회
   - Rate Limiter: `chat:stream`, `chat:user:{userId}`

2. **SearchController.vector_search()**
   - 전체: 분당 100회
   - Rate Limiter: `search:vector`

#### 사용 예시

```python
from utils.concurrency import RateLimiter

limiter = RateLimiter("my_endpoint", max_requests=100, window=60)
allowed, remaining = limiter.is_allowed()

if not allowed:
    raise HTTPException(status_code=429, detail="Rate limit exceeded")
```

---

### 4. Redis 트랜잭션

#### 적용 위치

1. **VectorSearchService.search()**
   - 캐시 저장 시 원자성 보장
   - 트랜잭션으로 캐시 업데이트

#### 사용 예시

```python
from utils.concurrency import redis_transaction

with redis_transaction() as tx:
    tx.set("key1", "value1", ttl=3600)
    tx.set("key2", "value2", ttl=3600)
    # 자동으로 커밋 또는 롤백
```

---

## 🎯 동시성 제어 전략

### 1. 임베딩 생성

**문제**: 동일 텍스트에 대해 여러 프로세스가 동시에 임베딩 생성 시도

**해결**:
- 분산 락으로 동일 텍스트 동시 생성 방지
- 락 획득 후 캐시 재확인 (다른 프로세스가 생성했을 수 있음)

### 2. 벡터 검색

**문제**: 동일 검색 쿼리 동시 실행 시 중복 API 호출

**해결**:
- 분산 락으로 동일 검색 동시 실행 방지
- 트랜잭션으로 캐시 저장 원자성 보장

### 3. 벡터 업로드

**문제**: 
- 동시 업로드 시 리소스 경쟁
- 동일 배치 중복 업로드

**해결**:
- 세마포어로 동시 업로드 수 제한 (최대 2개)
- 분산 락으로 동일 배치 중복 업로드 방지

### 4. API Rate Limiting

**문제**: API 남용 및 리소스 고갈

**해결**:
- 엔드포인트별 Rate Limiting
- 사용자별 Rate Limiting
- 토큰 버킷 알고리즘 사용

---

## 📊 성능 영향

### 분산 락

- **장점**: 중복 작업 방지, 리소스 절약
- **단점**: 락 대기 시간 발생 가능
- **최적화**: 짧은 타임아웃, 논블로킹 옵션

### 세마포어

- **장점**: 동시 실행 수 제어, 리소스 보호
- **단점**: 일부 요청 대기 필요
- **최적화**: 적절한 제한 수 설정

### Rate Limiting

- **장점**: API 남용 방지, 안정성 향상
- **단점**: 제한 초과 시 요청 거부
- **최적화**: 적절한 제한 값 설정

---

## 🔧 설정 조정

### Rate Limiting 설정

```python
# Chat 엔드포인트
_chat_rate_limiter = RateLimiter("chat:stream", max_requests=60, window=60)

# Search 엔드포인트
_search_rate_limiter = RateLimiter("search:vector", max_requests=100, window=60)
```

### 세마포어 설정

```python
# 배치 임베딩 생성
with semaphore("embedding_batch", limit=3, timeout=300):

# 벡터 업로드
with semaphore("vector_upsert", limit=2, timeout=600):
```

### 분산 락 타임아웃

```python
# 임베딩 생성
with distributed_lock(lock_key, timeout=60, blocking=True):

# 벡터 검색
with distributed_lock(lock_key, timeout=30, blocking=True):

# 벡터 업로드
with distributed_lock(lock_key, timeout=300, blocking=True):
```

---

## ✅ 완료된 작업

- ✅ 분산 락 구현 및 적용
- ✅ 세마포어 구현 및 적용
- ✅ Rate Limiting 구현 및 적용
- ✅ Redis 트랜잭션 구현 및 적용
- ✅ 모든 캐싱에 Redis 적용 확인
- ✅ 동시성 제어 문서화

---

**작성자**: AI Assistant  
**프로젝트**: InsightStock AI Service

