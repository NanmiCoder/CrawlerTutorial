# -*- coding: utf-8 -*-
"""
B站登录认证模块

本模块实现了 B站的登录认证功能，支持两种登录方式：
1. 扫码登录：显示二维码，用户使用 B站 APP 扫码登录
2. Cookie 登录：使用已有的 Cookie 字符串直接登录

登录成功后会将 Cookie 保存到浏览器上下文中，后续请求自动携带。

参考 MediaCrawler 项目的实现：
- https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/bilibili/login.py
"""

import asyncio
import base64
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Dict
from loguru import logger

# 可选依赖
try:
    from playwright.async_api import BrowserContext, Page
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

# 尝试导入图片显示库
try:
    from PIL import Image
    from io import BytesIO
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# 尝试导入 httpx
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


# ==================== B站登录相关常量 ====================

# B站主页
BILIBILI_URL = "https://www.bilibili.com"

# 登录按钮选择器
LOGIN_BUTTON_SELECTOR = "xpath=//div[@class='right-entry__outside go-login-btn']//div"

# 二维码选择器
QRCODE_SELECTOR = "//div[@class='login-scan-box']//img"

# 登录成功后的 Cookie 关键字段
LOGIN_COOKIE_KEYS = ["SESSDATA", "DedeUserID", "bili_jct"]


class AbstractLogin(ABC):
    """登录抽象基类"""

    @abstractmethod
    async def begin(self) -> bool:
        """开始登录流程"""
        pass

    @abstractmethod
    async def login_by_qrcode(self) -> bool:
        """扫码登录"""
        pass

    @abstractmethod
    async def login_by_cookies(self) -> bool:
        """Cookie 登录"""
        pass

    @abstractmethod
    async def check_login_state(self) -> bool:
        """检查登录状态"""
        pass


class BilibiliLogin(AbstractLogin):
    """
    B站登录类

    支持扫码登录和 Cookie 登录两种方式。

    使用示例：
    ```python
    login = BilibiliLogin(
        login_type="qrcode",
        browser_context=context,
        context_page=page
    )
    success = await login.begin()
    ```
    """

    def __init__(
        self,
        login_type: str,
        browser_context: "BrowserContext",
        context_page: "Page",
        cookie_str: str = "",
    ):
        """
        初始化 B站登录

        Args:
            login_type: 登录类型，"qrcode" 或 "cookie"
            browser_context: Playwright 浏览器上下文
            context_page: Playwright 页面对象
            cookie_str: Cookie 字符串（当 login_type="cookie" 时使用）
        """
        self.login_type = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.cookie_str = cookie_str

    async def begin(self) -> bool:
        """
        开始登录流程

        根据 login_type 自动选择登录方式。

        Returns:
            bool: 登录是否成功
        """
        logger.info(f"[BilibiliLogin] 开始登录，方式: {self.login_type}")

        if self.login_type == "qrcode":
            return await self.login_by_qrcode()
        elif self.login_type == "cookie":
            return await self.login_by_cookies()
        else:
            logger.error(f"[BilibiliLogin] 不支持的登录类型: {self.login_type}")
            return False

    async def login_by_qrcode(self) -> bool:
        """
        扫码登录

        流程：
        1. 访问 B站首页
        2. 点击登录按钮
        3. 获取二维码图片并显示
        4. 等待用户扫码
        5. 检查登录状态

        Returns:
            bool: 登录是否成功
        """
        logger.info("[BilibiliLogin] 开始扫码登录...")

        try:
            # 1. 访问 B站首页
            await self.context_page.goto(BILIBILI_URL)
            await asyncio.sleep(2)

            # 2. 点击登录按钮
            try:
                login_button = await self.context_page.wait_for_selector(
                    LOGIN_BUTTON_SELECTOR,
                    timeout=10000
                )
                if login_button:
                    await login_button.click()
                    await asyncio.sleep(1)
            except Exception as e:
                logger.warning(f"[BilibiliLogin] 点击登录按钮失败: {e}")
                # 可能已经有登录弹窗，继续尝试

            # 3. 获取二维码
            qrcode_img = await self._find_login_qrcode()
            if not qrcode_img:
                logger.error("[BilibiliLogin] 未找到二维码")
                return False

            # 4. 显示二维码
            await self._show_qrcode(qrcode_img)

            # 5. 等待登录成功
            logger.info("[BilibiliLogin] 请使用 B站 APP 扫描二维码登录...")
            logger.info("[BilibiliLogin] 等待登录成功（最长等待 120 秒）...")

            # 轮询检查登录状态
            for _ in range(120):  # 最多等待 120 秒
                if await self.check_login_state():
                    logger.info("[BilibiliLogin] 扫码登录成功！")
                    await asyncio.sleep(2)  # 等待页面跳转
                    return True
                await asyncio.sleep(1)

            logger.error("[BilibiliLogin] 扫码登录超时")
            return False

        except Exception as e:
            logger.error(f"[BilibiliLogin] 扫码登录失败: {e}")
            return False

    async def login_by_cookies(self) -> bool:
        """
        Cookie 登录

        将 Cookie 字符串解析后注入到浏览器上下文中。

        Returns:
            bool: 登录是否成功
        """
        logger.info("[BilibiliLogin] 开始 Cookie 登录...")

        if not self.cookie_str:
            logger.error("[BilibiliLogin] Cookie 字符串为空")
            return False

        try:
            # 解析 Cookie 字符串
            cookies = self._parse_cookie_str(self.cookie_str)
            if not cookies:
                logger.error("[BilibiliLogin] Cookie 解析失败")
                return False

            # 注入 Cookie
            await self.browser_context.add_cookies(cookies)
            logger.info(f"[BilibiliLogin] 成功注入 {len(cookies)} 个 Cookie")

            # 刷新页面验证
            await self.context_page.goto(BILIBILI_URL)
            await asyncio.sleep(2)

            # 检查登录状态
            if await self.check_login_state():
                logger.info("[BilibiliLogin] Cookie 登录成功！")
                return True
            else:
                logger.error("[BilibiliLogin] Cookie 登录失败，Cookie 可能已过期")
                return False

        except Exception as e:
            logger.error(f"[BilibiliLogin] Cookie 登录失败: {e}")
            return False

    async def check_login_state(self) -> bool:
        """
        检查登录状态

        通过检查 Cookie 中是否包含关键字段来判断是否已登录。
        关键字段：SESSDATA、DedeUserID

        Returns:
            bool: 是否已登录
        """
        try:
            # 获取当前 Cookie
            cookies = await self.browser_context.cookies()
            cookie_dict = {c['name']: c['value'] for c in cookies}

            # 检查关键 Cookie 是否存在
            for key in ["SESSDATA", "DedeUserID"]:
                if key in cookie_dict and cookie_dict[key]:
                    return True

            return False

        except Exception as e:
            logger.debug(f"[BilibiliLogin] 检查登录状态出错: {e}")
            return False

    async def _find_login_qrcode(self) -> Optional[str]:
        """
        查找登录二维码

        Returns:
            str: Base64 编码的二维码图片，如果未找到返回 None
        """
        try:
            # 等待二维码出现
            qrcode_element = await self.context_page.wait_for_selector(
                QRCODE_SELECTOR,
                timeout=10000
            )

            if not qrcode_element:
                return None

            # 获取二维码图片 src
            qrcode_src = await qrcode_element.get_attribute("src")

            if not qrcode_src:
                return None

            # 如果是 URL，下载图片
            if qrcode_src.startswith("http"):
                return await self._download_qrcode(qrcode_src)

            # 如果是 base64，直接返回
            if qrcode_src.startswith("data:image"):
                return qrcode_src.split(",")[1] if "," in qrcode_src else qrcode_src

            return qrcode_src

        except Exception as e:
            logger.error(f"[BilibiliLogin] 获取二维码失败: {e}")
            return None

    async def _download_qrcode(self, url: str) -> Optional[str]:
        """
        下载二维码图片

        Args:
            url: 二维码图片 URL

        Returns:
            str: Base64 编码的图片数据
        """
        if not HAS_HTTPX:
            logger.warning("[BilibiliLogin] httpx 未安装，无法下载二维码")
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10)
                if response.status_code == 200:
                    return base64.b64encode(response.content).decode('utf-8')
        except Exception as e:
            logger.error(f"[BilibiliLogin] 下载二维码失败: {e}")

        return None

    async def _show_qrcode(self, qrcode_base64: str):
        """
        显示二维码

        优先使用 PIL 显示，如果不可用则保存到文件。

        Args:
            qrcode_base64: Base64 编码的二维码图片
        """
        # 解码 base64
        try:
            qrcode_bytes = base64.b64decode(qrcode_base64)
        except Exception:
            logger.error("[BilibiliLogin] 二维码 Base64 解码失败")
            return

        # 保存到文件
        qrcode_path = Path("qrcode.png")
        with open(qrcode_path, 'wb') as f:
            f.write(qrcode_bytes)
        logger.info(f"[BilibiliLogin] 二维码已保存到: {qrcode_path.absolute()}")

        # 尝试显示图片
        if HAS_PIL:
            try:
                image = Image.open(BytesIO(qrcode_bytes))
                image.show()
                logger.info("[BilibiliLogin] 二维码已显示，请扫码登录")
            except Exception as e:
                logger.warning(f"[BilibiliLogin] 无法显示二维码: {e}")
                logger.info(f"[BilibiliLogin] 请手动打开文件: {qrcode_path.absolute()}")
        else:
            logger.info(f"[BilibiliLogin] 请手动打开文件扫码: {qrcode_path.absolute()}")

        # 打印提示
        print("\n" + "=" * 60)
        print("  请使用 B站 APP 扫描二维码登录")
        print(f"  二维码文件: {qrcode_path.absolute()}")
        print("  等待登录中...")
        print("=" * 60 + "\n")

    def _parse_cookie_str(self, cookie_str: str) -> List[Dict]:
        """
        解析 Cookie 字符串

        Args:
            cookie_str: Cookie 字符串，格式如 "name1=value1; name2=value2"

        Returns:
            List[Dict]: Playwright 格式的 Cookie 列表
        """
        cookies = []

        for item in cookie_str.split(";"):
            item = item.strip()
            if not item or "=" not in item:
                continue

            parts = item.split("=", 1)
            name = parts[0].strip()
            value = parts[1].strip() if len(parts) > 1 else ""

            if name:
                cookies.append({
                    "name": name,
                    "value": value,
                    "domain": ".bilibili.com",
                    "path": "/"
                })

        return cookies


# ==================== 工具函数 ====================

def convert_cookies_to_str(cookies: List[Dict]) -> str:
    """
    将 Cookie 列表转换为字符串

    Args:
        cookies: Playwright 格式的 Cookie 列表

    Returns:
        str: Cookie 字符串
    """
    return "; ".join([f"{c['name']}={c['value']}" for c in cookies])


def convert_cookies_to_dict(cookies: List[Dict]) -> Dict[str, str]:
    """
    将 Cookie 列表转换为字典

    Args:
        cookies: Playwright 格式的 Cookie 列表

    Returns:
        Dict[str, str]: Cookie 字典
    """
    return {c['name']: c['value'] for c in cookies}


async def save_cookies_to_file(context: "BrowserContext", filepath: str):
    """
    保存 Cookie 到文件

    Args:
        context: Playwright 浏览器上下文
        filepath: 保存路径
    """
    cookies = await context.cookies()
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(cookies, f, indent=2, ensure_ascii=False)
    logger.info(f"[BilibiliLogin] Cookie 已保存到: {filepath}")


async def load_cookies_from_file(context: "BrowserContext", filepath: str) -> bool:
    """
    从文件加载 Cookie

    Args:
        context: Playwright 浏览器上下文
        filepath: Cookie 文件路径

    Returns:
        bool: 是否加载成功
    """
    path = Path(filepath)
    if not path.exists():
        logger.warning(f"[BilibiliLogin] Cookie 文件不存在: {filepath}")
        return False

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)
        logger.info(f"[BilibiliLogin] 从文件加载了 {len(cookies)} 个 Cookie")
        return True
    except Exception as e:
        logger.error(f"[BilibiliLogin] 加载 Cookie 失败: {e}")
        return False


if __name__ == '__main__':
    # 测试 Cookie 解析
    test_cookie_str = "SESSDATA=abc123; DedeUserID=12345; bili_jct=xyz789"
    login = BilibiliLogin(
        login_type="cookie",
        browser_context=None,
        context_page=None,
        cookie_str=test_cookie_str
    )
    cookies = login._parse_cookie_str(test_cookie_str)
    print("解析后的 Cookie:")
    for c in cookies:
        print(f"  {c['name']}: {c['value']}")
