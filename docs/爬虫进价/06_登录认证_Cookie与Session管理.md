# 06_登录认证：Cookie 与 Session 管理

在爬虫开发中，很多数据需要登录后才能获取。本章将深入讲解 Cookie 和 Session 的工作机制，以及如何在爬虫中高效管理登录状态。

## 一、认证机制深入理解

### 1.1 Cookie 的工作原理

Cookie 是服务器发送给浏览器的小型数据片段，浏览器会保存并在后续请求中自动携带。

```mermaid
sequenceDiagram
    participant Client as 客户端
    participant Server as 服务器

    Client->>Server: HTTP 请求 (首次访问)
    Server-->>Client: Set-Cookie: session=xxx
    Note over Client: 保存 Cookie 到本地

    Client->>Server: HTTP 请求 + Cookie: session=xxx
    Server-->>Client: 返回用户数据
    Note over Server: 识别用户身份
```

### 1.2 Cookie 属性详解

每个 Cookie 都有多个属性，理解这些属性对于正确使用 Cookie 至关重要：

| 属性 | 说明 | 爬虫影响 |
|-----|------|---------|
| **Name/Value** | Cookie 的名称和值 | 核心数据，必须正确提取 |
| **Domain** | Cookie 生效的域名 | 决定请求哪些域名时携带 |
| **Path** | Cookie 生效的路径 | 决定请求哪些路径时携带 |
| **Expires/Max-Age** | 过期时间 | 决定 Cookie 何时失效 |
| **HttpOnly** | 禁止 JavaScript 访问 | 只能通过 HTTP 响应获取 |
| **Secure** | 仅 HTTPS 传输 | 注意协议匹配 |
| **SameSite** | 跨站请求限制 | 影响第三方请求 |

```python
# Cookie 属性示例
cookie_example = {
    "name": "session_id",
    "value": "abc123xyz",
    "domain": ".example.com",      # 包含子域名
    "path": "/",                   # 所有路径
    "expires": 1735689600,         # Unix 时间戳
    "httpOnly": True,              # 不能通过 JS 访问
    "secure": True,                # 仅 HTTPS
    "sameSite": "Lax"              # 跨站限制
}
```

### 1.3 Session 机制

Session 是服务端的会话状态存储机制，通常通过 Cookie 中的 Session ID 关联：

```python
# 服务端 Session 工作流程（伪代码）
class SessionFlow:
    """
    1. 用户登录 -> 服务器创建 Session
    2. 服务器返回 Session ID (通过 Set-Cookie)
    3. 浏览器携带 Session ID 访问
    4. 服务器根据 Session ID 查找用户状态
    """

    def login(self, username, password):
        if self.verify(username, password):
            session_id = generate_session_id()
            self.sessions[session_id] = {
                "user_id": user.id,
                "login_time": time.time(),
                "expires": time.time() + 3600 * 24
            }
            return session_id
        return None
```

### 1.4 Token 认证机制

现代应用越来越多使用 Token 认证（如 JWT），与 Cookie/Session 有所不同：

| 特性 | Cookie/Session | Token (JWT) |
|-----|----------------|-------------|
| 状态存储 | 服务端 | 客户端（Token 自包含） |
| 跨域支持 | 受限（SameSite） | 天然支持 |
| 传输方式 | Cookie 头 | Authorization 头 |
| 服务端开销 | 需要存储 Session | 无状态 |

```python
# Token 认证示例
import httpx

headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}

async with httpx.AsyncClient() as client:
    resp = await client.get("https://api.example.com/data", headers=headers)
```

## 二、Cookie 的提取与存储

### 2.1 从浏览器手动提取

最简单的方式是从浏览器开发者工具中手动复制 Cookie：

1. 打开浏览器，登录目标网站
2. 按 F12 打开开发者工具
3. 切换到 Application/Storage -> Cookies
4. 复制需要的 Cookie 值

```python
# 手动提取的 Cookie 使用示例
import httpx

cookies = {
    "session_id": "abc123",
    "user_token": "xyz789",
    "preferences": "theme=dark"
}

async with httpx.AsyncClient(cookies=cookies) as client:
    resp = await client.get("https://example.com/user/profile")
```

### 2.2 使用 Playwright 自动提取

Playwright 可以自动化登录流程并提取 Cookie：

```python
from playwright.async_api import async_playwright
import json

async def extract_cookies_after_login():
    """登录后自动提取 Cookie"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 有头模式便于手动登录
        context = await browser.new_context()
        page = await context.new_page()

        # 导航到登录页
        await page.goto("https://example.com/login")

        # 等待用户手动登录（或自动填写表单）
        # await page.fill("#username", "your_username")
        # await page.fill("#password", "your_password")
        # await page.click("#login-button")

        # 等待登录成功（检测特定元素或 URL 变化）
        await page.wait_for_url("**/dashboard**", timeout=120000)

        # 提取所有 Cookie
        cookies = await context.cookies()

        # 保存到文件
        with open("cookies.json", "w") as f:
            json.dump(cookies, f, indent=2)

        print(f"提取了 {len(cookies)} 个 Cookie")

        await browser.close()
        return cookies
```

### 2.3 Cookie 序列化格式

Cookie 可以用多种格式存储，常见的有 JSON 和 Netscape 格式：

```python
import json
from http.cookiejar import MozillaCookieJar
from datetime import datetime

class CookieSerializer:
    """Cookie 序列化工具"""

    @staticmethod
    def to_json(cookies: list, filepath: str):
        """保存为 JSON 格式"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)

    @staticmethod
    def from_json(filepath: str) -> list:
        """从 JSON 加载"""
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def to_netscape(cookies: list, filepath: str):
        """保存为 Netscape 格式（兼容 curl/wget）"""
        lines = ["# Netscape HTTP Cookie File"]
        for c in cookies:
            # 格式: domain, flag, path, secure, expiry, name, value
            domain = c.get("domain", "")
            flag = "TRUE" if domain.startswith(".") else "FALSE"
            path = c.get("path", "/")
            secure = "TRUE" if c.get("secure", False) else "FALSE"
            expiry = str(int(c.get("expires", 0)))
            name = c.get("name", "")
            value = c.get("value", "")

            lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}")

        with open(filepath, "w") as f:
            f.write("\n".join(lines))

    @staticmethod
    def to_dict(cookies: list) -> dict:
        """转换为简单字典格式（name: value）"""
        return {c["name"]: c["value"] for c in cookies}
```

### 2.4 Cookie 加密存储

对于敏感的 Cookie，建议加密存储：

```python
import json
import base64
from cryptography.fernet import Fernet

class SecureCookieStorage:
    """加密 Cookie 存储"""

    def __init__(self, key: bytes = None):
        # 如果没有提供密钥，生成新密钥
        self.key = key or Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def save_key(self, filepath: str):
        """保存密钥（请妥善保管）"""
        with open(filepath, "wb") as f:
            f.write(self.key)

    @classmethod
    def load_key(cls, filepath: str) -> "SecureCookieStorage":
        """从文件加载密钥"""
        with open(filepath, "rb") as f:
            return cls(f.read())

    def encrypt_cookies(self, cookies: list, filepath: str):
        """加密并保存 Cookie"""
        data = json.dumps(cookies).encode("utf-8")
        encrypted = self.cipher.encrypt(data)
        with open(filepath, "wb") as f:
            f.write(encrypted)

    def decrypt_cookies(self, filepath: str) -> list:
        """解密并加载 Cookie"""
        with open(filepath, "rb") as f:
            encrypted = f.read()
        decrypted = self.cipher.decrypt(encrypted)
        return json.loads(decrypted.decode("utf-8"))
```

## 三、Cookie 注入与使用

### 3.1 httpx 中使用 Cookie

httpx 提供了灵活的 Cookie 管理方式：

```python
import httpx

# 方式1: 直接传入字典
cookies_dict = {"session": "abc123", "token": "xyz"}
async with httpx.AsyncClient(cookies=cookies_dict) as client:
    resp = await client.get("https://example.com/api")

# 方式2: 使用 Cookies 对象
from httpx import Cookies

cookies = Cookies()
cookies.set("session", "abc123", domain="example.com")
cookies.set("token", "xyz", domain="example.com")

async with httpx.AsyncClient(cookies=cookies) as client:
    resp = await client.get("https://example.com/api")

# 方式3: 从响应中自动获取
async with httpx.AsyncClient() as client:
    # 登录请求会设置 Cookie
    login_resp = await client.post(
        "https://example.com/login",
        data={"username": "user", "password": "pass"}
    )
    # 后续请求自动携带 Cookie
    profile_resp = await client.get("https://example.com/profile")
```

### 3.2 Playwright 中注入 Cookie

Playwright 可以在访问页面前注入 Cookie：

```python
from playwright.async_api import async_playwright
import json

async def inject_cookies_and_browse():
    """注入 Cookie 并访问页面"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        # 从文件加载 Cookie
        with open("cookies.json", "r") as f:
            cookies = json.load(f)

        # 注入 Cookie
        await context.add_cookies(cookies)

        # 现在可以直接访问需要登录的页面
        page = await context.new_page()
        await page.goto("https://example.com/dashboard")

        # 检查是否登录成功
        if await page.locator(".user-avatar").is_visible():
            print("Cookie 注入成功，已登录")
        else:
            print("Cookie 可能已过期")

        await browser.close()
```

### 3.3 跨工具共享 Cookie

将 Playwright 提取的 Cookie 转换为 httpx 可用的格式：

```python
def playwright_cookies_to_httpx(playwright_cookies: list) -> dict:
    """
    将 Playwright 格式的 Cookie 转换为 httpx 格式

    Playwright 格式: [{"name": "x", "value": "y", "domain": "...", ...}, ...]
    httpx 格式: {"name": "value", ...}
    """
    return {c["name"]: c["value"] for c in playwright_cookies}

def httpx_cookies_to_playwright(cookies_dict: dict, domain: str) -> list:
    """
    将简单字典格式转换为 Playwright 格式
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
```

### 3.4 多账号 Cookie 轮换

在需要多账号爬取的场景，可以实现 Cookie 轮换：

```python
import asyncio
import random
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class AccountCookie:
    """账号 Cookie 信息"""
    account_id: str
    cookies: dict
    last_used: Optional[datetime] = None
    use_count: int = 0
    is_valid: bool = True

class CookieRotator:
    """Cookie 轮换器"""

    def __init__(self, min_interval: float = 5.0):
        self._accounts: Dict[str, AccountCookie] = {}
        self._min_interval = min_interval  # 同一账号最小使用间隔（秒）
        self._lock = asyncio.Lock()

    def add_account(self, account_id: str, cookies: dict):
        """添加账号"""
        self._accounts[account_id] = AccountCookie(
            account_id=account_id,
            cookies=cookies
        )

    async def get_cookies(self) -> Optional[dict]:
        """获取一个可用的 Cookie"""
        async with self._lock:
            now = datetime.now()
            available = []

            for acc in self._accounts.values():
                if not acc.is_valid:
                    continue

                # 检查使用间隔
                if acc.last_used:
                    elapsed = (now - acc.last_used).total_seconds()
                    if elapsed < self._min_interval:
                        continue

                available.append(acc)

            if not available:
                return None

            # 选择使用次数最少的账号（负载均衡）
            selected = min(available, key=lambda x: x.use_count)
            selected.last_used = now
            selected.use_count += 1

            return selected.cookies

    def mark_invalid(self, cookies: dict):
        """标记 Cookie 失效"""
        for acc in self._accounts.values():
            if acc.cookies == cookies:
                acc.is_valid = False
                break

    @property
    def valid_count(self) -> int:
        """有效账号数量"""
        return sum(1 for acc in self._accounts.values() if acc.is_valid)
```

## 四、登录状态管理

### 4.1 登录状态检测

检测 Cookie 是否仍然有效是关键步骤：

```python
import httpx
from typing import Callable, Awaitable
from loguru import logger

class LoginStateChecker:
    """登录状态检测器"""

    def __init__(
        self,
        check_url: str,
        success_indicator: Callable[[httpx.Response], bool]
    ):
        """
        Args:
            check_url: 用于检测登录状态的 URL
            success_indicator: 判断是否登录成功的函数
        """
        self.check_url = check_url
        self.success_indicator = success_indicator

    async def is_logged_in(self, cookies: dict) -> bool:
        """检查是否已登录"""
        try:
            async with httpx.AsyncClient(cookies=cookies) as client:
                resp = await client.get(self.check_url, timeout=10)
                return self.success_indicator(resp)
        except Exception as e:
            logger.warning(f"登录状态检测失败: {e}")
            return False

    @classmethod
    def create_json_checker(cls, check_url: str, success_field: str) -> "LoginStateChecker":
        """
        创建 JSON 响应检测器

        Args:
            check_url: API 地址
            success_field: 成功时 JSON 中存在的字段
        """
        def indicator(resp: httpx.Response) -> bool:
            try:
                data = resp.json()
                return success_field in data
            except:
                return False

        return cls(check_url, indicator)

    @classmethod
    def create_redirect_checker(cls, check_url: str, login_url: str) -> "LoginStateChecker":
        """
        创建重定向检测器

        Args:
            check_url: 需要登录的页面
            login_url: 登录页 URL（被重定向到此说明未登录）
        """
        def indicator(resp: httpx.Response) -> bool:
            # 如果没有被重定向到登录页，说明已登录
            return login_url not in str(resp.url)

        return cls(check_url, indicator)
```

### 4.2 Cookie 过期检测

监控 Cookie 的过期时间：

```python
import time
from datetime import datetime, timedelta
from typing import List, Tuple

class CookieExpiryMonitor:
    """Cookie 过期监控"""

    @staticmethod
    def check_expiry(cookies: list) -> Tuple[bool, List[dict]]:
        """
        检查 Cookie 是否过期

        Returns:
            (是否全部有效, 已过期的 Cookie 列表)
        """
        now = time.time()
        expired = []

        for cookie in cookies:
            expires = cookie.get("expires", 0)
            if expires > 0 and expires < now:
                expired.append(cookie)

        return len(expired) == 0, expired

    @staticmethod
    def get_earliest_expiry(cookies: list) -> datetime:
        """获取最早过期的时间"""
        expiry_times = [
            c.get("expires", float("inf"))
            for c in cookies
            if c.get("expires", 0) > 0
        ]

        if not expiry_times:
            return datetime.max

        return datetime.fromtimestamp(min(expiry_times))

    @staticmethod
    def will_expire_soon(cookies: list, threshold_hours: int = 1) -> bool:
        """检查 Cookie 是否即将过期"""
        earliest = CookieExpiryMonitor.get_earliest_expiry(cookies)
        return earliest < datetime.now() + timedelta(hours=threshold_hours)
```

### 4.3 完整的 Cookie 管理器

整合以上功能的完整管理器：

```python
import json
import asyncio
from pathlib import Path
from typing import Optional, Callable, Awaitable
from datetime import datetime
from loguru import logger

class CookieManager:
    """完整的 Cookie 管理器"""

    def __init__(
        self,
        storage_path: str,
        check_url: str,
        login_checker: Callable[[dict], Awaitable[bool]],
        auto_refresh_callback: Optional[Callable[[], Awaitable[dict]]] = None
    ):
        """
        Args:
            storage_path: Cookie 存储路径
            check_url: 登录状态检测 URL
            login_checker: 登录状态检测函数
            auto_refresh_callback: 自动刷新回调（如重新登录）
        """
        self.storage_path = Path(storage_path)
        self.check_url = check_url
        self.login_checker = login_checker
        self.auto_refresh_callback = auto_refresh_callback

        self._cookies: Optional[list] = None
        self._last_check: Optional[datetime] = None
        self._check_interval = 300  # 5分钟检测一次

    async def load(self) -> bool:
        """加载 Cookie"""
        if not self.storage_path.exists():
            logger.warning(f"Cookie 文件不存在: {self.storage_path}")
            return False

        try:
            with open(self.storage_path, "r") as f:
                self._cookies = json.load(f)
            logger.info(f"加载了 {len(self._cookies)} 个 Cookie")
            return True
        except Exception as e:
            logger.error(f"加载 Cookie 失败: {e}")
            return False

    async def save(self):
        """保存 Cookie"""
        if self._cookies:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, "w") as f:
                json.dump(self._cookies, f, indent=2)
            logger.info(f"保存了 {len(self._cookies)} 个 Cookie")

    def update(self, cookies: list):
        """更新 Cookie"""
        self._cookies = cookies
        self._last_check = datetime.now()

    async def get_valid_cookies(self) -> Optional[dict]:
        """获取有效的 Cookie（自动检测和刷新）"""
        # 首次加载
        if self._cookies is None:
            await self.load()

        if not self._cookies:
            if self.auto_refresh_callback:
                await self._refresh_cookies()
            return None

        # 检查是否需要验证
        if self._need_check():
            is_valid = await self._validate()
            if not is_valid:
                if self.auto_refresh_callback:
                    await self._refresh_cookies()
                else:
                    return None

        # 返回简单字典格式
        return {c["name"]: c["value"] for c in self._cookies}

    def _need_check(self) -> bool:
        """是否需要检测"""
        if self._last_check is None:
            return True
        elapsed = (datetime.now() - self._last_check).total_seconds()
        return elapsed > self._check_interval

    async def _validate(self) -> bool:
        """验证 Cookie 是否有效"""
        logger.debug("验证 Cookie 有效性...")
        cookies_dict = {c["name"]: c["value"] for c in self._cookies}
        is_valid = await self.login_checker(cookies_dict)
        self._last_check = datetime.now()

        if is_valid:
            logger.info("Cookie 验证通过")
        else:
            logger.warning("Cookie 已失效")

        return is_valid

    async def _refresh_cookies(self):
        """刷新 Cookie"""
        if not self.auto_refresh_callback:
            return

        logger.info("开始刷新 Cookie...")
        try:
            new_cookies = await self.auto_refresh_callback()
            if new_cookies:
                self._cookies = new_cookies
                await self.save()
                logger.info("Cookie 刷新成功")
        except Exception as e:
            logger.error(f"Cookie 刷新失败: {e}")
```

## 五、B站 Cookie 管理实战

### 5.1 B站 Cookie 结构分析

B站使用多个关键 Cookie 来管理用户登录状态：

```mermaid
graph TB
    subgraph B站核心Cookie
        SESSDATA["SESSDATA<br/>会话凭证"]
        DedeUserID["DedeUserID<br/>用户ID"]
        bili_jct["bili_jct<br/>CSRF Token"]
    end

    subgraph 辅助Cookie
        buvid3["buvid3<br/>设备标识"]
        buvid4["buvid4<br/>设备标识"]
        sid["sid<br/>短会话ID"]
    end

    SESSDATA --> API["API请求认证"]
    DedeUserID --> API
    bili_jct --> POST["POST请求CSRF"]

    style SESSDATA fill:#e8f5e9,stroke:#4caf50
    style DedeUserID fill:#e8f5e9,stroke:#4caf50
    style bili_jct fill:#fff3e0,stroke:#ff9800
```

| Cookie 名称 | 作用 | 有效期 | 说明 |
|------------|------|-------|------|
| **SESSDATA** | 会话凭证 | ~1个月 | 最重要的登录凭证 |
| **DedeUserID** | 用户ID | ~1个月 | 用于部分API请求 |
| **bili_jct** | CSRF Token | ~1个月 | POST请求必需 |
| buvid3 | 设备标识 | ~1年 | 追踪设备 |
| buvid4 | 设备标识 | ~1年 | 追踪设备 |
| sid | 短会话 | 会话 | 短期会话标识 |

### 5.2 B站 Cookie 提取器

```python
# -*- coding: utf-8 -*-
"""
B站 Cookie 提取和管理
"""

import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime
from loguru import logger


@dataclass
class BilibiliCookies:
    """B站 Cookie 数据类"""
    sessdata: str
    dede_user_id: str
    bili_jct: str
    buvid3: str = ""
    buvid4: str = ""
    sid: str = ""
    raw_cookies: List[dict] = None

    @classmethod
    def from_playwright_cookies(cls, cookies: List[dict]) -> "BilibiliCookies":
        """从 Playwright 格式的 Cookie 创建"""
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

        格式: "SESSDATA=xxx; DedeUserID=xxx; bili_jct=xxx"
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
        """转换为 httpx 可用的格式"""
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
        """转换为 Playwright 可用的格式"""
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
        """转换为请求头格式"""
        return "; ".join(f"{k}={v}" for k, v in self.to_httpx_cookies().items())


class BilibiliCookieManager:
    """
    B站 Cookie 管理器

    功能：
    - Cookie 加载/保存
    - 登录状态检测
    - Cookie 有效性验证
    """

    # 登录状态检测 API
    CHECK_URL = "https://api.bilibili.com/x/web-interface/nav"

    def __init__(self, storage_path: str = "bilibili_cookies.json"):
        self.storage_path = Path(storage_path)
        self._cookies: Optional[BilibiliCookies] = None
        self._last_check: Optional[datetime] = None

    async def load(self) -> bool:
        """从文件加载 Cookie"""
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

    async def save(self, cookies: BilibiliCookies):
        """保存 Cookie 到文件"""
        self._cookies = cookies
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "SESSDATA": cookies.sessdata,
            "DedeUserID": cookies.dede_user_id,
            "bili_jct": cookies.bili_jct,
            "buvid3": cookies.buvid3,
            "buvid4": cookies.buvid4,
            "sid": cookies.sid,
            "save_time": datetime.now().isoformat()
        }

        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Cookie 已保存到: {self.storage_path}")

    async def verify(self) -> bool:
        """验证 Cookie 是否有效"""
        if not self._cookies or not self._cookies.is_valid():
            return False

        import httpx

        try:
            async with httpx.AsyncClient(
                cookies=self._cookies.to_httpx_cookies(),
                timeout=10
            ) as client:
                resp = await client.get(self.CHECK_URL)
                data = resp.json()

                if data.get("code") == 0:
                    user_info = data.get("data", {})
                    if user_info.get("isLogin"):
                        logger.info(f"Cookie 有效，用户: {user_info.get('uname')}")
                        self._last_check = datetime.now()
                        return True

                logger.warning("Cookie 已失效")
                return False

        except Exception as e:
            logger.error(f"验证 Cookie 失败: {e}")
            return False

    async def get_valid_cookies(self) -> Optional[BilibiliCookies]:
        """获取有效的 Cookie"""
        if self._cookies is None:
            await self.load()

        if self._cookies and await self.verify():
            return self._cookies

        return None

    @property
    def cookies(self) -> Optional[BilibiliCookies]:
        """获取当前 Cookie（不验证）"""
        return self._cookies
```

### 5.3 B站 Cookie 使用示例

```python
# -*- coding: utf-8 -*-
"""
B站 Cookie 使用示例
"""

import asyncio
import httpx
from loguru import logger


async def demo_bilibili_cookie():
    """演示如何使用 B站 Cookie"""

    # 方式1: 从浏览器复制的字符串
    cookie_string = "SESSDATA=xxx; DedeUserID=123456; bili_jct=xxx"
    cookies = BilibiliCookies.from_browser_string(cookie_string)

    # 方式2: 使用 Cookie 管理器
    manager = BilibiliCookieManager("data/bilibili_cookies.json")
    await manager.load()

    if not await manager.verify():
        logger.error("Cookie 无效，请重新登录")
        return

    cookies = manager.cookies

    # 使用 Cookie 请求 API
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
            print(f"用户名: {user.get('uname')}")
            print(f"等级: {user.get('level_info', {}).get('current_level')}")
            print(f"硬币: {user.get('money')}")

        # 获取收藏夹（需要登录）
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
```

### 5.4 B站 Cookie 与 Playwright 集成

```python
# -*- coding: utf-8 -*-
"""
B站 Cookie 与 Playwright 集成
"""

import asyncio
from playwright.async_api import async_playwright
from loguru import logger


async def bilibili_with_playwright():
    """使用 Playwright 注入 B站 Cookie"""

    # 加载 Cookie
    manager = BilibiliCookieManager("data/bilibili_cookies.json")
    await manager.load()

    if not manager.cookies or not manager.cookies.is_valid():
        logger.error("Cookie 无效")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN"
        )

        # 注入 Cookie
        await context.add_cookies(
            manager.cookies.to_playwright_cookies()
        )

        page = await context.new_page()

        # 访问个人主页
        await page.goto("https://space.bilibili.com/", wait_until="networkidle")

        # 检查是否登录成功
        avatar = page.locator(".bili-avatar")
        if await avatar.count() > 0:
            logger.info("Cookie 注入成功，已登录")

            # 获取用户名
            username = await page.locator(".h-name").text_content()
            print(f"当前用户: {username}")
        else:
            logger.warning("Cookie 可能已过期")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(bilibili_with_playwright())
```

---

## 六、完整的登录会话管理

下面是一个完整的实战示例，展示如何在爬虫中管理登录状态：

```python
# session_crawler.py
import asyncio
import httpx
from typing import Optional
from loguru import logger

from cookie_manager import CookieManager
from login_state_checker import LoginStateChecker

class SessionCrawler:
    """带登录状态管理的爬虫"""

    def __init__(self, base_url: str, cookie_path: str):
        self.base_url = base_url
        self.cookie_path = cookie_path

        # 初始化登录检测器
        self.checker = LoginStateChecker.create_json_checker(
            check_url=f"{base_url}/api/user/info",
            success_field="user_id"
        )

        # 初始化 Cookie 管理器
        self.cookie_manager = CookieManager(
            storage_path=cookie_path,
            check_url=f"{base_url}/api/user/info",
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
            raise RuntimeError("无法获取有效的 Cookie，请先登录")

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            cookies=cookies,
            timeout=30
        )
        logger.info("爬虫启动成功")

    async def close(self):
        """关闭爬虫"""
        if self._client:
            await self._client.aclose()
        await self.cookie_manager.save()
        logger.info("爬虫已关闭")

    async def fetch(self, endpoint: str) -> dict:
        """获取数据"""
        try:
            resp = await self._client.get(endpoint)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.warning("登录状态失效，需要重新登录")
                # 可以在这里触发重新登录逻辑
            raise


async def main():
    """使用示例"""
    async with SessionCrawler(
        base_url="https://example.com",
        cookie_path="data/cookies.json"
    ) as crawler:
        # 获取用户信息
        user_info = await crawler.fetch("/api/user/info")
        print(f"用户: {user_info.get('username')}")

        # 获取数据列表
        data_list = await crawler.fetch("/api/data/list")
        print(f"获取了 {len(data_list)} 条数据")


if __name__ == "__main__":
    asyncio.run(main())
```

## 六、最佳实践

### 6.1 Cookie 安全存储建议

1. **不要硬编码 Cookie**：将 Cookie 存储在配置文件或环境变量中
2. **敏感 Cookie 加密**：使用加密存储敏感的登录凭证
3. **设置合适的文件权限**：Cookie 文件应限制访问权限
4. **定期轮换**：定期重新登录获取新 Cookie

### 6.2 登录状态管理建议

1. **检测频率控制**：不要频繁检测，设置合理的检测间隔
2. **优雅降级**：Cookie 失效时应有备用方案
3. **多账号轮换**：大规模爬取时使用多账号
4. **遵守频率限制**：避免触发反爬机制

### 6.3 常见问题排查

| 问题 | 可能原因 | 解决方案 |
|-----|---------|---------|
| Cookie 无效 | 已过期/被踢出 | 检查过期时间，重新登录 |
| 请求被拒绝 | 缺少必要 Cookie | 检查 Cookie 完整性 |
| 跨域问题 | Domain 不匹配 | 检查 Cookie 的 Domain 属性 |
| HTTPS 问题 | Secure 属性 | 确保使用 HTTPS 协议 |

## 本章小结

本章深入讲解了 Cookie 和 Session 的工作机制，以及在爬虫中如何有效管理登录状态：

1. **理解认证机制**：Cookie 属性、Session 原理、Token 认证
2. **Cookie 提取存储**：手动提取、自动化提取、序列化格式、加密存储
3. **Cookie 注入使用**：httpx 和 Playwright 中的使用方式、跨工具共享
4. **登录状态管理**：状态检测、过期监控、自动刷新机制
5. **B站实战**：Cookie 结构分析、专用管理器、验证与使用

掌握这些技术后，你就能够处理大多数需要登录的爬虫场景。

---

## 与第11章实战项目的关联

本章 Cookie 管理技术在第11章 B站综合实战项目中有核心应用：

| 本章内容 | 第11章对应实现 | 文件位置 |
|---------|--------------|---------|
| BilibiliCookies 数据类 | Cookie 模型定义 | `models/cookies.py` |
| BilibiliCookieManager | 登录管理器 | `login/auth.py` |
| Cookie 验证逻辑 | 登录状态检测 | `login/auth.py` |
| Playwright 集成 | 扫码登录实现 | `login/auth.py` |

```mermaid
graph LR
    subgraph 本章知识点
        A1["Cookie结构"]
        A2["Cookie管理器"]
        A3["登录验证"]
    end

    subgraph 第11章实战应用
        B1["扫码登录"]
        B2["登录态保持"]
        B3["API请求认证"]
    end

    A1 --> B1
    A2 --> B2
    A3 --> B3

    style A1 fill:#e3f2fd,stroke:#2196f3
    style A2 fill:#e3f2fd,stroke:#2196f3
    style A3 fill:#e3f2fd,stroke:#2196f3
    style B1 fill:#c8e6c9,stroke:#4caf50
    style B2 fill:#c8e6c9,stroke:#4caf50
    style B3 fill:#c8e6c9,stroke:#4caf50
```

**学习建议**：

1. 理解 B站三大核心 Cookie（SESSDATA、DedeUserID、bili_jct）的作用
2. 掌握 Cookie 的提取、存储、验证完整流程
3. 在第11章中，`login/auth.py` 是 Cookie 管理的核心实现

## 下一章预告

下一章我们将学习更复杂的登录方式——**扫码登录和短信验证码登录**的实现。我们会参考 MediaCrawler 的登录模块设计，学习如何处理二维码扫码流程、短信验证码接收等高级场景。
