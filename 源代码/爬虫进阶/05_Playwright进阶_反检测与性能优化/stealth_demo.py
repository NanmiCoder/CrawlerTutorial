# -*- coding: utf-8 -*-
# @Desc: Playwright stealth 反检测演示

import asyncio
from playwright.async_api import async_playwright
from loguru import logger


# stealth.min.js 核心脚本（简化版）
# 实际使用时建议使用完整的 stealth.min.js
STEALTH_JS_MINIMAL = """
// 1. 隐藏 webdriver 标志
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});

// 2. 模拟 Chrome 对象
window.chrome = {
    runtime: {},
    loadTimes: function() {},
    csi: function() {},
    app: {}
};

// 3. 模拟 plugins 列表
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const plugins = [
            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
            { name: 'Native Client', filename: 'internal-nacl-plugin' }
        ];
        plugins.length = 3;
        return plugins;
    }
});

// 4. 模拟 languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['zh-CN', 'zh', 'en-US', 'en']
});

// 5. 修复 permissions API
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);

// 6. 隐藏 automation 标志
if (navigator.userAgentData) {
    Object.defineProperty(navigator.userAgentData, 'brands', {
        get: () => [
            { brand: 'Google Chrome', version: '120' },
            { brand: 'Chromium', version: '120' },
            { brand: 'Not_A Brand', version: '8' }
        ]
    });
}

// 7. 修复 iframe contentWindow
const originalAttachShadow = Element.prototype.attachShadow;
Element.prototype.attachShadow = function(init) {
    if (init.mode === 'closed') {
        init.mode = 'open';
    }
    return originalAttachShadow.call(this, init);
};

console.log('Stealth script injected!');
"""


async def create_stealth_browser(playwright, headless: bool = True):
    """
    创建带反检测的浏览器实例

    Args:
        playwright: playwright 实例
        headless: 是否无头模式

    Returns:
        配置好的浏览器实例
    """
    browser = await playwright.chromium.launch(
        headless=headless,
        args=[
            '--disable-blink-features=AutomationControlled',  # 禁用自动化控制特征
            '--disable-dev-shm-usage',
            '--no-sandbox',
        ]
    )
    return browser


async def create_stealth_context(browser, stealth_js: str = None):
    """
    创建带反检测的浏览器上下文

    Args:
        browser: 浏览器实例
        stealth_js: stealth 脚本内容

    Returns:
        配置好的上下文
    """
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent=(
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
        locale='zh-CN',
        timezone_id='Asia/Shanghai',
    )

    # 注入 stealth 脚本
    js = stealth_js or STEALTH_JS_MINIMAL
    await context.add_init_script(js)

    return context


async def test_detection(page, test_url: str = "https://bot.sannysoft.com/"):
    """
    测试反检测效果

    Args:
        page: 页面实例
        test_url: 检测网站 URL
    """
    logger.info(f"访问检测网站: {test_url}")
    await page.goto(test_url, wait_until="networkidle")

    # 检查关键指标
    checks = {
        "webdriver": await page.evaluate("navigator.webdriver"),
        "chrome": await page.evaluate("!!window.chrome"),
        "plugins_length": await page.evaluate("navigator.plugins.length"),
        "languages": await page.evaluate("navigator.languages"),
    }

    logger.info("检测结果:")
    for key, value in checks.items():
        status = "✓" if _check_passed(key, value) else "✗"
        logger.info(f"  {status} {key}: {value}")

    # 保存截图
    await page.screenshot(path="stealth_test_result.png", full_page=True)
    logger.info("截图已保存: stealth_test_result.png")


def _check_passed(key: str, value) -> bool:
    """检查是否通过"""
    if key == "webdriver":
        return value is None or value == "undefined"
    elif key == "chrome":
        return value is True
    elif key == "plugins_length":
        return value > 0
    elif key == "languages":
        return len(value) > 0
    return True


async def demo_without_stealth():
    """演示没有 stealth 的情况"""
    print("\n" + "=" * 50)
    print("1. 没有 stealth 的浏览器")
    print("=" * 50)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto("https://bot.sannysoft.com/", wait_until="networkidle")

        # 检查 webdriver
        webdriver = await page.evaluate("navigator.webdriver")
        chrome = await page.evaluate("!!window.chrome")

        print(f"navigator.webdriver: {webdriver}")
        print(f"window.chrome exists: {chrome}")

        await page.screenshot(path="no_stealth.png", full_page=True)
        print("截图已保存: no_stealth.png")

        await browser.close()


async def demo_with_stealth():
    """演示使用 stealth 的情况"""
    print("\n" + "=" * 50)
    print("2. 使用 stealth 的浏览器")
    print("=" * 50)

    async with async_playwright() as p:
        browser = await create_stealth_browser(p, headless=True)
        context = await create_stealth_context(browser)
        page = await context.new_page()

        await test_detection(page)

        await browser.close()


async def demo_custom_stealth():
    """演示自定义 stealth 配置"""
    print("\n" + "=" * 50)
    print("3. 自定义 stealth 配置")
    print("=" * 50)

    # 可以根据需要添加更多的规避代码
    custom_stealth = STEALTH_JS_MINIMAL + """
    // 额外的自定义规避
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => 8
    });

    Object.defineProperty(navigator, 'deviceMemory', {
        get: () => 8
    });

    Object.defineProperty(screen, 'colorDepth', {
        get: () => 24
    });
    """

    async with async_playwright() as p:
        browser = await create_stealth_browser(p, headless=True)
        context = await create_stealth_context(browser, custom_stealth)
        page = await context.new_page()

        # 检查自定义属性
        await page.goto("about:blank")

        hardware = await page.evaluate("navigator.hardwareConcurrency")
        memory = await page.evaluate("navigator.deviceMemory")
        color_depth = await page.evaluate("screen.colorDepth")

        print(f"hardwareConcurrency: {hardware}")
        print(f"deviceMemory: {memory}")
        print(f"colorDepth: {color_depth}")

        await browser.close()


async def main():
    """主函数"""
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    print("=" * 50)
    print("Playwright Stealth 反检测演示")
    print("=" * 50)

    await demo_without_stealth()
    await demo_with_stealth()
    await demo_custom_stealth()

    print("\n" + "=" * 50)
    print("演示完成")
    print("=" * 50)
    print("\n提示: 查看生成的截图文件对比效果")


if __name__ == "__main__":
    asyncio.run(main())
