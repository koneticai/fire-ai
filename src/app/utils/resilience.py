from typing import Callable, Any
import asyncio
from functools import wraps

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == "OPEN":
            if (asyncio.get_event_loop().time() - self.last_failure_time 
                > self.recovery_timeout):
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = asyncio.get_event_loop().time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            raise e

def with_circuit_breaker(breaker: CircuitBreaker):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator

# Exponential backoff retry
async def retry_with_backoff(
    func: Callable,
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 300.0
):
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            
            delay = min(base_delay * (2 ** attempt), max_delay)
            await asyncio.sleep(delay)