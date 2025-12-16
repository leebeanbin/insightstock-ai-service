"""
Chat Storage Queue
챗 저장을 위한 Redis 메시지 큐 래퍼
"""

from typing import Dict, Any, Optional, List
from loguru import logger
from src.services.redis_message_queue import RedisMessageQueue


class ChatStorageQueue:
    """챗 저장 큐"""
    
    QUEUE_NAME = "chat:storage"
    
    def __init__(self):
        self.queue = RedisMessageQueue()
    
    async def enqueue_chat(
        self,
        userId: str,
        question: str,
        answer: str,
        messages: Optional[List[Dict[str, str]]] = None,
        related_stocks: Optional[List[str]] = None,
    ) -> bool:
        """
        챗 저장 작업을 큐에 추가
        
        Args:
            userId: 사용자 ID
            question: 질문
            answer: 응답
            messages: 대화 히스토리 (선택)
            related_stocks: 관련 종목 코드 (선택)
            
        Returns:
            성공 여부
        """
        if not userId:
            logger.warning("Cannot enqueue chat: userId is missing")
            return False
        
        chat_data = {
            "userId": userId,
            "question": question,
            "answer": answer,
            "messages": messages or [],
            "related_stocks": related_stocks or [],
            "timestamp": None,  # Worker에서 설정
        }
        
        success = await self.queue.enqueue(self.QUEUE_NAME, chat_data)
        if success:
            logger.debug(f"Chat storage queued for user: {userId}")
        else:
            logger.warning(f"Failed to queue chat storage for user: {userId}")
        
        return success
    
    def get_queue_length(self) -> int:
        """대기 중인 챗 저장 작업 수"""
        return self.queue.get_queue_length(self.QUEUE_NAME)

