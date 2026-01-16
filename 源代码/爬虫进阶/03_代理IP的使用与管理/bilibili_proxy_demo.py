"""
B站代理IP使用示例

本模块展示如何使用代理IP访问B站API，包括：
- B站专用代理检测器
- 代理轮换策略
- 风控响应处理
- 智能重试机制

这是第03章"代理IP的使用与管理"的B站实战示例。

与第11章综合实战项目的关联：
- proxy/pool.py: 代理池管理
- client/bilibili_client.py: 集成代理支持
"""

import asyncio
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum

import httpx
from loguru import logger


# ============== 代理数据结构 ==============

class ProxyProtocol(str, Enum):
    """代理协议类型"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


@dataclass
class ProxyInfo:
    """代理信息"""
    host: str
    port: int
    protocol: ProxyProtocol = ProxyProtocol.HTTP
    username: Optional[str] = None
    password: Optional[str] = None

    # 统计信息
    success_count: int = 0
    fail_count: int = 0
    avg_response_time: float = 0.0
    last_check_time: float = 0.0

    @property
    def url(self) -> str:
        """生成代理URL"""
        if self.username and self.password:
            return f"{self.protocol.value}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol.value}://{self.host}:{self.port}"

    @property
    def score(self) -> float:
        """计算代理评分"""
        total = self.success_count + self.fail_count
        if total == 0:
            return 0.5
        success_rate = self.success_count / total
        # 综合评分 = 成功率 * 0.7 + 响应时间评分 * 0.3
        time_score = max(0, 1 - self.avg_response_time / 10)
        return success_rate * 0.7 + time_score * 0.3


# ============== 代理检测接口 ==============

class IProxyChecker(ABC):
    """代理检测器接口"""

    @abstractmethod
    async def check(self, proxy: ProxyInfo) -> bool:
        """检测代理是否可用"""
        pass


# ============== B站专用代理检测器 ==============

class BilibiliProxyChecker(IProxyChecker):
    """
    B站专用代理检测器

    使用B站真实API检测代理可用性，确保代理能正常访问B站
    """

    # B站检测URL - 使用轻量级API
    CHECK_URL = "https://api.bilibili.com/x/web-interface/nav/stat"

    # B站必要请求头
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/131.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/",
        "Origin": "https://www.bilibili.com"
    }

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    async def check(self, proxy: ProxyInfo) -> bool:
        """
        检测代理是否可用于B站

        判断标准：
        - 请求成功（状态码200）
        - 响应包含有效JSON
        - 未触发风控（code != -412）
        """
        start_time = time.time()

        try:
            async with httpx.AsyncClient(
                proxies=proxy.url,
                timeout=self.timeout,
                headers=self.HEADERS
            ) as client:
                response = await client.get(self.CHECK_URL)

                if response.status_code != 200:
                    logger.debug(f"代理状态码异常: {proxy.host}:{proxy.port} - {response.status_code}")
                    return False

                data = response.json()

                # 检查是否触发风控
                if data.get("code") == -412:
                    logger.debug(f"代理触发B站风控: {proxy.host}:{proxy.port}")
                    return False

                # 更新响应时间
                response_time = time.time() - start_time
                proxy.avg_response_time = (
                    proxy.avg_response_time * 0.7 + response_time * 0.3
                )
                proxy.last_check_time = time.time()

                logger.debug(
                    f"代理B站可用: {proxy.host}:{proxy.port}, "
                    f"响应时间: {response_time:.2f}s"
                )
                return True

        except Exception as e:
            logger.debug(f"代理B站检测失败: {proxy.host}:{proxy.port} - {e}")
            return False


# ============== 简单代理池 ==============

class SimpleProxyPool:
    """
    简单代理池实现

    用于演示，实际项目中建议使用更完善的代理池
    """

    def __init__(self, proxies: List[ProxyInfo] = None):
        self.proxies = proxies or []
        self._index = 0

    async def add_proxy(self, proxy: ProxyInfo):
        """添加代理"""
        self.proxies.append(proxy)

    async def get_proxy(self) -> Optional[ProxyInfo]:
        """获取代理（轮询）"""
        if not self.proxies:
            return None
        proxy = self.proxies[self._index % len(self.proxies)]
        self._index += 1
        return proxy

    async def return_proxy(self, proxy: ProxyInfo, success: bool):
        """返回代理并更新状态"""
        if success:
            proxy.success_count += 1
        else:
            proxy.fail_count += 1

    async def remove_invalid(self, checker: IProxyChecker):
        """移除无效代理"""
        valid_proxies = []
        for proxy in self.proxies:
            if await checker.check(proxy):
                valid_proxies.append(proxy)
        self.proxies = valid_proxies


# ============== B站代理配置 ==============

@dataclass
class BilibiliProxyConfig:
    """B站代理配置"""
    # 代理池配置
    min_proxies: int = 10
    max_proxies: int = 50

    # 请求配置
    request_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0

    # 频率控制
    request_interval: float = 0.5  # 请求间隔(秒)


# ============== B站代理爬虫 ==============

class BilibiliProxyCrawler:
    """
    B站代理爬虫

    特性：
    - 自动代理轮换
    - 智能重试
    - 频率控制
    - 风控响应处理
    """

    # B站API基础URL
    BASE_URL = "https://api.bilibili.com"

    # 通用请求头
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/131.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/",
        "Origin": "https://www.bilibili.com",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    def __init__(
        self,
        proxy_pool: SimpleProxyPool,
        config: Optional[BilibiliProxyConfig] = None
    ):
        self.proxy_pool = proxy_pool
        self.config = config or BilibiliProxyConfig()
        self._last_request_time = 0.0

    async def _wait_for_rate_limit(self):
        """频率控制"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.config.request_interval:
            await asyncio.sleep(self.config.request_interval - elapsed)
        self._last_request_time = time.time()

    async def _request(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """
        发送带代理的请求

        自动处理代理轮换和重试
        """
        await self._wait_for_rate_limit()

        merged_headers = {**self.DEFAULT_HEADERS, **(headers or {})}

        for attempt in range(self.config.max_retries):
            proxy = await self.proxy_pool.get_proxy()
            if not proxy:
                logger.warning("无可用代理，使用直连")
                proxy_url = None
            else:
                proxy_url = proxy.url

            try:
                async with httpx.AsyncClient(
                    proxies=proxy_url,
                    timeout=self.config.request_timeout,
                    headers=merged_headers
                ) as client:
                    response = await client.get(url, params=params)

                    # 处理响应
                    if response.status_code == 200:
                        data = response.json()

                        # 检查B站业务错误码
                        code = data.get("code", 0)
                        if code == 0:
                            if proxy:
                                await self.proxy_pool.return_proxy(proxy, success=True)
                            return data

                        # 风控错误，切换代理重试
                        if code == -412:
                            logger.warning(f"触发风控，切换代理重试 (尝试 {attempt + 1})")
                            if proxy:
                                await self.proxy_pool.return_proxy(proxy, success=False)
                            await asyncio.sleep(self.config.retry_delay)
                            continue

                        # 其他业务错误
                        logger.warning(f"B站API错误: {code} - {data.get('message')}")
                        if proxy:
                            await self.proxy_pool.return_proxy(proxy, success=True)
                        return data

                    # HTTP错误
                    if response.status_code == 429:
                        logger.warning("请求频率过高，等待后重试")
                        if proxy:
                            await self.proxy_pool.return_proxy(proxy, success=False)
                        await asyncio.sleep(self.config.retry_delay * 2)
                        continue

                    if response.status_code in (403, 412):
                        logger.warning(f"IP被封禁 ({response.status_code})，切换代理")
                        if proxy:
                            await self.proxy_pool.return_proxy(proxy, success=False)
                        continue

            except httpx.TimeoutException:
                logger.warning(f"请求超时，切换代理重试 (尝试 {attempt + 1})")
                if proxy:
                    await self.proxy_pool.return_proxy(proxy, success=False)
            except Exception as e:
                logger.error(f"请求异常: {e}")
                if proxy:
                    await self.proxy_pool.return_proxy(proxy, success=False)

        logger.error(f"请求失败，已达最大重试次数: {url}")
        return None

    async def get_video_info(self, bvid: str) -> Optional[Dict[str, Any]]:
        """
        获取B站视频信息

        Args:
            bvid: 视频BV号

        Returns:
            视频信息
        """
        url = f"{self.BASE_URL}/x/web-interface/view"
        params = {"bvid": bvid}
        headers = {"Referer": f"https://www.bilibili.com/video/{bvid}"}

        logger.info(f"[BilibiliProxy] 获取视频信息: {bvid}")
        return await self._request(url, params=params, headers=headers)

    async def search_videos(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20
    ) -> Optional[Dict[str, Any]]:
        """
        搜索B站视频

        Args:
            keyword: 搜索关键词
            page: 页码
            page_size: 每页数量

        Returns:
            搜索结果
        """
        url = f"{self.BASE_URL}/x/web-interface/search/type"
        params = {
            "search_type": "video",
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
        }
        headers = {"Referer": f"https://search.bilibili.com/all?keyword={keyword}"}

        logger.info(f"[BilibiliProxy] 搜索视频: {keyword}, 第{page}页")
        return await self._request(url, params=params, headers=headers)


# ============== 演示入口 ==============

async def demo():
    """演示B站代理使用"""
    logger.info("=" * 50)
    logger.info("B站代理IP使用示例")
    logger.info("=" * 50)

    # 1. 创建代理池（演示用，实际使用需要真实代理）
    pool = SimpleProxyPool()

    # 添加示例代理（这些是假的，仅用于演示结构）
    # 实际使用时需要替换为真实的代理IP
    sample_proxies = [
        ProxyInfo(host="127.0.0.1", port=7890),  # 本地代理示例
    ]

    for proxy in sample_proxies:
        await pool.add_proxy(proxy)

    logger.info(f"代理池初始化完成，共 {len(pool.proxies)} 个代理")

    # 2. 创建B站专用检测器
    checker = BilibiliProxyChecker(timeout=10)
    logger.info("B站专用代理检测器已创建")

    # 3. 检测代理（演示代码结构，实际需要真实代理）
    logger.info("-" * 50)
    logger.info("代理检测示例代码结构:")
    logger.info("""
    # 检测代理
    for proxy in proxies:
        if await checker.check(proxy):
            logger.info(f"代理可用: {proxy.url}")
        else:
            logger.warning(f"代理不可用: {proxy.url}")
    """)

    # 4. 创建B站代理爬虫
    crawler = BilibiliProxyCrawler(pool)
    logger.info("B站代理爬虫已创建")

    # 5. 展示使用方法
    logger.info("-" * 50)
    logger.info("爬虫使用示例代码:")
    logger.info("""
    # 搜索视频
    result = await crawler.search_videos("Python教程")
    if result and result.get("code") == 0:
        videos = result.get("data", {}).get("result", [])
        logger.info(f"搜索到 {len(videos)} 个视频")

    # 获取视频详情
    info = await crawler.get_video_info("BV1234567890")
    if info and info.get("code") == 0:
        data = info.get("data", {})
        logger.info(f"视频标题: {data.get('title')}")
    """)

    logger.info("-" * 50)
    logger.info("B站代理使用建议:")
    logger.info("1. 使用高匿代理，避免透明代理被识别")
    logger.info("2. 定期检测代理可用性")
    logger.info("3. 实现代理评分机制，优先使用优质代理")
    logger.info("4. 遇到-412风控时自动切换代理")
    logger.info("5. 控制请求频率，避免过快被封")


if __name__ == "__main__":
    asyncio.run(demo())
