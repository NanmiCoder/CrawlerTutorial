# -*- coding: utf-8 -*-
# @Desc: Cookie 管理器 - 完整的 Cookie 存储、加载、验证和刷新功能

import json
import asyncio
from pathlib import Path
from typing import Optional, Callable, Awaitable, List, Dict
from datetime import datetime
from dataclasses import dataclass, field
from loguru import logger

# 可选的加密支持
try:
    from cryptography.fernet import Fernet
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


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
        """
        保存为 Netscape 格式（兼容 curl/wget）
        格式: domain, flag, path, secure, expiry, name, value
        """
        lines = ["# Netscape HTTP Cookie File", "# https://curl.se/docs/http-cookies.html"]

        for c in cookies:
            domain = c.get("domain", "")
            flag = "TRUE" if domain.startswith(".") else "FALSE"
            path = c.get("path", "/")
            secure = "TRUE" if c.get("secure", False) else "FALSE"
            expiry = str(int(c.get("expires", 0)))
            name = c.get("name", "")
            value = c.get("value", "")

            lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    @staticmethod
    def to_dict(cookies: list) -> dict:
        """转换为简单字典格式（name: value）"""
        return {c["name"]: c["value"] for c in cookies}

    @staticmethod
    def playwright_to_httpx(playwright_cookies: list) -> dict:
        """将 Playwright 格式转换为 httpx 格式"""
        return {c["name"]: c["value"] for c in playwright_cookies}

    @staticmethod
    def dict_to_playwright(cookies_dict: dict, domain: str) -> list:
        """将简单字典转换为 Playwright 格式"""
        return [
            {
                "name": name,
                "value": value,
                "domain": domain,
                "path": "/"
            }
            for name, value in cookies_dict.items()
        ]


class SecureCookieStorage:
    """加密 Cookie 存储"""

    def __init__(self, key: bytes = None):
        if not HAS_CRYPTO:
            raise ImportError("需要安装 cryptography 库: pip install cryptography")

        # 如果没有提供密钥，生成新密钥
        self.key = key or Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def save_key(self, filepath: str):
        """保存密钥（请妥善保管）"""
        with open(filepath, "wb") as f:
            f.write(self.key)
        logger.info(f"密钥已保存到: {filepath}")

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
        logger.info(f"Cookie 已加密保存到: {filepath}")

    def decrypt_cookies(self, filepath: str) -> list:
        """解密并加载 Cookie"""
        with open(filepath, "rb") as f:
            encrypted = f.read()
        decrypted = self.cipher.decrypt(encrypted)
        cookies = json.loads(decrypted.decode("utf-8"))
        logger.info(f"已解密加载 {len(cookies)} 个 Cookie")
        return cookies


@dataclass
class AccountCookie:
    """账号 Cookie 信息"""
    account_id: str
    cookies: dict
    last_used: Optional[datetime] = None
    use_count: int = 0
    is_valid: bool = True
    created_at: datetime = field(default_factory=datetime.now)


class CookieRotator:
    """Cookie 轮换器 - 支持多账号 Cookie 管理"""

    def __init__(self, min_interval: float = 5.0):
        """
        Args:
            min_interval: 同一账号最小使用间隔（秒）
        """
        self._accounts: Dict[str, AccountCookie] = {}
        self._min_interval = min_interval
        self._lock = asyncio.Lock()

    def add_account(self, account_id: str, cookies: dict):
        """添加账号"""
        self._accounts[account_id] = AccountCookie(
            account_id=account_id,
            cookies=cookies
        )
        logger.info(f"添加账号: {account_id}")

    def remove_account(self, account_id: str):
        """移除账号"""
        if account_id in self._accounts:
            del self._accounts[account_id]
            logger.info(f"移除账号: {account_id}")

    async def get_cookies(self) -> Optional[dict]:
        """获取一个可用的 Cookie（负载均衡）"""
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
                logger.warning("没有可用的账号")
                return None

            # 选择使用次数最少的账号（负载均衡）
            selected = min(available, key=lambda x: x.use_count)
            selected.last_used = now
            selected.use_count += 1

            logger.debug(f"使用账号: {selected.account_id} (使用次数: {selected.use_count})")
            return selected.cookies

    def mark_invalid(self, account_id: str):
        """标记账号失效"""
        if account_id in self._accounts:
            self._accounts[account_id].is_valid = False
            logger.warning(f"账号已标记失效: {account_id}")

    def mark_valid(self, account_id: str):
        """标记账号有效"""
        if account_id in self._accounts:
            self._accounts[account_id].is_valid = True
            logger.info(f"账号已标记有效: {account_id}")

    @property
    def valid_count(self) -> int:
        """有效账号数量"""
        return sum(1 for acc in self._accounts.values() if acc.is_valid)

    @property
    def total_count(self) -> int:
        """总账号数量"""
        return len(self._accounts)

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total": self.total_count,
            "valid": self.valid_count,
            "invalid": self.total_count - self.valid_count,
            "accounts": [
                {
                    "id": acc.account_id,
                    "valid": acc.is_valid,
                    "use_count": acc.use_count,
                    "last_used": acc.last_used.isoformat() if acc.last_used else None
                }
                for acc in self._accounts.values()
            ]
        }


class CookieManager:
    """完整的 Cookie 管理器"""

    def __init__(
        self,
        storage_path: str,
        login_checker: Callable[[dict], Awaitable[bool]],
        auto_refresh_callback: Optional[Callable[[], Awaitable[list]]] = None,
        check_interval: int = 300
    ):
        """
        Args:
            storage_path: Cookie 存储路径
            login_checker: 登录状态检测函数，接收 cookies dict，返回是否有效
            auto_refresh_callback: 自动刷新回调（如重新登录），返回新的 cookies list
            check_interval: 检测间隔（秒），默认 5 分钟
        """
        self.storage_path = Path(storage_path)
        self.login_checker = login_checker
        self.auto_refresh_callback = auto_refresh_callback
        self._check_interval = check_interval

        self._cookies: Optional[list] = None
        self._last_check: Optional[datetime] = None

    async def load(self) -> bool:
        """加载 Cookie"""
        if not self.storage_path.exists():
            logger.warning(f"Cookie 文件不存在: {self.storage_path}")
            return False

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
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
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self._cookies, f, indent=2, ensure_ascii=False)
            logger.info(f"保存了 {len(self._cookies)} 个 Cookie")

    def update(self, cookies: list):
        """更新 Cookie"""
        self._cookies = cookies
        self._last_check = datetime.now()
        logger.info(f"更新了 {len(cookies)} 个 Cookie")

    async def get_valid_cookies(self) -> Optional[dict]:
        """
        获取有效的 Cookie（自动检测和刷新）

        Returns:
            简单字典格式的 Cookie，如 {"name": "value", ...}
        """
        # 首次加载
        if self._cookies is None:
            await self.load()

        if not self._cookies:
            if self.auto_refresh_callback:
                await self._refresh_cookies()
            if not self._cookies:
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
        return CookieSerializer.to_dict(self._cookies)

    async def get_playwright_cookies(self) -> Optional[list]:
        """
        获取 Playwright 格式的 Cookie

        Returns:
            Playwright 格式的 Cookie 列表
        """
        if self._cookies is None:
            await self.load()
        return self._cookies

    def _need_check(self) -> bool:
        """是否需要检测"""
        if self._last_check is None:
            return True
        elapsed = (datetime.now() - self._last_check).total_seconds()
        return elapsed > self._check_interval

    async def _validate(self) -> bool:
        """验证 Cookie 是否有效"""
        logger.debug("验证 Cookie 有效性...")
        cookies_dict = CookieSerializer.to_dict(self._cookies)
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
                self._last_check = datetime.now()
                await self.save()
                logger.info("Cookie 刷新成功")
        except Exception as e:
            logger.error(f"Cookie 刷新失败: {e}")

    async def force_refresh(self) -> bool:
        """强制刷新 Cookie"""
        if not self.auto_refresh_callback:
            logger.error("未设置刷新回调")
            return False

        await self._refresh_cookies()
        return self._cookies is not None


async def demo():
    """演示 Cookie 管理器的使用"""
    import httpx

    # 模拟登录检测函数
    async def check_login(cookies: dict) -> bool:
        """检测登录状态"""
        try:
            async with httpx.AsyncClient(cookies=cookies) as client:
                resp = await client.get("https://httpbin.org/cookies", timeout=10)
                data = resp.json()
                # 检查是否有我们设置的 cookie
                return "session" in data.get("cookies", {})
        except Exception as e:
            logger.error(f"检测失败: {e}")
            return False

    # 创建管理器
    manager = CookieManager(
        storage_path="data/demo_cookies.json",
        login_checker=check_login
    )

    # 手动设置一些测试 Cookie
    test_cookies = [
        {"name": "session", "value": "test123", "domain": "httpbin.org", "path": "/"},
        {"name": "user", "value": "demo", "domain": "httpbin.org", "path": "/"}
    ]
    manager.update(test_cookies)
    await manager.save()

    # 获取有效的 Cookie
    cookies = await manager.get_valid_cookies()
    if cookies:
        print(f"获取到 Cookie: {cookies}")

    # 演示 Cookie 轮换器
    print("\n--- Cookie 轮换器演示 ---")
    rotator = CookieRotator(min_interval=2.0)

    # 添加多个账号
    rotator.add_account("account_1", {"session": "sess_1", "token": "tok_1"})
    rotator.add_account("account_2", {"session": "sess_2", "token": "tok_2"})
    rotator.add_account("account_3", {"session": "sess_3", "token": "tok_3"})

    # 模拟获取 Cookie（负载均衡）
    for i in range(5):
        cookies = await rotator.get_cookies()
        print(f"请求 {i+1}: 使用 Cookie = {cookies}")
        await asyncio.sleep(0.5)

    # 查看统计
    print(f"\n统计信息: {rotator.get_stats()}")


if __name__ == "__main__":
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="DEBUG"
    )

    asyncio.run(demo())
