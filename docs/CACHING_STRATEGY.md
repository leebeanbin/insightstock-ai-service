# 캐싱 전략 문서

**작성일**: 2025년 12월 15일  
**업데이트**: Redis 기반 캐싱으로 변경

---

## 📋 캐싱 접근 방식

### Redis 기반 캐싱 (프로덕션 권장)

**AI 서비스 (Python)**:
- ✅ **Redis 캐싱** 사용 (메인 백엔드와 동일한 Redis 인스턴스)
- ✅ Redis 연결 실패 시 **인메모리 캐시로 자동 폴백**
- ✅ 분산 캐싱 지원 (여러 서버 인스턴스 간 캐시 공유)
- ✅ 서버 재시작 후에도 캐시 유지 가능
- ✅ 더 많은 데이터 저장 가능

**메인 백엔드 (TypeScript)**:
- ✅ **Redis** 사용 (이미 구현됨)
- ✅ 동일한 Redis 인스턴스 공유

---

## 🎯 AI 서비스 캐싱 전략

### 1. EmbeddingService 캐싱

```python
# 임베딩 결과 캐싱 (1시간 TTL)
cache_key = f"embedding:{md5(text:model)}"
```

**캐시 대상**:
- ✅ 단일 텍스트 임베딩 결과
- ✅ 동일한 텍스트 + 모델 조합

**TTL**: 1시간 (3600초)

**이유**: 임베딩은 동일 입력에 대해 항상 동일한 결과를 반환하므로 캐싱 효과가 큼

### 2. VectorSearchService 캐싱

```python
# 검색 결과 캐싱 (30분 TTL)
cache_key = f"vector_search:{md5(query:top_k:filter)}"
```

**캐시 대상**:
- ✅ 벡터 검색 결과
- ✅ 쿼리 + top_k + 필터 조합

**TTL**: 30분 (1800초)

**이유**: 검색 결과는 데이터가 업데이트될 수 있으므로 임베딩보다 짧게

### 3. ModelRouterService 캐싱

```python
# 쿼리 분류 결과 캐싱 (1시간 TTL)
cache_key = f"classification:{md5(query)}"
```

**캐시 대상**:
- ✅ 쿼리 복잡도 분류 결과
- ✅ 동일한 쿼리는 항상 동일한 분류 결과

**TTL**: 1시간 (3600초)

**이유**: 쿼리 분류는 결정적(deterministic)이므로 캐싱 효과가 큼

---

## 🔧 Redis 설정

### 환경 변수

```env
# Redis 설정
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=  # 선택사항
REDIS_DB=0  # AI 서비스 전용 DB (기본값: 0)
```

### Redis 클라이언트

- **위치**: `src/config/redis.py`
- **싱글톤 패턴**: 하나의 클라이언트 인스턴스만 사용
- **자동 재연결**: 연결 실패 시 자동 재시도
- **Health Check**: 30초마다 연결 상태 확인

### 폴백 메커니즘

Redis 연결 실패 시:
1. 자동으로 인메모리 캐시(`SimpleCache`)로 폴백
2. 로그에 경고 메시지 기록
3. 서비스는 정상 작동 (캐시만 인메모리로 처리)

---

## 📊 캐시 성능

### 메모리 사용량

- **임베딩 벡터**: ~6KB (1536차원 × 4바이트)
- **검색 결과**: ~1-5KB (결과 수에 따라)
- **분류 결과**: ~100바이트

**예상 메모리 사용량**:
- 10,000개 임베딩 캐시: ~60MB
- 1,000개 검색 결과 캐시: ~5MB
- 10,000개 분류 결과: ~1MB

**총 예상**: ~70MB (일반적인 사용량)

### 캐시 히트율

- **임베딩**: 높음 (동일한 텍스트가 자주 검색됨)
- **검색 결과**: 중간 (사용자별로 다름)
- **분류 결과**: 높음 (자주 묻는 질문)

---

## 🔧 캐시 관리

### 자동 만료

- TTL 기반 자동 만료
- 만료된 항목은 조회 시 자동 삭제

### 수동 관리

```python
from utils.cache import cache

# 캐시 삭제
cache.delete("embedding:abc123")

# 전체 캐시 초기화 (현재 DB만)
cache.clear()

# 캐시 크기 확인
size = cache.size()
```

### Redis 명령어

```bash
# Redis CLI 접속
redis-cli

# 현재 DB의 모든 키 확인
KEYS *

# 특정 패턴의 키 확인
KEYS embedding:*

# 캐시 통계
INFO stats

# 메모리 사용량
INFO memory
```

---

## ✅ 장점

### Redis 사용의 이점

1. **분산 캐싱**: 여러 서버 인스턴스 간 캐시 공유
2. **영구성**: 서버 재시작 후에도 캐시 유지
3. **메모리 관리**: 별도 프로세스로 메모리 관리
4. **확장성**: 더 많은 데이터 저장 가능
5. **일관성**: 메인 백엔드와 동일한 캐싱 인프라

### 폴백 메커니즘

- Redis 연결 실패 시에도 서비스 정상 작동
- 개발 환경에서 Redis 없이도 테스트 가능
- 점진적 마이그레이션 가능

---

## ⚠️ 주의사항

### Redis 연결

- Redis 서버가 실행 중이어야 함
- 네트워크 연결이 안정적이어야 함
- Redis 메모리 제한 설정 권장

### 데이터 직렬화

- Pickle을 사용하여 Python 객체 직렬화
- 바이너리 데이터 지원
- 큰 객체는 압축 고려

---

## ✅ 현재 구현 상태

- ✅ `RedisCache` 클래스 구현
- ✅ `SimpleCache` 폴백 구현
- ✅ `EmbeddingService`에 Redis 캐싱 적용
- ✅ `VectorSearchService`에 Redis 캐싱 적용
- ✅ `ModelRouterService`에 Redis 캐싱 적용
- ✅ TTL 기반 자동 만료
- ✅ 캐시 키 해싱 (MD5)
- ✅ 자동 폴백 메커니즘

---

## 🎯 사용 예시

### Redis 캐시 사용 (기본)

```python
# 자동으로 Redis 캐싱됨 (실패 시 인메모리로 폴백)
embedding = embedding_service.create_embedding("삼성전자 주가 분석")
```

### 캐시 비활성화

```python
# 캐시 없이 실행
embedding = embedding_service.create_embedding(
    "삼성전자 주가 분석",
    use_cache=False
)
```

---

## 📝 환경 변수 설정

### `.env` 파일

```env
# Redis 설정
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=  # 선택사항
REDIS_DB=0  # AI 서비스 전용 DB
```

### 메인 백엔드와 동일한 Redis 사용

메인 백엔드와 AI 서비스가 동일한 Redis 인스턴스를 사용하지만, 다른 DB 번호를 사용할 수 있습니다:

- **메인 백엔드**: `REDIS_DB=0` (기본값)
- **AI 서비스**: `REDIS_DB=1` (선택사항, 분리하려면)

---

**작성자**: AI Assistant  
**프로젝트**: InsightStock AI Service

