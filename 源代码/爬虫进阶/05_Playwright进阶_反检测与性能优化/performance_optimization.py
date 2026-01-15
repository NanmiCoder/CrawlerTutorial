# -*- coding: utf-8 -*-
# @Desc: Playwright 性能优化演示

import asyncio
import time
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from loguru import logger


class ResourceBlocker:
    """资源拦截器 - 阻止不必要的资源加载"""

    # 要阻止的资源类型
    BLOCKED_RESOURCE_TYPES = {
        "image",
        "media",
        "font",
        "stylesheet",
    }

    # 要阻止的 URL 模式
    BLOCKED_URL_PATTERNS = [
        "**/analytics**",
        "**/gtag/**",
        "**/google-analytics**",
        "**/facebook.com/**",
        "**/doubleclick.net/**",
        "**/*.woff",
        "**/*.woff2",
        "**/*.ttf",
    ]

    @classmethod
    async def setup(cls, context: BrowserContext):
        """设置资源拦截"""
        # 按资源类型拦截
        async def block_by_type(route):
            if route.request.resource_type in cls.BLOCKED_RESOURCE_TYPES:
                await route.abort()
            else:
                await route.continue_()

        await context.route("**/*", block_by_type)

        logger.debug("资源拦截器已设置")

    @classmethod
    async def setup_selective(cls, context: BrowserContext, allow_css: bool = False):
        """选择性资源拦截"""
        blocked_types = cls.BLOCKED_RESOURCE_TYPES.copy()
        if allow_css:
            blocked_types.discard("stylesheet")

        async def block_selective(route):
            if route.request.resource_type in blocked_types:
                await route.abort()
            else:
                await route.continue_()

        await context.route("**/*", block_selective)


class ContextPool:
    """浏览器上下文池"""

    def __init__(self, browser: Browser, pool_size: int = 3):
        self.browser = browser
        self.pool_size = pool_size
        self._contexts: List[BrowserContext] = []
        self._available: asyncio.Queue = asyncio.Queue()
        self._lock = asyncio.Lock()

    async def initialize(self, with_stealth: bool = False, block_resources: bool = True):
        """初始化上下文池"""
        for i in range(self.pool_size):
            context = await self.browser.new_context(
                viewport={"width": 1920, "height": 1080}
            )

            if block_resources:
                await ResourceBlocker.setup(context)

            if with_stealth:
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                """)

            self._contexts.append(context)
            await self._available.put(context)

        logger.info(f"上下文池初始化完成，大小: {self.pool_size}")

    async def acquire(self) -> BrowserContext:
        """获取上下文"""
        return await self._available.get()

    async def release(self, context: BrowserContext):
        """释放上下文"""
        # 清理 cookies
        await context.clear_cookies()
        await self._available.put(context)

    async def close_all(self):
        """关闭所有上下文"""
        for context in self._contexts:
            await context.close()
        self._contexts.clear()
        logger.info("所有上下文已关闭")


class OptimizedCrawler:
    """优化的爬虫"""

    def __init__(
        self,
        max_concurrent: int = 5,
        block_resources: bool = True,
        use_stealth: bool = True
    ):
        self.max_concurrent = max_concurrent
        self.block_resources = block_resources
        self.use_stealth = use_stealth

        self._browser: Optional[Browser] = None
        self._context_pool: Optional[ContextPool] = None
        self._semaphore = asyncio.Semaphore(max_concurrent)

        # 统计
        self.stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "total_time": 0.0,
        }

    async def start(self, playwright):
        """启动爬虫"""
        self._browser = await playwright.chromium.launch(headless=True)
        self._context_pool = ContextPool(self._browser, pool_size=self.max_concurrent)
        await self._context_pool.initialize(
            with_stealth=self.use_stealth,
            block_resources=self.block_resources
        )
        logger.info("优化爬虫已启动")

    async def stop(self):
        """停止爬虫"""
        if self._context_pool:
            await self._context_pool.close_all()
        if self._browser:
            await self._browser.close()
        logger.info("优化爬虫已停止")

    async def fetch(self, url: str) -> Dict:
        """获取单个页面"""
        start_time = time.time()
        self.stats["total"] += 1

        async with self._semaphore:
            context = await self._context_pool.acquire()
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                title = await page.title()
                content_length = len(await page.content())

                elapsed = time.time() - start_time
                self.stats["success"] += 1
                self.stats["total_time"] += elapsed

                return {
                    "url": url,
                    "title": title,
                    "content_length": content_length,
                    "time": elapsed,
                    "success": True
                }

            except Exception as e:
                self.stats["failed"] += 1
                return {
                    "url": url,
                    "error": str(e),
                    "success": False
                }

            finally:
                await page.close()
                await self._context_pool.release(context)

    async def fetch_batch(self, urls: List[str]) -> List[Dict]:
        """批量获取页面"""
        tasks = [self.fetch(url) for url in urls]
        return await asyncio.gather(*tasks)


async def demo_resource_blocking():
    """演示资源拦截效果"""
    print("\n" + "=" * 50)
    print("1. 资源拦截效果对比")
    print("=" * 50)

    test_url = "https://quotes.toscrape.com/"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # 不拦截资源
        context1 = await browser.new_context()
        page1 = await context1.new_page()

        start = time.time()
        await page1.goto(test_url, wait_until="load")
        time_without_blocking = time.time() - start
        await context1.close()

        # 拦截资源
        context2 = await browser.new_context()
        await ResourceBlocker.setup(context2)
        page2 = await context2.new_page()

        start = time.time()
        await page2.goto(test_url, wait_until="load")
        time_with_blocking = time.time() - start
        await context2.close()

        print(f"不拦截资源: {time_without_blocking:.2f}s")
        print(f"拦截资源:   {time_with_blocking:.2f}s")
        print(f"提升:       {(1 - time_with_blocking/time_without_blocking)*100:.1f}%")

        await browser.close()


async def demo_context_pool():
    """演示上下文池"""
    print("\n" + "=" * 50)
    print("2. 上下文池演示")
    print("=" * 50)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        pool = ContextPool(browser, pool_size=3)
        await pool.initialize()

        # 模拟并发使用
        async def use_context(task_id: int):
            context = await pool.acquire()
            page = await context.new_page()
            await page.goto("https://example.com")
            print(f"任务 {task_id}: 使用上下文完成")
            await page.close()
            await pool.release(context)

        # 启动 5 个任务（但池大小只有 3）
        tasks = [use_context(i) for i in range(5)]
        await asyncio.gather(*tasks)

        await pool.close_all()
        await browser.close()


async def demo_optimized_crawler():
    """演示优化爬虫"""
    print("\n" + "=" * 50)
    print("3. 优化爬虫演示")
    print("=" * 50)

    urls = [
        "https://quotes.toscrape.com/",
        "https://quotes.toscrape.com/page/2/",
        "https://quotes.toscrape.com/page/3/",
        "https://example.com/",
        "https://httpbin.org/html",
    ]

    async with async_playwright() as p:
        crawler = OptimizedCrawler(
            max_concurrent=3,
            block_resources=True,
            use_stealth=True
        )

        await crawler.start(p)

        try:
            results = await crawler.fetch_batch(urls)

            print("\n爬取结果:")
            for result in results:
                if result["success"]:
                    print(f"  ✓ {result['url'][:40]}... ({result['time']:.2f}s)")
                else:
                    print(f"  ✗ {result['url'][:40]}... ({result['error'][:30]})")

            print(f"\n统计:")
            print(f"  总请求: {crawler.stats['total']}")
            print(f"  成功:   {crawler.stats['success']}")
            print(f"  失败:   {crawler.stats['failed']}")
            if crawler.stats['success'] > 0:
                avg_time = crawler.stats['total_time'] / crawler.stats['success']
                print(f"  平均耗时: {avg_time:.2f}s")

        finally:
            await crawler.stop()


async def main():
    """主函数"""
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    print("=" * 50)
    print("Playwright 性能优化演示")
    print("=" * 50)

    await demo_resource_blocking()
    await demo_context_pool()
    await demo_optimized_crawler()

    print("\n" + "=" * 50)
    print("演示完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
