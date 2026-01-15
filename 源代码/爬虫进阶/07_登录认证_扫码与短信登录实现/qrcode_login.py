# -*- coding: utf-8 -*-
# @Desc: 扫码登录实现

import asyncio
from pathlib import Path
from typing import Optional, Callable, Awaitable
from playwright.async_api import async_playwright, Page, BrowserContext, Playwright
from loguru import logger
from enum import Enum

# 可选的终端二维码显示支持
try:
    import qrcode
    HAS_QRCODE_LIB = True
except ImportError:
    HAS_QRCODE_LIB = False


class QRCodeStatus(Enum):
    """二维码状态枚举"""
    WAITING = "waiting"       # 等待扫描
    SCANNED = "scanned"       # 已扫描，等待确认
    CONFIRMED = "confirmed"   # 已确认登录
    EXPIRED = "expired"       # 二维码已过期
    CANCELED = "canceled"     # 用户取消


def display_qrcode_in_terminal(data: str):
    """在终端显示二维码（需要安装 qrcode 库）"""
    if not HAS_QRCODE_LIB:
        print("提示: 安装 qrcode 库可在终端显示二维码: pip install qrcode")
        return

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=1,
        border=1
    )
    qr.add_data(data)
    qr.make(fit=True)
    qr.print_ascii(invert=True)


def display_qrcode_image_in_terminal(image_path: str):
    """
    将图片二维码转换为终端可显示的 ASCII 艺术

    需要安装: pip install pillow
    """
    try:
        from PIL import Image

        img = Image.open(image_path)
        img = img.convert('L')  # 转为灰度

        # 缩小图片以适应终端
        width = 50
        ratio = width / img.width
        height = int(img.height * ratio * 0.5)  # 0.5 补偿终端字符高宽比
        img = img.resize((width, height))

        # 转换为 ASCII
        chars = " .:-=+*#%@"
        pixels = img.getdata()
        ascii_img = ""
        for i, pixel in enumerate(pixels):
            if i > 0 and i % width == 0:
                ascii_img += "\n"
            char_idx = pixel * len(chars) // 256
            ascii_img += chars[char_idx]

        print(ascii_img)
    except ImportError:
        print(f"二维码已保存到: {image_path}")
        print("提示: 安装 pillow 库可在终端显示: pip install pillow")


class QRCodeLogin:
    """通用扫码登录实现"""

    def __init__(
        self,
        login_url: str,
        qrcode_selector: str,
        success_url_pattern: str,
        timeout: int = 120,
        poll_interval: float = 2.0
    ):
        """
        Args:
            login_url: 登录页面 URL
            qrcode_selector: 二维码元素选择器 (CSS/XPath)
            success_url_pattern: 登录成功后 URL 的特征字符串
            timeout: 等待登录的超时时间（秒）
            poll_interval: 状态轮询间隔（秒）
        """
        self.login_url = login_url
        self.qrcode_selector = qrcode_selector
        self.success_url_pattern = success_url_pattern
        self.timeout = timeout
        self.poll_interval = poll_interval

        self._playwright: Optional[Playwright] = None
        self._browser = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def start(self, playwright: Playwright, headless: bool = False):
        """
        启动浏览器

        Args:
            playwright: Playwright 实例
            headless: 是否无头模式（扫码时通常使用有头模式）
        """
        self._playwright = playwright
        self._browser = await playwright.chromium.launch(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        self._context = await self._browser.new_context(
            viewport={'width': 1280, 'height': 720}
        )
        self._page = await self._context.new_page()
        logger.info(f"浏览器已启动 (headless={headless})")

    async def close(self):
        """关闭浏览器"""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._context = None
            self._page = None
        logger.info("浏览器已关闭")

    async def navigate_to_login(self):
        """导航到登录页面"""
        await self._page.goto(self.login_url, wait_until="networkidle")
        logger.info(f"已打开登录页面: {self.login_url}")

    async def wait_for_qrcode(self, timeout: int = 10000) -> bool:
        """等待二维码出现"""
        try:
            await self._page.wait_for_selector(
                self.qrcode_selector,
                state="visible",
                timeout=timeout
            )
            logger.info("二维码已出现")
            return True
        except Exception as e:
            logger.error(f"等待二维码超时: {e}")
            return False

    async def save_qrcode(self, filepath: str = "qrcode.png") -> Optional[str]:
        """
        保存二维码图片

        Args:
            filepath: 保存路径

        Returns:
            成功返回文件路径，失败返回 None
        """
        if not await self.wait_for_qrcode():
            return None

        try:
            qrcode_element = self._page.locator(self.qrcode_selector)
            await qrcode_element.screenshot(path=filepath)
            logger.info(f"二维码已保存: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"保存二维码失败: {e}")
            return None

    async def wait_for_login(
        self,
        on_qrcode_ready: Optional[Callable[[str], Awaitable[None]]] = None,
        on_status_change: Optional[Callable[[QRCodeStatus], Awaitable[None]]] = None
    ) -> bool:
        """
        等待用户扫码登录

        Args:
            on_qrcode_ready: 二维码准备好后的回调
            on_status_change: 状态变化回调

        Returns:
            是否登录成功
        """
        # 保存二维码
        qrcode_path = await self.save_qrcode()
        if not qrcode_path:
            return False

        # 通知二维码已准备好
        if on_qrcode_ready:
            await on_qrcode_ready(qrcode_path)

        if on_status_change:
            await on_status_change(QRCodeStatus.WAITING)

        # 等待登录成功（URL 变化）
        try:
            await self._page.wait_for_url(
                f"**{self.success_url_pattern}**",
                timeout=self.timeout * 1000
            )

            if on_status_change:
                await on_status_change(QRCodeStatus.CONFIRMED)

            logger.info("扫码登录成功！")
            return True

        except Exception as e:
            logger.warning(f"登录超时或失败: {e}")
            if on_status_change:
                await on_status_change(QRCodeStatus.EXPIRED)
            return False

    async def get_cookies(self) -> list:
        """获取登录后的 Cookie"""
        if self._context:
            return await self._context.cookies()
        return []

    async def login(
        self,
        on_qrcode_ready: Optional[Callable[[str], Awaitable[None]]] = None,
        on_status_change: Optional[Callable[[QRCodeStatus], Awaitable[None]]] = None
    ) -> Optional[list]:
        """
        执行完整的扫码登录流程

        Args:
            on_qrcode_ready: 二维码准备好后的回调
            on_status_change: 状态变化回调

        Returns:
            成功返回 Cookie 列表，失败返回 None
        """
        await self.navigate_to_login()

        success = await self.wait_for_login(
            on_qrcode_ready=on_qrcode_ready,
            on_status_change=on_status_change
        )

        if success:
            cookies = await self.get_cookies()
            logger.info(f"获取到 {len(cookies)} 个 Cookie")
            return cookies

        return None


async def demo_qrcode_login():
    """扫码登录演示"""
    print("=" * 50)
    print("扫码登录演示")
    print("=" * 50)
    print("\n注意: 这是一个演示示例，实际使用需要替换为真实网站的配置")

    # 二维码准备好后的回调
    async def on_qrcode_ready(path: str):
        print(f"\n{'='*40}")
        print(f"二维码已准备好: {path}")
        print("请使用手机扫描登录")
        print(f"{'='*40}\n")
        # 在终端显示
        display_qrcode_image_in_terminal(path)

    # 状态变化回调
    async def on_status_change(status: QRCodeStatus):
        status_text = {
            QRCodeStatus.WAITING: "等待扫描...",
            QRCodeStatus.SCANNED: "已扫描，请在手机上确认",
            QRCodeStatus.CONFIRMED: "登录成功！",
            QRCodeStatus.EXPIRED: "二维码已过期",
            QRCodeStatus.CANCELED: "用户取消"
        }
        print(f"状态: {status_text.get(status, status.value)}")

    async with async_playwright() as p:
        # 使用示例网站演示（实际使用时替换）
        qr_login = QRCodeLogin(
            login_url="https://quotes.toscrape.com/login",  # 示例网站
            qrcode_selector="form",  # 示例选择器
            success_url_pattern="/",
            timeout=30
        )

        await qr_login.start(p, headless=False)

        try:
            print("\n这是一个演示，不会真正执行扫码登录")
            print("实际使用时，请配置正确的登录 URL 和选择器\n")

            # 演示导航到页面
            await qr_login.navigate_to_login()
            await asyncio.sleep(3)

            print("演示完成")

        finally:
            await qr_login.close()


if __name__ == "__main__":
    asyncio.run(demo_qrcode_login())
