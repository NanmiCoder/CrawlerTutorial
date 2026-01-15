# -*- coding: utf-8 -*-
# @Desc: 速率限制器实现

import asyncio
import time
import random
from typing import Optional, List, Any, Callable, Coroutine
from dataclasses import dataclass


class TokenBucket:
    """
    令牌桶限速器

    工作原理：
    - 桶有固定容量（最大令牌数）
    - 以固定速率向桶中添加令牌
    - 每次请求消耗一个令牌
    - 桶空时请求需要等待

    适用场景：
    - 需要精确控制平均请求速率
    - 允许一定程度的突发请求
    """

    def __init__(
        self,
        rate: float,
        capacity: Optional[int] = None
    ):
        """
        初始化令牌桶

        Args:
            rate: 每秒添加的令牌数（即每秒最多请求数）
            capacity: 桶容量，默认等于 rate（允许的最大突发数）
        """
        self.rate = rate
        self.capacity = capacity if capacity is not None else int(rate)
        self.tokens = float(self.capacity)  # 初始令牌数
        self.last_time = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> float:
        """
        获取令牌

        Args:
            tokens: 需要的令牌数

        Returns:
            实际等待的时间（秒）
        """
        async with self._lock:
            now = time.monotonic()

            # 计算从上次到现在应该添加的令牌数
            elapsed = now - self.last_time
            self.tokens = min(
                float(self.capacity),
                self.tokens + elapsed * self.rate
            )
            self.last_time = now

            # 如果令牌不足，计算需要等待的时间
            wait_time = 0.0
            if self.tokens < tokens:
                wait_time = (tokens - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= tokens

            return wait_time

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, *args):
        pass


class RandomDelayLimiter:
    """
    随机延迟限速器

    在每次请求后添加随机延迟，模拟人类行为
    """

    def __init__(
        self,
        min_delay: float = 1.0,
        max_delay: float = 3.0
    ):
        """
        初始化随机延迟限速器

        Args:
            min_delay: 最小延迟（秒）
            max_delay: 最大延迟（秒）
        """
        self.min_delay = min_delay
        self.max_delay = max_delay

    async def wait(self) -> float:
        """
        等待随机时间

        Returns:
            实际等待的时间（秒）
        """
        delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(delay)
        return delay

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.wait()


class AdaptiveRateLimiter:
    """
    自适应速率限制器

    根据响应情况自动调整请求速率：
    - 正常响应：逐渐提升速率
    - 被限制/错误：降低速率
    """

    def __init__(
        self,
        initial_rate: float = 1.0,
        min_rate: float = 0.1,
        max_rate: float = 5.0,
        increase_factor: float = 1.1,
        decrease_factor: float = 0.5
    ):
        """
        初始化自适应限速器

        Args:
            initial_rate: 初始速率（请求/秒）
            min_rate: 最小速率
            max_rate: 最大速率
            increase_factor: 成功时的速率增长因子
            decrease_factor: 失败时的速率降低因子
        """
        self.current_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.increase_factor = increase_factor
        self.decrease_factor = decrease_factor
        self._bucket = TokenBucket(rate=initial_rate)
        self._lock = asyncio.Lock()

    async def acquire(self) -> float:
        """获取令牌"""
        return await self._bucket.acquire()

    async def report_success(self):
        """报告请求成功，提升速率"""
        async with self._lock:
            new_rate = min(
                self.current_rate * self.increase_factor,
                self.max_rate
            )
            if new_rate != self.current_rate:
                self.current_rate = new_rate
                self._bucket = TokenBucket(rate=self.current_rate)

    async def report_failure(self):
        """报告请求失败/被限制，降低速率"""
        async with self._lock:
            new_rate = max(
                self.current_rate * self.decrease_factor,
                self.min_rate
            )
            if new_rate != self.current_rate:
                self.current_rate = new_rate
                self._bucket = TokenBucket(rate=self.current_rate)
                # 失败后额外等待
                await asyncio.sleep(2.0)

    @property
    def rate(self) -> float:
        """当前速率"""
        return self.current_rate


class ConcurrencyLimiter:
    """
    并发限制器

    限制同时进行的请求数量
    """

    def __init__(self, max_concurrent: int = 10):
        """
        初始化并发限制器

        Args:
            max_concurrent: 最大并发数
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._active_count = 0
        self._lock = asyncio.Lock()

    async def acquire(self):
        """获取并发许可"""
        await self.semaphore.acquire()
        async with self._lock:
            self._active_count += 1

    async def release(self):
        """释放并发许可"""
        self.semaphore.release()
        async with self._lock:
            self._active_count -= 1

    @property
    def active_count(self) -> int:
        """当前活跃请求数"""
        return self._active_count

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, *args):
        await self.release()


@dataclass
class RateLimitConfig:
    """速率限制配置"""
    requests_per_second: float = 2.0
    max_concurrent: int = 5
    min_delay: float = 0.5
    max_delay: float = 2.0


class CompositeRateLimiter:
    """
    组合速率限制器

    结合多种限速策略：
    - 令牌桶控制平均速率
    - 并发限制控制同时请求数
    - 随机延迟模拟人类行为
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        初始化组合限速器

        Args:
            config: 速率限制配置
        """
        self.config = config or RateLimitConfig()
        self.token_bucket = TokenBucket(rate=self.config.requests_per_second)
        self.concurrency_limiter = ConcurrencyLimiter(self.config.max_concurrent)
        self.delay_limiter = RandomDelayLimiter(
            self.config.min_delay,
            self.config.max_delay
        )

    async def __aenter__(self):
        """进入限速上下文"""
        # 先获取并发许可
        await self.concurrency_limiter.acquire()
        # 再获取令牌
        await self.token_bucket.acquire()
        return self

    async def __aexit__(self, *args):
        """退出限速上下文"""
        # 随机延迟
        await self.delay_limiter.wait()
        # 释放并发许可
        await self.concurrency_limiter.release()


# ==================== 演示代码 ====================

async def demo_token_bucket():
    """演示令牌桶限速器"""
    print("\n" + "=" * 50)
    print("1. 令牌桶限速器演示")
    print("=" * 50)

    # 每秒 2 个请求
    limiter = TokenBucket(rate=2.0)

    start_time = time.time()
    for i in range(6):
        async with limiter:
            elapsed = time.time() - start_time
            print(f"   请求 {i+1}: 时间 {elapsed:.2f}s")


async def demo_random_delay():
    """演示随机延迟限速器"""
    print("\n" + "=" * 50)
    print("2. 随机延迟限速器演示")
    print("=" * 50)

    limiter = RandomDelayLimiter(min_delay=0.5, max_delay=1.5)

    for i in range(3):
        print(f"   请求 {i+1}...")
        async with limiter:
            pass  # 请求完成后自动延迟


async def demo_concurrency():
    """演示并发限制器"""
    print("\n" + "=" * 50)
    print("3. 并发限制器演示")
    print("=" * 50)

    limiter = ConcurrencyLimiter(max_concurrent=3)

    async def task(task_id: int):
        async with limiter:
            print(f"   任务 {task_id} 开始, 当前并发: {limiter.active_count}")
            await asyncio.sleep(0.5)
            print(f"   任务 {task_id} 完成")

    # 同时启动 6 个任务，但最多 3 个并发
    tasks = [task(i) for i in range(6)]
    await asyncio.gather(*tasks)


async def demo_composite():
    """演示组合限速器"""
    print("\n" + "=" * 50)
    print("4. 组合限速器演示")
    print("=" * 50)

    config = RateLimitConfig(
        requests_per_second=2.0,
        max_concurrent=2,
        min_delay=0.3,
        max_delay=0.8
    )
    limiter = CompositeRateLimiter(config)

    start_time = time.time()

    async def request(req_id: int):
        async with limiter:
            elapsed = time.time() - start_time
            print(f"   请求 {req_id}: 时间 {elapsed:.2f}s, 并发: {limiter.concurrency_limiter.active_count}")

    tasks = [request(i) for i in range(5)]
    await asyncio.gather(*tasks)


async def main():
    """主函数"""
    print("=" * 50)
    print("速率限制器演示")
    print("=" * 50)

    await demo_token_bucket()
    await demo_random_delay()
    await demo_concurrency()
    await demo_composite()

    print("\n" + "=" * 50)
    print("演示完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
