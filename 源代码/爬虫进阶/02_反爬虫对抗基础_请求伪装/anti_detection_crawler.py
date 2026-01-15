# -*- coding: utf-8 -*-
# @Desc: 完整的反检测爬虫示例
# 结合 UA 轮换、请求头伪装、速率控制的实战案例

import asyncio
import random
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from loguru import logger

# 导入本章的模块
from ua_rotator import UARotator
from headers_builder import HeadersBuilder
from rate_limiter import CompositeRateLimiter, RateLimitConfig

# 尝试导入 curl_cffi，如果不可用则使用 httpx
try:
    from curl_cffi.requests import AsyncSession
    USE_CURL_CFFI = True
    logger.info("使用 curl_cffi 作为 HTTP 客户端（支持 TLS 指纹模拟）")
except ImportError:
    import httpx
    USE_CURL_CFFI = False
    logger.info("使用 httpx 作为 HTTP 客户端")


@dataclass
class CrawlerConfig:
    """爬虫配置"""
    # 目标站点
    base_url: str = "https://httpbin.org"

    # 速率限制
    requests_per_second: float = 2.0
    max_concurrent: int = 3
    min_delay: float = 0.5
    max_delay: float = 1.5

    # 请求配置
    timeout: int = 30
    max_retries: int = 3

    # curl_cffi 配置
    browser_type: str = "chrome120"


class AntiDetectionCrawler:
    """
    反检测爬虫

    特性：
    - User-Agent 随机轮换
    - 完整的请求头伪装
    - TLS 指纹模拟（使用 curl_cffi）
    - 智能速率控制
    - 优雅的重试机制
    """

    def __init__(self, config: Optional[CrawlerConfig] = None):
        """
        初始化爬虫

        Args:
            config: 爬虫配置
        """
        self.config = config or CrawlerConfig()

        # 初始化组件
        self.ua_rotator = UARotator()
        self.headers_builder = HeadersBuilder(self.ua_rotator)
        self.rate_limiter = CompositeRateLimiter(
            RateLimitConfig(
                requests_per_second=self.config.requests_per_second,
                max_concurrent=self.config.max_concurrent,
                min_delay=self.config.min_delay,
                max_delay=self.config.max_delay
            )
        )

        self._session = None
        self._stats = {
            "total_requests": 0,
            "success_requests": 0,
            "failed_requests": 0
        }

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def start(self):
        """启动爬虫"""
        if USE_CURL_CFFI:
            self._session = AsyncSession(
                impersonate=self.config.browser_type,
                timeout=self.config.timeout
            )
        else:
            self._session = httpx.AsyncClient(timeout=self.config.timeout)

        logger.info(f"爬虫启动 - 目标: {self.config.base_url}")

    async def close(self):
        """关闭爬虫"""
        if self._session:
            if USE_CURL_CFFI:
                await self._session.close()
            else:
                await self._session.aclose()
            self._session = None

        logger.info(f"爬虫关闭 - 统计: {self._stats}")

    async def fetch(
        self,
        url: str,
        referer: Optional[str] = None,
        is_api: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        获取页面/API 数据

        Args:
            url: 目标 URL
            referer: Referer 地址
            is_api: 是否是 API 请求

        Returns:
            响应数据或 None
        """
        async with self.rate_limiter:
            self._stats["total_requests"] += 1

            # 构建请求头
            if is_api:
                headers = self.headers_builder.build_api_headers(
                    referer=referer or self.config.base_url
                )
            else:
                headers = self.headers_builder.build_page_headers(referer=referer)

            # 重试逻辑
            for attempt in range(self.config.max_retries):
                try:
                    logger.debug(f"请求: {url} (尝试 {attempt + 1}/{self.config.max_retries})")

                    response = await self._session.get(url, headers=headers)

                    # 检查状态码
                    if USE_CURL_CFFI:
                        status_code = response.status_code
                        if status_code >= 400:
                            raise Exception(f"HTTP {status_code}")
                        data = response.json() if is_api else {"text": response.text}
                    else:
                        response.raise_for_status()
                        data = response.json() if is_api else {"text": response.text}

                    self._stats["success_requests"] += 1
                    logger.info(f"成功: {url}")
                    return data

                except Exception as e:
                    logger.warning(f"请求失败: {url} - {e}")
                    if attempt < self.config.max_retries - 1:
                        # 等待后重试
                        await asyncio.sleep(random.uniform(1, 3))
                    else:
                        self._stats["failed_requests"] += 1
                        logger.error(f"最终失败: {url}")
                        return None

    async def fetch_batch(
        self,
        urls: List[str],
        referer: Optional[str] = None
    ) -> List[Optional[Dict[str, Any]]]:
        """
        批量获取数据

        Args:
            urls: URL 列表
            referer: Referer 地址

        Returns:
            结果列表
        """
        tasks = [self.fetch(url, referer) for url in urls]
        return await asyncio.gather(*tasks)


async def demo():
    """演示反检测爬虫"""
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="DEBUG"
    )

    print("=" * 60)
    print("反检测爬虫演示")
    print("=" * 60)

    config = CrawlerConfig(
        base_url="https://httpbin.org",
        requests_per_second=1.0,
        max_concurrent=2,
        min_delay=0.5,
        max_delay=1.0
    )

    async with AntiDetectionCrawler(config) as crawler:
        # 测试 1: 检查请求头
        print("\n--- 测试 1: 检查请求头 ---")
        result = await crawler.fetch(
            "https://httpbin.org/headers",
            is_api=True
        )
        if result:
            headers = result.get("headers", {})
            print(f"User-Agent: {headers.get('User-Agent', 'N/A')[:60]}...")
            print(f"Accept: {headers.get('Accept', 'N/A')[:40]}...")

        # 测试 2: 检查 IP
        print("\n--- 测试 2: 检查 IP ---")
        result = await crawler.fetch(
            "https://httpbin.org/ip",
            is_api=True
        )
        if result:
            print(f"Origin IP: {result.get('origin', 'N/A')}")

        # 测试 3: 批量请求（测试速率控制）
        print("\n--- 测试 3: 批量请求（速率控制） ---")
        urls = [
            "https://httpbin.org/get?id=1",
            "https://httpbin.org/get?id=2",
            "https://httpbin.org/get?id=3",
            "https://httpbin.org/get?id=4",
        ]
        results = await crawler.fetch_batch(urls)
        print(f"批量请求完成: 成功 {sum(1 for r in results if r)}/{len(urls)}")

    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())
