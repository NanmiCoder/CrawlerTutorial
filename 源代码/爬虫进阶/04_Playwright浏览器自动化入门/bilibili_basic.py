# -*- coding: utf-8 -*-
"""
B站 Playwright 基础操作示例

本模块展示如何使用 Playwright 访问和操作 B站页面，包括：
- 访问B站首页
- 提取视频卡片信息
- 搜索视频
- 页面滚动加载

这是第04章"Playwright浏览器自动化入门"的B站实战示例。

与第11章综合实战项目的关联：
- core/browser.py: 浏览器管理器
- crawler/spider.py: 页面操作逻辑
"""

import asyncio
from typing import List, Dict, Any, Optional

from playwright.async_api import async_playwright
from loguru import logger


async def visit_bilibili_home() -> List[Dict[str, Any]]:
    """
    访问B站首页并提取热门视频

    Returns:
        视频信息列表
    """
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )

        # 创建上下文，设置视口和语言
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/131.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            logger.info("正在访问B站首页...")
            await page.goto(
                "https://www.bilibili.com",
                wait_until="networkidle"
            )

            # 等待视频卡片加载
            await page.wait_for_selector(".bili-video-card", timeout=10000)

            # 提取热门视频
            video_cards = await page.locator(".bili-video-card").all()
            logger.info(f"找到 {len(video_cards)} 个视频卡片")

            results = []
            for card in video_cards[:10]:
                try:
                    # 提取视频标题
                    title_el = card.locator(".bili-video-card__info--tit")
                    title = await title_el.get_attribute("title") or await title_el.text_content()

                    # 提取UP主
                    author_el = card.locator(".bili-video-card__info--author")
                    author = await author_el.text_content() if await author_el.count() > 0 else "未知"

                    # 提取播放量
                    view_el = card.locator(".bili-video-card__stats--item span").first
                    view = await view_el.text_content() if await view_el.count() > 0 else "0"

                    # 提取视频链接
                    link_el = card.locator("a").first
                    href = await link_el.get_attribute("href") or ""

                    results.append({
                        "title": title.strip() if title else "",
                        "author": author.strip() if author else "",
                        "view": view.strip() if view else "",
                        "url": f"https:{href}" if href.startswith("//") else href
                    })
                except Exception as e:
                    logger.debug(f"提取视频信息失败: {e}")
                    continue

            logger.info(f"成功提取 {len(results)} 个视频信息")
            return results

        finally:
            await browser.close()


async def search_bilibili_videos(keyword: str, max_results: int = 20) -> List[Dict[str, Any]]:
    """
    搜索B站视频

    Args:
        keyword: 搜索关键词
        max_results: 最大结果数

    Returns:
        视频列表
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN"
        )
        page = await context.new_page()

        try:
            # 直接访问搜索页
            search_url = f"https://search.bilibili.com/all?keyword={keyword}"
            logger.info(f"搜索关键词: {keyword}")
            await page.goto(search_url, wait_until="networkidle")

            # 等待搜索结果加载
            await page.wait_for_selector(".bili-video-card", timeout=15000)

            # 滚动加载更多结果
            for _ in range(3):
                await page.mouse.wheel(0, 1000)
                await page.wait_for_timeout(500)

            # 提取搜索结果
            video_items = await page.locator(".bili-video-card").all()
            logger.info(f"找到 {len(video_items)} 个搜索结果")

            results = []
            for item in video_items[:max_results]:
                try:
                    # 标题
                    title_el = item.locator(".bili-video-card__info--tit a")
                    title = await title_el.get_attribute("title") or ""

                    # 链接
                    href = await title_el.get_attribute("href") or ""

                    # 从链接提取BV号
                    bvid = ""
                    if "/video/" in href:
                        bvid = href.split("/video/")[-1].split("?")[0].strip("/")

                    # UP主
                    author_el = item.locator(".bili-video-card__info--author")
                    author = await author_el.text_content() if await author_el.count() > 0 else ""

                    # 播放量和弹幕数
                    stats = item.locator(".bili-video-card__stats--item")
                    view_count = ""
                    danmaku_count = ""
                    if await stats.count() >= 2:
                        view_count = await stats.nth(0).locator("span").text_content() or ""
                        danmaku_count = await stats.nth(1).locator("span").text_content() or ""

                    if title and bvid:
                        results.append({
                            "title": title.strip(),
                            "bvid": bvid,
                            "author": author.strip(),
                            "view": view_count.strip(),
                            "danmaku": danmaku_count.strip(),
                            "url": f"https://www.bilibili.com/video/{bvid}"
                        })

                except Exception as e:
                    logger.debug(f"提取视频失败: {e}")
                    continue

            logger.info(f"成功提取 {len(results)} 个视频")
            return results

        finally:
            await browser.close()


async def intercept_bilibili_api(keyword: str) -> List[Dict[str, Any]]:
    """
    拦截B站搜索API响应

    使用Playwright的网络拦截功能直接获取API返回的JSON数据

    Args:
        keyword: 搜索关键词

    Returns:
        API返回的视频数据
    """
    api_results = []

    async def handle_response(response):
        """处理API响应"""
        if "search/type" in response.url and response.status == 200:
            try:
                data = await response.json()
                if data.get("code") == 0:
                    result = data.get("data", {}).get("result", [])
                    api_results.extend(result)
                    logger.info(f"拦截到API响应: {len(result)} 条数据")
            except Exception as e:
                logger.debug(f"解析API响应失败: {e}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN"
        )
        page = await context.new_page()

        # 监听响应
        page.on("response", handle_response)

        try:
            search_url = f"https://search.bilibili.com/all?keyword={keyword}"
            logger.info(f"开始监听API: {keyword}")
            await page.goto(search_url, wait_until="networkidle")

            # 等待API响应
            await page.wait_for_timeout(2000)

            return api_results

        finally:
            await browser.close()


async def main():
    """主演示函数"""
    logger.info("=" * 50)
    logger.info("B站 Playwright 基础操作示例")
    logger.info("=" * 50)

    # 1. 访问首页
    logger.info("\n--- 1. 访问B站首页 ---")
    videos = await visit_bilibili_home()
    for i, video in enumerate(videos[:5], 1):
        print(f"{i}. {video['title'][:40]}...")
        print(f"   UP主: {video['author']} | 播放: {video['view']}")

    # 2. 搜索视频
    logger.info("\n--- 2. 搜索B站视频 ---")
    search_results = await search_bilibili_videos("Python教程", max_results=5)
    print("\n=== B站视频搜索结果 ===")
    for i, video in enumerate(search_results, 1):
        print(f"{i}. {video['title']}")
        print(f"   UP主: {video['author']} | BV号: {video['bvid']}")

    # 3. 拦截API（演示）
    logger.info("\n--- 3. 拦截B站API响应 ---")
    api_data = await intercept_bilibili_api("Python爬虫")
    logger.info(f"通过API拦截获取到 {len(api_data)} 条数据")


if __name__ == "__main__":
    asyncio.run(main())
