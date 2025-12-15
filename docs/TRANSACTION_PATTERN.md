# 트랜잭션 패턴 가이드 (스프링 스타일)

**작성일**: 2025년 12월 15일

---

## ✅ 구현된 트랜잭션 패턴

### 1. 데이터베이스 트랜잭션 (스프링 `@Transactional` 스타일)

#### `@transactional` 데코레이터

```python
from utils.transaction import transactional

@transactional()
async def create_news_with_indexing(news_data):
    """
    뉴스 생성 및 벡터 DB 인덱싱
    트랜잭션 내에서 실행되어 정합성 보장
    """
    # PostgreSQL에 뉴스 저장
    news = await save_news_to_db(news_data)
    
    # 벡터 DB에 인덱싱 (Saga 패턴으로 보상 트랜잭션 지원)
    vector_ids = await index_news_to_vector_db(news)
    
    return news, vector_ids
```

#### 트랜잭션 전파 방식

```python
# REQUIRED: 기존 트랜잭션이 있으면 사용, 없으면 새로 생성 (기본값)
@transactional(propagation="REQUIRED")
async def operation1():
    ...

# REQUIRES_NEW: 항상 새 트랜잭션 생성
@transactional(propagation="REQUIRES_NEW")
async def operation2():
    ...

# SUPPORTS: 트랜잭션이 있으면 사용, 없으면 트랜잭션 없이 실행
@transactional(propagation="SUPPORTS")
async def operation3():
    ...
```

#### 격리 수준

```python
# READ COMMITTED (기본값)
@transactional(isolation_level="READ COMMITTED")

# REPEATABLE READ
@transactional(isolation_level="REPEATABLE READ")

# SERIALIZABLE
@transactional(isolation_level="SERIALIZABLE")
```

---

### 2. Saga 패턴 (분산 트랜잭션)

#### PostgreSQL + 벡터 DB 동기화

```python
from utils.transaction import create_saga

async def create_news_with_indexing(news_data):
    saga = create_saga()
    
    # 1단계: PostgreSQL 저장
    async def save_to_postgres():
        news = await prisma.news.create(data=news_data)
        return news
    
    async def rollback_postgres(news):
        await prisma.news.delete(where={"id": news.id})
    
    # 2단계: 벡터 DB 인덱싱
    async def index_to_vector_db(news):
        vector_ids = await indexing_service.index_news(news)
        return vector_ids
    
    async def rollback_vector_db(vector_ids):
        await vector_search_service.delete(vector_ids)
    
    # Saga 구성
    news = None
    vector_ids = []
    
    try:
        # 1단계 실행
        news = await save_to_postgres()
        saga.add_step(
            operation=lambda: save_to_postgres(),
            compensation=lambda: rollback_postgres(news),
            step_id="save_news"
        )
        
        # 2단계 실행
        vector_ids = await index_to_vector_db(news)
        saga.add_step(
            operation=lambda: index_to_vector_db(news),
            compensation=lambda: rollback_vector_db(vector_ids),
            step_id="index_vectors"
        )
        
        # Saga 실행
        await saga.execute()
        
        return news, vector_ids
        
    except Exception as e:
        # 자동으로 보상 트랜잭션 실행
        logger.error(f"Transaction failed: {e}")
        raise
```

---

### 3. 트랜잭션 컨텍스트 매니저

#### 직접 사용

```python
from utils.transaction import transaction

async def complex_operation():
    with transaction(isolation_level="REPEATABLE READ") as tx:
        # 트랜잭션 내 작업
        result1 = await operation1(tx)
        result2 = await operation2(tx)
        
        # 자동 커밋 또는 롤백
        return result1, result2
```

---

## 🎯 정합성과 일관성 보장

### 1. ACID 속성

#### Atomicity (원자성)
- ✅ 모든 작업이 성공하거나 모두 실패
- ✅ Saga 패턴으로 분산 트랜잭션 보장

#### Consistency (일관성)
- ✅ 데이터베이스가 항상 일관된 상태 유지
- ✅ 외래 키 제약 조건 자동 검증

#### Isolation (격리성)
- ✅ 동시 실행 트랜잭션 간 간섭 방지
- ✅ 격리 수준 설정 가능

#### Durability (지속성)
- ✅ 커밋된 변경사항은 영구적으로 저장
- ✅ PostgreSQL 트랜잭션 보장

---

### 2. 분산 트랜잭션 (PostgreSQL + 벡터 DB)

#### 문제점
- 벡터 DB(Pinecone)는 트랜잭션을 지원하지 않음
- PostgreSQL과 벡터 DB 간 원자적 연산 불가

#### 해결책: Saga 패턴
- ✅ 각 단계를 독립적으로 실행
- ✅ 실패 시 보상 트랜잭션으로 롤백
- ✅ 최종 일관성 보장

#### 보상 트랜잭션 예시

```python
# 뉴스 생성 실패 시
async def rollback_news(news_id):
    await prisma.news.delete(where={"id": news_id})

# 벡터 인덱싱 실패 시
async def rollback_vectors(vector_ids):
    await vector_search_service.delete(vector_ids)
```

---

## 📊 트랜잭션 사용 예시

### 1. 뉴스 생성 및 인덱싱

```python
@transactional()
async def create_news_with_indexing(news_data, _tx=None):
    """
    뉴스 생성 및 벡터 DB 인덱싱
    트랜잭션으로 정합성 보장
    """
    # PostgreSQL 저장
    news = await prisma.news.create(data=news_data)
    
    # 벡터 DB 인덱싱 (Saga 패턴)
    vector_ids = await indexing_service.index_news(news_data, _tx=_tx)
    
    return news, vector_ids
```

### 2. 주식 정보 업데이트 및 인덱싱

```python
@transactional()
async def update_stock_with_indexing(stock_id, stock_data, _tx=None):
    """
    주식 정보 업데이트 및 벡터 DB 재인덱싱
    """
    # PostgreSQL 업데이트
    stock = await prisma.stock.update(
        where={"id": stock_id},
        data=stock_data
    )
    
    # 기존 벡터 삭제
    await vector_search_service.delete([f"stock_{stock.code}"])
    
    # 새로 인덱싱
    vector_id = await indexing_service.index_stock(stock_data, _tx=_tx)
    
    return stock, vector_id
```

---

## ✅ 완료된 작업

- ✅ 스프링 스타일 `@transactional` 데코레이터 구현
- ✅ 트랜잭션 전파 방식 지원 (REQUIRED, REQUIRES_NEW, SUPPORTS)
- ✅ 격리 수준 설정 가능
- ✅ Saga 패턴 구현 (분산 트랜잭션)
- ✅ 보상 트랜잭션 자동 실행
- ✅ 트랜잭션 컨텍스트 매니저
- ✅ PostgreSQL + 벡터 DB 동기화 패턴

---

## 🔄 메인 백엔드와의 통합

### 메인 백엔드 트랜잭션 패턴

메인 백엔드는 이미 Prisma 트랜잭션을 사용:

```typescript
// Backend: src/utils/transaction.ts
export async function executeTransaction<T>(
  callback: (tx: Prisma.TransactionClient) => Promise<T>,
  timeout: number = TRANSACTION_TIMEOUT.DEFAULT
): Promise<T>
```

### AI 서비스와의 통합

AI 서비스의 트랜잭션은 메인 백엔드와 독립적으로 동작하지만, 동일한 패턴을 따릅니다:

```python
# AI Service: src/utils/transaction.py
@transactional()
async def operation(_tx=None):
    # 트랜잭션 내 작업
    ...
```

---

## 📝 사용 가이드

### 1. 단순 트랜잭션

```python
@transactional()
async def simple_operation():
    # 트랜잭션 내에서 실행
    result = await some_operation()
    return result
```

### 2. 분산 트랜잭션 (Saga)

```python
@transactional()
async def distributed_operation():
    saga = create_saga()
    
    # 단계 추가
    saga.add_step(
        operation=step1,
        compensation=rollback_step1,
    )
    
    saga.add_step(
        operation=step2,
        compensation=rollback_step2,
    )
    
    # 실행
    await saga.execute()
```

### 3. 트랜잭션 중첩

```python
@transactional(propagation="REQUIRED")
async def outer_operation():
    # 기존 트랜잭션 사용
    await inner_operation()

@transactional(propagation="REQUIRES_NEW")
async def inner_operation():
    # 새 트랜잭션 생성
    ...
```

---

**작성자**: AI Assistant  
**프로젝트**: InsightStock AI Service
