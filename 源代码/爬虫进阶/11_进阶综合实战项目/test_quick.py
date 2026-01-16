# -*- coding: utf-8 -*-
# 快速测试脚本 - 只爬取1页数据验证功能

import asyncio
import sys
from pathlib import Path
from loguru import logger

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.browser import BrowserManager
from crawler.spider import ContentCrawler

# 配置简单日志
logger.remove()
logger.add(sys.stderr, level="INFO")


async def quick_test():
    """快速测试"""
    logger.info("开始快速测试 books.toscrape.com")

    browser = BrowserManager(headless=True, timeout=30000)

    try:
        async with browser:
            context = await browser.start()
            page = await browser.new_page()

            # 创建爬虫 - 只爬取1页数据
            crawler = ContentCrawler(
                start_url="http://books.toscrape.com/catalogue/page-1.html",
                item_selector="article.product_pod",
                fields={
                    "title": "h3 a|title",
                    "price": ".price_color",
                    "rating": ".star-rating|class",
                    "availability": ".availability",
                    "link": "h3 a|href",
                },
                next_page_selector=".next a",
                max_pages=1,  # 只爬取1页
                delay_min=0.5,
                delay_max=1.0
            )

            logger.info("开始爬取...")
            results = await crawler.crawl(page)

            logger.info(f"爬取完成: {len(results)} 条数据")

            if results:
                logger.info("第一条数据示例:")
                logger.info(results[0])
                logger.success("✅ 测试成功！")
                return True
            else:
                logger.error("❌ 没有爬取到数据")
                return False

    except Exception as e:
        logger.exception(f"测试失败: {e}")
        return False


if __name__ == "__main__":
    result = asyncio.run(quick_test())
    sys.exit(0 if result else 1)
