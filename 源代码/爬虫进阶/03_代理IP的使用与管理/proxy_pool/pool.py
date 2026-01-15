# -*- coding: utf-8 -*-
# @Desc: 代理池实现

import asyncio
import random
import time
from typing import Optional, Dict, List
from loguru import logger

from .base import ProxyInfo, IProxyFetcher, IProxyChecker, IProxyPool


class ProxyPool(IProxyPool):
    """
    代理池实现

    特性：
    - 自动获取和检测代理
    - 基于评分的智能分配
    - 自动淘汰失效代理
    - 后台自动刷新
    """

    def __init__(
        self,
        fetcher: IProxyFetcher,
        checker: IProxyChecker,
        min_proxies: int = 10,
        max_proxies: int = 100,
        check_interval: int = 300,
        max_fail_count: int = 3,
        score_threshold: float = 0.3
    ):
        """
        初始化代理池

        Args:
            fetcher: 代理获取器
            checker: 代理检测器
            min_proxies: 最小代理数量（低于此数量时自动补充）
            max_proxies: 最大代理数量
            check_interval: 检测间隔（秒）
            max_fail_count: 最大连续失败次数（超过后触发淘汰检查）
            score_threshold: 淘汰评分阈值
        """
        self.fetcher = fetcher
        self.checker = checker
        self.min_proxies = min_proxies
        self.max_proxies = max_proxies
        self.check_interval = check_interval
        self.max_fail_count = max_fail_count
        self.score_threshold = score_threshold

        # 代理存储 {key: ProxyInfo}
        self._proxies: Dict[str, ProxyInfo] = {}
        self._lock = asyncio.Lock()

        # 后台任务
        self._refresh_task: Optional[asyncio.Task] = None
        self._running = False

    def _proxy_key(self, proxy: ProxyInfo) -> str:
        """生成代理唯一标识"""
        return f"{proxy.host}:{proxy.port}"

    async def start(self):
        """启动代理池"""
        if self._running:
            return

        self._running = True
        logger.info("代理池启动中...")

        # 初始获取代理
        await self._refresh_proxies()

        # 启动后台刷新任务
        self._refresh_task = asyncio.create_task(self._refresh_loop())

        logger.info(f"代理池已启动，当前代理数: {self.size}")

    async def stop(self):
        """停止代理池"""
        if not self._running:
            return

        self._running = False

        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass

        logger.info("代理池已停止")

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.stop()

    async def _refresh_loop(self):
        """后台刷新循环"""
        while self._running:
            try:
                await asyncio.sleep(self.check_interval)

                # 检查是否需要刷新
                if self.size < self.min_proxies:
                    logger.info("代理数量不足，触发刷新")
                    await self._refresh_proxies()
                else:
                    # 清理过期代理
                    await self._cleanup_stale_proxies()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"代理刷新异常: {e}")
                await asyncio.sleep(60)  # 出错后等待一分钟

    async def _refresh_proxies(self):
        """刷新代理"""
        logger.info(f"开始刷新代理，当前数量: {self.size}")

        try:
            # 获取新代理
            new_proxies = await self.fetcher.fetch()

            if not new_proxies:
                logger.warning("未获取到新代理")
                return

            logger.info(f"获取到 {len(new_proxies)} 个代理，开始检测...")

            # 检测代理
            valid_proxies = await self.checker.check_batch(new_proxies)

            # 添加到池中
            async with self._lock:
                added_count = 0
                for proxy in valid_proxies:
                    key = self._proxy_key(proxy)
                    if key not in self._proxies and len(self._proxies) < self.max_proxies:
                        self._proxies[key] = proxy
                        added_count += 1

                logger.info(f"添加了 {added_count} 个新代理，当前总数: {self.size}")

        except Exception as e:
            logger.error(f"刷新代理失败: {e}")

    async def _cleanup_stale_proxies(self):
        """清理过期代理"""
        async with self._lock:
            stale_keys = [
                key for key, proxy in self._proxies.items()
                if proxy.is_stale
            ]

            for key in stale_keys:
                del self._proxies[key]

            if stale_keys:
                logger.info(f"清理了 {len(stale_keys)} 个过期代理")

    async def get_proxy(self) -> Optional[ProxyInfo]:
        """
        获取一个可用代理

        使用加权随机选择，评分高的代理被选中概率更大
        """
        async with self._lock:
            if not self._proxies:
                logger.warning("代理池为空")
                return None

            # 获取所有代理
            proxies = list(self._proxies.values())

            # 计算权重（评分越高权重越大，最小权重 0.1）
            weights = [max(p.score, 0.1) for p in proxies]

            # 加权随机选择
            selected = random.choices(proxies, weights=weights, k=1)[0]
            selected.last_use_time = time.time()

            logger.debug(
                f"分配代理: {selected.host}:{selected.port} "
                f"(评分: {selected.score:.2f})"
            )

            return selected

    async def return_proxy(self, proxy: ProxyInfo, success: bool):
        """
        归还代理并报告使用结果

        Args:
            proxy: 代理信息
            success: 使用是否成功
        """
        async with self._lock:
            key = self._proxy_key(proxy)

            if key not in self._proxies:
                return

            stored_proxy = self._proxies[key]

            if success:
                stored_proxy.success_count += 1
                logger.debug(f"代理使用成功: {proxy.host}:{proxy.port}")
            else:
                stored_proxy.fail_count += 1
                logger.debug(f"代理使用失败: {proxy.host}:{proxy.port}")

                # 检查是否需要淘汰
                if stored_proxy.fail_count >= self.max_fail_count:
                    total = stored_proxy.success_count + stored_proxy.fail_count

                    # 有足够样本且评分过低时淘汰
                    if total >= 5 and stored_proxy.score < self.score_threshold:
                        del self._proxies[key]
                        logger.info(
                            f"淘汰低质量代理: {proxy.host}:{proxy.port} "
                            f"(评分: {stored_proxy.score:.2f})"
                        )

    async def add_proxy(self, proxy: ProxyInfo):
        """添加代理"""
        async with self._lock:
            key = self._proxy_key(proxy)
            if key not in self._proxies and len(self._proxies) < self.max_proxies:
                self._proxies[key] = proxy
                logger.debug(f"添加代理: {proxy.host}:{proxy.port}")

    async def remove_proxy(self, proxy: ProxyInfo):
        """移除代理"""
        async with self._lock:
            key = self._proxy_key(proxy)
            if key in self._proxies:
                del self._proxies[key]
                logger.debug(f"移除代理: {proxy.host}:{proxy.port}")

    @property
    def size(self) -> int:
        """代理池大小"""
        return len(self._proxies)

    def get_stats(self) -> Dict:
        """
        获取统计信息

        Returns:
            包含各种统计指标的字典
        """
        if not self._proxies:
            return {
                "total": 0,
                "avg_score": 0,
                "max_score": 0,
                "min_score": 0,
            }

        proxies = list(self._proxies.values())
        scores = [p.score for p in proxies]

        return {
            "total": len(proxies),
            "avg_score": sum(scores) / len(scores),
            "max_score": max(scores),
            "min_score": min(scores),
            "total_success": sum(p.success_count for p in proxies),
            "total_fail": sum(p.fail_count for p in proxies),
        }

    def get_all_proxies(self) -> List[ProxyInfo]:
        """获取所有代理列表（用于调试）"""
        return list(self._proxies.values())
