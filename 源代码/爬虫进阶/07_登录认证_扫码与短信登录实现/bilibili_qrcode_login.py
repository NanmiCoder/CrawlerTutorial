# -*- coding: utf-8 -*-
"""
B站扫码登录实战

本模块展示B站扫码登录的完整实现，包括：
- B站扫码API调用（二维码生成、状态轮询）
- 二维码图片生成与终端显示
- 登录状态监控与回调
- Cookie提取与保存

这是第07章"登录认证-扫码与短信登录实现"的B站实战示例。

与第11章综合实战项目的关联：
- login/auth.py: 登录模块实现
- config/bilibili_config.py: 登录相关常量定义
"""

import asyncio
import json
from io import BytesIO
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Callable, Awaitable, Dict
from enum import IntEnum

import httpx
from loguru import logger

# 可选依赖：二维码生成
try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False
    logger.warning("未安装 qrcode 库，终端二维码显示功能不可用。安装: pip install qrcode")


# ============== B站扫码状态枚举 ==============

class BilibiliQRStatus(IntEnum):
    """
    B站扫码状态码

    | 状态码 | 含义 |
    |-------|------|
    | 0 | 登录成功 |
    | 86101 | 未扫描 |
    | 86090 | 已扫描，待确认 |
    | 86038 | 已过期 |
    """
    SUCCESS = 0           # 登录成功
    NOT_SCANNED = 86101   # 未扫描
    SCANNED = 86090       # 已扫描，待确认
    EXPIRED = 86038       # 已过期


# ============== B站 Cookie 数据类 ==============

@dataclass
class BilibiliLoginCookies:
    """
    B站登录 Cookie 数据类

    扫码登录成功后提取的Cookie
    """
    sessdata: str
    dede_user_id: str
    bili_jct: str
    buvid3: str = ""
    buvid4: str = ""
    sid: str = ""

    def to_dict(self) -> Dict[str, str]:
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

    def to_header_string(self) -> str:
        """转换为请求头 Cookie 格式"""
        return "; ".join(f"{k}={v}" for k, v in self.to_dict().items())

    def is_valid(self) -> bool:
        """检查核心 Cookie 是否存在"""
        return bool(self.sessdata and self.dede_user_id and self.bili_jct)


# ============== B站扫码登录实现 ==============

class BilibiliQRCodeLogin:
    """
    B站扫码登录实现

    流程：
    1. 调用 /qrcode/generate 获取二维码URL和qrcode_key
    2. 生成二维码图片（保存到文件或终端显示）
    3. 轮询 /qrcode/poll 检查扫码状态
    4. 登录成功后提取Cookie

    使用示例：
        async with BilibiliQRCodeLogin() as login:
            cookies = await login.login()
            if cookies:
                print(f"登录成功: {cookies.dede_user_id}")
    """

    # B站登录相关API
    QRCODE_GENERATE_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
    QRCODE_POLL_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"

    # 请求头
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/131.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/",
        "Origin": "https://www.bilibili.com"
    }

    def __init__(
        self,
        timeout: int = 180,
        poll_interval: float = 2.0,
        on_status_change: Optional[Callable[[int, str], Awaitable[None]]] = None
    ):
        """
        初始化扫码登录

        Args:
            timeout: 登录超时时间（秒）
            poll_interval: 状态轮询间隔（秒）
            on_status_change: 状态变化回调 (status_code, message)
        """
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.on_status_change = on_status_change

        self._client: Optional[httpx.AsyncClient] = None
        self._qrcode_key: str = ""
        self._qrcode_url: str = ""
        self._current_status: int = -1

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self._client = httpx.AsyncClient(
            headers=self.HEADERS,
            timeout=30
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self._client:
            await self._client.aclose()

    async def _notify_status(self, code: int, message: str):
        """通知状态变化"""
        if code != self._current_status:
            self._current_status = code
            logger.info(f"B站登录状态: {message} ({code})")
            if self.on_status_change:
                await self.on_status_change(code, message)

    async def generate_qrcode(self) -> tuple:
        """
        生成登录二维码

        Returns:
            (qrcode_url, qrcode_image_bytes) 或 (qrcode_url, None) 如果无法生成图片
        """
        resp = await self._client.get(self.QRCODE_GENERATE_URL)
        data = resp.json()

        if data["code"] != 0:
            raise Exception(f"获取二维码失败: {data['message']}")

        self._qrcode_key = data["data"]["qrcode_key"]
        self._qrcode_url = data["data"]["url"]

        logger.info(f"二维码生成成功，qrcode_key: {self._qrcode_key[:20]}...")

        # 生成二维码图片
        image_bytes = None
        if HAS_QRCODE:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=2
            )
            qr.add_data(self._qrcode_url)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            image_bytes = buffer.getvalue()

        return self._qrcode_url, image_bytes

    def print_qrcode_to_terminal(self, url: Optional[str] = None):
        """在终端打印二维码"""
        if not HAS_QRCODE:
            logger.warning("需要安装 qrcode 库才能在终端显示二维码: pip install qrcode")
            return

        url = url or self._qrcode_url
        if not url:
            logger.warning("没有可用的二维码URL")
            return

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1
        )
        qr.add_data(url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)

    async def poll_status(self) -> tuple:
        """
        轮询登录状态

        Returns:
            (status_code, cookies_if_success)
        """
        if not self._qrcode_key:
            raise RuntimeError("请先调用 generate_qrcode() 生成二维码")

        resp = await self._client.get(
            self.QRCODE_POLL_URL,
            params={"qrcode_key": self._qrcode_key}
        )
        data = resp.json()

        code = data["data"]["code"]
        message = data["data"]["message"]

        await self._notify_status(code, message)

        if code == BilibiliQRStatus.SUCCESS:
            # 登录成功，从响应中提取Cookie
            cookies = self._extract_cookies(resp)
            return code, cookies

        return code, None

    def _extract_cookies(self, resp: httpx.Response) -> BilibiliLoginCookies:
        """从响应中提取B站Cookie"""
        cookies = resp.cookies

        return BilibiliLoginCookies(
            sessdata=cookies.get("SESSDATA", ""),
            dede_user_id=cookies.get("DedeUserID", ""),
            bili_jct=cookies.get("bili_jct", ""),
            buvid3=cookies.get("buvid3", ""),
            buvid4=cookies.get("buvid4", ""),
            sid=cookies.get("sid", ""),
        )

    async def login(
        self,
        save_qrcode_path: str = "bilibili_qrcode.png",
        show_in_terminal: bool = True
    ) -> Optional[BilibiliLoginCookies]:
        """
        执行完整的扫码登录流程

        Args:
            save_qrcode_path: 二维码图片保存路径
            show_in_terminal: 是否在终端显示二维码

        Returns:
            登录成功返回Cookie，失败返回None
        """
        # 1. 生成二维码
        url, image_bytes = await self.generate_qrcode()

        # 保存二维码图片
        if image_bytes:
            with open(save_qrcode_path, "wb") as f:
                f.write(image_bytes)
            logger.info(f"二维码已保存至: {save_qrcode_path}")

        # 在终端显示
        if show_in_terminal:
            print("\n" + "=" * 50)
            print("请使用B站APP扫描以下二维码登录")
            print("=" * 50 + "\n")

            if HAS_QRCODE:
                self.print_qrcode_to_terminal(url)
            else:
                print(f"二维码URL: {url}")

            if image_bytes:
                print(f"\n二维码图片也已保存至: {save_qrcode_path}\n")

        # 2. 轮询登录状态
        start_time = asyncio.get_event_loop().time()

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > self.timeout:
                logger.warning("登录超时")
                return None

            code, cookies = await self.poll_status()

            if code == BilibiliQRStatus.SUCCESS:
                logger.info("B站登录成功！")
                return cookies

            if code == BilibiliQRStatus.EXPIRED:
                logger.warning("二维码已过期")
                return None

            await asyncio.sleep(self.poll_interval)


# ============== Cookie 验证工具 ==============

async def verify_bilibili_cookies(cookies: Dict[str, str]) -> Optional[dict]:
    """
    验证B站Cookie是否有效

    Args:
        cookies: Cookie字典

    Returns:
        有效返回用户信息，无效返回None
    """
    async with httpx.AsyncClient(
        cookies=cookies,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/131.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com/",
        },
        timeout=10
    ) as client:
        resp = await client.get("https://api.bilibili.com/x/web-interface/nav")
        data = resp.json()

        if data["code"] == 0 and data["data"].get("isLogin"):
            return {
                "mid": data["data"]["mid"],
                "uname": data["data"]["uname"],
                "level": data["data"]["level_info"]["current_level"],
                "vip_type": data["data"]["vipType"],
                "money": data["data"]["money"],
            }

        return None


# ============== 演示入口 ==============

async def demo_bilibili_qrcode_login():
    """演示B站扫码登录"""
    logger.info("=" * 50)
    logger.info("B站扫码登录示例")
    logger.info("=" * 50)

    # 定义状态变化回调
    async def on_status(code: int, message: str):
        status_emoji = {
            BilibiliQRStatus.NOT_SCANNED: "...",
            BilibiliQRStatus.SCANNED: "[已扫描]",
            BilibiliQRStatus.SUCCESS: "[成功]",
            BilibiliQRStatus.EXPIRED: "[过期]",
        }
        emoji = status_emoji.get(code, "?")
        print(f"  {emoji} {message}")

    # 执行扫码登录
    async with BilibiliQRCodeLogin(
        timeout=180,
        poll_interval=2.0,
        on_status_change=on_status
    ) as login:
        cookies = await login.login(
            save_qrcode_path="bilibili_qrcode.png",
            show_in_terminal=True
        )

        if cookies:
            # 保存Cookie
            cookie_path = Path("data/bilibili_login_cookies.json")
            cookie_path.parent.mkdir(parents=True, exist_ok=True)

            with open(cookie_path, "w", encoding="utf-8") as f:
                json.dump(cookies.to_dict(), f, indent=2, ensure_ascii=False)

            print("\n" + "=" * 50)
            print("登录成功！")
            print("=" * 50)
            print(f"Cookie已保存至: {cookie_path}")
            print(f"SESSDATA: {cookies.sessdata[:20]}...")
            print(f"DedeUserID: {cookies.dede_user_id}")
            print(f"bili_jct: {cookies.bili_jct[:20]}...")

            # 验证Cookie
            user_info = await verify_bilibili_cookies(cookies.to_dict())
            if user_info:
                print(f"\n用户信息:")
                print(f"  用户名: {user_info['uname']}")
                print(f"  等级: LV{user_info['level']}")
                print(f"  硬币: {user_info['money']}")
        else:
            print("\n登录失败或超时")


async def demo_verify_existing_cookies():
    """演示验证已保存的Cookie"""
    logger.info("=" * 50)
    logger.info("验证已保存的B站Cookie")
    logger.info("=" * 50)

    cookie_path = Path("data/bilibili_login_cookies.json")

    if not cookie_path.exists():
        logger.info("没有找到已保存的Cookie，请先执行扫码登录")
        return

    with open(cookie_path, "r", encoding="utf-8") as f:
        cookies = json.load(f)

    user_info = await verify_bilibili_cookies(cookies)

    if user_info:
        print(f"Cookie有效！")
        print(f"  用户名: {user_info['uname']}")
        print(f"  用户ID: {user_info['mid']}")
        print(f"  等级: LV{user_info['level']}")
    else:
        print("Cookie已失效，请重新登录")


async def main():
    """主演示函数"""
    logger.info("\n" + "=" * 60)
    logger.info("B站扫码登录实战示例")
    logger.info("=" * 60)

    # 检查是否有已保存的Cookie
    cookie_path = Path("data/bilibili_login_cookies.json")
    if cookie_path.exists():
        logger.info("\n检测到已保存的Cookie，正在验证...")
        await demo_verify_existing_cookies()
        print("\n如需重新登录，请删除 data/bilibili_login_cookies.json 后重试")
    else:
        logger.info("\n开始扫码登录流程...")
        await demo_bilibili_qrcode_login()


if __name__ == "__main__":
    asyncio.run(main())
