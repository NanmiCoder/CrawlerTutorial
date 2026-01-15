# -*- coding: utf-8 -*-
# @Desc: 登录认证模块

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from loguru import logger

# 可选依赖
try:
    from playwright.async_api import BrowserContext, Page
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


class BaseAuth(ABC):
    """认证基类"""

    @abstractmethod
    async def login(self, context) -> bool:
        """执行登录"""
        pass

    @abstractmethod
    async def check_login(self, page) -> bool:
        """检查登录状态"""
        pass


class CookieAuth(BaseAuth):
    """Cookie 认证"""

    def __init__(self, cookie_file: str, domain: str):
        """
        初始化 Cookie 认证

        Args:
            cookie_file: Cookie 文件路径
            domain: 目标域名
        """
        self.cookie_file = Path(cookie_file)
        self.domain = domain

    async def login(self, context) -> bool:
        """通过 Cookie 登录"""
        if not self.cookie_file.exists():
            logger.error(f"Cookie 文件不存在: {self.cookie_file}")
            return False

        try:
            with open(self.cookie_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)

            # 确保 Cookie 格式正确
            valid_cookies = []
            for cookie in cookies:
                if isinstance(cookie, dict) and 'name' in cookie and 'value' in cookie:
                    # 设置默认域名
                    if 'domain' not in cookie:
                        cookie['domain'] = self.domain
                    valid_cookies.append(cookie)

            # 注入 Cookie
            await context.add_cookies(valid_cookies)
            logger.info(f"成功注入 {len(valid_cookies)} 个 Cookie")
            return True
        except json.JSONDecodeError as e:
            logger.error(f"Cookie 文件格式错误: {e}")
            return False
        except Exception as e:
            logger.error(f"Cookie 注入失败: {e}")
            return False

    async def check_login(self, page) -> bool:
        """检查登录状态"""
        try:
            # 尝试查找登录标识元素
            # 这里需要根据实际网站调整选择器
            await page.wait_for_selector('.user-avatar, .user-info, .logged-in', timeout=5000)
            return True
        except Exception:
            return False

    async def save_cookies(self, context, output_file: str = None):
        """保存 Cookie"""
        output = output_file or str(self.cookie_file)
        cookies = await context.cookies()
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)
        logger.info(f"Cookie 已保存到: {output}")


class QRCodeAuth(BaseAuth):
    """扫码认证"""

    def __init__(
        self,
        login_url: str,
        qrcode_selector: str,
        success_selector: str,
        save_cookie_file: str = None
    ):
        """
        初始化扫码认证

        Args:
            login_url: 登录页面 URL
            qrcode_selector: 二维码元素选择器
            success_selector: 登录成功标识选择器
            save_cookie_file: Cookie 保存路径
        """
        self.login_url = login_url
        self.qrcode_selector = qrcode_selector
        self.success_selector = success_selector
        self.save_cookie_file = save_cookie_file

    async def login(self, context) -> bool:
        """扫码登录"""
        page = await context.new_page()

        try:
            # 访问登录页
            await page.goto(self.login_url)
            logger.info(f"访问登录页: {self.login_url}")

            # 等待二维码出现
            qrcode = await page.wait_for_selector(self.qrcode_selector, timeout=10000)
            if not qrcode:
                logger.error("未找到二维码元素")
                return False

            # 截图保存二维码
            await qrcode.screenshot(path='qrcode.png')
            logger.info("二维码已保存到 qrcode.png，请使用手机扫码登录")
            print("\n" + "=" * 50)
            print("请扫描 qrcode.png 中的二维码进行登录")
            print("等待登录成功... (最长等待 2 分钟)")
            print("=" * 50 + "\n")

            # 等待登录成功（最长等待 2 分钟）
            await page.wait_for_selector(self.success_selector, timeout=120000)
            logger.info("扫码登录成功")

            # 保存 Cookie
            if self.save_cookie_file:
                cookies = await context.cookies()
                with open(self.save_cookie_file, 'w', encoding='utf-8') as f:
                    json.dump(cookies, f, indent=2, ensure_ascii=False)
                logger.info(f"Cookie 已保存: {self.save_cookie_file}")

            return True
        except Exception as e:
            logger.error(f"扫码登录失败: {e}")
            return False
        finally:
            await page.close()

    async def check_login(self, page) -> bool:
        """检查登录状态"""
        try:
            await page.wait_for_selector(self.success_selector, timeout=5000)
            return True
        except Exception:
            return False


class AuthManager:
    """认证管理器"""

    def __init__(self):
        self._auth: Optional[BaseAuth] = None

    def set_cookie_auth(self, cookie_file: str, domain: str):
        """设置 Cookie 认证"""
        self._auth = CookieAuth(cookie_file, domain)
        logger.info(f"已配置 Cookie 认证: {cookie_file}")

    def set_qrcode_auth(
        self,
        login_url: str,
        qrcode_selector: str,
        success_selector: str,
        save_cookie_file: str = None
    ):
        """设置扫码认证"""
        self._auth = QRCodeAuth(
            login_url, qrcode_selector, success_selector, save_cookie_file
        )
        logger.info("已配置扫码认证")

    async def login(self, context) -> bool:
        """执行登录"""
        if not self._auth:
            logger.warning("未配置认证方式")
            return False
        return await self._auth.login(context)

    async def check_login(self, page) -> bool:
        """检查登录状态"""
        if not self._auth:
            return False
        return await self._auth.check_login(page)
