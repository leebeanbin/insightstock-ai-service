# 백엔드 DB 구조 통합 가이드

**작성일**: 2025년 12월 15일

---

## 📊 백엔드 DB 구조 파악

### PostgreSQL + Prisma 구조

#### 주요 모델

1. **News 모델**
   ```prisma
   model News {
     id           String   @id
     title        String
     content      String   @db.Text
     summary      String?  @db.Text
     source       String
     url          String?  @unique
     publishedAt  DateTime
     sentiment    String?  // positive, negative, neutral
     sentimentScore Float?
     thumbnailUrl String?
     
     stocks      NewsStock[]      // 관계: 뉴스-주식
     keyPoints   NewsKeyPoint[]   // 핵심 포인트
     concepts    NewsConcept[]    // 관련 개념
   }
   ```

2. **Stock 모델**
   ```prisma
   model Stock {
     id          String   @id
     code        String   @unique  // 종목 코드
     name        String   // 종목명
     market      String   // KOSPI, KOSDAQ 등
     sector      String?
     description String?
     
     news        NewsStock[]  // 관계: 주식-뉴스
   }
   ```

3. **Learning 모델**
   ```prisma
   model Learning {
     id            String   @id
     userId        String
     concept       String
     question      String   @db.Text
     answer        String   @db.Text
     relatedStocks String[] // stock codes
   }
   ```

4. **Note 모델**
   ```prisma
   model Note {
     id             String   @id
     userId         String
     title          String
     content        String   @db.Text
     tags           String[]
     newsId         String?  // 스크랩한 뉴스 ID
     relatedStocks  String[] // 관련 종목 코드
   }
   ```

---

## 🔄 동기화 패턴

### 1. 뉴스 인덱싱

**백엔드 구조**:
- News 테이블에 뉴스 저장
- NewsStock으로 Stock과 연결
- NewsKeyPoint, NewsConcept 포함

**AI 서비스 동기화**:
```python
# 백엔드에서 뉴스 데이터 조회
news_data = await fetch_news_from_backend(news_id)

# 벡터 DB에 인덱싱 (트랜잭션 기반)
vector_ids = await indexing_service.index_news(news_data)
```

**데이터 매핑**:
- `news_data.id` → `news_{id}`
- `news_data.title + summary/content` → 청킹
- `news_data.stockCodes` → 메타데이터
- `news_data.sentiment` → 메타데이터

### 2. 주식 인덱싱

**백엔드 구조**:
- Stock 테이블에 주식 정보 저장
- StockPrice로 가격 이력 관리

**AI 서비스 동기화**:
```python
# 백엔드에서 주식 데이터 조회
stock_data = await fetch_stock_from_backend(stock_code)

# 벡터 DB에 인덱싱 (트랜잭션 기반)
vector_id = await indexing_service.index_stock(stock_data)
```

**데이터 매핑**:
- `stock_data.code` → `stock_{code}`
- `stock_data.name + code + sector + description` → 텍스트

---

## ✅ 완료된 통합

### 1. SyncService 구현

- ✅ 백엔드 API와 통신
- ✅ 뉴스/주식 데이터 조회
- ✅ 벡터 DB 동기화
- ✅ 트랜잭션 기반 정합성 보장

### 2. 트랜잭션 패턴

- ✅ 스프링 스타일 `@transactional` 데코레이터
- ✅ Saga 패턴 (PostgreSQL + 벡터 DB)
- ✅ 보상 트랜잭션 자동 실행

### 3. 비용 최적화

- ✅ 배치 처리 (비용 50% 절감)
- ✅ 캐싱 전략 (중복 호출 방지)
- ✅ 적응형 청킹 (청크 수 최소화)
- ✅ 모델 선택 최적화 (SLM 우선)

---

## 📝 사용 예시

### 뉴스 동기화

```python
from services.sync_service import SyncService

sync_service = SyncService()

# 단일 뉴스 동기화
vector_ids = await sync_service.sync_news_to_vector_db(news_id)

# 배치 동기화 (비용 최적화)
results = await sync_service.sync_news_batch(news_ids)
```

### 주식 동기화

```python
# 주식 동기화
vector_id = await sync_service.sync_stock_to_vector_db(stock_code)
```

---

**작성자**: AI Assistant  
**프로젝트**: InsightStock AI Service
