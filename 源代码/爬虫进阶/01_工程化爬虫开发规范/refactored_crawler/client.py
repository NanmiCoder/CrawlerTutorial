# -*- coding: utf-8 -*-
# @Desc: HTTP 客户端封装

import httpx
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from .config import settings
from .exceptions import RequestException, TimeoutException


class CrawlerClient:
    """
    封装的 HTTP 客户端

    特性:
    - 统一的请求头配置
    - 自动重试机制
    - 优雅的错误处理
    - 资源自动管理
    """

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/123.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self):
        """启动客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=settings.request_timeout,
                headers=self.DEFAULT_HEADERS,
                follow_redirects=True
            )
            logger.debug("HTTP 客户端已启动")

    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.debug("HTTP 客户端已关闭")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
    )
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """
        发送 GET 请求（带重试）

        Args:
            url: 请求 URL
            **kwargs: 传递给 httpx 的其他参数

        Returns:
            httpx.Response 响应对象

        Raises:
            RequestException: 请求失败
        """
        if not self._client:
            await self.start()

        logger.debug(f"GET 请求: {url}")

        try:
            response = await self._client.get(url, **kwargs)
            response.raise_for_status()
            logger.info(f"请求成功: {url} [{response.status_code}]")
            return response

        except httpx.TimeoutException as e:
            logger.warning(f"请求超时: {url}")
            raise TimeoutException(f"请求超时: {url}") from e

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP 错误: {url} [{e.response.status_code}]")
            raise RequestException(
                f"HTTP 状态码异常: {e.response.status_code}",
                url=url
            ) from e

        except Exception as e:
            logger.exception(f"请求异常: {url}")
            raise RequestException(f"请求异常: {e}", url=url) from e
