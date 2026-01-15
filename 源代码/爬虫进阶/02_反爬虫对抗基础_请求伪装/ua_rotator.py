# -*- coding: utf-8 -*-
# @Desc: User-Agent 轮换器实现

import random
from typing import List, Optional

# 尝试导入 fake_useragent
try:
    from fake_useragent import UserAgent
    FAKE_UA_AVAILABLE = True
except ImportError:
    FAKE_UA_AVAILABLE = False


# 预定义的 User-Agent 列表（2025年主流浏览器版本）
DESKTOP_USER_AGENTS = [
    # Chrome - Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    # Chrome - Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    # Firefox - Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    # Firefox - Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
    # Safari - Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
    # Edge - Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
]

MOBILE_USER_AGENTS = [
    # iPhone - Safari
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
    # iPhone - Chrome
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/131.0.6778.103 Mobile/15E148 Safari/604.1",
    # Android - Chrome
    "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.104 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.104 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.104 Mobile Safari/537.36",
]


class UARotator:
    """
    User-Agent 轮换器

    支持：
    - 随机获取桌面端/移动端 UA
    - 自定义 UA 列表
    - 集成 fake-useragent 库（可选）
    """

    def __init__(
        self,
        use_fake_ua: bool = False,
        custom_uas: Optional[List[str]] = None
    ):
        """
        初始化 UA 轮换器

        Args:
            use_fake_ua: 是否使用 fake-useragent 库
            custom_uas: 自定义 UA 列表（优先级最高）
        """
        self.custom_uas = custom_uas or []
        self.use_fake_ua = use_fake_ua and FAKE_UA_AVAILABLE
        self._fake_ua = None

        if self.use_fake_ua:
            try:
                self._fake_ua = UserAgent()
            except Exception as e:
                print(f"Warning: fake-useragent 初始化失败: {e}")
                self.use_fake_ua = False

    def get_random(self) -> str:
        """
        获取随机 User-Agent（桌面端）

        Returns:
            随机的 User-Agent 字符串
        """
        # 优先使用自定义列表
        if self.custom_uas:
            return random.choice(self.custom_uas)

        # 使用 fake-useragent
        if self.use_fake_ua and self._fake_ua:
            try:
                return self._fake_ua.random
            except Exception:
                pass

        # 使用预定义列表
        return random.choice(DESKTOP_USER_AGENTS)

    def get_chrome(self) -> str:
        """获取 Chrome User-Agent"""
        if self.use_fake_ua and self._fake_ua:
            try:
                return self._fake_ua.chrome
            except Exception:
                pass

        # 从预定义列表中筛选 Chrome UA
        chrome_uas = [ua for ua in DESKTOP_USER_AGENTS if "Chrome" in ua and "Edg" not in ua]
        return random.choice(chrome_uas) if chrome_uas else self.get_random()

    def get_firefox(self) -> str:
        """获取 Firefox User-Agent"""
        if self.use_fake_ua and self._fake_ua:
            try:
                return self._fake_ua.firefox
            except Exception:
                pass

        firefox_uas = [ua for ua in DESKTOP_USER_AGENTS if "Firefox" in ua]
        return random.choice(firefox_uas) if firefox_uas else self.get_random()

    def get_safari(self) -> str:
        """获取 Safari User-Agent"""
        if self.use_fake_ua and self._fake_ua:
            try:
                return self._fake_ua.safari
            except Exception:
                pass

        safari_uas = [ua for ua in DESKTOP_USER_AGENTS if "Safari" in ua and "Chrome" not in ua]
        return random.choice(safari_uas) if safari_uas else self.get_random()

    def get_mobile(self) -> str:
        """获取移动端 User-Agent"""
        return random.choice(MOBILE_USER_AGENTS)

    def get_ios(self) -> str:
        """获取 iOS User-Agent"""
        ios_uas = [ua for ua in MOBILE_USER_AGENTS if "iPhone" in ua]
        return random.choice(ios_uas) if ios_uas else self.get_mobile()

    def get_android(self) -> str:
        """获取 Android User-Agent"""
        android_uas = [ua for ua in MOBILE_USER_AGENTS if "Android" in ua]
        return random.choice(android_uas) if android_uas else self.get_mobile()


def demo():
    """演示 UA 轮换器的使用"""
    print("=" * 60)
    print("User-Agent 轮换器演示")
    print("=" * 60)

    rotator = UARotator()

    print("\n1. 随机桌面端 UA:")
    for i in range(3):
        print(f"   {i+1}. {rotator.get_random()[:80]}...")

    print("\n2. Chrome UA:")
    print(f"   {rotator.get_chrome()[:80]}...")

    print("\n3. Firefox UA:")
    print(f"   {rotator.get_firefox()[:80]}...")

    print("\n4. 移动端 UA:")
    print(f"   iOS: {rotator.get_ios()[:60]}...")
    print(f"   Android: {rotator.get_android()[:60]}...")

    # 测试 fake-useragent（如果可用）
    if FAKE_UA_AVAILABLE:
        print("\n5. 使用 fake-useragent:")
        rotator_fake = UARotator(use_fake_ua=True)
        for i in range(3):
            print(f"   {i+1}. {rotator_fake.get_random()[:80]}...")


if __name__ == "__main__":
    demo()
