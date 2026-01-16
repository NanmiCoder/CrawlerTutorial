# -*- coding: utf-8 -*-
"""
B站 Cookie 管理实战

本模块展示如何管理 B站 Cookie，包括：
- B站核心 Cookie 结构（SESSDATA、DedeUserID、bili_jct）
- Cookie 提取与存储
- 登录状态验证
- httpx 和 Playwright 集成

这是第06章"登录认证-Cookie与Session管理"的B站实战示例。

与第11章综合实战项目的关联：
- login/auth.py: BilibiliCookieManager 登录管理
- models/cookies.py: Cookie 模型定义
"""

import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime

import httpx
from loguru import logger


# ============== B站 Cookie 数据类 ==============

@dataclass
class BilibiliCookies:
    """
    B站 Cookie 数据类

    核心 Cookie：
    - SESSDATA: 会话凭证（最重要）
    - DedeUserID: 用户ID
    - bili_jct: CSRF Token（POST请求必需）

    辅助 Cookie：
    - buvid3/buvid4: 设备标识
    - sid: 短会话ID
    """
    sessdata: str
    dede_user_id: str
    bili_jct: str
    buvid3: str = ""
    buvid4: str = ""
    sid: str = ""
    raw_cookies: List[dict] = field(default_factory=list)

    @classmethod
    def from_playwright_cookies(cls, cookies: List[dict]) -> "BilibiliCookies":
        """
        从 Playwright 格式的 Cookie 创建

        Args:
            cookies: Playwright context.cookies() 返回的列表

        Returns:
            BilibiliCookies 实例
        """
        cookie_dict = {c["name"]: c["value"] for c in cookies}

        return cls(
            sessdata=cookie_dict.get("SESSDATA", ""),
            dede_user_id=cookie_dict.get("DedeUserID", ""),
            bili_jct=cookie_dict.get("bili_jct", ""),
            buvid3=cookie_dict.get("buvid3", ""),
            buvid4=cookie_dict.get("buvid4", ""),
            sid=cookie_dict.get("sid", ""),
            raw_cookies=cookies
        )

    @classmethod
    def from_browser_string(cls, cookie_string: str) -> "BilibiliCookies":
        """
        从浏览器复制的 Cookie 字符串创建

        Args:
            cookie_string: 格式 "SESSDATA=xxx; DedeUserID=xxx; bili_jct=xxx"

        Returns:
            BilibiliCookies 实例
        """
        cookie_dict = {}
        for item in cookie_string.split(";"):
            item = item.strip()
            if "=" in item:
                key, value = item.split("=", 1)
                cookie_dict[key.strip()] = value.strip()

        return cls(
            sessdata=cookie_dict.get("SESSDATA", ""),
            dede_user_id=cookie_dict.get("DedeUserID", ""),
            bili_jct=cookie_dict.get("bili_jct", ""),
            buvid3=cookie_dict.get("buvid3", ""),
            buvid4=cookie_dict.get("buvid4", ""),
            sid=cookie_dict.get("sid", "")
        )

    def to_httpx_cookies(self) -> Dict[str, str]:
        """转换为 httpx 可用的字典格式"""
        cookies = {
            "SESSDATA": self.sessdata,
            "DedeUserID": self.dede_user_id,
            "bili_jct": self.bili_jct,
        }
        if self.buvid3:
            cookies["buvid3"] = self.buvid3
        if self.buvid4:
            cookies["buvid4"] = self.buvid4
        if self.sid:
            cookies["sid"] = self.sid
        return cookies

    def to_playwright_cookies(self, domain: str = ".bilibili.com") -> List[dict]:
        """
        转换为 Playwright 可用的格式

        Args:
            domain: Cookie 的域名

        Returns:
            Playwright 格式的 Cookie 列表
        """
        if self.raw_cookies:
            return self.raw_cookies

        cookies = []
        for name, value in self.to_httpx_cookies().items():
            cookies.append({
                "name": name,
                "value": value,
                "domain": domain,
                "path": "/"
            })
        return cookies

    def is_valid(self) -> bool:
        """检查核心 Cookie 是否存在"""
        return bool(self.sessdata and self.dede_user_id and self.bili_jct)

    def to_header_string(self) -> str:
        """转换为请求头 Cookie 格式"""
        return "; ".join(f"{k}={v}" for k, v in self.to_httpx_cookies().items())


# ============== B站 Cookie 管理器 ==============

class BilibiliCookieManager:
    """
    B站 Cookie 管理器

    功能：
    - Cookie 加载/保存
    - 登录状态检测
    - Cookie 有效性验证
    - 支持多种格式（JSON、字符串）
    """

    # 登录状态检测 API
    CHECK_URL = "https://api.bilibili.com/x/web-interface/nav"

    # 请求头
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/131.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/"
    }

    def __init__(self, storage_path: str = "bilibili_cookies.json"):
        """
        初始化管理器

        Args:
            storage_path: Cookie 存储文件路径
        """
        self.storage_path = Path(storage_path)
        self._cookies: Optional[BilibiliCookies] = None
        self._last_check: Optional[datetime] = None
        self._user_info: Optional[dict] = None

    async def load(self) -> bool:
        """
        从文件加载 Cookie

        Returns:
            是否加载成功
        """
        if not self.storage_path.exists():
            logger.warning(f"Cookie 文件不存在: {self.storage_path}")
            return False

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                # Playwright 格式
                self._cookies = BilibiliCookies.from_playwright_cookies(data)
            elif isinstance(data, dict):
                # 自定义格式
                self._cookies = BilibiliCookies(
                    sessdata=data.get("SESSDATA", ""),
                    dede_user_id=data.get("DedeUserID", ""),
                    bili_jct=data.get("bili_jct", ""),
                    buvid3=data.get("buvid3", ""),
                    buvid4=data.get("buvid4", ""),
                    sid=data.get("sid", "")
                )

            logger.info(f"Cookie 加载成功，用户ID: {self._cookies.dede_user_id}")
            return True

        except Exception as e:
            logger.error(f"加载 Cookie 失败: {e}")
            return False

    async def save(self, cookies: Optional[BilibiliCookies] = None):
        """
        保存 Cookie 到文件

        Args:
            cookies: 要保存的 Cookie，如果为 None 则保存当前 Cookie
        """
        if cookies:
            self._cookies = cookies

        if not self._cookies:
            logger.warning("没有 Cookie 可保存")
            return

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "SESSDATA": self._cookies.sessdata,
            "DedeUserID": self._cookies.dede_user_id,
            "bili_jct": self._cookies.bili_jct,
            "buvid3": self._cookies.buvid3,
            "buvid4": self._cookies.buvid4,
            "sid": self._cookies.sid,
            "save_time": datetime.now().isoformat()
        }

        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Cookie 已保存到: {self.storage_path}")

    async def verify(self) -> bool:
        """
        验证 Cookie 是否有效

        Returns:
            Cookie 是否有效
        """
        if not self._cookies or not self._cookies.is_valid():
            return False

        try:
            async with httpx.AsyncClient(
                cookies=self._cookies.to_httpx_cookies(),
                headers=self.HEADERS,
                timeout=10
            ) as client:
                resp = await client.get(self.CHECK_URL)
                data = resp.json()

                if data.get("code") == 0:
                    user_info = data.get("data", {})
                    if user_info.get("isLogin"):
                        self._user_info = user_info
                        self._last_check = datetime.now()
                        logger.info(f"Cookie 有效，用户: {user_info.get('uname')}")
                        return True

                logger.warning("Cookie 已失效")
                return False

        except Exception as e:
            logger.error(f"验证 Cookie 失败: {e}")
            return False

    async def get_valid_cookies(self) -> Optional[BilibiliCookies]:
        """
        获取有效的 Cookie

        Returns:
            有效的 BilibiliCookies，如果无效则返回 None
        """
        if self._cookies is None:
            await self.load()

        if self._cookies and await self.verify():
            return self._cookies

        return None

    def set_cookies_from_string(self, cookie_string: str):
        """
        从浏览器复制的字符串设置 Cookie

        Args:
            cookie_string: 格式 "SESSDATA=xxx; DedeUserID=xxx; bili_jct=xxx"
        """
        self._cookies = BilibiliCookies.from_browser_string(cookie_string)
        logger.info(f"Cookie 已设置，用户ID: {self._cookies.dede_user_id}")

    @property
    def cookies(self) -> Optional[BilibiliCookies]:
        """获取当前 Cookie（不验证）"""
        return self._cookies

    @property
    def user_info(self) -> Optional[dict]:
        """获取用户信息（需先调用 verify）"""
        return self._user_info


# ============== Cookie 格式转换工具 ==============

def playwright_cookies_to_httpx(playwright_cookies: List[dict]) -> dict:
    """
    将 Playwright 格式的 Cookie 转换为 httpx 格式

    Args:
        playwright_cookies: Playwright 格式 [{"name": "x", "value": "y", ...}, ...]

    Returns:
        httpx 格式 {"name": "value", ...}
    """
    return {c["name"]: c["value"] for c in playwright_cookies}


def httpx_cookies_to_playwright(cookies_dict: dict, domain: str = ".bilibili.com") -> List[dict]:
    """
    将 httpx 字典格式转换为 Playwright 格式

    Args:
        cookies_dict: 简单字典 {"name": "value", ...}
        domain: Cookie 的域名

    Returns:
        Playwright 格式的 Cookie 列表
    """
    return [
        {
            "name": name,
            "value": value,
            "domain": domain,
            "path": "/"
        }
        for name, value in cookies_dict.items()
    ]


# ============== 演示入口 ==============

async def demo_bilibili_cookie():
    """演示 B站 Cookie 管理"""
    logger.info("=" * 50)
    logger.info("B站 Cookie 管理示例")
    logger.info("=" * 50)

    # 1. 展示 Cookie 结构
    logger.info("\n--- 1. B站核心 Cookie 结构 ---")
    logger.info("SESSDATA: 会话凭证（最重要，有效期约1个月）")
    logger.info("DedeUserID: 用户ID")
    logger.info("bili_jct: CSRF Token（POST请求必需）")
    logger.info("buvid3/buvid4: 设备标识")

    # 2. 演示从字符串创建 Cookie
    logger.info("\n--- 2. 从浏览器字符串创建 Cookie ---")
    # 示例字符串（实际使用时替换为真实值）
    sample_string = "SESSDATA=sample_sessdata; DedeUserID=123456; bili_jct=sample_csrf"
    cookies = BilibiliCookies.from_browser_string(sample_string)

    logger.info(f"SESSDATA: {cookies.sessdata}")
    logger.info(f"DedeUserID: {cookies.dede_user_id}")
    logger.info(f"bili_jct: {cookies.bili_jct}")
    logger.info(f"Cookie 是否有效: {cookies.is_valid()}")

    # 3. 演示 Cookie 管理器
    logger.info("\n--- 3. Cookie 管理器使用 ---")
    manager = BilibiliCookieManager("data/bilibili_cookies.json")

    # 检查是否有现有 Cookie
    if await manager.load():
        logger.info("已加载现有 Cookie")

        # 验证 Cookie
        if await manager.verify():
            user_info = manager.user_info
            if user_info:
                logger.info(f"用户名: {user_info.get('uname')}")
                logger.info(f"等级: {user_info.get('level_info', {}).get('current_level')}")
                logger.info(f"硬币: {user_info.get('money')}")
        else:
            logger.warning("Cookie 已失效，需要重新登录")
    else:
        logger.info("没有找到 Cookie 文件")

    # 4. 展示使用方法
    logger.info("\n--- 4. 使用 Cookie 请求 API ---")
    logger.info("""
使用示例代码:

    # 方式1: 直接使用 httpx
    async with httpx.AsyncClient(
        cookies=cookies.to_httpx_cookies(),
        headers={"Referer": "https://www.bilibili.com/"}
    ) as client:
        resp = await client.get("https://api.bilibili.com/x/web-interface/nav")
        data = resp.json()

    # 方式2: 使用 Playwright
    context = await browser.new_context()
    await context.add_cookies(cookies.to_playwright_cookies())
    page = await context.new_page()
    """)

    # 5. 格式转换演示
    logger.info("\n--- 5. Cookie 格式转换 ---")
    playwright_format = cookies.to_playwright_cookies()
    httpx_format = cookies.to_httpx_cookies()
    header_format = cookies.to_header_string()

    logger.info(f"Playwright 格式: {playwright_format[:1]}...")
    logger.info(f"httpx 格式: {list(httpx_format.keys())}")
    logger.info(f"Header 格式: {header_format[:50]}...")


async def demo_with_real_api():
    """使用真实 API 的演示（需要有效 Cookie）"""
    manager = BilibiliCookieManager("data/bilibili_cookies.json")

    if not await manager.load():
        logger.info("请先准备 Cookie 文件")
        return

    cookies = await manager.get_valid_cookies()
    if not cookies:
        logger.error("Cookie 无效")
        return

    async with httpx.AsyncClient(
        cookies=cookies.to_httpx_cookies(),
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/131.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com/"
        }
    ) as client:
        # 获取用户信息
        resp = await client.get("https://api.bilibili.com/x/web-interface/nav")
        data = resp.json()

        if data.get("code") == 0:
            user = data.get("data", {})
            print(f"\n用户名: {user.get('uname')}")
            print(f"等级: {user.get('level_info', {}).get('current_level')}")
            print(f"硬币: {user.get('money')}")

        # 获取收藏夹
        resp = await client.get(
            "https://api.bilibili.com/x/v3/fav/folder/created/list-all",
            params={"up_mid": cookies.dede_user_id}
        )
        fav_data = resp.json()

        if fav_data.get("code") == 0:
            folders = fav_data.get("data", {}).get("list", [])
            print(f"\n收藏夹列表 ({len(folders)}个):")
            for folder in folders[:5]:
                print(f"  - {folder.get('title')} ({folder.get('media_count')}个)")


if __name__ == "__main__":
    asyncio.run(demo_bilibili_cookie())
