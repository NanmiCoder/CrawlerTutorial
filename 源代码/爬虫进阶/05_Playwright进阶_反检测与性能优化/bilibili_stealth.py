# -*- coding: utf-8 -*-
"""
B站 Playwright 反检测配置

本模块展示如何配置 Playwright 以绕过 B站的反自动化检测，包括：
- 隐藏 webdriver 标志
- 模拟真实浏览器环境
- 性能优化配置
- Cookie 管理

这是第05章"Playwright进阶-反检测与性能优化"的B站实战示例。

与第11章综合实战项目的关联：
- core/browser.py: BrowserManager 使用相同的反检测技术
"""

import asyncio
import os
from typing import Optional, Set

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Route
from loguru import logger


# B站专用 stealth 脚本
BILIBILI_STEALTH_JS = """
// 隐藏 webdriver 标志
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});

// 模拟 Chrome 对象
window.chrome = {
    runtime: {},
    loadTimes: function() {},
    csi: function() {},
    app: {}
};

// 模拟正常的插件列表
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const plugins = [
            {
                name: 'Chrome PDF Plugin',
                description: 'Portable Document Format',
                filename: 'internal-pdf-viewer'
            },
            {
                name: 'Chrome PDF Viewer',
                description: '',
                filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'
            },
            {
                name: 'Native Client',
                description: '',
                filename: 'internal-nacl-plugin'
            }
        ];
        plugins.item = (i) => plugins[i];
        plugins.namedItem = (name) => plugins.find(p => p.name === name);
        plugins.refresh = () => {};
        return plugins;
    }
});

// 模拟语言设置
Object.defineProperty(navigator, 'languages', {
    get: () => ['zh-CN', 'zh', 'en-US', 'en']
});

// 修复 permissions API
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters)
);

// 模拟硬件并发数
Object.defineProperty(navigator, 'hardwareConcurrency', {
    get: () => 8
});

// 模拟设备内存
Object.defineProperty(navigator, 'deviceMemory', {
    get: () => 8
});

// 隐藏自动化相关属性
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
"""


class BilibiliStealthBrowser:
    """
    B站反检测浏览器封装

    特性：
    - 自动注入 stealth 脚本
    - 模拟真实浏览器环境
    - 支持资源优化
    - Cookie 管理
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def start(self) -> BrowserContext:
        """启动浏览器并创建反检测上下文"""
        self._playwright = await async_playwright().start()

        # 启动浏览器，添加反检测参数
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-size=1920,1080",
                "--start-maximized",
            ]
        )

        # 创建上下文
        self._context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/131.0.0.0 Safari/537.36",
            extra_http_headers={
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
        )

        # 注入 stealth 脚本
        await self._context.add_init_script(BILIBILI_STEALTH_JS)

        logger.info("B站反检测浏览器已启动")
        return self._context

    async def create_page(self) -> Page:
        """创建普通页面"""
        if not self._context:
            raise RuntimeError("浏览器未启动，请先调用 start()")
        return await self._context.new_page()

    async def create_optimized_page(self) -> Page:
        """创建性能优化的页面（禁用图片/字体等资源）"""
        if not self._context:
            raise RuntimeError("浏览器未启动，请先调用 start()")

        page = await self._context.new_page()

        # 禁用不必要的资源
        await page.route("**/*.{png,jpg,jpeg,gif,webp,svg,ico}", lambda r: r.abort())
        await page.route("**/*.{woff,woff2,ttf,otf,eot}", lambda r: r.abort())
        await page.route("**/analytics**", lambda r: r.abort())
        await page.route("**/tracking**", lambda r: r.abort())

        return page

    async def save_cookies(self, path: str):
        """保存 Cookie 到文件"""
        if self._context:
            await self._context.storage_state(path=path)
            logger.info(f"Cookie 已保存到: {path}")

    async def load_cookies(self, path: str):
        """从文件加载 Cookie"""
        if os.path.exists(path):
            # 需要重新创建 context
            if self._context:
                await self._context.close()

            self._context = await self._browser.new_context(
                storage_state=path,
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN"
            )
            await self._context.add_init_script(BILIBILI_STEALTH_JS)
            logger.info(f"Cookie 已从 {path} 加载")

    async def stop(self):
        """关闭浏览器"""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("浏览器已关闭")


class BilibiliOptimizedCrawler:
    """
    B站性能优化爬虫

    优化策略：
    - 禁用图片/字体/CSS加载
    - 拦截广告和追踪脚本
    - 复用浏览器上下文
    """

    # 需要拦截的资源模式
    BLOCK_PATTERNS: Set[str] = {
        "**/cm.bilibili.com/**",      # 广告
        "**/api.bilibili.com/x/web-show/**",  # 广告
        "**/*.gif",
        "**/*.png",
        "**/*.jpg",
        "**/*.jpeg",
        "**/*.webp",
        "**/*.woff*",
        "**/*.ttf",
    }

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._browser = BilibiliStealthBrowser(headless=headless)
        self._page: Optional[Page] = None

    async def start(self):
        """启动爬虫"""
        await self._browser.start()
        self._page = await self._browser.create_page()

        # 设置资源拦截
        async def handle_route(route: Route):
            for pattern in ["cm.bilibili.com", "web-show", "tracking"]:
                if pattern in route.request.url:
                    await route.abort()
                    return
            await route.continue_()

        await self._page.route("**/*", handle_route)
        logger.info("性能优化爬虫已启动")

    async def get_video_info(self, bvid: str) -> Optional[dict]:
        """获取视频详情"""
        if not self._page:
            raise RuntimeError("爬虫未启动")

        url = f"https://www.bilibili.com/video/{bvid}"
        logger.info(f"获取视频详情: {bvid}")

        try:
            await self._page.goto(url, wait_until="domcontentloaded")

            # 等待标题加载
            await self._page.wait_for_selector("h1.video-title", timeout=10000)

            # 提取信息
            title = await self._page.locator("h1.video-title").text_content()
            author = await self._page.locator(".up-name").text_content()

            return {
                "bvid": bvid,
                "title": title.strip() if title else "",
                "author": author.strip() if author else "",
                "url": url
            }

        except Exception as e:
            logger.error(f"获取视频详情失败: {e}")
            return None

    async def stop(self):
        """停止爬虫"""
        await self._browser.stop()


async def test_bilibili_stealth():
    """测试B站反检测效果"""
    browser = BilibiliStealthBrowser(headless=True)
    context = await browser.start()

    try:
        page = await browser.create_optimized_page()

        # 访问B站首页
        logger.info("访问B站首页...")
        await page.goto("https://www.bilibili.com", wait_until="networkidle")

        # 检查反检测效果
        webdriver = await page.evaluate("navigator.webdriver")
        chrome = await page.evaluate("!!window.chrome")
        plugins = await page.evaluate("navigator.plugins.length")

        logger.info(f"反检测检查:")
        logger.info(f"  - navigator.webdriver: {webdriver}")
        logger.info(f"  - window.chrome 存在: {chrome}")
        logger.info(f"  - plugins 数量: {plugins}")

        # 等待视频卡片加载
        await page.wait_for_selector(".bili-video-card", timeout=10000)
        cards = await page.locator(".bili-video-card").count()
        logger.info(f"成功加载 {cards} 个视频卡片")

        # 截图
        await page.screenshot(path="bilibili_stealth_test.png")
        logger.info("截图已保存: bilibili_stealth_test.png")

    finally:
        await browser.stop()


async def main():
    """主演示函数"""
    logger.info("=" * 50)
    logger.info("B站 Playwright 反检测示例")
    logger.info("=" * 50)

    await test_bilibili_stealth()


if __name__ == "__main__":
    asyncio.run(main())
