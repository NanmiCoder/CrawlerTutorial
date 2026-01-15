# -*- coding: utf-8 -*-
# @Desc: 代理池使用演示
# 展示完整的代理池使用流程

import asyncio
from typing import List, Optional
from loguru import logger
import httpx

from proxy_pool.base import ProxyInfo, ProxyProtocol, IProxyFetcher
from proxy_pool.checker import ProxyChecker
from proxy_pool.pool import ProxyPool


class MockProxyFetcher(IProxyFetcher):
    """
    模拟代理获取器

    用于演示，实际使用时替换为真实的代理获取器
    """

    # 模拟的代理列表（这些是公开的测试代理，可能不可用）
    MOCK_PROXIES = [
        # 这些只是示例，实际运行时可能不可用
        ("103.152.112.157", 80),
        ("203.142.78.109", 8080),
        ("103.83.232.225", 80),
        ("190.61.88.147", 8080),
        ("45.167.126.108", 3128),
    ]

    async def fetch(self) -> List[ProxyInfo]:
        """获取模拟代理"""
        proxies = []
        for host, port in self.MOCK_PROXIES:
            proxies.append(ProxyInfo(
                host=host,
                port=port,
                protocol=ProxyProtocol.HTTP
            ))
        logger.info(f"获取到 {len(proxies)} 个模拟代理")
        return proxies


class ProxiedCrawler:
    """
    使用代理池的爬虫示例
    """

    def __init__(self, proxy_pool: ProxyPool):
        self.proxy_pool = proxy_pool
        self.success_count = 0
        self.fail_count = 0

    async def fetch(self, url: str) -> Optional[str]:
        """
        使用代理获取页面

        Args:
            url: 目标 URL

        Returns:
            页面内容或 None
        """
        # 获取代理
        proxy = await self.proxy_pool.get_proxy()

        if not proxy:
            logger.warning("无可用代理，直接请求")
            proxy_url = None
        else:
            proxy_url = proxy.url
            logger.info(f"使用代理: {proxy.host}:{proxy.port}")

        try:
            async with httpx.AsyncClient(
                proxies=proxy_url,
                timeout=15,
                verify=False
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

                # 报告成功
                if proxy:
                    await self.proxy_pool.return_proxy(proxy, success=True)
                self.success_count += 1

                return response.text

        except Exception as e:
            logger.warning(f"请求失败: {e}")
            # 报告失败
            if proxy:
                await self.proxy_pool.return_proxy(proxy, success=False)
            self.fail_count += 1
            return None


async def demo_proxy_pool():
    """演示代理池基本功能"""
    print("=" * 60)
    print("代理池基本功能演示")
    print("=" * 60)

    # 创建组件
    fetcher = MockProxyFetcher()
    checker = ProxyChecker(timeout=10)

    # 创建代理池
    pool = ProxyPool(
        fetcher=fetcher,
        checker=checker,
        min_proxies=2,
        max_proxies=10,
        check_interval=60
    )

    async with pool:
        print(f"\n代理池大小: {pool.size}")
        print(f"统计信息: {pool.get_stats()}")

        # 获取代理
        print("\n获取代理测试:")
        for i in range(3):
            proxy = await pool.get_proxy()
            if proxy:
                print(f"  {i+1}. {proxy.host}:{proxy.port} (评分: {proxy.score:.2f})")
                # 模拟使用结果
                await pool.return_proxy(proxy, success=(i % 2 == 0))
            else:
                print(f"  {i+1}. 无可用代理")

        print(f"\n最终统计: {pool.get_stats()}")


async def demo_proxied_crawler():
    """演示集成代理池的爬虫"""
    print("\n" + "=" * 60)
    print("代理爬虫演示")
    print("=" * 60)

    # 创建代理池
    pool = ProxyPool(
        fetcher=MockProxyFetcher(),
        checker=ProxyChecker(timeout=10),
        min_proxies=2,
        max_proxies=10
    )

    async with pool:
        # 创建爬虫
        crawler = ProxiedCrawler(pool)

        # 测试请求
        urls = [
            "https://httpbin.org/ip",
            "https://httpbin.org/headers",
        ]

        print("\n开始爬取测试:")
        for url in urls:
            content = await crawler.fetch(url)
            if content:
                print(f"  ✓ {url[:40]}... ({len(content)} bytes)")
            else:
                print(f"  ✗ {url[:40]}... 失败")

        print(f"\n爬取统计: 成功 {crawler.success_count}, 失败 {crawler.fail_count}")


async def demo_manual_proxy():
    """演示手动使用代理"""
    print("\n" + "=" * 60)
    print("手动代理使用演示")
    print("=" * 60)

    # 直接使用 httpx 设置代理
    proxy_url = "http://127.0.0.1:7890"  # 替换为你的代理地址

    print(f"\n使用代理: {proxy_url}")
    print("(如果代理不可用，请求会失败)")

    try:
        async with httpx.AsyncClient(
            proxies=proxy_url,
            timeout=10
        ) as client:
            response = await client.get("https://httpbin.org/ip")
            print(f"响应: {response.text}")
    except Exception as e:
        print(f"请求失败 (代理可能不可用): {e}")


async def main():
    """主函数"""
    # 配置日志
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="DEBUG"
    )

    print("=" * 60)
    print("代理 IP 使用与管理演示")
    print("=" * 60)
    print("\n注意: 演示使用的是模拟代理，可能不可用")
    print("实际使用时请替换为真实的代理服务")

    # 运行演示
    await demo_proxy_pool()
    await demo_proxied_crawler()
    # await demo_manual_proxy()  # 需要有可用代理才能测试

    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
