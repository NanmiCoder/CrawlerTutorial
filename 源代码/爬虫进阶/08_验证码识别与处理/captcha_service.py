# -*- coding: utf-8 -*-
# @Desc: 验证码服务 - 整合本地识别和第三方打码平台

import asyncio
import base64
from abc import ABC, abstractmethod
from typing import Optional, Callable, Awaitable
from datetime import date
from loguru import logger

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class CaptchaServiceBase(ABC):
    """验证码服务基类"""

    @abstractmethod
    async def solve_image(self, image_bytes: bytes) -> Optional[str]:
        """识别图片验证码"""
        pass


class LocalOCRService(CaptchaServiceBase):
    """本地 OCR 服务"""

    def __init__(self, preprocess: bool = True):
        from ocr_captcha import OCRCaptchaSolver
        self.solver = OCRCaptchaSolver(preprocess=preprocess)

    async def solve_image(self, image_bytes: bytes) -> Optional[str]:
        """使用本地 OCR 识别"""
        return self.solver.solve(image_bytes)


class RemoteCaptchaService(CaptchaServiceBase):
    """
    远程打码平台服务（示例实现）

    注意：这是一个通用的示例接口，实际使用需要根据具体平台 API 调整
    """

    def __init__(
        self,
        api_key: str,
        api_url: str,
        timeout: int = 30
    ):
        """
        Args:
            api_key: API 密钥
            api_url: API 地址
            timeout: 超时时间（秒）
        """
        if not HAS_HTTPX:
            raise ImportError("需要安装 httpx: pip install httpx")

        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout
        self._last_task_id: Optional[str] = None

    async def solve_image(
        self,
        image_bytes: bytes,
        captcha_type: str = "default"
    ) -> Optional[str]:
        """
        识别图片验证码

        Args:
            image_bytes: 图片字节
            captcha_type: 验证码类型

        Returns:
            识别结果
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 编码图片
                image_base64 = base64.b64encode(image_bytes).decode()

                # 提交任务
                resp = await client.post(
                    f"{self.api_url}/create_task",
                    json={
                        "api_key": self.api_key,
                        "image": image_base64,
                        "type": captcha_type
                    }
                )

                data = resp.json()
                task_id = data.get("task_id")

                if not task_id:
                    logger.error(f"创建任务失败: {data}")
                    return None

                self._last_task_id = task_id
                logger.debug(f"任务已创建: {task_id}")

                # 轮询获取结果
                return await self._poll_result(client, task_id)

        except Exception as e:
            logger.error(f"打码平台请求失败: {e}")
            return None

    async def _poll_result(
        self,
        client: httpx.AsyncClient,
        task_id: str,
        max_attempts: int = 30
    ) -> Optional[str]:
        """轮询获取结果"""
        for attempt in range(max_attempts):
            try:
                resp = await client.get(
                    f"{self.api_url}/get_result",
                    params={"task_id": task_id}
                )

                data = resp.json()
                status = data.get("status")

                if status == "ready":
                    result = data.get("result")
                    logger.debug(f"识别成功: {result}")
                    return result
                elif status == "error":
                    logger.error(f"识别错误: {data.get('error')}")
                    return None

                await asyncio.sleep(1)

            except Exception as e:
                logger.warning(f"轮询异常: {e}")
                await asyncio.sleep(1)

        logger.error("识别超时")
        return None

    async def report_error(self, task_id: str = None):
        """
        报告识别错误（用于退款）

        Args:
            task_id: 任务 ID，不提供则使用最后一个任务
        """
        task_id = task_id or self._last_task_id
        if not task_id:
            logger.warning("没有可报告的任务")
            return

        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.api_url}/report_error",
                    json={
                        "api_key": self.api_key,
                        "task_id": task_id
                    }
                )
                logger.info(f"已报告错误: {task_id}")
        except Exception as e:
            logger.warning(f"报告错误失败: {e}")

    async def get_balance(self) -> float:
        """获取账户余额"""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.api_url}/balance",
                    params={"api_key": self.api_key}
                )
                data = resp.json()
                return data.get("balance", 0.0)
        except Exception as e:
            logger.error(f"获取余额失败: {e}")
            return 0.0


class CostController:
    """打码成本控制器"""

    def __init__(
        self,
        daily_budget: float,
        cost_per_captcha: float = 0.01
    ):
        """
        Args:
            daily_budget: 每日预算
            cost_per_captcha: 每次识别成本
        """
        self.daily_budget = daily_budget
        self.cost_per_captcha = cost_per_captcha
        self._daily_spent = 0.0
        self._last_reset: Optional[date] = None
        self._usage_count = 0

    def can_use_service(self) -> bool:
        """是否可以使用打码服务"""
        self._check_reset()
        return self._daily_spent < self.daily_budget

    def record_usage(self):
        """记录一次使用"""
        self._check_reset()
        self._daily_spent += self.cost_per_captcha
        self._usage_count += 1
        logger.debug(f"记录使用: 已花费 {self._daily_spent:.2f}")

    def _check_reset(self):
        """检查是否需要重置（跨天）"""
        today = date.today()
        if self._last_reset != today:
            self._daily_spent = 0.0
            self._usage_count = 0
            self._last_reset = today
            logger.info("成本计数器已重置")

    @property
    def remaining_budget(self) -> float:
        """剩余预算"""
        self._check_reset()
        return max(0, self.daily_budget - self._daily_spent)

    @property
    def today_usage(self) -> int:
        """今日使用次数"""
        self._check_reset()
        return self._usage_count

    def get_stats(self) -> dict:
        """获取统计信息"""
        self._check_reset()
        return {
            "daily_budget": self.daily_budget,
            "daily_spent": self._daily_spent,
            "remaining": self.remaining_budget,
            "usage_count": self._usage_count,
            "cost_per_captcha": self.cost_per_captcha
        }


class CaptchaSolverWithFallback:
    """带降级策略的验证码解决器"""

    def __init__(
        self,
        local_service: CaptchaServiceBase = None,
        remote_service: CaptchaServiceBase = None,
        cost_controller: CostController = None
    ):
        """
        Args:
            local_service: 本地识别服务
            remote_service: 远程打码服务
            cost_controller: 成本控制器
        """
        self.local_service = local_service
        self.remote_service = remote_service
        self.cost_controller = cost_controller

    async def solve(
        self,
        image_bytes: bytes,
        verify_callback: Callable[[str], Awaitable[bool]] = None,
        prefer_local: bool = True,
        max_local_retries: int = 2
    ) -> Optional[str]:
        """
        解决验证码

        Args:
            image_bytes: 验证码图片
            verify_callback: 验证回调（可选）
            prefer_local: 是否优先使用本地识别
            max_local_retries: 本地识别最大重试次数

        Returns:
            识别结果
        """
        # 优先本地识别
        if prefer_local and self.local_service:
            for attempt in range(max_local_retries):
                result = await self.local_service.solve_image(image_bytes)

                if result:
                    # 如果有验证回调
                    if verify_callback:
                        if await verify_callback(result):
                            logger.info(f"本地识别成功 (尝试 {attempt + 1})")
                            return result
                    else:
                        return result

                logger.debug(f"本地识别失败，重试 {attempt + 1}/{max_local_retries}")

        # 降级到远程服务
        if self.remote_service:
            # 检查成本
            if self.cost_controller and not self.cost_controller.can_use_service():
                logger.warning("超出每日预算，无法使用打码服务")
                return None

            result = await self.remote_service.solve_image(image_bytes)

            if result:
                if self.cost_controller:
                    self.cost_controller.record_usage()
                logger.info("远程识别成功")
                return result

        logger.error("验证码识别失败")
        return None


async def demo():
    """验证码服务演示"""
    print("=" * 50)
    print("验证码服务演示")
    print("=" * 50)

    # 1. 本地 OCR 服务
    print("\n1. 本地 OCR 服务:")
    try:
        local_service = LocalOCRService(preprocess=True)
        print("   本地 OCR 服务已创建")
        print("   用法: result = await local_service.solve_image(image_bytes)")
    except ImportError as e:
        print(f"   创建失败: {e}")

    # 2. 成本控制器
    print("\n2. 成本控制器演示:")
    controller = CostController(
        daily_budget=10.0,
        cost_per_captcha=0.01
    )
    print(f"   每日预算: {controller.daily_budget}")
    print(f"   每次成本: {controller.cost_per_captcha}")
    print(f"   可以使用: {controller.can_use_service()}")

    # 模拟使用
    for i in range(5):
        if controller.can_use_service():
            controller.record_usage()

    stats = controller.get_stats()
    print(f"   使用后统计: {stats}")

    # 3. 带降级的解决器
    print("\n3. 带降级策略的解决器:")
    print("""
    solver = CaptchaSolverWithFallback(
        local_service=local_service,
        remote_service=remote_service,
        cost_controller=cost_controller
    )

    result = await solver.solve(
        image_bytes,
        verify_callback=verify_func,  # 可选
        prefer_local=True,
        max_local_retries=2
    )
    """)

    # 4. 远程服务示例
    print("\n4. 远程打码服务（示例配置）:")
    print("""
    remote_service = RemoteCaptchaService(
        api_key="your_api_key",
        api_url="https://api.captcha-service.com",
        timeout=30
    )

    # 识别验证码
    result = await remote_service.solve_image(image_bytes)

    # 报告错误（退款）
    if not is_correct:
        await remote_service.report_error()

    # 查询余额
    balance = await remote_service.get_balance()
    """)

    print("\n" + "=" * 50)
    print("演示完成")
    print("=" * 50)


if __name__ == "__main__":
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="DEBUG"
    )

    asyncio.run(demo())
