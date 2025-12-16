"""
Chat Storage Worker
백그라운드에서 챗 저장 작업을 처리하는 워커
"""

import asyncio
from typing import Optional, Dict, List
from loguru import logger
from src.services.redis_message_queue import RedisMessageQueue
from src.services.chat_storage_service import ChatStorageService


class ChatStorageWorker:
    """챗 저장 워커"""
    
    QUEUE_NAME = "chat:storage"
    
    def __init__(self):
        self.queue = RedisMessageQueue()
        self.running = False
    
    async def process_chat_storage(
        self,
        max_retries: int = 3,
        batch_size: int = 1,
    ):
        """
        챗 저장 작업 처리 (단일 또는 배치, 재시도 포함)
        
        Args:
            max_retries: 최대 재시도 횟수
            batch_size: 배치 크기 (1이면 단일 처리)
        """
        # 배치 처리 (대규모 처리 최적화)
        if batch_size > 1:
            chat_data_list = await self.queue.dequeue_batch(self.QUEUE_NAME, batch_size=batch_size, timeout=5)
            if not chat_data_list:
                return False
            
            # 배치 저장으로 최적화
            return await self._process_batch_chat(chat_data_list, max_retries)
        
        # 단일 처리
        chat_data = await self.queue.dequeue(self.QUEUE_NAME, timeout=5)
        if not chat_data:
            return False
        
        return await self._process_single_chat(chat_data, max_retries)
    
    async def _process_batch_chat(self, chat_data_list: List[Dict], max_retries: int) -> bool:
        """배치 챗 저장 처리 (성능 최적화)"""
        from datetime import datetime
        
        # 타임스탬프 추가
        for chat_data in chat_data_list:
            chat_data["timestamp"] = datetime.now().isoformat()
        
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                storage_service = ChatStorageService()
                
                # 배치 저장 시도
                saved_count = await storage_service.save_chat_batch(chat_data_list)
                
                if saved_count == len(chat_data_list):
                    logger.info(f"Batch stored {saved_count} chats")
                    return True
                elif saved_count > 0:
                    logger.warning(
                        f"Partially saved batch: {saved_count}/{len(chat_data_list)}"
                    )
                    # 부분 성공 시 실패한 항목만 재시도
                    failed_chats = chat_data_list[saved_count:]
                    if failed_chats:
                        return await self._process_batch_chat(failed_chats, max_retries)
                    return True
                else:
                    # 전체 실패
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.info(f"Retrying batch storage (attempt {retry_count + 1}/{max_retries})")
                        await asyncio.sleep(2 ** retry_count)  # 지수 백오프
                    else:
                        # 최대 재시도 횟수 초과 시 DLQ로 이동
                        for chat_data in chat_data_list:
                            await self._move_to_dlq(chat_data)
                        return False
                        
            except Exception as e:
                logger.error(f"Error processing batch storage (attempt {retry_count + 1}): {e}")
                retry_count += 1
                
                if retry_count < max_retries:
                    await asyncio.sleep(2 ** retry_count)  # 지수 백오프
                else:
                    # 최대 재시도 횟수 초과 시 DLQ로 이동
                    for chat_data in chat_data_list:
                        await self._move_to_dlq(chat_data)
                    return False
        
        return False
    
    async def _process_single_chat(self, chat_data: Dict, max_retries: int) -> bool:
        """단일 챗 저장 처리"""
        
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                storage_service = ChatStorageService()
                
                # 타임스탬프 추가
                from datetime import datetime
                chat_data["timestamp"] = datetime.now().isoformat()
                
                success = await storage_service.save_chat(
                    userId=chat_data["userId"],
                    question=chat_data["question"],
                    answer=chat_data["answer"],
                    messages=chat_data.get("messages"),
                    related_stocks=chat_data.get("related_stocks"),
                )
                
                # HTTP 클라이언트는 싱글톤이므로 close 불필요
                
                if success:
                    logger.info(f"Chat stored for user: {chat_data['userId']}")
                    return True
                else:
                    logger.warning(f"Failed to store chat for user: {chat_data['userId']}")
                    retry_count += 1
                    
                    if retry_count < max_retries:
                        logger.info(f"Retrying chat storage (attempt {retry_count + 1}/{max_retries})")
                        await asyncio.sleep(2 ** retry_count)  # 지수 백오프
                    else:
                        # 최대 재시도 횟수 초과 시 DLQ로 이동
                        await self._move_to_dlq(chat_data)
                        return False
                        
            except Exception as e:
                logger.error(f"Error processing chat storage (attempt {retry_count + 1}): {e}")
                retry_count += 1
                
                if retry_count < max_retries:
                    await asyncio.sleep(2 ** retry_count)  # 지수 백오프
                else:
                    # 최대 재시도 횟수 초과 시 DLQ로 이동
                    await self._move_to_dlq(chat_data)
                    return False
        
        return False
    
    async def _move_to_dlq(self, chat_data: Dict):
        """Dead Letter Queue로 이동 (파일 시스템 또는 Redis)"""
        try:
            from src.services.dlq_handler import DLQHandler
            
            # EnvConfig에서 설정 읽기 (일관성 유지)
            dlq_handler = DLQHandler()
            chat_data["failed_at"] = chat_data.get("timestamp")
            chat_data["retry_count"] = 3
            
            success = await dlq_handler.add_to_dlq(self.QUEUE_NAME, chat_data)
            if success:
                logger.error(f"Chat storage moved to DLQ: {chat_data.get('userId')}")
            else:
                logger.error(f"Failed to move to DLQ: {chat_data.get('userId')}")
        except Exception as e:
            logger.error(f"Failed to move to DLQ: {e}")
    
    async def run(
        self,
        max_iterations: Optional[int] = None,
        batch_size: int = 1,
    ):
        """
        워커 실행 (무한 루프 또는 최대 반복 횟수, 배치 처리 지원)
        
        Args:
            max_iterations: 최대 반복 횟수 (None이면 무한)
            batch_size: 배치 크기 (대규모 처리 최적화)
        """
        self.running = True
        iteration = 0
        consecutive_errors = 0
        max_errors = 10
        
        logger.info(f"Chat storage worker started (batch_size={batch_size})")
        
        while self.running:
            try:
                success = await self.process_chat_storage(batch_size=batch_size)
                
                if success:
                    consecutive_errors = 0
                else:
                    # 타임아웃은 정상 (큐가 비어있음)
                    consecutive_errors = 0
                
                iteration += 1
                if max_iterations and iteration >= max_iterations:
                    logger.info(f"Worker reached max iterations: {max_iterations}")
                    break
                    
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Worker error (consecutive: {consecutive_errors}): {e}")
                
                if consecutive_errors >= max_errors:
                    logger.error(f"Too many consecutive errors ({max_errors}), stopping worker")
                    break
                
                # 에러 시 잠시 대기
                await asyncio.sleep(1)
        
        self.running = False
        logger.info("Chat storage worker stopped")
    
    def stop(self):
        """워커 중지"""
        self.running = False


async def main():
    """워커 메인 함수 (독립 실행용)"""
    worker = ChatStorageWorker()
    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
        worker.stop()


if __name__ == "__main__":
    asyncio.run(main())

