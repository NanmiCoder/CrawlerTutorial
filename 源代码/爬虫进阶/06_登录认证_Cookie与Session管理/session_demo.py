# -*- coding: utf-8 -*-
# @Desc: 完整的会话管理演示 - 展示如何在爬虫中管理登录状态

import asyncio
import json
from typing import Optional
from pathlib import Path
import httpx
from loguru import logger

from cookie_manager import CookieManager, CookieSerializer, CookieRotator
from login_state_checker import LoginStateChecker, CookieExpiryMonitor


class SessionCrawler:
    """带登录状态管理的爬虫"""

    def __init__(
        self,
        base_url: str,
        cookie_path: str,
        check_endpoint: str = "/api/user/info"
    ):
        """
        Args:
            base_url: 基础 URL
            cookie_path: Cookie 存储路径
            check_endpoint: 登录状态检测端点
        """
        self.base_url = base_url.rstrip("/")
        self.cookie_path = cookie_path
        self.check_endpoint = check_endpoint

        # 初始化登录检测器
        self.checker = LoginStateChecker.create_json_checker(
            check_url=f"{self.base_url}{check_endpoint}",
            success_field="user"
        )

        # 初始化 Cookie 管理器
        self.cookie_manager = CookieManager(
            storage_path=cookie_path,
            login_checker=self.checker.is_logged_in
        )

        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def start(self):
        """启动爬虫"""
        cookies = await self.cookie_manager.get_valid_cookies()
        if not cookies:
            logger.warning("无法获取有效的 Cookie，将以未登录状态运行")
            cookies = {}

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            cookies=cookies,
            timeout=30.0,
            follow_redirects=True
        )
        logger.info(f"爬虫启动成功，基础URL: {self.base_url}")

    async def close(self):
        """关闭爬虫"""
        if self._client:
            await self._client.aclose()
        await self.cookie_manager.save()
        logger.info("爬虫已关闭")

    async def get(self, endpoint: str, **kwargs) -> httpx.Response:
        """GET 请求"""
        return await self._client.get(endpoint, **kwargs)

    async def post(self, endpoint: str, **kwargs) -> httpx.Response:
        """POST 请求"""
        return await self._client.post(endpoint, **kwargs)

    async def fetch_json(self, endpoint: str) -> dict:
        """获取 JSON 数据"""
        try:
            resp = await self._client.get(endpoint)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.warning("登录状态失效，需要重新登录")
            raise


async def demo_basic_session():
    """演示基本的会话管理"""
    print("\n" + "=" * 50)
    print("1. 基本会话管理演示")
    print("=" * 50)

    # 使用 httpbin.org 演示
    async with httpx.AsyncClient() as client:
        # 设置 Cookie
        resp = await client.get(
            "https://httpbin.org/cookies/set",
            params={"session": "demo123", "user": "test"}
        )
        print(f"设置 Cookie 后的响应: {resp.status_code}")

        # 查看当前 Cookie
        resp = await client.get("https://httpbin.org/cookies")
        cookies = resp.json().get("cookies", {})
        print(f"当前 Cookie: {cookies}")


async def demo_cookie_persistence():
    """演示 Cookie 持久化"""
    print("\n" + "=" * 50)
    print("2. Cookie 持久化演示")
    print("=" * 50)

    # 创建测试 Cookie
    test_cookies = [
        {
            "name": "session_id",
            "value": "abc123xyz",
            "domain": "example.com",
            "path": "/",
            "secure": True,
            "httpOnly": True
        },
        {
            "name": "user_token",
            "value": "token_value_here",
            "domain": "example.com",
            "path": "/"
        }
    ]

    # 保存为 JSON
    json_path = "data/demo_cookies.json"
    Path("data").mkdir(exist_ok=True)
    CookieSerializer.to_json(test_cookies, json_path)
    print(f"已保存为 JSON: {json_path}")

    # 保存为 Netscape 格式
    netscape_path = "data/demo_cookies.txt"
    CookieSerializer.to_netscape(test_cookies, netscape_path)
    print(f"已保存为 Netscape: {netscape_path}")

    # 从 JSON 加载
    loaded = CookieSerializer.from_json(json_path)
    print(f"从 JSON 加载了 {len(loaded)} 个 Cookie")

    # 转换为 httpx 格式
    httpx_cookies = CookieSerializer.to_dict(loaded)
    print(f"httpx 格式: {httpx_cookies}")


async def demo_cookie_rotation():
    """演示多账号 Cookie 轮换"""
    print("\n" + "=" * 50)
    print("3. 多账号 Cookie 轮换演示")
    print("=" * 50)

    rotator = CookieRotator(min_interval=1.0)

    # 添加多个账号
    rotator.add_account("user_001", {"session": "sess_001", "token": "tok_001"})
    rotator.add_account("user_002", {"session": "sess_002", "token": "tok_002"})
    rotator.add_account("user_003", {"session": "sess_003", "token": "tok_003"})

    print(f"添加了 {rotator.total_count} 个账号")

    # 模拟多次请求
    print("\n模拟请求（负载均衡）:")
    for i in range(6):
        cookies = await rotator.get_cookies()
        if cookies:
            print(f"  请求 {i+1}: session={cookies.get('session')}")
        await asyncio.sleep(0.3)

    # 标记一个账号失效
    rotator.mark_invalid("user_002")
    print(f"\n标记 user_002 失效后，有效账号: {rotator.valid_count}")

    # 继续请求
    print("\n继续请求（排除失效账号）:")
    for i in range(3):
        cookies = await rotator.get_cookies()
        if cookies:
            print(f"  请求 {i+1}: session={cookies.get('session')}")
        await asyncio.sleep(0.3)

    # 获取统计
    stats = rotator.get_stats()
    print(f"\n统计信息:")
    for acc in stats["accounts"]:
        print(f"  {acc['id']}: 有效={acc['valid']}, 使用次数={acc['use_count']}")


async def demo_login_detection():
    """演示登录状态检测"""
    print("\n" + "=" * 50)
    print("4. 登录状态检测演示")
    print("=" * 50)

    # 使用不同的检测方式

    # 1. JSON 字段检测
    print("\n1) JSON 字段检测:")
    checker1 = LoginStateChecker.create_json_checker(
        "https://httpbin.org/json",
        "slideshow"
    )
    result = await checker1.is_logged_in({})
    print(f"   结果: {'通过' if result else '失败'}")

    # 2. 状态码检测
    print("\n2) 状态码检测:")
    checker2 = LoginStateChecker.create_status_code_checker(
        "https://httpbin.org/status/200"
    )
    result = await checker2.is_logged_in({})
    print(f"   200 状态: {'通过' if result else '失败'}")

    checker2_fail = LoginStateChecker.create_status_code_checker(
        "https://httpbin.org/status/401"
    )
    result = await checker2_fail.is_logged_in({})
    print(f"   401 状态: {'通过' if result else '失败'}")

    # 3. 内容检测
    print("\n3) 内容检测:")
    checker3 = LoginStateChecker.create_content_checker(
        "https://httpbin.org/html",
        "Herman Melville"
    )
    result = await checker3.is_logged_in({})
    print(f"   包含指定文本: {'通过' if result else '失败'}")


async def demo_expiry_monitoring():
    """演示 Cookie 过期监控"""
    print("\n" + "=" * 50)
    print("5. Cookie 过期监控演示")
    print("=" * 50)

    import time

    # 创建不同过期时间的 Cookie
    test_cookies = [
        {"name": "expired", "value": "1", "expires": time.time() - 3600},     # 已过期
        {"name": "expiring", "value": "2", "expires": time.time() + 1800},    # 30分钟后过期
        {"name": "valid", "value": "3", "expires": time.time() + 86400},      # 1天后过期
        {"name": "session", "value": "4", "expires": 0},                       # 会话 Cookie
    ]

    # 检查过期
    is_valid, expired = CookieExpiryMonitor.check_expiry(test_cookies)
    print(f"全部有效: {is_valid}")
    print(f"已过期 Cookie: {[c['name'] for c in expired]}")

    # 是否即将过期
    will_expire = CookieExpiryMonitor.will_expire_soon(test_cookies, threshold_hours=1)
    print(f"1小时内过期: {will_expire}")

    # 获取摘要
    summary = CookieExpiryMonitor.get_expiry_summary(test_cookies)
    print(f"\nCookie 摘要:")
    print(f"  总数: {summary['total']}")
    print(f"  会话 Cookie: {summary['session_cookies']}")
    print(f"  有效: {summary['valid']}")
    print(f"  已过期: {summary['expired']}")
    print(f"  即将过期: {summary['expiring_soon']}")


async def demo_real_login():
    """演示真实网站登录流程 - quotes.toscrape.com"""
    print("\n" + "=" * 50)
    print("6. 真实网站登录演示 (quotes.toscrape.com)")
    print("=" * 50)

    login_url = "https://quotes.toscrape.com/login"
    home_url = "https://quotes.toscrape.com/"

    async with httpx.AsyncClient(follow_redirects=True) as client:
        # 1. 访问登录页面
        print(f"\n1) 访问登录页面: {login_url}")
        resp = await client.get(login_url)
        print(f"   状态码: {resp.status_code}")

        # 2. 提交登录表单（quotes.toscrape.com 接受任意用户名密码）
        print("\n2) 提交登录表单...")
        login_data = {
            "username": "admin",
            "password": "admin"
        }
        resp = await client.post(login_url, data=login_data)
        print(f"   状态码: {resp.status_code}")

        # 3. 检查登录状态
        print("\n3) 检查登录状态...")
        if "Logout" in resp.text:
            print("   ✅ 登录成功！")

            # 4. 获取并显示 Cookie
            print("\n4) 获取到的 Cookie:")
            cookies_dict = dict(client.cookies)
            for name, value in cookies_dict.items():
                print(f"   {name}: {value}")

            # 5. 保存 Cookie 到文件
            print("\n5) 保存 Cookie 到文件...")
            Path("data").mkdir(exist_ok=True)
            cookie_path = "data/quotes_cookies.json"

            # 转换为标准格式
            cookies_list = [
                {
                    "name": name,
                    "value": value,
                    "domain": "quotes.toscrape.com",
                    "path": "/"
                }
                for name, value in cookies_dict.items()
            ]

            with open(cookie_path, "w") as f:
                json.dump(cookies_list, f, indent=2)
            print(f"   Cookie 已保存到: {cookie_path}")

            # 6. 测试 Cookie 复用
            print("\n6) 测试 Cookie 复用...")
            async with httpx.AsyncClient() as new_client:
                # 加载保存的 Cookie
                with open(cookie_path, "r") as f:
                    loaded_cookies = json.load(f)

                # 转换为 httpx 格式并注入
                cookies_dict = {c["name"]: c["value"] for c in loaded_cookies}
                new_client.cookies.update(cookies_dict)

                # 访问主页
                resp = await new_client.get(home_url)
                if "Logout" in resp.text:
                    print("   ✅ Cookie 复用成功！保持登录状态")
                else:
                    print("   ❌ Cookie 复用失败")

            # 7. 使用 CookieManager 管理
            print("\n7) 使用 CookieManager 管理...")

            async def check_quotes_login(cookies: dict) -> bool:
                """检查 quotes.toscrape.com 登录状态"""
                try:
                    async with httpx.AsyncClient(cookies=cookies, timeout=10) as c:
                        resp = await c.get(home_url)
                        return "Logout" in resp.text
                except Exception:
                    return False

            manager = CookieManager(
                storage_path="data/quotes_managed_cookies.json",
                login_checker=check_quotes_login
            )

            # 保存 Cookie
            manager.update(cookies_list)
            await manager.save()
            print("   Cookie 已通过 CookieManager 保存")

            # 验证并获取有效 Cookie
            valid_cookies = await manager.get_valid_cookies()
            if valid_cookies:
                print(f"   ✅ CookieManager 验证通过，获取到 {len(valid_cookies)} 个有效 Cookie")
            else:
                print("   ❌ CookieManager 验证失败")

        else:
            print("   ❌ 登录失败")

    print("\n真实登录演示完成")


async def demo_complete_workflow():
    """演示完整的工作流程"""
    print("\n" + "=" * 50)
    print("7. 完整工作流程演示")
    print("=" * 50)

    # 模拟一个完整的登录和爬取流程

    # 1. 定义检测函数
    async def check_login(cookies: dict) -> bool:
        try:
            async with httpx.AsyncClient(cookies=cookies) as client:
                resp = await client.get("https://httpbin.org/cookies", timeout=10)
                data = resp.json()
                return "session" in data.get("cookies", {})
        except Exception:
            return False

    # 2. 创建 Cookie 管理器
    manager = CookieManager(
        storage_path="data/workflow_cookies.json",
        login_checker=check_login,
        check_interval=60
    )

    # 3. 模拟已有 Cookie（实际场景中可能是从浏览器提取的）
    existing_cookies = [
        {
            "name": "session",
            "value": "workflow_session_123",
            "domain": "httpbin.org",
            "path": "/"
        }
    ]
    manager.update(existing_cookies)
    await manager.save()
    print("已保存初始 Cookie")

    # 4. 获取有效 Cookie 并使用
    cookies = await manager.get_valid_cookies()
    if cookies:
        print(f"获取到有效 Cookie: {cookies}")

        # 使用 Cookie 发起请求
        async with httpx.AsyncClient(cookies=cookies) as client:
            resp = await client.get("https://httpbin.org/cookies")
            print(f"请求结果: {resp.json()}")
    else:
        print("Cookie 无效或不存在")

    print("\n工作流程演示完成")


async def main():
    """主函数"""
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    print("=" * 50)
    print("Cookie 与 Session 管理演示")
    print("=" * 50)

    await demo_basic_session()
    await demo_cookie_persistence()
    await demo_cookie_rotation()
    await demo_login_detection()
    await demo_expiry_monitoring()
    await demo_real_login()  # 新增：真实登录演示
    await demo_complete_workflow()

    print("\n" + "=" * 50)
    print("所有演示完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
