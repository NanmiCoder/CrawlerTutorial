# -*- coding: utf-8 -*-
# @Desc: 使用 Playwright 爬取 SPA（单页应用）完整示例

import asyncio
import json
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from playwright.async_api import async_playwright, Page, Browser
from loguru import logger


@dataclass
class Quote:
    """名言数据模型"""
    text: str
    author: str
    tags: List[str]


class SPACrawler:
    """
    SPA 爬虫示例

    爬取 https://quotes.toscrape.com/js/ - 一个需要 JavaScript 渲染的页面
    """

    BASE_URL = "https://quotes.toscrape.com/js/"

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30000
    ):
        """
        初始化爬虫

        Args:
            headless: 是否无头模式
            timeout: 默认超时时间（毫秒）
        """
        self.headless = headless
        self.timeout = timeout
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def start(self):
        """启动浏览器"""
        playwright = await async_playwright().start()
        self._browser = await playwright.chromium.launch(
            headless=self.headless
        )
        context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        self._page = await context.new_page()
        self._page.set_default_timeout(self.timeout)
        logger.info(f"浏览器已启动 (headless={self.headless})")

    async def close(self):
        """关闭浏览器"""
        if self._browser:
            await self._browser.close()
            logger.info("浏览器已关闭")

    async def crawl_page(self, page_num: int = 1) -> List[Quote]:
        """
        爬取单页数据

        Args:
            page_num: 页码

        Returns:
            名言列表
        """
        url = f"{self.BASE_URL}page/{page_num}/" if page_num > 1 else self.BASE_URL

        logger.info(f"正在爬取第 {page_num} 页: {url}")

        # 访问页面
        await self._page.goto(url, wait_until="networkidle")

        # 等待内容加载（SPA 需要等待 JS 渲染）
        await self._page.wait_for_selector("div.quote")

        # 提取数据
        quotes = []
        quote_elements = await self._page.locator("div.quote").all()

        for element in quote_elements:
            text = await element.locator("span.text").text_content()
            author = await element.locator("small.author").text_content()
            tags = await element.locator("a.tag").all_text_contents()

            # 清理文本（去除引号符号）
            text = text.strip().strip(""").strip(""")

            quotes.append(Quote(
                text=text,
                author=author.strip(),
                tags=tags
            ))

        logger.info(f"第 {page_num} 页爬取完成，获取 {len(quotes)} 条名言")
        return quotes

    async def crawl_all_pages(self, max_pages: int = 10) -> List[Quote]:
        """
        爬取所有页面

        Args:
            max_pages: 最大页数

        Returns:
            所有名言列表
        """
        all_quotes = []

        for page_num in range(1, max_pages + 1):
            try:
                quotes = await self.crawl_page(page_num)
                all_quotes.extend(quotes)

                # 检查是否还有下一页
                next_button = self._page.locator("li.next a")
                if await next_button.count() == 0:
                    logger.info("已到达最后一页")
                    break

                # 页面间延迟
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"爬取第 {page_num} 页失败: {e}")
                break

        logger.info(f"爬取完成，共获取 {len(all_quotes)} 条名言")
        return all_quotes

    async def crawl_with_pagination(self) -> List[Quote]:
        """
        使用点击分页的方式爬取

        Returns:
            所有名言列表
        """
        all_quotes = []
        page_num = 1

        # 访问首页
        await self._page.goto(self.BASE_URL, wait_until="networkidle")

        while True:
            logger.info(f"正在爬取第 {page_num} 页...")

            # 等待内容加载
            await self._page.wait_for_selector("div.quote")

            # 提取当前页数据
            quote_elements = await self._page.locator("div.quote").all()

            for element in quote_elements:
                text = await element.locator("span.text").text_content()
                author = await element.locator("small.author").text_content()
                tags = await element.locator("a.tag").all_text_contents()

                text = text.strip().strip(""").strip(""")

                all_quotes.append(Quote(
                    text=text,
                    author=author.strip(),
                    tags=tags
                ))

            logger.info(f"第 {page_num} 页完成，累计 {len(all_quotes)} 条")

            # 检查并点击下一页
            next_button = self._page.locator("li.next a")
            if await next_button.count() == 0:
                logger.info("已到达最后一页")
                break

            # 点击下一页
            await next_button.click()
            await self._page.wait_for_load_state("networkidle")

            page_num += 1

            # 防止无限循环
            if page_num > 20:
                break

        return all_quotes


async def main():
    """主函数"""
    # 配置日志
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    print("=" * 60)
    print("Playwright SPA 爬虫示例")
    print("=" * 60)
    print("\n目标网站: https://quotes.toscrape.com/js/")
    print("这是一个需要 JavaScript 渲染的页面\n")

    async with SPACrawler(headless=True) as crawler:
        # 方法 1: 直接访问各页面 URL
        print("\n--- 方法 1: 直接访问各页面 URL ---")
        quotes = await crawler.crawl_all_pages(max_pages=3)

        # 输出部分结果
        print("\n爬取结果示例:")
        for i, quote in enumerate(quotes[:5], 1):
            print(f"\n{i}. {quote.author}")
            print(f"   \"{quote.text[:60]}...\"")
            print(f"   标签: {', '.join(quote.tags)}")

        # 保存结果
        output_file = "quotes_spa.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                [asdict(q) for q in quotes],
                f,
                ensure_ascii=False,
                indent=2
            )
        print(f"\n结果已保存到: {output_file}")

    # 统计信息
    print("\n" + "=" * 60)
    print("爬取统计")
    print("=" * 60)
    print(f"总名言数: {len(quotes)}")

    # 作者统计
    authors = {}
    for quote in quotes:
        authors[quote.author] = authors.get(quote.author, 0) + 1

    print(f"作者数量: {len(authors)}")
    print("\n出现最多的作者:")
    for author, count in sorted(authors.items(), key=lambda x: -x[1])[:5]:
        print(f"  {author}: {count} 条")

    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
