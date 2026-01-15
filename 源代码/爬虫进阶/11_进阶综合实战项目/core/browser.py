# -*- coding: utf-8 -*-
# @Desc: 浏览器管理模块

from typing import Optional
from loguru import logger

# 可选依赖
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    logger.warning("playwright 未安装")

# stealth.min.js 内容（简化版）
STEALTH_JS = """
// 隐藏 webdriver 属性
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});

// 修改 plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5]
});

// 修改 languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['zh-CN', 'zh', 'en']
});

// 修改 platform
Object.defineProperty(navigator, 'platform', {
    get: () => 'MacIntel'
});

// 隐藏 automation 特征
window.chrome = {
    runtime: {}
};

// 修改 permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);
"""


class BrowserManager:
    """浏览器管理器"""

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30000,
        user_data_dir: str = None,
        proxy: str = None
    ):
        """
        初始化浏览器管理器

        Args:
            headless: 是否无头模式
            timeout: 默认超时时间（毫秒）
            user_data_dir: 用户数据目录
            proxy: 代理服务器地址
        """
        if not HAS_PLAYWRIGHT:
            raise ImportError("请安装 playwright: pip install playwright && playwright install")

        self.headless = headless
        self.timeout = timeout
        self.user_data_dir = user_data_dir
        self.proxy = proxy

        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def start(self) -> BrowserContext:
        """启动浏览器"""
        self._playwright = await async_playwright().start()

        # 浏览器启动参数
        launch_args = [
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-dev-shm-usage',
        ]

        # 启动浏览器
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=launch_args
        )

        # 创建上下文
        context_options = {
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/131.0.0.0 Safari/537.36'
            ),
            'locale': 'zh-CN',
            'timezone_id': 'Asia/Shanghai',
        }

        if self.proxy:
            context_options['proxy'] = {'server': self.proxy}

        self._context = await self._browser.new_context(**context_options)

        # 注入反检测脚本
        await self._context.add_init_script(STEALTH_JS)

        logger.info("浏览器启动成功")
        return self._context

    async def new_page(self) -> 'Page':
        """创建新页面"""
        if not self._context:
            await self.start()
        page = await self._context.new_page()
        page.set_default_timeout(self.timeout)
        return page

    async def close(self):
        """关闭浏览器"""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("浏览器已关闭")

    @property
    def context(self) -> Optional[BrowserContext]:
        """获取浏览器上下文"""
        return self._context

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
