import asyncio
import time


class TokenBucketRateLimiter:
    """Async token-bucket rate limiter with deterministic (no-jitter) behavior.

    Uses ``time.monotonic()`` for drift-free wall-clock timing and
    ``asyncio.Lock`` so concurrent coroutines see a consistent token count.
    """

    def __init__(self, rate_per_second: float, burst: int = 1) -> None:
        self.rate_per_second = rate_per_second
        self.burst = burst
        self._tokens = float(burst)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Block until a token is available, then consume one."""
        async with self._lock:
            self._refill()
            while self._tokens < 1.0:
                wait = (1.0 - self._tokens) / self.rate_per_second
                await asyncio.sleep(wait)
                self._refill()
            self._tokens -= 1.0

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.burst, self._tokens + elapsed * self.rate_per_second)
        self._last_refill = now


arxiv_rate_limiter = TokenBucketRateLimiter(rate_per_second=1 / 3, burst=1)
