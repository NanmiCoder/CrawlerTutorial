# -*- coding: utf-8 -*-
# @Desc: 代理池基础类和接口定义

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List
import time


class ProxyProtocol(Enum):
    """代理协议枚举"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


@dataclass
class ProxyInfo:
    """
    代理信息数据类

    包含代理的基本信息和质量指标
    """
    host: str
    port: int
    protocol: ProxyProtocol = ProxyProtocol.HTTP
    username: Optional[str] = None
    password: Optional[str] = None

    # 质量指标
    success_count: int = 0
    fail_count: int = 0
    avg_response_time: float = 0.0
    last_check_time: float = field(default_factory=time.time)
    last_use_time: float = 0.0

    @property
    def url(self) -> str:
        """
        构建代理 URL

        Returns:
            代理 URL 字符串，如 http://user:pass@host:port
        """
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        return f"{self.protocol.value}://{auth}{self.host}:{self.port}"

    @property
    def score(self) -> float:
        """
        计算代理评分

        综合考虑成功率和响应时间

        Returns:
            0-1 之间的评分
        """
        total = self.success_count + self.fail_count

        if total == 0:
            return 0.5  # 未测试的代理给中等分数

        # 成功率权重 70%
        success_rate = self.success_count / total

        # 响应时间权重 30%，响应时间越短分数越高
        # 假设 10 秒以上响应时间为 0 分
        time_score = max(0, 1 - self.avg_response_time / 10)

        return success_rate * 0.7 + time_score * 0.3

    @property
    def is_stale(self) -> bool:
        """
        检查代理是否过期（超过 10 分钟未检测）
        """
        return time.time() - self.last_check_time > 600

    def __hash__(self):
        return hash((self.host, self.port))

    def __eq__(self, other):
        if not isinstance(other, ProxyInfo):
            return False
        return self.host == other.host and self.port == other.port

    def __str__(self):
        return f"Proxy({self.host}:{self.port}, score={self.score:.2f})"


class IProxyFetcher(ABC):
    """
    代理获取器接口

    负责从各种来源获取代理列表
    """

    @abstractmethod
    async def fetch(self) -> List[ProxyInfo]:
        """
        获取代理列表

        Returns:
            代理信息列表
        """
        pass


class IProxyChecker(ABC):
    """
    代理检测器接口

    负责检测代理的可用性
    """

    @abstractmethod
    async def check(self, proxy: ProxyInfo) -> bool:
        """
        检测单个代理是否可用

        Args:
            proxy: 代理信息

        Returns:
            代理是否可用
        """
        pass


class IProxyPool(ABC):
    """
    代理池接口

    负责代理的存储和分配
    """

    @abstractmethod
    async def get_proxy(self) -> Optional[ProxyInfo]:
        """
        获取一个可用代理

        Returns:
            代理信息，如果没有可用代理则返回 None
        """
        pass

    @abstractmethod
    async def return_proxy(self, proxy: ProxyInfo, success: bool):
        """
        归还代理并报告使用结果

        Args:
            proxy: 代理信息
            success: 使用是否成功
        """
        pass

    @abstractmethod
    async def add_proxy(self, proxy: ProxyInfo):
        """
        添加代理到池中

        Args:
            proxy: 代理信息
        """
        pass

    @abstractmethod
    async def remove_proxy(self, proxy: ProxyInfo):
        """
        从池中移除代理

        Args:
            proxy: 代理信息
        """
        pass

    @property
    @abstractmethod
    def size(self) -> int:
        """
        获取代理池大小

        Returns:
            代理数量
        """
        pass
