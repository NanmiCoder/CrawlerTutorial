# -*- coding: utf-8 -*-
# @Desc: 短信验证码登录实现

import asyncio
from typing import Optional, Callable, Awaitable
from playwright.async_api import async_playwright, Page, BrowserContext, Playwright
from loguru import logger


class SMSLogin:
    """短信验证码登录"""

    def __init__(
        self,
        login_url: str,
        phone_input_selector: str,
        send_code_btn_selector: str,
        code_input_selector: str,
        submit_btn_selector: str,
        success_url_pattern: str,
        timeout: int = 60
    ):
        """
        Args:
            login_url: 登录页 URL
            phone_input_selector: 手机号输入框选择器
            send_code_btn_selector: 发送验证码按钮选择器
            code_input_selector: 验证码输入框选择器
            submit_btn_selector: 登录按钮选择器
            success_url_pattern: 登录成功 URL 特征
            timeout: 超时时间（秒）
        """
        self.login_url = login_url
        self.phone_input_selector = phone_input_selector
        self.send_code_btn_selector = send_code_btn_selector
        self.code_input_selector = code_input_selector
        self.submit_btn_selector = submit_btn_selector
        self.success_url_pattern = success_url_pattern
        self.timeout = timeout

        self._playwright: Optional[Playwright] = None
        self._browser = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def start(self, playwright: Playwright, headless: bool = False):
        """启动浏览器"""
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

    async def input_phone(self, phone: str):
        """输入手机号"""
        await self._page.wait_for_selector(self.phone_input_selector)
        await self._page.fill(self.phone_input_selector, phone)
        # 隐藏中间四位
        masked_phone = f"{phone[:3]}****{phone[-4:]}"
        logger.info(f"已输入手机号: {masked_phone}")

    async def send_verification_code(self) -> bool:
        """
        发送验证码

        Returns:
            是否发送成功
        """
        try:
            await self._page.wait_for_selector(self.send_code_btn_selector)
            await self._page.click(self.send_code_btn_selector)
            logger.info("验证码发送请求已提交")
            # 等待一小段时间确保请求发出
            await asyncio.sleep(1)
            return True
        except Exception as e:
            logger.error(f"发送验证码失败: {e}")
            return False

    async def input_code(self, code: str):
        """输入验证码"""
        await self._page.wait_for_selector(self.code_input_selector)
        await self._page.fill(self.code_input_selector, code)
        logger.info(f"已输入验证码: {code}")

    async def submit_login(self) -> bool:
        """
        提交登录

        Returns:
            是否登录成功
        """
        try:
            await self._page.click(self.submit_btn_selector)

            # 等待登录成功（URL 变化）
            await self._page.wait_for_url(
                f"**{self.success_url_pattern}**",
                timeout=self.timeout * 1000
            )
            logger.info("登录成功！")
            return True

        except Exception as e:
            logger.error(f"登录失败: {e}")
            return False

    async def get_cookies(self) -> list:
        """获取 Cookie"""
        if self._context:
            return await self._context.cookies()
        return []

    async def login_with_manual_code(
        self,
        phone: str,
        get_code_callback: Callable[[], Awaitable[str]]
    ) -> Optional[list]:
        """
        使用手动输入验证码的方式登录

        Args:
            phone: 手机号
            get_code_callback: 获取验证码的异步回调

        Returns:
            成功返回 Cookie，失败返回 None
        """
        await self.navigate_to_login()
        await self.input_phone(phone)

        if not await self.send_verification_code():
            return None

        # 获取验证码
        logger.info("等待获取验证码...")
        code = await get_code_callback()

        await self.input_code(code)

        if await self.submit_login():
            return await self.get_cookies()

        return None

    async def login_with_code(
        self,
        phone: str,
        code: str
    ) -> Optional[list]:
        """
        使用指定的验证码登录

        Args:
            phone: 手机号
            code: 验证码

        Returns:
            成功返回 Cookie，失败返回 None
        """
        await self.navigate_to_login()
        await self.input_phone(phone)

        if not await self.send_verification_code():
            return None

        await self.input_code(code)

        if await self.submit_login():
            return await self.get_cookies()

        return None


async def get_code_from_user() -> str:
    """从控制台获取用户输入的验证码"""
    print("\n请输入收到的验证码: ", end="", flush=True)
    loop = asyncio.get_event_loop()
    code = await loop.run_in_executor(None, input)
    return code.strip()


class SMSCodeReceiver:
    """
    短信接码平台接口基类

    注意：这是一个示意接口，实际使用需要接入具体的接码平台 API
    """

    def __init__(self, api_key: str, api_url: str):
        """
        Args:
            api_key: API 密钥
            api_url: API 地址
        """
        self.api_key = api_key
        self.api_url = api_url

    async def get_phone_number(self) -> Optional[str]:
        """
        获取手机号

        Returns:
            手机号或 None
        """
        # 实际实现时调用接码平台 API
        raise NotImplementedError("需要实现具体的接码平台接口")

    async def wait_for_code(
        self,
        phone: str,
        timeout: int = 60,
        poll_interval: float = 2.0
    ) -> Optional[str]:
        """
        等待接收验证码

        Args:
            phone: 手机号
            timeout: 超时时间（秒）
            poll_interval: 轮询间隔（秒）

        Returns:
            验证码或 None
        """
        # 实际实现时轮询接码平台获取验证码
        raise NotImplementedError("需要实现具体的接码平台接口")

    async def release_phone(self, phone: str):
        """
        释放手机号

        Args:
            phone: 手机号
        """
        # 实际实现时调用接码平台释放手机号
        raise NotImplementedError("需要实现具体的接码平台接口")


class MockSMSCodeReceiver(SMSCodeReceiver):
    """模拟接码平台（用于测试）"""

    def __init__(self):
        super().__init__("mock_key", "mock_url")
        self._phones = ["13800138001", "13800138002", "13800138003"]
        self._used_phones = set()

    async def get_phone_number(self) -> Optional[str]:
        for phone in self._phones:
            if phone not in self._used_phones:
                self._used_phones.add(phone)
                logger.info(f"[Mock] 获取手机号: {phone}")
                return phone
        return None

    async def wait_for_code(
        self,
        phone: str,
        timeout: int = 60,
        poll_interval: float = 2.0
    ) -> Optional[str]:
        logger.info(f"[Mock] 等待验证码 (手机号: {phone})")
        await asyncio.sleep(2)  # 模拟等待
        code = "123456"  # 模拟验证码
        logger.info(f"[Mock] 收到验证码: {code}")
        return code

    async def release_phone(self, phone: str):
        self._used_phones.discard(phone)
        logger.info(f"[Mock] 释放手机号: {phone}")


async def demo_sms_login():
    """短信登录演示"""
    print("=" * 50)
    print("短信验证码登录演示")
    print("=" * 50)
    print("\n注意: 这是一个演示示例，实际使用需要替换为真实网站的配置")

    async with async_playwright() as p:
        # 使用示例网站演示
        sms_login = SMSLogin(
            login_url="https://quotes.toscrape.com/login",
            phone_input_selector="#username",
            send_code_btn_selector="input[type='submit']",  # 示例
            code_input_selector="#password",
            submit_btn_selector="input[type='submit']",
            success_url_pattern="/"
        )

        await sms_login.start(p, headless=False)

        try:
            print("\n这是一个演示，使用示例网站的登录表单")
            print("实际短信登录需要配置正确的选择器\n")

            # 演示导航到页面
            await sms_login.navigate_to_login()

            # 演示输入（使用示例网站的账号密码）
            await sms_login._page.fill("#username", "demo_user")
            await sms_login._page.fill("#password", "demo_pass")

            print("已填写表单（演示）")
            await asyncio.sleep(3)

            print("演示完成")

        finally:
            await sms_login.close()


async def demo_mock_receiver():
    """模拟接码平台演示"""
    print("\n" + "=" * 50)
    print("模拟接码平台演示")
    print("=" * 50)

    receiver = MockSMSCodeReceiver()

    # 获取手机号
    phone = await receiver.get_phone_number()
    print(f"获取到手机号: {phone}")

    # 等待验证码
    code = await receiver.wait_for_code(phone)
    print(f"收到验证码: {code}")

    # 释放手机号
    await receiver.release_phone(phone)
    print("手机号已释放")


async def main():
    """主函数"""
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    await demo_sms_login()
    await demo_mock_receiver()

    print("\n" + "=" * 50)
    print("所有演示完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
