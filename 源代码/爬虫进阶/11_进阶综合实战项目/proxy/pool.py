# -*- coding: utf-8 -*-
# @Desc: 代理池模块

import random
import asyncio
from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger

# 可选依赖
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


@dataclass
class ProxyInfo:
    """代理信息"""
    ip: str
    port: int
    protocol: str = "http"
    username: str = None
    password: str = None
    expire_time: datetime = None
    fail_count: int = 0
    success_count: int = 0

    @property
    def url(self) -> str:
        """获取代理 URL"""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.ip}:{self.port}"
        return f"{self.protocol}://{self.ip}:{self.port}"

    @property
    def is_valid(self) -> bool:
        """检查是否有效"""
        if self.expire_time and datetime.now() > self.expire_time:
            return False
        return self.fail_count < 3

    def __str__(self) -> str:
        return f"{self.ip}:{self.port}"


class ProxyPool:
    """代理池"""

    def __init__(self, api_url: str = None):
        """
        初始化代理池

        Args:
            api_url: 代理 API 地址（可选）
        """
        self.api_url = api_url
        self._proxies: List[ProxyInfo] = []
        self._lock = asyncio.Lock()

    async def fetch_proxies(self, count: int = 10) -> List[ProxyInfo]:
        """
        从 API 获取代理

        Args:
            count: 获取数量

        Returns:
            代理列表
        """
        if not self.api_url:
            logger.warning("未配置代理 API")
            return []

        if not HAS_HTTPX:
            logger.warning("httpx 未安装，无法获取代理")
            return []

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.api_url,
                    params={'count': count},
                    timeout=10
                )

                if response.status_code != 200:
                    logger.error(f"获取代理失败: HTTP {response.status_code}")
                    return []

                data = response.json()

                proxies = []
                # 支持多种 API 响应格式
                items = data.get('data', data.get('proxies', data))
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            proxy = ProxyInfo(
                                ip=item.get('ip', item.get('host', '')),
                                port=int(item.get('port', 0)),
                                protocol=item.get('protocol', item.get('type', 'http')),
                                expire_time=datetime.fromisoformat(item['expire_time'])
                                if 'expire_time' in item else None
                            )
                            if proxy.ip and proxy.port:
                                proxies.append(proxy)

                logger.info(f"获取 {len(proxies)} 个代理")
                return proxies
        except Exception as e:
            logger.error(f"获取代理失败: {e}")
            return []

    async def add_proxy(self, proxy: ProxyInfo):
        """添加单个代理"""
        async with self._lock:
            self._proxies.append(proxy)

    async def add_proxies(self, proxies: List[ProxyInfo]):
        """添加多个代理"""
        async with self._lock:
            self._proxies.extend(proxies)
            logger.info(f"添加 {len(proxies)} 个代理到池中")

    async def add_proxy_from_url(self, url: str):
        """从 URL 添加代理"""
        try:
            # 解析 URL，格式：protocol://[user:pass@]ip:port
            from urllib.parse import urlparse
            parsed = urlparse(url)

            proxy = ProxyInfo(
                ip=parsed.hostname,
                port=parsed.port,
                protocol=parsed.scheme or 'http',
                username=parsed.username,
                password=parsed.password
            )
            await self.add_proxy(proxy)
        except Exception as e:
            logger.error(f"解析代理 URL 失败: {e}")

    async def get_proxy(self) -> Optional[ProxyInfo]:
        """
        获取一个可用代理

        Returns:
            代理信息，如果没有可用代理返回 None
        """
        async with self._lock:
            # 过滤有效代理
            valid_proxies = [p for p in self._proxies if p.is_valid]

            if not valid_proxies:
                # 尝试获取新代理
                if self.api_url:
                    new_proxies = await self.fetch_proxies()
                    if new_proxies:
                        self._proxies = new_proxies
                        valid_proxies = new_proxies

            if not valid_proxies:
                return None

            # 随机选择一个
            return random.choice(valid_proxies)

    async def report_success(self, proxy: ProxyInfo):
        """报告代理成功"""
        proxy.success_count += 1
        proxy.fail_count = 0
        logger.debug(f"代理 {proxy} 成功，总成功次数: {proxy.success_count}")

    async def report_failure(self, proxy: ProxyInfo):
        """报告代理失败"""
        proxy.fail_count += 1
        logger.debug(f"代理 {proxy} 失败，失败次数: {proxy.fail_count}")

    async def remove_invalid(self):
        """移除无效代理"""
        async with self._lock:
            before = len(self._proxies)
            self._proxies = [p for p in self._proxies if p.is_valid]
            removed = before - len(self._proxies)
            if removed > 0:
                logger.info(f"移除 {removed} 个无效代理")

    async def clear(self):
        """清空代理池"""
        async with self._lock:
            self._proxies.clear()
            logger.info("代理池已清空")

    @property
    def size(self) -> int:
        """代理池大小"""
        return len(self._proxies)

    @property
    def valid_size(self) -> int:
        """有效代理数量"""
        return len([p for p in self._proxies if p.is_valid])

    def get_stats(self) -> dict:
        """获取代理池统计信息"""
        return {
            "total": self.size,
            "valid": self.valid_size,
            "invalid": self.size - self.valid_size
        }
