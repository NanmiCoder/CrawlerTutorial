# -*- coding: utf-8 -*-
# @Desc: 登录状态检测器 - 支持多种检测方式

import asyncio
import time
from typing import Callable, Optional
from datetime import datetime, timedelta
import httpx
from loguru import logger


class LoginStateChecker:
    """登录状态检测器"""

    def __init__(
        self,
        check_url: str,
        success_indicator: Callable[[httpx.Response], bool],
        timeout: float = 10.0
    ):
        """
        Args:
            check_url: 用于检测登录状态的 URL
            success_indicator: 判断是否登录成功的函数，接收响应对象
            timeout: 请求超时时间
        """
        self.check_url = check_url
        self.success_indicator = success_indicator
        self.timeout = timeout

    async def is_logged_in(self, cookies: dict) -> bool:
        """
        检查是否已登录

        Args:
            cookies: Cookie 字典

        Returns:
            是否已登录
        """
        try:
            async with httpx.AsyncClient(cookies=cookies, follow_redirects=True) as client:
                resp = await client.get(self.check_url, timeout=self.timeout)
                return self.success_indicator(resp)
        except httpx.TimeoutException:
            logger.warning(f"登录状态检测超时: {self.check_url}")
            return False
        except Exception as e:
            logger.warning(f"登录状态检测失败: {e}")
            return False

    @classmethod
    def create_json_checker(
        cls,
        check_url: str,
        success_field: str,
        timeout: float = 10.0
    ) -> "LoginStateChecker":
        """
        创建 JSON 响应检测器

        检测响应 JSON 中是否包含指定字段

        Args:
            check_url: API 地址
            success_field: 成功时 JSON 中存在的字段
            timeout: 超时时间

        Example:
            # 检测 /api/user/info 返回的 JSON 是否包含 user_id 字段
            checker = LoginStateChecker.create_json_checker(
                "https://example.com/api/user/info",
                "user_id"
            )
        """
        def indicator(resp: httpx.Response) -> bool:
            try:
                if resp.status_code != 200:
                    return False
                data = resp.json()
                return success_field in data
            except Exception:
                return False

        return cls(check_url, indicator, timeout)

    @classmethod
    def create_json_value_checker(
        cls,
        check_url: str,
        field: str,
        expected_value,
        timeout: float = 10.0
    ) -> "LoginStateChecker":
        """
        创建 JSON 值检测器

        检测响应 JSON 中指定字段是否等于预期值

        Args:
            check_url: API 地址
            field: 要检测的字段
            expected_value: 预期值
            timeout: 超时时间

        Example:
            # 检测 /api/status 返回的 logged_in 字段是否为 True
            checker = LoginStateChecker.create_json_value_checker(
                "https://example.com/api/status",
                "logged_in",
                True
            )
        """
        def indicator(resp: httpx.Response) -> bool:
            try:
                if resp.status_code != 200:
                    return False
                data = resp.json()
                return data.get(field) == expected_value
            except Exception:
                return False

        return cls(check_url, indicator, timeout)

    @classmethod
    def create_redirect_checker(
        cls,
        check_url: str,
        login_url_pattern: str,
        timeout: float = 10.0
    ) -> "LoginStateChecker":
        """
        创建重定向检测器

        如果被重定向到登录页，说明未登录

        Args:
            check_url: 需要登录的页面
            login_url_pattern: 登录页 URL 特征（如 "/login"）
            timeout: 超时时间

        Example:
            # 访问 /dashboard，如果被重定向到 /login 说明未登录
            checker = LoginStateChecker.create_redirect_checker(
                "https://example.com/dashboard",
                "/login"
            )
        """
        def indicator(resp: httpx.Response) -> bool:
            # 如果没有被重定向到登录页，说明已登录
            return login_url_pattern not in str(resp.url)

        return cls(check_url, indicator, timeout)

    @classmethod
    def create_status_code_checker(
        cls,
        check_url: str,
        success_codes: list = None,
        timeout: float = 10.0
    ) -> "LoginStateChecker":
        """
        创建状态码检测器

        Args:
            check_url: 检测 URL
            success_codes: 成功的状态码列表，默认 [200]
            timeout: 超时时间

        Example:
            # 检测 API 是否返回 200
            checker = LoginStateChecker.create_status_code_checker(
                "https://example.com/api/user",
                [200]
            )
        """
        success_codes = success_codes or [200]

        def indicator(resp: httpx.Response) -> bool:
            return resp.status_code in success_codes

        return cls(check_url, indicator, timeout)

    @classmethod
    def create_content_checker(
        cls,
        check_url: str,
        success_text: str,
        timeout: float = 10.0
    ) -> "LoginStateChecker":
        """
        创建内容检测器

        检测响应内容是否包含指定文本

        Args:
            check_url: 检测 URL
            success_text: 登录成功时页面包含的文本
            timeout: 超时时间

        Example:
            # 检测页面是否包含"欢迎回来"
            checker = LoginStateChecker.create_content_checker(
                "https://example.com/dashboard",
                "欢迎回来"
            )
        """
        def indicator(resp: httpx.Response) -> bool:
            return success_text in resp.text

        return cls(check_url, indicator, timeout)


class CookieExpiryMonitor:
    """Cookie 过期监控器"""

    @staticmethod
    def check_expiry(cookies: list) -> tuple:
        """
        检查 Cookie 是否过期

        Args:
            cookies: Playwright 格式的 Cookie 列表

        Returns:
            (是否全部有效, 已过期的 Cookie 列表)
        """
        now = time.time()
        expired = []

        for cookie in cookies:
            expires = cookie.get("expires", 0)
            # expires > 0 表示设置了过期时间
            # expires == -1 或 0 通常表示会话 Cookie
            if expires > 0 and expires < now:
                expired.append(cookie)

        return len(expired) == 0, expired

    @staticmethod
    def get_earliest_expiry(cookies: list) -> Optional[datetime]:
        """
        获取最早过期的时间

        Args:
            cookies: Cookie 列表

        Returns:
            最早过期的 datetime，如果没有过期时间则返回 None
        """
        expiry_times = []
        for c in cookies:
            expires = c.get("expires", 0)
            if expires > 0:
                expiry_times.append(expires)

        if not expiry_times:
            return None

        return datetime.fromtimestamp(min(expiry_times))

    @staticmethod
    def will_expire_soon(cookies: list, threshold_hours: int = 1) -> bool:
        """
        检查 Cookie 是否即将过期

        Args:
            cookies: Cookie 列表
            threshold_hours: 阈值小时数

        Returns:
            是否在阈值时间内过期
        """
        earliest = CookieExpiryMonitor.get_earliest_expiry(cookies)
        if earliest is None:
            return False  # 没有过期时间的认为不会过期
        return earliest < datetime.now() + timedelta(hours=threshold_hours)

    @staticmethod
    def get_expiry_summary(cookies: list) -> dict:
        """
        获取 Cookie 过期时间摘要

        Args:
            cookies: Cookie 列表

        Returns:
            摘要信息字典
        """
        now = time.time()
        summary = {
            "total": len(cookies),
            "session_cookies": 0,  # 会话 Cookie（无过期时间）
            "valid": 0,
            "expired": 0,
            "expiring_soon": 0,  # 1小时内过期
            "earliest_expiry": None,
            "latest_expiry": None
        }

        expiry_times = []

        for cookie in cookies:
            expires = cookie.get("expires", 0)
            if expires <= 0:
                summary["session_cookies"] += 1
            elif expires < now:
                summary["expired"] += 1
            elif expires < now + 3600:  # 1小时内
                summary["expiring_soon"] += 1
                summary["valid"] += 1
                expiry_times.append(expires)
            else:
                summary["valid"] += 1
                expiry_times.append(expires)

        if expiry_times:
            summary["earliest_expiry"] = datetime.fromtimestamp(min(expiry_times)).isoformat()
            summary["latest_expiry"] = datetime.fromtimestamp(max(expiry_times)).isoformat()

        return summary


async def demo():
    """演示登录状态检测"""

    print("=" * 50)
    print("登录状态检测器演示")
    print("=" * 50)

    # 1. JSON 检测器
    print("\n1. JSON 字段检测器")
    checker1 = LoginStateChecker.create_json_checker(
        "https://httpbin.org/json",
        "slideshow"
    )
    # httpbin.org/json 总是返回包含 slideshow 的 JSON
    result = await checker1.is_logged_in({})
    print(f"   检测结果: {'已登录' if result else '未登录'}")

    # 2. 状态码检测器
    print("\n2. 状态码检测器")
    checker2 = LoginStateChecker.create_status_code_checker(
        "https://httpbin.org/status/200",
        [200]
    )
    result = await checker2.is_logged_in({})
    print(f"   检测结果 (200): {'已登录' if result else '未登录'}")

    checker2_fail = LoginStateChecker.create_status_code_checker(
        "https://httpbin.org/status/401",
        [200]
    )
    result = await checker2_fail.is_logged_in({})
    print(f"   检测结果 (401): {'已登录' if result else '未登录'}")

    # 3. 内容检测器
    print("\n3. 内容检测器")
    checker3 = LoginStateChecker.create_content_checker(
        "https://httpbin.org/html",
        "Herman Melville"  # httpbin.org/html 页面包含这个名字
    )
    result = await checker3.is_logged_in({})
    print(f"   检测结果: {'已登录' if result else '未登录'}")

    # 4. Cookie 过期监控
    print("\n4. Cookie 过期监控")
    test_cookies = [
        {"name": "session", "value": "abc", "expires": time.time() + 3600},  # 1小时后过期
        {"name": "token", "value": "xyz", "expires": time.time() + 86400},   # 1天后过期
        {"name": "temp", "value": "123", "expires": 0},  # 会话 Cookie
    ]

    is_valid, expired = CookieExpiryMonitor.check_expiry(test_cookies)
    print(f"   全部有效: {is_valid}, 过期数量: {len(expired)}")

    will_expire = CookieExpiryMonitor.will_expire_soon(test_cookies, threshold_hours=2)
    print(f"   2小时内过期: {will_expire}")

    summary = CookieExpiryMonitor.get_expiry_summary(test_cookies)
    print(f"   摘要: {summary}")

    print("\n" + "=" * 50)
    print("演示完成")
    print("=" * 50)


if __name__ == "__main__":
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="DEBUG"
    )

    asyncio.run(demo())
