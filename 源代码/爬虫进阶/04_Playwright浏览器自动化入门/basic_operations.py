# -*- coding: utf-8 -*-
# @Desc: Playwright 基础操作演示

import asyncio
from playwright.async_api import async_playwright
from loguru import logger


async def demo_navigation():
    """演示页面导航"""
    print("\n" + "=" * 50)
    print("1. 页面导航演示")
    print("=" * 50)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # 基本导航
            logger.info("访问 example.com...")
            await page.goto("https://example.com")
            print(f"页面标题: {await page.title()}")
            print(f"当前 URL: {page.url}")

            # 使用不同的等待策略
            logger.info("使用 networkidle 等待策略...")
            await page.goto(
                "https://quotes.toscrape.com/",
                wait_until="networkidle"
            )
            print(f"页面标题: {await page.title()}")

        finally:
            await browser.close()


async def demo_locators():
    """演示元素定位"""
    print("\n" + "=" * 50)
    print("2. 元素定位演示")
    print("=" * 50)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto("https://quotes.toscrape.com/")

            # 使用 CSS 选择器
            title = await page.locator("h1 a").text_content()
            print(f"CSS 选择器 - 标题: {title}")

            # 使用 text 定位
            about_link = page.get_by_text("About")
            print(f"Text 定位 - About 链接存在: {await about_link.count() > 0}")

            # 使用 role 定位
            links = page.get_by_role("link")
            print(f"Role 定位 - 链接数量: {await links.count()}")

            # 组合定位
            first_quote = page.locator("div.quote").first
            author = await first_quote.locator("small.author").text_content()
            print(f"组合定位 - 第一条名言作者: {author}")

            # 获取所有元素
            quotes = await page.locator("div.quote").all()
            print(f"共找到 {len(quotes)} 条名言")

        finally:
            await browser.close()


async def demo_interactions():
    """演示交互操作"""
    print("\n" + "=" * 50)
    print("3. 交互操作演示")
    print("=" * 50)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # 访问登录页面
            await page.goto("https://quotes.toscrape.com/login")
            logger.info("访问登录页面")

            # 输入用户名
            await page.fill("input#username", "testuser")
            print("输入用户名: testuser")

            # 输入密码
            await page.fill("input#password", "testpass")
            print("输入密码: ******")

            # 点击登录按钮
            await page.click("input[type='submit']")
            print("点击登录按钮")

            # 等待页面跳转
            await page.wait_for_load_state("networkidle")
            print(f"登录后 URL: {page.url}")

        finally:
            await browser.close()


async def demo_content_extraction():
    """演示内容提取"""
    print("\n" + "=" * 50)
    print("4. 内容提取演示")
    print("=" * 50)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto("https://quotes.toscrape.com/")

            # 提取文本内容
            quotes_data = []
            quotes = await page.locator("div.quote").all()

            for quote in quotes[:3]:  # 只取前 3 条
                text = await quote.locator("span.text").text_content()
                author = await quote.locator("small.author").text_content()
                tags = await quote.locator("a.tag").all_text_contents()

                quotes_data.append({
                    "text": text[:60] + "..." if len(text) > 60 else text,
                    "author": author,
                    "tags": tags
                })

            print("\n提取的名言数据:")
            for i, item in enumerate(quotes_data, 1):
                print(f"\n{i}. {item['author']}")
                print(f"   {item['text']}")
                print(f"   标签: {', '.join(item['tags'])}")

            # 获取属性
            first_link = page.locator("div.quote a.tag").first
            href = await first_link.get_attribute("href")
            print(f"\n第一个标签链接: {href}")

            # 执行 JavaScript
            title = await page.evaluate("document.title")
            print(f"通过 JS 获取标题: {title}")

        finally:
            await browser.close()


async def demo_waiting():
    """演示等待策略"""
    print("\n" + "=" * 50)
    print("5. 等待策略演示")
    print("=" * 50)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # 设置默认超时
            page.set_default_timeout(30000)
            logger.info("设置默认超时: 30秒")

            # 访问页面
            await page.goto("https://quotes.toscrape.com/")

            # 等待选择器
            await page.wait_for_selector("div.quote")
            print("等待 div.quote 出现 - 成功")

            # 等待页面状态
            await page.wait_for_load_state("networkidle")
            print("等待 networkidle - 成功")

            # 单次操作超时
            try:
                await page.wait_for_selector("div.not-exist", timeout=2000)
            except Exception as e:
                print(f"等待不存在的元素 - 超时 (预期行为)")

        finally:
            await browser.close()


async def demo_screenshot():
    """演示截图功能"""
    print("\n" + "=" * 50)
    print("6. 截图功能演示")
    print("=" * 50)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto("https://quotes.toscrape.com/")

            # 页面截图
            await page.screenshot(path="screenshot_viewport.png")
            print("视口截图已保存: screenshot_viewport.png")

            # 全页面截图
            await page.screenshot(path="screenshot_fullpage.png", full_page=True)
            print("全页面截图已保存: screenshot_fullpage.png")

            # 元素截图
            first_quote = page.locator("div.quote").first
            await first_quote.screenshot(path="screenshot_element.png")
            print("元素截图已保存: screenshot_element.png")

        finally:
            await browser.close()


async def main():
    """主函数"""
    # 配置日志
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>",
        level="INFO"
    )

    print("=" * 50)
    print("Playwright 基础操作演示")
    print("=" * 50)

    # 运行所有演示
    await demo_navigation()
    await demo_locators()
    await demo_interactions()
    await demo_content_extraction()
    await demo_waiting()
    await demo_screenshot()

    print("\n" + "=" * 50)
    print("演示完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
