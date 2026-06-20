import time

from app.utils.rate_limiters import TokenBucketRateLimiter, arxiv_rate_limiter


class TestTokenBucketRateLimiter:

    async def test_arxiv_3s_gap_enforced(self) -> None:
        """Two sequential acquire() calls must take >= 3.0 s wall-clock."""
        limiter = TokenBucketRateLimiter(rate_per_second=1 / 3, burst=1)

        t0 = time.monotonic()
        await limiter.acquire()
        await limiter.acquire()
        elapsed = time.monotonic() - t0

        assert elapsed >= 3.0, f"Expected >= 3.0 s gap, got {elapsed:.3f} s"

    async def test_burst_of_one(self) -> None:
        """First acquire() returns immediately; second waits."""
        limiter = TokenBucketRateLimiter(rate_per_second=1 / 3, burst=1)

        t0 = time.monotonic()
        await limiter.acquire()
        fast_elapsed = time.monotonic() - t0

        assert fast_elapsed < 0.5, (
            f"First acquire() should be near-instant, took {fast_elapsed:.3f} s"
        )

        t1 = time.monotonic()
        await limiter.acquire()
        slow_elapsed = time.monotonic() - t1

        assert slow_elapsed >= 3.0, (
            f"Second acquire() should wait >= 3.0 s, took {slow_elapsed:.3f} s"
        )

    async def test_module_singleton_exists(self) -> None:
        assert arxiv_rate_limiter is not None
        assert arxiv_rate_limiter.rate_per_second == 1 / 3
        assert arxiv_rate_limiter.burst == 1
