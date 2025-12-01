"""
Rate Limiter for FUTU API

实现令牌桶算法，限制API调用频率。
FUTU API限制：30秒内最多60次请求。
"""
import time
from threading import Lock
from typing import Optional


class TokenBucketRateLimiter:
    """
    令牌桶算法的Rate Limiter
    
    规则：30秒内最多60次请求
    即：每30秒补充60个令牌，或每秒补充2个令牌
    """
    
    def __init__(self, max_tokens: int = 60, refill_period: float = 30.0):
        """
        初始化Rate Limiter
        
        Args:
            max_tokens: 最大令牌数（默认60）
            refill_period: 令牌补充周期（秒，默认30秒）
        """
        self.max_tokens = max_tokens
        self.refill_period = refill_period
        self.tokens = max_tokens  # 当前令牌数
        self.last_refill_time = time.time()  # 上次补充令牌的时间
        self.lock = Lock()  # 线程锁，确保线程安全
    
    def _refill_tokens(self) -> None:
        """
        根据时间补充令牌
        """
        current_time = time.time()
        elapsed = current_time - self.last_refill_time
        
        if elapsed >= self.refill_period:
            # 如果超过一个周期，直接补充到最大值
            self.tokens = self.max_tokens
            self.last_refill_time = current_time
        else:
            # 按比例补充令牌
            tokens_to_add = (elapsed / self.refill_period) * self.max_tokens
            self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
            self.last_refill_time = current_time
    
    def acquire(self, tokens: int = 1, wait: bool = True) -> bool:
        """
        获取令牌
        
        Args:
            tokens: 需要的令牌数（默认1）
            wait: 如果令牌不足，是否等待（默认True）
        
        Returns:
            如果成功获取令牌返回True，否则返回False
        """
        with self.lock:
            # 先补充令牌
            self._refill_tokens()
            
            # 检查是否有足够的令牌
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            # 令牌不足
            if not wait:
                return False
            
            # 计算需要等待的时间
            tokens_needed = tokens - self.tokens
            wait_time = (tokens_needed / self.max_tokens) * self.refill_period
            
            # 等待并补充令牌
            time.sleep(wait_time)
            
            # 再次补充令牌（等待期间可能已经补充了一些）
            self._refill_tokens()
            
            # 再次检查
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            # 如果还是不够（理论上不应该发生），等待一个完整周期
            time.sleep(self.refill_period)
            self.tokens = self.max_tokens
            self.tokens -= tokens
            return True
    
    def try_acquire(self, tokens: int = 1) -> bool:
        """
        尝试获取令牌，不等待
        
        Args:
            tokens: 需要的令牌数（默认1）
        
        Returns:
            如果成功获取令牌返回True，否则返回False
        """
        return self.acquire(tokens, wait=False)
    
    def get_available_tokens(self) -> float:
        """
        获取当前可用的令牌数
        
        Returns:
            当前可用的令牌数
        """
        with self.lock:
            self._refill_tokens()
            return self.tokens
    
    def reset(self) -> None:
        """
        重置Rate Limiter（补充到最大令牌数）
        """
        with self.lock:
            self.tokens = self.max_tokens
            self.last_refill_time = time.time()


# 全局Rate Limiter实例（用于FUTU API）
_futu_rate_limiter: Optional[TokenBucketRateLimiter] = None


def get_futu_rate_limiter() -> TokenBucketRateLimiter:
    """
    获取FUTU API的全局Rate Limiter实例
    
    Returns:
        TokenBucketRateLimiter实例
    """
    global _futu_rate_limiter
    if _futu_rate_limiter is None:
        _futu_rate_limiter = TokenBucketRateLimiter(max_tokens=60, refill_period=30.0)
    return _futu_rate_limiter

