"""
Redis Message Queue
Redis 기반 메시지 큐 (비동기 작업 처리)
대규모 처리를 위한 개선: 배치 처리, 백프레셔, 압축 지원
"""

from typing import Dict, Optional, Any, List
import json
import gzip
import base64
from loguru import logger
from src.config.managers import get_redis_manager
from src.config.env import EnvConfig
from src.interfaces.message_queue import IMessageQueue


class RedisMessageQueue(IMessageQueue):
    """Redis 기반 메시지 큐 (대규모 처리 최적화)"""
    
    def __init__(
        self,
        max_queue_length: Optional[int] = None,  # 백프레셔: 최대 큐 길이
        enable_compression: Optional[bool] = None,  # 메시지 압축 (메모리 효율)
        compression_threshold: Optional[int] = None,  # 압축 임계값 (1KB 이상)
    ):
        """
        Args:
            max_queue_length: 최대 큐 길이 (None이면 EnvConfig에서 읽음)
            enable_compression: 메시지 압축 활성화 (None이면 EnvConfig에서 읽음)
            compression_threshold: 압축 임계값 (None이면 EnvConfig에서 읽음)
        """
        self.redis_manager = get_redis_manager()
        # 환경 변수에서 설정 읽기 (일관성 유지)
        self.max_queue_length = max_queue_length if max_queue_length is not None else EnvConfig.MAX_QUEUE_LENGTH
        self.enable_compression = enable_compression if enable_compression is not None else EnvConfig.ENABLE_MESSAGE_COMPRESSION
        self.compression_threshold = compression_threshold if compression_threshold is not None else EnvConfig.MESSAGE_COMPRESSION_THRESHOLD
    
    def _get_queue_key(self, queue_name: str) -> str:
        """큐 키 생성"""
        return f"queue:{queue_name}"
    
    def _compress_message(self, message: str) -> str:
        """메시지 압축 (큰 메시지만)"""
        if not self.enable_compression or len(message.encode('utf-8')) < self.compression_threshold:
            return message
        
        try:
            compressed = gzip.compress(message.encode('utf-8'))
            encoded = base64.b64encode(compressed).decode('utf-8')
            return f"__compressed__:{encoded}"
        except Exception as e:
            logger.warning(f"Compression failed: {e}, using uncompressed")
            return message
    
    def _decompress_message(self, message: str) -> str:
        """메시지 압축 해제"""
        if not message.startswith("__compressed__:"):
            return message
        
        try:
            encoded = message.replace("__compressed__:", "")
            compressed = base64.b64decode(encoded)
            decompressed = gzip.decompress(compressed).decode('utf-8')
            return decompressed
        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            return message
    
    async def enqueue(self, queue_name: str, data: Dict[str, Any]) -> bool:
        """
        큐에 메시지 추가 (백프레셔 지원)
        
        Args:
            queue_name: 큐 이름
            data: 메시지 데이터
            
        Returns:
            성공 여부
        """
        if not self.redis_manager.is_available():
            logger.warning(f"Redis unavailable, message not queued: {queue_name}")
            return False
        
        try:
            client = self.redis_manager.get_client()
            if client:
                queue_key = self._get_queue_key(queue_name)
                
                # 백프레셔: 큐 길이 확인
                current_length = client.llen(queue_key)
                if current_length >= self.max_queue_length:
                    logger.warning(
                        f"Queue {queue_name} is full ({current_length}/{self.max_queue_length}), "
                        "message rejected (backpressure)"
                    )
                    return False
                
                message = json.dumps(data, ensure_ascii=False)
                compressed_message = self._compress_message(message)
                client.lpush(queue_key, compressed_message)
                
                logger.debug(
                    f"Message enqueued: {queue_name} "
                    f"(queue length: {client.llen(queue_key)}, "
                    f"compressed: {compressed_message != message})"
                )
                return True
        except Exception as e:
            logger.error(f"Failed to enqueue message to {queue_name}: {e}")
        
        return False
    
    async def enqueue_batch(self, queue_name: str, data_list: List[Dict[str, Any]]) -> int:
        """
        배치로 메시지 추가 (대규모 처리 최적화)
        
        Args:
            queue_name: 큐 이름
            data_list: 메시지 데이터 리스트
            
        Returns:
            성공적으로 추가된 메시지 수
        """
        if not self.redis_manager.is_available():
            logger.warning(f"Redis unavailable, batch not queued: {queue_name}")
            return 0
        
        try:
            client = self.redis_manager.get_client()
            if client:
                queue_key = self._get_queue_key(queue_name)
                current_length = client.llen(queue_key)
                
                # 배치 크기 제한 (백프레셔)
                available_slots = self.max_queue_length - current_length
                if available_slots <= 0:
                    logger.warning(f"Queue {queue_name} is full, batch rejected")
                    return 0
                
                # 사용 가능한 슬롯만큼만 처리
                batch_size = min(len(data_list), available_slots)
                messages = []
                
                for data in data_list[:batch_size]:
                    message = json.dumps(data, ensure_ascii=False)
                    compressed_message = self._compress_message(message)
                    messages.append(compressed_message)
                
                if messages:
                    # 파이프라인으로 배치 추가 (성능 최적화)
                    pipe = client.pipeline()
                    for msg in messages:
                        pipe.lpush(queue_key, msg)
                    pipe.execute()
                    
                    logger.info(
                        f"Batch enqueued: {queue_name} "
                        f"({batch_size}/{len(data_list)} messages, "
                        f"queue length: {client.llen(queue_key)})"
                    )
                    return batch_size
        except Exception as e:
            logger.error(f"Failed to enqueue batch to {queue_name}: {e}")
        
        return 0
    
    async def dequeue(self, queue_name: str, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """
        큐에서 메시지 가져오기 (블로킹, 압축 해제)
        
        Args:
            queue_name: 큐 이름
            timeout: 대기 시간 (초)
            
        Returns:
            메시지 데이터 또는 None
        """
        if not self.redis_manager.is_available():
            return None
        
        try:
            client = self.redis_manager.get_client()
            if client:
                queue_key = self._get_queue_key(queue_name)
                result = client.brpop(queue_key, timeout=timeout)
                if result:
                    _, message = result
                    # 압축 해제
                    decompressed = self._decompress_message(message)
                    data = json.loads(decompressed)
                    logger.debug(f"Message dequeued: {queue_name}")
                    return data
        except Exception as e:
            logger.error(f"Failed to dequeue message from {queue_name}: {e}")
        
        return None
    
    async def dequeue_batch(self, queue_name: str, batch_size: int = 10, timeout: int = 5) -> List[Dict[str, Any]]:
        """
        배치로 메시지 가져오기 (대규모 처리 최적화)
        
        주의: FIFO 순서 보장을 위해 lrange + ltrim 사용 (원자성 보장)
        
        Args:
            queue_name: 큐 이름
            batch_size: 배치 크기
            timeout: 대기 시간 (초, 현재는 사용하지 않음)
            
        Returns:
            메시지 데이터 리스트
        """
        if not self.redis_manager.is_available():
            return []
        
        try:
            client = self.redis_manager.get_client()
            if client:
                queue_key = self._get_queue_key(queue_name)
                
                # Lua 스크립트로 원자적으로 배치 가져오기 (FIFO 보장)
                # 실무에서 많이 사용하는 패턴: 원자성 보장을 위한 Lua 스크립트
                lua_script = """
                local queue_key = KEYS[1]
                local batch_size = tonumber(ARGV[1])
                local queue_len = redis.call('llen', queue_key)
                local actual_size = math.min(batch_size, queue_len)
                if actual_size == 0 then
                    return {}
                end
                local messages = redis.call('lrange', queue_key, -actual_size, -1)
                redis.call('ltrim', queue_key, 0, -(actual_size + 1))
                return messages
                """
                
                # Lua 스크립트 실행 (원자성 보장)
                try:
                    messages_raw = client.eval(lua_script, 1, queue_key, batch_size)
                except Exception as lua_error:
                    logger.warning(f"Lua script failed, using fallback: {lua_error}")
                    return await self._fallback_dequeue_batch(queue_name, batch_size, timeout)
                
                if not messages_raw:
                    return []
                
                # 메시지 파싱 및 압축 해제
                messages = []
                for message in messages_raw:
                    if message:
                        decompressed = self._decompress_message(message)
                        data = json.loads(decompressed)
                        messages.append(data)
                
                # 역순으로 반환 (FIFO 순서 유지)
                messages.reverse()
                
                if messages:
                    logger.debug(f"Batch dequeued: {queue_name} ({len(messages)} messages)")
                
                return messages
        except Exception as e:
            logger.error(f"Failed to dequeue batch from {queue_name}: {e}")
            # Lua 스크립트 실패 시 폴백: 단일 dequeue 여러 번 호출
            return await self._fallback_dequeue_batch(queue_name, batch_size, timeout)
        
        return []
    
    async def _fallback_dequeue_batch(
        self, queue_name: str, batch_size: int, timeout: int
    ) -> List[Dict[str, Any]]:
        """폴백: 단일 dequeue를 여러 번 호출"""
        messages = []
        for _ in range(batch_size):
            message = await self.dequeue(queue_name, timeout=1)
            if message:
                messages.append(message)
            else:
                break
        return messages
    
    def get_queue_length(self, queue_name: str) -> int:
        """
        큐 길이 조회
        
        Args:
            queue_name: 큐 이름
            
        Returns:
            큐 길이
        """
        if not self.redis_manager.is_available():
            return 0
        
        try:
            client = self.redis_manager.get_client()
            if client:
                queue_key = self._get_queue_key(queue_name)
                return client.llen(queue_key)
        except Exception as e:
            logger.error(f"Failed to get queue length for {queue_name}: {e}")
        
        return 0
    
    def clear_queue(self, queue_name: str) -> bool:
        """
        큐 비우기
        
        Args:
            queue_name: 큐 이름
            
        Returns:
            성공 여부
        """
        if not self.redis_manager.is_available():
            return False
        
        try:
            client = self.redis_manager.get_client()
            if client:
                queue_key = self._get_queue_key(queue_name)
                client.delete(queue_key)
                logger.info(f"Queue cleared: {queue_name}")
                return True
        except Exception as e:
            logger.error(f"Failed to clear queue {queue_name}: {e}")
        
        return False

