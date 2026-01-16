# -*- coding: utf-8 -*-
"""
B站爬虫模块

本模块实现了 B站视频数据的爬取功能，包括：
- 关键词搜索视频
- 获取指定视频详情
- 并发爬取控制
- 数据存储回调

参考 MediaCrawler 项目的实现：
- https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/bilibili/core.py
"""

import asyncio
import random
from typing import List, Dict, Optional, Callable, Any
from loguru import logger

# 可选依赖
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

from config import settings, CrawlerType
from config import bilibili_config
from core.browser import BrowserManager
from login.auth import BilibiliLogin
from client.bilibili_client import BilibiliClient
from models.bilibili import BilibiliVideo
from tools.sign import parse_video_info_from_url


class BilibiliCrawler:
    """
    B站爬虫类

    整合浏览器管理、登录认证、API客户端，实现完整的爬取流程。

    使用示例：
    ```python
    crawler = BilibiliCrawler()
    videos = await crawler.start()
    ```
    """

    def __init__(self):
        """初始化爬虫"""
        self.browser_manager: Optional[BrowserManager] = None
        self.browser_context: Optional[BrowserContext] = None
        self.context_page: Optional[Page] = None
        self.bili_client: Optional[BilibiliClient] = None

        # 爬取结果
        self._results: List[BilibiliVideo] = []

        # 配置
        self.max_video_count = settings.max_video_count
        self.max_concurrency = settings.max_concurrency
        self.delay_min = settings.crawl_delay_min
        self.delay_max = settings.crawl_delay_max

    async def start(self) -> List[BilibiliVideo]:
        """
        启动爬虫

        完整流程：
        1. 启动浏览器
        2. 执行登录
        3. 初始化 API 客户端
        4. 根据配置执行爬取
        5. 关闭浏览器

        Returns:
            List[BilibiliVideo]: 爬取的视频列表
        """
        logger.info(f"[BilibiliCrawler] 启动爬虫，类型: {settings.crawler_type}")

        try:
            # 1. 启动浏览器
            await self._init_browser()

            # 2. 执行登录
            login_success = await self._do_login()
            if not login_success:
                logger.error("[BilibiliCrawler] 登录失败，退出")
                return []

            # 3. 初始化 API 客户端
            await self._init_client()

            # 4. 根据配置执行爬取
            if settings.crawler_type == CrawlerType.SEARCH:
                await self.search_by_keywords()
            elif settings.crawler_type == CrawlerType.DETAIL:
                await self.get_specified_videos()
            else:
                logger.error(f"[BilibiliCrawler] 不支持的爬取类型: {settings.crawler_type}")

            logger.info(f"[BilibiliCrawler] 爬取完成，共 {len(self._results)} 个视频")
            return self._results

        except Exception as e:
            logger.exception(f"[BilibiliCrawler] 爬取出错: {e}")
            return self._results

        finally:
            # 5. 关闭浏览器
            await self.close()

    async def _init_browser(self):
        """初始化浏览器"""
        logger.info("[BilibiliCrawler] 初始化浏览器...")

        self.browser_manager = BrowserManager(
            headless=settings.browser_headless,
            timeout=settings.browser_timeout,
            user_data_dir=settings.browser_user_data_dir if settings.save_login_state else None
        )

        self.browser_context = await self.browser_manager.start()
        self.context_page = await self.browser_manager.new_page()

        logger.info("[BilibiliCrawler] 浏览器初始化完成")

    async def _do_login(self) -> bool:
        """
        执行登录

        Returns:
            bool: 是否登录成功
        """
        # 先检查是否已登录（通过保存的状态）
        self.bili_client = BilibiliClient()
        await self.bili_client.update_cookies(self.browser_context)

        if await self.bili_client.pong():
            logger.info("[BilibiliCrawler] 已有登录状态，跳过登录")
            return True

        # 执行登录
        login = BilibiliLogin(
            login_type=settings.login_type.value,
            browser_context=self.browser_context,
            context_page=self.context_page,
            cookie_str=settings.cookie_str
        )

        success = await login.begin()

        if success:
            # 更新客户端 Cookie
            await self.bili_client.update_cookies(self.browser_context)

        return success

    async def _init_client(self):
        """初始化 API 客户端"""
        # 初始化 WBI 签名器
        await self.bili_client.init_wbi_sign(self.context_page)

    async def search_by_keywords(self) -> List[BilibiliVideo]:
        """
        按关键词搜索视频

        支持多个关键词（逗号分隔）。

        Returns:
            List[BilibiliVideo]: 视频列表
        """
        keywords = [kw.strip() for kw in settings.keywords.split(",") if kw.strip()]

        if not keywords:
            logger.warning("[BilibiliCrawler] 未配置搜索关键词")
            return []

        logger.info(f"[BilibiliCrawler] 开始搜索，关键词: {keywords}")

        for keyword in keywords:
            await self._search_single_keyword(keyword)

            # 达到最大数量后停止
            if len(self._results) >= self.max_video_count:
                break

        return self._results

    async def _search_single_keyword(self, keyword: str):
        """
        搜索单个关键词

        Args:
            keyword: 搜索关键词
        """
        page = 1
        page_size = bilibili_config.SEARCH_PAGE_SIZE

        while len(self._results) < self.max_video_count:
            logger.info(f"[BilibiliCrawler] 搜索 '{keyword}'，第 {page} 页")

            # 搜索视频
            videos = await self.bili_client.search_video_by_keyword(
                keyword=keyword,
                page=page,
                page_size=page_size
            )

            if not videos:
                logger.info(f"[BilibiliCrawler] '{keyword}' 第 {page} 页无结果，停止搜索")
                break

            # 获取视频详情
            for video in videos:
                if len(self._results) >= self.max_video_count:
                    break

                # 获取完整视频详情
                video_detail = await self.bili_client.get_video_info(bvid=video.bvid)
                if video_detail:
                    video_detail.source_keyword = keyword
                    self._results.append(video_detail)
                    logger.info(f"[BilibiliCrawler] 获取视频: {video_detail.title[:30]}...")
                else:
                    # 如果获取详情失败，使用搜索结果
                    self._results.append(video)

                # 随机延迟
                await self._random_delay()

            page += 1

            # 防止无限循环
            if page > 50:
                break

    async def get_specified_videos(self) -> List[BilibiliVideo]:
        """
        获取指定视频列表的详情

        从配置中读取视频列表（BV号或URL）。

        Returns:
            List[BilibiliVideo]: 视频列表
        """
        video_list = settings.specified_id_list

        if not video_list:
            logger.warning("[BilibiliCrawler] 未配置指定视频列表")
            return []

        logger.info(f"[BilibiliCrawler] 获取 {len(video_list)} 个指定视频")

        for video_id in video_list:
            if len(self._results) >= self.max_video_count:
                break

            # 解析 BV 号
            try:
                video_info = parse_video_info_from_url(video_id)
                bvid = video_info.video_id
            except ValueError:
                logger.warning(f"[BilibiliCrawler] 无法解析视频 ID: {video_id}")
                continue

            # 获取视频详情
            video = await self.bili_client.get_video_info(bvid=bvid)
            if video:
                self._results.append(video)
                logger.info(f"[BilibiliCrawler] 获取视频: {video.title[:30]}...")

            # 随机延迟
            await self._random_delay()

        return self._results

    async def _random_delay(self):
        """随机延迟，避免请求过快"""
        delay = random.uniform(self.delay_min, self.delay_max)
        await asyncio.sleep(delay)

    def get_results(self) -> List[BilibiliVideo]:
        """
        获取爬取结果

        Returns:
            List[BilibiliVideo]: 视频列表
        """
        return self._results

    async def close(self):
        """关闭浏览器"""
        if self.browser_manager:
            await self.browser_manager.close()
            logger.info("[BilibiliCrawler] 浏览器已关闭")


async def run_crawler(
    on_video: Optional[Callable[[BilibiliVideo], Any]] = None
) -> List[BilibiliVideo]:
    """
    运行爬虫（便捷函数）

    Args:
        on_video: 每获取一个视频后的回调函数

    Returns:
        List[BilibiliVideo]: 视频列表
    """
    crawler = BilibiliCrawler()
    return await crawler.start()


if __name__ == '__main__':
    # 测试代码
    async def test():
        crawler = BilibiliCrawler()
        videos = await crawler.start()

        print(f"\n爬取完成，共 {len(videos)} 个视频：")
        for i, video in enumerate(videos[:5], 1):
            print(f"{i}. {video.title}")
            print(f"   UP主: {video.nickname}")
            print(f"   播放: {video.play_count}")
            print()

    asyncio.run(test())
