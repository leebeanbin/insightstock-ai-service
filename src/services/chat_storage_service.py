"""
Chat Storage Service
챗 히스토리 백엔드 저장 서비스
"""

from typing import Optional, List, Dict, Any
from loguru import logger

from src.config.env import EnvConfig
from src.config.managers import get_http_client_manager
from src.interfaces.services.sync_service import ISyncService


class ChatStorageService:
    """
    챗 히스토리 백엔드 저장 서비스

    백엔드 구조:
    - Learning 모델: userId, concept, question, answer, relatedStocks
    - POST /api/learning 엔드포인트 사용
    """

    def __init__(self):
        self.backend_url = EnvConfig.BACKEND_API_URL
        http_client_manager = get_http_client_manager()
        # HTTP 클라이언트 재사용 (연결 풀링)
        self.client = http_client_manager.get_async_client(timeout=30.0)

    def _extract_stock_codes(self, text: str) -> List[str]:
        """
        텍스트에서 종목 코드 추출 (6자리 숫자)

        Args:
            text: 분석할 텍스트

        Returns:
            추출된 종목 코드 리스트
        """
        import re

        # 6자리 숫자 패턴 (한국 주식 코드)
        pattern = r"\b\d{6}\b"
        codes = re.findall(pattern, text)
        return list(set(codes))  # 중복 제거

    def _extract_concept(self, question: str) -> str:
        """
        질문에서 개념 추출 (간단한 키워드 기반)

        Args:
            question: 사용자 질문

        Returns:
            추출된 개념 (기본값: "chat")
        """
        question_lower = question.lower()

        # 키워드 기반 개념 추출
        if any(keyword in question_lower for keyword in ["주가", "가격", "시세", "종가"]):
            return "stock_price"
        elif any(keyword in question_lower for keyword in ["분석", "전망", "예측"]):
            return "analysis"
        elif any(keyword in question_lower for keyword in ["뉴스", "기사", "공시"]):
            return "news"
        else:
            return "chat"

    async def save_chat(
        self,
        userId: str,
        question: str,
        answer: str,
        messages: Optional[List[Dict[str, str]]] = None,
        related_stocks: Optional[List[str]] = None,
        concept: Optional[str] = None,
    ) -> bool:
        """
        챗을 백엔드에 저장

        Args:
            userId: 사용자 ID
            question: 사용자 질문
            answer: AI 응답
            messages: 대화 히스토리 (선택적)
            related_stocks: 관련 종목 코드 리스트 (선택적, 자동 추출 가능)
            concept: 개념 (선택적, 자동 추출 가능)

        Returns:
            성공 여부 (True/False)
        """
        # 입력 검증
        if not userId or not userId.strip():
            logger.warning("userId is required for chat storage")
            return False
        
        if not question or not question.strip():
            logger.warning("question is required for chat storage")
            return False
        
        if not answer or not answer.strip():
            logger.warning("answer is required for chat storage")
            return False

        try:
            # 입력 정규화
            question = question.strip()
            answer = answer.strip()
            
            # 관련 종목 코드 자동 추출 (제공되지 않은 경우)
            if related_stocks is None:
                related_stocks = self._extract_stock_codes(question + " " + answer)

            # 개념 자동 추출 (제공되지 않은 경우)
            if concept is None:
                concept = self._extract_concept(question)

            # 백엔드 API 호출
            response = await self.client.post(
                f"{self.backend_url}/api/learning",
                json={
                    "userId": userId,
                    "concept": concept,
                    "question": question,
                    "answer": answer,
                    "relatedStocks": related_stocks,  # 백엔드 API는 camelCase 사용
                },
                headers={"Content-Type": "application/json"},
            )

            # 201 (동기 처리) 또는 202 (비동기 큐 처리) 모두 성공으로 처리
            if response.status_code in (201, 202):
                try:
                    data = response.json()
                    if response.status_code == 201:
                        learning_id = data.get("data", {}).get("id") or data.get("id")
                        logger.info(f"Chat saved to backend: {learning_id} (user: {userId})")
                    else:  # 202
                        job_id = data.get("jobId")
                        logger.info(f"Chat queued for backend: {job_id} (user: {userId})")
                    return True
                except Exception as e:
                    logger.warning(f"Failed to parse response JSON: {e}, but status code indicates success")
                    return True  # 상태 코드가 성공이면 True 반환
            elif response.status_code == 400:
                # 입력 검증 실패
                error_text = response.text[:200] if response.text else "Bad request"
                logger.error(f"Validation error saving chat: {error_text}")
                return False
            else:
                error_text = response.text[:200] if response.text else "Unknown error"
                logger.error(
                    f"Failed to save chat: {response.status_code} - {error_text}"
                )
                return False

        except Exception as e:
            logger.error(f"Chat storage error: {e}", exc_info=True)
            # 백엔드 저장 실패는 챗 응답에 영향을 주지 않도록 에러만 로깅
            return False

    async def save_chat_batch(
        self,
        chats: List[Dict[str, Any]],
    ) -> int:
        """
        배치로 챗 저장 (성능 최적화)
        
        Args:
            chats: 챗 데이터 리스트
                각 항목: {
                    "userId": str,
                    "question": str,
                    "answer": str,
                    "messages": Optional[List[Dict[str, str]]],
                    "related_stocks": Optional[List[str]],
                    "concept": Optional[str],
                }
        
        Returns:
            성공적으로 저장된 챗 수
        """
        if not chats:
            return 0
        
        try:
            # 배치 데이터 준비
            batch_data = []
            for chat in chats:
                if not chat.get("userId"):
                    logger.warning("Skipping chat without userId")
                    continue
                
                # 관련 종목 코드 자동 추출
                related_stocks = chat.get("related_stocks")
                if related_stocks is None:
                    related_stocks = self._extract_stock_codes(
                        chat.get("question", "") + " " + chat.get("answer", "")
                    )
                
                # 개념 자동 추출
                concept = chat.get("concept")
                if concept is None:
                    concept = self._extract_concept(chat.get("question", ""))
                
                batch_data.append({
                    "userId": chat["userId"],
                    "concept": concept,
                    "question": chat["question"],
                    "answer": chat["answer"],
                    "relatedStocks": related_stocks,
                })
            
            if not batch_data:
                return 0
            
            # 배치 크기 제한 (백엔드와 동일하게 100개)
            MAX_BATCH_SIZE = 100
            if len(batch_data) > MAX_BATCH_SIZE:
                logger.warning(
                    f"Batch size {len(batch_data)} exceeds maximum {MAX_BATCH_SIZE}, "
                    "splitting into smaller batches"
                )
                # 배치를 나눠서 처리
                total_saved = 0
                for i in range(0, len(batch_data), MAX_BATCH_SIZE):
                    chunk = batch_data[i:i + MAX_BATCH_SIZE]
                    saved = await self._save_batch_chunk(chunk)
                    total_saved += saved
                return total_saved
            
            # 배치 저장 API 호출
            return await self._save_batch_chunk(batch_data)
            
        except Exception as e:
            logger.error(f"Batch chat storage error: {e}", exc_info=True)
            return 0
    
    async def _save_batch_chunk(self, batch_data: List[Dict[str, Any]]) -> int:
        """배치 청크 저장 (내부 헬퍼 메서드)"""
        try:
            response = await self.client.post(
                f"{self.backend_url}/api/learning/batch",
                json=batch_data,
                headers={"Content-Type": "application/json"},
            )
            
            # 201 (동기 처리) 또는 202 (비동기 큐 처리) 모두 성공으로 처리
            if response.status_code in (201, 202):
                try:
                    data = response.json()
                    if response.status_code == 201:
                        saved_count = len(data.get("data", [])) if isinstance(data.get("data"), list) else data.get("meta", {}).get("count", len(batch_data))
                        logger.info(f"Batch saved {saved_count} chats to backend")
                    else:  # 202
                        saved_count = data.get("count", len(batch_data))
                        logger.info(f"Batch queued {saved_count} chats to backend")
                    return saved_count
                except Exception as e:
                    logger.warning(f"Failed to parse batch response JSON: {e}, assuming success")
                    return len(batch_data)  # 상태 코드가 성공이면 전체 개수 반환
            elif response.status_code == 400:
                error_text = response.text[:200] if response.text else "Bad request"
                logger.warning(f"Batch API validation error: {error_text}, falling back to individual saves")
            else:
                logger.warning(
                    f"Batch API not available ({response.status_code}), "
                    "falling back to individual saves"
                )
            
            # 폴백: 개별 저장
            return await self._fallback_individual_saves(batch_data)
            
        except Exception as e:
            logger.warning(f"Batch API error: {e}, falling back to individual saves")
            return await self._fallback_individual_saves(batch_data)
    
    async def _fallback_individual_saves(self, batch_data: List[Dict[str, Any]]) -> int:
        """폴백: 개별 저장 (내부 헬퍼 메서드)"""
        success_count = 0
        for chat_data in batch_data:
            try:
                response = await self.client.post(
                    f"{self.backend_url}/api/learning",
                    json=chat_data,
                    headers={"Content-Type": "application/json"},
                )
                if response.status_code in (201, 202):
                    success_count += 1
            except Exception as e:
                logger.error(f"Failed to save chat in batch fallback: {e}")
        
        return success_count

    async def close(self):
        """리소스 정리"""
        # HTTP 클라이언트는 싱글톤이므로 여기서 닫지 않음
        # 실제로는 HTTPClientManager에서 관리
        pass

