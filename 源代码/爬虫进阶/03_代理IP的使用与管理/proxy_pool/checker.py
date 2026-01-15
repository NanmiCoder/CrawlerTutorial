# -*- coding: utf-8 -*-
# @Desc: 代理检测器实现

import asyncio
import time
from typing import List
from loguru import logger
import httpx

from base import ProxyInfo, IProxyChecker


class ProxyChecker(IProxyChecker):
    """
    代理检测器

    功能：
    - 检测代理的可用性
    - 测量响应时间
    - 支持批量检测
    """

    # 用于检测的 URL 列表（按优先级排序）
    CHECK_URLS = [
        "https://httpbin.org/ip",
        "https://api.ipify.org?format=json",
        "https://ifconfig.me/ip",
    ]

    def __init__(
        self,
        timeout: int = 10,
        check_urls: List[str] = None
    ):
        """
        初始化检测器

        Args:
            timeout: 检测超时时间（秒）
            check_urls: 自定义检测 URL 列表
        """
        self.timeout = timeout
        self.check_urls = check_urls or self.CHECK_URLS

    async def check(self, proxy: ProxyInfo) -> bool:
        """
        检测单个代理是否可用

        Args:
            proxy: 代理信息

        Returns:
            代理是否可用
        """
        start_time = time.time()

        try:
            async with httpx.AsyncClient(
                proxies=proxy.url,
                timeout=self.timeout,
                verify=False  # 跳过 SSL 验证（某些代理可能有问题）
            ) as client:
                for url in self.check_urls:
                    try:
                        response = await client.get(url)

                        if response.status_code == 200:
                            # 计算响应时间
                            response_time = time.time() - start_time

                            # 更新代理信息
                            # 使用指数移动平均更新响应时间
                            if proxy.avg_response_time > 0:
                                proxy.avg_response_time = (
                                    proxy.avg_response_time * 0.7 +
                                    response_time * 0.3
                                )
                            else:
                                proxy.avg_response_time = response_time

                            proxy.last_check_time = time.time()

                            logger.debug(
                                f"代理可用: {proxy.host}:{proxy.port}, "
                                f"响应时间: {response_time:.2f}s"
                            )
                            return True

                    except httpx.TimeoutException:
                        continue
                    except httpx.ConnectError:
                        continue
                    except Exception as e:
                        logger.debug(f"检测请求异常: {url} - {e}")
                        continue

        except Exception as e:
            logger.debug(f"代理检测失败: {proxy.host}:{proxy.port} - {e}")

        return False

    async def check_batch(
        self,
        proxies: List[ProxyInfo],
        concurrency: int = 20
    ) -> List[ProxyInfo]:
        """
        批量检测代理

        Args:
            proxies: 代理列表
            concurrency: 并发数

        Returns:
            可用的代理列表
        """
        semaphore = asyncio.Semaphore(concurrency)
        valid_proxies = []
        checked_count = 0
        total_count = len(proxies)

        async def check_one(proxy: ProxyInfo):
            nonlocal checked_count
            async with semaphore:
                is_valid = await self.check(proxy)
                checked_count += 1

                if is_valid:
                    valid_proxies.append(proxy)

                # 进度日志
                if checked_count % 10 == 0 or checked_count == total_count:
                    logger.info(
                        f"检测进度: {checked_count}/{total_count}, "
                        f"有效: {len(valid_proxies)}"
                    )

        # 创建任务
        tasks = [check_one(p) for p in proxies]

        # 并发执行
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(
            f"检测完成: {len(valid_proxies)}/{len(proxies)} 可用 "
            f"({len(valid_proxies)/len(proxies)*100:.1f}%)"
        )

        return valid_proxies


class TargetSiteChecker(ProxyChecker):
    """
    目标站点检测器

    使用实际目标站点进行检测，确保代理对目标网站可用
    """

    def __init__(
        self,
        target_url: str,
        expected_status: int = 200,
        timeout: int = 15
    ):
        """
        初始化目标站点检测器

        Args:
            target_url: 目标站点 URL
            expected_status: 期望的状态码
            timeout: 超时时间
        """
        super().__init__(timeout=timeout, check_urls=[target_url])
        self.expected_status = expected_status
