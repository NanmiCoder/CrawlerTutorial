# -*- coding: utf-8 -*-
# @Desc: Playwright 等待策略详解

import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from loguru import logger


async def demo_auto_waiting():
    """演示自动等待"""
    print("\n" + "=" * 50)
    print("1. 自动等待机制")
    print("=" * 50)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto("https://quotes.toscrape.com/login")

            # Playwright 的操作会自动等待元素可操作
            # 以下操作会自动等待:
            # - 元素存在于 DOM
            # - 元素可见
            # - 元素稳定（不在动画中）
            # - 元素可接收事件
            # - 元素没有被其他元素遮挡

            print("自动等待 - 填充用户名...")
            await page.fill("input#username", "test")
            print("自动等待 - 成功")

            print("自动等待 - 点击登录...")
            await page.click("input[type='submit']")
            print("自动等待 - 成功")

        finally:
            await browser.close()


async def demo_wait_for_selector():
    """演示 wait_for_selector"""
    print("\n" + "=" * 50)
    print("2. wait_for_selector 用法")
    print("=" * 50)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto("https://quotes.toscrape.com/")

            # 等待元素出现（默认 state="visible"）
            element = await page.wait_for_selector("div.quote")
            print(f"等待 visible - 找到元素")

            # 等待元素附加到 DOM（不管是否可见）
            element = await page.wait_for_selector("div.quote", state="attached")
            print(f"等待 attached - 找到元素")

            # 等待元素消失
            # await page.wait_for_selector("div.loading", state="hidden")
            print(f"等待 hidden - 跳过（页面无 loading 元素）")

            # 等待元素从 DOM 移除
            # await page.wait_for_selector("div.temp", state="detached")
            print(f"等待 detached - 跳过")

        finally:
            await browser.close()


async def demo_wait_for_load_state():
    """演示 wait_for_load_state"""
    print("\n" + "=" * 50)
    print("3. wait_for_load_state 用法")
    print("=" * 50)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # 导航并等待 DOM 加载
            print("导航到页面...")
            await page.goto("https://quotes.toscrape.com/")

            # 等待 domcontentloaded - DOM 解析完成
            await page.wait_for_load_state("domcontentloaded")
            print("domcontentloaded - 完成")

            # 等待 load - 所有资源加载完成
            await page.wait_for_load_state("load")
            print("load - 完成")

            # 等待 networkidle - 网络空闲（500ms 无新请求）
            await page.wait_for_load_state("networkidle")
            print("networkidle - 完成")

        finally:
            await browser.close()


async def demo_wait_for_url():
    """演示 wait_for_url"""
    print("\n" + "=" * 50)
    print("4. wait_for_url 用法")
    print("=" * 50)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto("https://quotes.toscrape.com/login")

            # 填写登录表单
            await page.fill("input#username", "test")
            await page.fill("input#password", "test")
            await page.click("input[type='submit']")

            # 等待 URL 变化（使用 glob 模式）
            await page.wait_for_url("**/")
            print(f"URL 已变化到: {page.url}")

            # 也可以使用函数
            # await page.wait_for_url(lambda url: "quotes" in url)

        finally:
            await browser.close()


async def demo_wait_for_function():
    """演示 wait_for_function"""
    print("\n" + "=" * 50)
    print("5. wait_for_function 用法")
    print("=" * 50)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto("https://quotes.toscrape.com/")

            # 等待 JavaScript 条件为真
            await page.wait_for_function(
                "document.querySelectorAll('.quote').length > 0"
            )
            print("等待 JS 条件 - 名言已加载")

            # 等待特定元素数量
            await page.wait_for_function(
                "document.querySelectorAll('.quote').length >= 10"
            )
            print("等待 JS 条件 - 至少 10 条名言")

            # 等待全局变量
            # await page.wait_for_function("window.dataLoaded === true")

        finally:
            await browser.close()


async def demo_expect_patterns():
    """演示 expect 模式（等待请求/响应）"""
    print("\n" + "=" * 50)
    print("6. expect 模式（等待请求/响应）")
    print("=" * 50)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # 等待响应
            async with page.expect_response("**/api/**") as response_info:
                # 这个例子使用的网站没有 API，所以会超时
                # 实际使用时，这里会等待匹配的响应
                pass
            # response = await response_info.value

            print("expect_response - 跳过（示例网站无 API）")

            # 正常访问
            await page.goto("https://quotes.toscrape.com/")

            # 等待导航
            async with page.expect_navigation():
                await page.click("a[href='/page/2/']")
            print(f"expect_navigation - 导航到: {page.url}")

        except PlaywrightTimeout:
            print("超时 - 这是预期行为（示例网站无 API）")

        finally:
            await browser.close()


async def demo_timeout_handling():
    """演示超时处理"""
    print("\n" + "=" * 50)
    print("7. 超时处理")
    print("=" * 50)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto("https://quotes.toscrape.com/")

            # 设置默认超时
            page.set_default_timeout(5000)  # 5 秒
            print("设置默认超时: 5秒")

            # 单次操作超时
            try:
                await page.wait_for_selector(
                    "div.not-exist",
                    timeout=2000  # 2 秒
                )
            except PlaywrightTimeout:
                print("捕获超时异常 - 元素不存在")

            # 使用 try-except 处理可能的超时
            try:
                await page.click("button.maybe-exist", timeout=1000)
            except PlaywrightTimeout:
                print("捕获超时异常 - 按钮不存在")
            except Exception as e:
                print(f"捕获其他异常: {type(e).__name__}")

        finally:
            await browser.close()


async def main():
    """主函数"""
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>",
        level="INFO"
    )

    print("=" * 50)
    print("Playwright 等待策略详解")
    print("=" * 50)

    await demo_auto_waiting()
    await demo_wait_for_selector()
    await demo_wait_for_load_state()
    await demo_wait_for_url()
    await demo_wait_for_function()
    await demo_expect_patterns()
    await demo_timeout_handling()

    print("\n" + "=" * 50)
    print("演示完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
