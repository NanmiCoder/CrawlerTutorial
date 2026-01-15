# -*- coding: utf-8 -*-
# @Desc: Playwright CDP 模式演示

import asyncio
import base64
from playwright.async_api import async_playwright
from loguru import logger


async def demo_cdp_session():
    """演示 CDP Session 基本用法"""
    print("\n" + "=" * 50)
    print("1. CDP Session 基本用法")
    print("=" * 50)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # 创建 CDP Session
        client = await context.new_cdp_session(page)

        # 启用网络事件
        await client.send("Network.enable")

        # 获取性能指标
        await page.goto("https://example.com")
        metrics = await client.send("Performance.getMetrics")

        print("性能指标:")
        for metric in metrics.get("metrics", [])[:5]:
            print(f"  {metric['name']}: {metric['value']:.2f}")

        await browser.close()


async def demo_network_emulation():
    """演示网络条件模拟"""
    print("\n" + "=" * 50)
    print("2. 网络条件模拟")
    print("=" * 50)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        client = await context.new_cdp_session(page)

        # 启用网络
        await client.send("Network.enable")

        # 模拟慢速网络（3G）
        await client.send("Network.emulateNetworkConditions", {
            "offline": False,
            "downloadThroughput": 750 * 1024 / 8,  # 750 Kbps
            "uploadThroughput": 250 * 1024 / 8,    # 250 Kbps
            "latency": 100  # 100ms
        })

        print("已设置 3G 网络条件")

        # 测试加载时间
        import time
        start = time.time()
        await page.goto("https://example.com", wait_until="load")
        elapsed = time.time() - start
        print(f"加载时间 (3G): {elapsed:.2f}s")

        # 恢复正常网络
        await client.send("Network.emulateNetworkConditions", {
            "offline": False,
            "downloadThroughput": -1,  # 不限制
            "uploadThroughput": -1,
            "latency": 0
        })

        start = time.time()
        await page.reload(wait_until="load")
        elapsed = time.time() - start
        print(f"加载时间 (正常): {elapsed:.2f}s")

        await browser.close()


async def demo_cdp_screenshot():
    """演示 CDP 截图"""
    print("\n" + "=" * 50)
    print("3. CDP 截图（高级选项）")
    print("=" * 50)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        client = await context.new_cdp_session(page)

        await page.goto("https://quotes.toscrape.com/")

        # 使用 CDP 截取完整页面
        result = await client.send("Page.captureScreenshot", {
            "format": "png",
            "captureBeyondViewport": True,  # 捕获视口外内容
            "fromSurface": True
        })

        # 保存截图
        image_data = base64.b64decode(result["data"])
        with open("cdp_screenshot.png", "wb") as f:
            f.write(image_data)

        print("CDP 截图已保存: cdp_screenshot.png")

        await browser.close()


async def demo_cdp_dom():
    """演示 CDP DOM 操作"""
    print("\n" + "=" * 50)
    print("4. CDP DOM 操作")
    print("=" * 50)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        client = await context.new_cdp_session(page)

        await page.goto("https://quotes.toscrape.com/")

        # 启用 DOM
        await client.send("DOM.enable")

        # 获取文档
        doc = await client.send("DOM.getDocument")
        root_node_id = doc["root"]["nodeId"]

        # 查询选择器
        result = await client.send("DOM.querySelectorAll", {
            "nodeId": root_node_id,
            "selector": "div.quote"
        })

        print(f"找到 {len(result['nodeIds'])} 个 quote 元素")

        # 获取第一个元素的 HTML
        if result["nodeIds"]:
            outer_html = await client.send("DOM.getOuterHTML", {
                "nodeId": result["nodeIds"][0]
            })
            print(f"第一个元素 HTML 长度: {len(outer_html['outerHTML'])} 字符")

        await browser.close()


async def demo_cdp_cookies():
    """演示 CDP Cookie 操作"""
    print("\n" + "=" * 50)
    print("5. CDP Cookie 操作")
    print("=" * 50)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        client = await context.new_cdp_session(page)

        # 启用网络
        await client.send("Network.enable")

        await page.goto("https://quotes.toscrape.com/login")

        # 获取所有 cookies
        cookies = await client.send("Network.getAllCookies")
        print(f"当前 Cookies 数量: {len(cookies['cookies'])}")

        # 设置自定义 cookie
        await client.send("Network.setCookie", {
            "name": "custom_cookie",
            "value": "test_value",
            "domain": "quotes.toscrape.com",
            "path": "/"
        })

        # 再次获取
        cookies = await client.send("Network.getAllCookies")
        print(f"添加后 Cookies 数量: {len(cookies['cookies'])}")

        for cookie in cookies['cookies']:
            print(f"  {cookie['name']}: {cookie['value'][:20]}...")

        await browser.close()


async def demo_connect_existing():
    """演示连接已有浏览器（需要手动启动 Chrome）"""
    print("\n" + "=" * 50)
    print("6. 连接已有浏览器")
    print("=" * 50)

    print("此功能需要先手动启动带调试端口的 Chrome:")
    print("  chrome --remote-debugging-port=9222")
    print("")
    print("跳过此演示...")

    # 实际代码:
    # async with async_playwright() as p:
    #     browser = await p.chromium.connect_over_cdp("http://localhost:9222")
    #     contexts = browser.contexts
    #     if contexts:
    #         page = contexts[0].pages[0]
    #         print(f"已连接到: {page.url}")
    #     await browser.close()


async def main():
    """主函数"""
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    print("=" * 50)
    print("Playwright CDP 模式演示")
    print("=" * 50)

    await demo_cdp_session()
    await demo_network_emulation()
    await demo_cdp_screenshot()
    await demo_cdp_dom()
    await demo_cdp_cookies()
    await demo_connect_existing()

    print("\n" + "=" * 50)
    print("演示完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
