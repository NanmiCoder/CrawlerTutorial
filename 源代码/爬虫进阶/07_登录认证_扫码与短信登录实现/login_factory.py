# -*- coding: utf-8 -*-
# @Desc: 登录模块工厂 - 统一封装多种登录方式

import asyncio
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Callable, Awaitable, Dict, Any
from enum import Enum
from dataclasses import dataclass
from loguru import logger


class LoginMethod(Enum):
    """登录方式枚举"""
    QRCODE = "qrcode"        # 扫码登录
    SMS = "sms"              # 短信验证码
    PASSWORD = "password"    # 账号密码
    COOKIE = "cookie"        # Cookie 注入


@dataclass
class LoginResult:
    """登录结果"""
    success: bool
    cookies: list = None
    error: str = None
    method: LoginMethod = None

    def __post_init__(self):
        if self.cookies is None:
            self.cookies = []


class BaseLogin(ABC):
    """登录基类"""

    @property
    @abstractmethod
    def method(self) -> LoginMethod:
        """登录方式"""
        pass

    @abstractmethod
    async def login(self) -> LoginResult:
        """
        执行登录

        Returns:
            登录结果
        """
        pass

    @abstractmethod
    async def close(self):
        """清理资源"""
        pass


class CookieLogin(BaseLogin):
    """Cookie 注入登录"""

    def __init__(self, cookies: list, verify_url: str = None):
        """
        Args:
            cookies: Cookie 列表
            verify_url: 验证 URL（可选）
        """
        self._cookies = cookies
        self._verify_url = verify_url

    @property
    def method(self) -> LoginMethod:
        return LoginMethod.COOKIE

    async def login(self) -> LoginResult:
        """Cookie 注入直接返回成功"""
        logger.info(f"使用 Cookie 注入登录，Cookie 数量: {len(self._cookies)}")
        return LoginResult(
            success=True,
            cookies=self._cookies,
            method=self.method
        )

    async def close(self):
        pass


class QRCodeLoginWrapper(BaseLogin):
    """扫码登录包装器"""

    def __init__(
        self,
        login_url: str,
        qrcode_selector: str,
        success_url_pattern: str,
        timeout: int = 120,
        on_qrcode_ready: Callable[[str], Awaitable[None]] = None,
        headless: bool = False
    ):
        self.login_url = login_url
        self.qrcode_selector = qrcode_selector
        self.success_url_pattern = success_url_pattern
        self.timeout = timeout
        self.on_qrcode_ready = on_qrcode_ready
        self.headless = headless

        self._playwright = None
        self._qrcode_login = None

    @property
    def method(self) -> LoginMethod:
        return LoginMethod.QRCODE

    async def login(self) -> LoginResult:
        from playwright.async_api import async_playwright
        from qrcode_login import QRCodeLogin

        try:
            self._playwright = await async_playwright().start()
            self._qrcode_login = QRCodeLogin(
                login_url=self.login_url,
                qrcode_selector=self.qrcode_selector,
                success_url_pattern=self.success_url_pattern,
                timeout=self.timeout
            )

            await self._qrcode_login.start(self._playwright, headless=self.headless)

            cookies = await self._qrcode_login.login(
                on_qrcode_ready=self.on_qrcode_ready
            )

            if cookies:
                return LoginResult(
                    success=True,
                    cookies=cookies,
                    method=self.method
                )

            return LoginResult(
                success=False,
                error="登录超时或用户取消",
                method=self.method
            )

        except Exception as e:
            logger.error(f"扫码登录异常: {e}")
            return LoginResult(
                success=False,
                error=str(e),
                method=self.method
            )

    async def close(self):
        if self._qrcode_login:
            await self._qrcode_login.close()
        if self._playwright:
            await self._playwright.stop()


class SMSLoginWrapper(BaseLogin):
    """短信登录包装器"""

    def __init__(
        self,
        login_url: str,
        phone_input_selector: str,
        send_code_btn_selector: str,
        code_input_selector: str,
        submit_btn_selector: str,
        success_url_pattern: str,
        phone: str,
        get_code_callback: Callable[[], Awaitable[str]],
        headless: bool = False
    ):
        self.login_url = login_url
        self.phone_input_selector = phone_input_selector
        self.send_code_btn_selector = send_code_btn_selector
        self.code_input_selector = code_input_selector
        self.submit_btn_selector = submit_btn_selector
        self.success_url_pattern = success_url_pattern
        self.phone = phone
        self.get_code_callback = get_code_callback
        self.headless = headless

        self._playwright = None
        self._sms_login = None

    @property
    def method(self) -> LoginMethod:
        return LoginMethod.SMS

    async def login(self) -> LoginResult:
        from playwright.async_api import async_playwright
        from sms_login import SMSLogin

        try:
            self._playwright = await async_playwright().start()
            self._sms_login = SMSLogin(
                login_url=self.login_url,
                phone_input_selector=self.phone_input_selector,
                send_code_btn_selector=self.send_code_btn_selector,
                code_input_selector=self.code_input_selector,
                submit_btn_selector=self.submit_btn_selector,
                success_url_pattern=self.success_url_pattern
            )

            await self._sms_login.start(self._playwright, headless=self.headless)

            cookies = await self._sms_login.login_with_manual_code(
                phone=self.phone,
                get_code_callback=self.get_code_callback
            )

            if cookies:
                return LoginResult(
                    success=True,
                    cookies=cookies,
                    method=self.method
                )

            return LoginResult(
                success=False,
                error="登录失败",
                method=self.method
            )

        except Exception as e:
            logger.error(f"短信登录异常: {e}")
            return LoginResult(
                success=False,
                error=str(e),
                method=self.method
            )

    async def close(self):
        if self._sms_login:
            await self._sms_login.close()
        if self._playwright:
            await self._playwright.stop()


class LoginFactory:
    """登录工厂"""

    @staticmethod
    def create_cookie_login(cookies: list, **kwargs) -> BaseLogin:
        """创建 Cookie 登录"""
        return CookieLogin(cookies, **kwargs)

    @staticmethod
    def create_qrcode_login(
        login_url: str,
        qrcode_selector: str,
        success_url_pattern: str,
        **kwargs
    ) -> BaseLogin:
        """创建扫码登录"""
        return QRCodeLoginWrapper(
            login_url=login_url,
            qrcode_selector=qrcode_selector,
            success_url_pattern=success_url_pattern,
            **kwargs
        )

    @staticmethod
    def create_sms_login(
        login_url: str,
        phone: str,
        get_code_callback: Callable[[], Awaitable[str]],
        phone_input_selector: str,
        send_code_btn_selector: str,
        code_input_selector: str,
        submit_btn_selector: str,
        success_url_pattern: str,
        **kwargs
    ) -> BaseLogin:
        """创建短信登录"""
        return SMSLoginWrapper(
            login_url=login_url,
            phone=phone,
            get_code_callback=get_code_callback,
            phone_input_selector=phone_input_selector,
            send_code_btn_selector=send_code_btn_selector,
            code_input_selector=code_input_selector,
            submit_btn_selector=submit_btn_selector,
            success_url_pattern=success_url_pattern,
            **kwargs
        )


class LoginManager:
    """统一登录管理器"""

    def __init__(
        self,
        platform: str,
        cookie_path: str,
        default_method: LoginMethod = LoginMethod.COOKIE
    ):
        """
        Args:
            platform: 平台名称
            cookie_path: Cookie 存储路径
            default_method: 默认登录方式
        """
        self.platform = platform
        self.cookie_path = Path(cookie_path)
        self.default_method = default_method
        self._cookies: list = []

    async def ensure_login(
        self,
        login_config: Dict[str, Any] = None,
        force_login: bool = False
    ) -> bool:
        """
        确保已登录

        优先使用已保存的 Cookie，如果无效则使用指定方式登录

        Args:
            login_config: 登录配置
            force_login: 是否强制重新登录

        Returns:
            是否登录成功
        """
        # 如果不强制登录，先尝试加载已保存的 Cookie
        if not force_login and await self._try_load_cookies():
            logger.info(f"[{self.platform}] 使用已保存的 Cookie")
            return True

        # 执行登录
        if not login_config:
            logger.error(f"[{self.platform}] 需要登录配置")
            return False

        method = login_config.pop('method', self.default_method)
        logger.info(f"[{self.platform}] 开始 {method.value} 登录")

        # 创建登录实例
        login = self._create_login(method, login_config)
        if not login:
            logger.error(f"[{self.platform}] 不支持的登录方式: {method}")
            return False

        try:
            result = await login.login()

            if result.success:
                self._cookies = result.cookies
                await self._save_cookies()
                logger.info(f"[{self.platform}] 登录成功")
                return True
            else:
                logger.error(f"[{self.platform}] 登录失败: {result.error}")
                return False

        finally:
            await login.close()

    def _create_login(
        self,
        method: LoginMethod,
        config: Dict[str, Any]
    ) -> Optional[BaseLogin]:
        """根据方式创建登录实例"""
        if method == LoginMethod.COOKIE:
            return LoginFactory.create_cookie_login(**config)
        elif method == LoginMethod.QRCODE:
            return LoginFactory.create_qrcode_login(**config)
        elif method == LoginMethod.SMS:
            return LoginFactory.create_sms_login(**config)
        return None

    async def _try_load_cookies(self) -> bool:
        """尝试加载 Cookie"""
        if not self.cookie_path.exists():
            return False

        try:
            with open(self.cookie_path, "r", encoding="utf-8") as f:
                self._cookies = json.load(f)

            # 简单验证：检查是否有 Cookie
            return len(self._cookies) > 0

        except Exception as e:
            logger.warning(f"加载 Cookie 失败: {e}")
            return False

    async def _save_cookies(self):
        """保存 Cookie"""
        self.cookie_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cookie_path, "w", encoding="utf-8") as f:
            json.dump(self._cookies, f, indent=2, ensure_ascii=False)
        logger.info(f"Cookie 已保存: {self.cookie_path}")

    def get_cookies(self) -> list:
        """获取 Cookie 列表"""
        return self._cookies

    def get_cookies_dict(self) -> dict:
        """获取字典格式的 Cookie"""
        return {c["name"]: c["value"] for c in self._cookies}

    async def clear_cookies(self):
        """清除 Cookie"""
        self._cookies = []
        if self.cookie_path.exists():
            self.cookie_path.unlink()
        logger.info(f"[{self.platform}] Cookie 已清除")


async def demo_login_factory():
    """登录工厂演示"""
    print("=" * 50)
    print("登录工厂演示")
    print("=" * 50)

    # 1. Cookie 登录演示
    print("\n1. Cookie 登录演示:")
    test_cookies = [
        {"name": "session", "value": "test123", "domain": "example.com", "path": "/"}
    ]
    cookie_login = LoginFactory.create_cookie_login(cookies=test_cookies)
    result = await cookie_login.login()
    print(f"   登录方式: {result.method.value}")
    print(f"   登录结果: {'成功' if result.success else '失败'}")
    print(f"   Cookie 数量: {len(result.cookies)}")
    await cookie_login.close()

    # 2. 登录管理器演示
    print("\n2. 登录管理器演示:")
    manager = LoginManager(
        platform="demo_platform",
        cookie_path="data/demo_login_cookies.json",
        default_method=LoginMethod.COOKIE
    )

    # 使用 Cookie 配置
    success = await manager.ensure_login(
        login_config={
            'method': LoginMethod.COOKIE,
            'cookies': test_cookies
        }
    )
    print(f"   登录结果: {'成功' if success else '失败'}")
    print(f"   Cookie: {manager.get_cookies_dict()}")

    # 3. 再次调用会使用缓存的 Cookie
    print("\n3. 使用缓存的 Cookie:")
    success = await manager.ensure_login()
    print(f"   登录结果: {'成功' if success else '失败'}")

    print("\n" + "=" * 50)
    print("演示完成")
    print("=" * 50)


async def main():
    """主函数"""
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    await demo_login_factory()


if __name__ == "__main__":
    asyncio.run(main())
