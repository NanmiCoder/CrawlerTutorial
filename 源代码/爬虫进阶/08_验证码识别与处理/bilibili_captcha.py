# -*- coding: utf-8 -*-
"""
B站验证码处理实战

本模块展示B站验证码的触发场景和处理策略，包括：
- B站滑块验证码检测与处理
- 人类轨迹模拟
- 频率控制避免触发验证码
- 验证码预防策略

这是第08章"验证码识别与处理"的B站实战示例。

与第11章综合实战项目的关联：
- tools/captcha.py: 验证码处理模块
- client/bilibili_client.py: 请求频率控制
"""

import asyncio
import random
import math
from typing import Optional, List, Tuple
from dataclasses import dataclass

from loguru import logger

# 可选依赖
try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    logger.warning("未安装 opencv-python，滑块缺口检测功能不可用")

try:
    from playwright.async_api import Page, FrameLocator
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    logger.warning("未安装 playwright，浏览器验证码处理功能不可用")


# ============== B站验证码触发场景 ==============

"""
B站验证码触发场景说明：

| 场景 | 验证码类型 | 触发条件 | 处理难度 |
|-----|-----------|---------|---------|
| 登录保护 | 滑块验证码 | 异地登录、频繁登录 | 中等 |
| 接口防护 | 极验验证码 | 请求频率过高 | 较难 |
| 评论/弹幕 | 点选验证码 | 短时间大量发送 | 困难 |
| 关注/收藏 | 简单确认 | 批量操作 | 简单 |

预防策略：
1. 控制请求频率（每分钟<30请求）
2. 使用随机延迟（2-5秒）
3. 保持登录态（Cookie有效）
4. IP轮换（高匿代理池）
"""


# ============== 频率控制器 ==============

class BilibiliRateLimiter:
    """
    B站请求频率控制器

    通过控制请求频率来避免触发验证码，这是预防验证码的核心策略。

    建议配置：
    - requests_per_minute: 20 (安全值)
    - min_delay: 2.0 秒
    - max_delay: 5.0 秒
    """

    def __init__(
        self,
        requests_per_minute: int = 20,
        min_delay: float = 2.0,
        max_delay: float = 5.0
    ):
        """
        初始化频率控制器

        Args:
            requests_per_minute: 每分钟最大请求数
            min_delay: 最小请求间隔（秒）
            max_delay: 最大请求间隔（秒）
        """
        self.requests_per_minute = requests_per_minute
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._last_request_time: Optional[float] = None
        self._request_count = 0
        self._minute_start: Optional[float] = None

    async def wait(self):
        """等待直到可以发送下一个请求"""
        now = asyncio.get_event_loop().time()

        # 重置分钟计数
        if self._minute_start is None or now - self._minute_start > 60:
            self._minute_start = now
            self._request_count = 0

        # 检查是否超过频率限制
        if self._request_count >= self.requests_per_minute:
            wait_time = 60 - (now - self._minute_start)
            if wait_time > 0:
                logger.debug(f"达到频率限制，等待 {wait_time:.1f} 秒")
                await asyncio.sleep(wait_time)
            self._minute_start = asyncio.get_event_loop().time()
            self._request_count = 0

        # 随机延迟
        if self._last_request_time:
            elapsed = now - self._last_request_time
            if elapsed < self.min_delay:
                delay = random.uniform(self.min_delay, self.max_delay)
                actual_delay = delay - elapsed
                if actual_delay > 0:
                    logger.debug(f"随机延迟 {actual_delay:.2f} 秒")
                    await asyncio.sleep(actual_delay)

        self._last_request_time = asyncio.get_event_loop().time()
        self._request_count += 1

    @property
    def remaining_requests(self) -> int:
        """本分钟剩余可用请求数"""
        return max(0, self.requests_per_minute - self._request_count)


# ============== 人类轨迹生成器 ==============

class HumanTrajectoryGenerator:
    """
    人类轨迹生成器

    生成模拟人类拖拽行为的轨迹点，用于滑块验证码。
    包含多种轨迹生成算法。
    """

    @staticmethod
    def generate_trajectory(
        distance: int,
        duration: float = 0.5
    ) -> List[Tuple[int, int, float]]:
        """
        生成基础人类轨迹（缓动函数）

        Args:
            distance: 需要移动的距离
            duration: 预期持续时间（秒）

        Returns:
            轨迹点列表 [(x, y, time), ...]
        """
        trajectory = []
        current_x = 0
        current_time = 0

        steps = random.randint(20, 30)
        step_time = duration / steps

        for i in range(steps):
            progress = i / steps
            # 使用 ease-out 缓动
            eased = progress * (2 - progress)

            target_x = int(distance * eased)

            # 添加随机偏移
            offset_y = random.randint(-3, 3)

            current_x = target_x
            current_time += step_time + random.uniform(-0.01, 0.01)

            trajectory.append((current_x, offset_y, current_time))

        # 确保最后到达目标
        trajectory.append((distance, 0, duration))

        return trajectory

    @staticmethod
    def generate_bezier_trajectory(
        distance: int,
        duration: float = 0.5
    ) -> List[Tuple[int, int, float]]:
        """
        使用贝塞尔曲线生成更自然的轨迹

        Args:
            distance: 移动距离
            duration: 持续时间

        Returns:
            轨迹点列表
        """
        trajectory = []

        # 控制点（随机偏移使轨迹更自然）
        p0 = (0, 0)
        p1 = (distance * 0.3, random.randint(-10, 10))
        p2 = (distance * 0.7, random.randint(-5, 5))
        p3 = (distance, 0)

        steps = random.randint(25, 35)

        for i in range(steps + 1):
            t = i / steps

            # 三阶贝塞尔曲线
            x = ((1-t)**3 * p0[0] +
                 3*(1-t)**2*t * p1[0] +
                 3*(1-t)*t**2 * p2[0] +
                 t**3 * p3[0])

            y = ((1-t)**3 * p0[1] +
                 3*(1-t)**2*t * p1[1] +
                 3*(1-t)*t**2 * p2[1] +
                 t**3 * p3[1])

            time_point = duration * t + random.uniform(-0.005, 0.005)
            trajectory.append((int(x), int(y), max(0, time_point)))

        return trajectory

    @staticmethod
    def generate_physics_trajectory(
        distance: int,
        duration: float = 0.8
    ) -> List[Tuple[int, int, float]]:
        """
        基于物理模型的轨迹（加速-匀速-减速）

        Args:
            distance: 移动距离
            duration: 持续时间

        Returns:
            轨迹点列表
        """
        trajectory = []

        # 三阶段：加速(30%) - 匀速(40%) - 减速(30%)
        acc_phase = 0.3
        const_phase = 0.4
        dec_phase = 0.3

        steps = random.randint(30, 40)

        for i in range(steps + 1):
            t = i / steps
            time_point = duration * t

            if t < acc_phase:
                # 加速阶段（二次加速）
                phase_t = t / acc_phase
                x = distance * 0.15 * (phase_t ** 2)
            elif t < acc_phase + const_phase:
                # 匀速阶段
                phase_t = (t - acc_phase) / const_phase
                x = distance * 0.15 + distance * 0.5 * phase_t
            else:
                # 减速阶段（二次减速）
                phase_t = (t - acc_phase - const_phase) / dec_phase
                x = distance * 0.65 + distance * 0.35 * (1 - (1 - phase_t) ** 2)

            # 添加随机Y偏移
            y = random.randint(-2, 2)

            trajectory.append((int(x), y, time_point + random.uniform(-0.005, 0.005)))

        return trajectory


# ============== 滑块缺口检测器 ==============

class SliderGapDetector:
    """
    滑块缺口位置检测器

    使用图像处理技术检测滑块验证码的缺口位置
    """

    @staticmethod
    def detect_gap_by_edge(
        background_bytes: bytes,
        slider_bytes: bytes
    ) -> Optional[int]:
        """
        通过边缘检测找缺口位置

        Args:
            background_bytes: 背景图片字节
            slider_bytes: 滑块图片字节

        Returns:
            缺口 x 坐标，检测失败返回 None
        """
        if not HAS_CV2:
            logger.error("需要安装 opencv-python: pip install opencv-python")
            return None

        try:
            # 读取图片
            bg = cv2.imdecode(
                np.frombuffer(background_bytes, np.uint8),
                cv2.IMREAD_COLOR
            )
            slider = cv2.imdecode(
                np.frombuffer(slider_bytes, np.uint8),
                cv2.IMREAD_COLOR
            )

            # 转灰度
            bg_gray = cv2.cvtColor(bg, cv2.COLOR_BGR2GRAY)
            slider_gray = cv2.cvtColor(slider, cv2.COLOR_BGR2GRAY)

            # 边缘检测
            bg_edges = cv2.Canny(bg_gray, 100, 200)
            slider_edges = cv2.Canny(slider_gray, 100, 200)

            # 模板匹配
            result = cv2.matchTemplate(bg_edges, slider_edges, cv2.TM_CCOEFF_NORMED)
            _, _, _, max_loc = cv2.minMaxLoc(result)

            gap_x = max_loc[0]
            logger.debug(f"检测到缺口位置: x={gap_x}")
            return gap_x

        except Exception as e:
            logger.error(f"缺口检测失败: {e}")
            return None

    @staticmethod
    def detect_gap_by_contrast(
        background_bytes: bytes,
        threshold: int = 60
    ) -> Optional[int]:
        """
        通过对比度差异检测缺口

        Args:
            background_bytes: 背景图片
            threshold: 对比度阈值

        Returns:
            缺口 x 坐标
        """
        if not HAS_CV2:
            return None

        try:
            bg = cv2.imdecode(
                np.frombuffer(background_bytes, np.uint8),
                cv2.IMREAD_COLOR
            )

            # 转灰度并计算梯度
            gray = cv2.cvtColor(bg, cv2.COLOR_BGR2GRAY)
            sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sobel_abs = np.abs(sobel_x)

            # 找到梯度突变最大的列
            col_sum = np.sum(sobel_abs, axis=0)

            # 在合理范围内查找（排除边缘）
            start = int(len(col_sum) * 0.2)
            end = int(len(col_sum) * 0.8)

            gap_x = start + np.argmax(col_sum[start:end])
            return int(gap_x)

        except Exception as e:
            logger.error(f"对比度检测失败: {e}")
            return None


# ============== B站滑块验证码处理器 ==============

if HAS_PLAYWRIGHT:
    class BilibiliSliderCaptcha:
        """
        B站滑块验证码处理器

        检测并自动处理B站的滑块验证码
        """

        def __init__(self, page: Page):
            """
            初始化处理器

            Args:
                page: Playwright Page 对象
            """
            self.page = page
            self.gap_detector = SliderGapDetector()
            self.trajectory_gen = HumanTrajectoryGenerator()

        async def detect_and_solve(self) -> bool:
            """
            检测并解决滑块验证码

            Returns:
                是否成功解决
            """
            try:
                # 检测是否出现滑块验证码
                slider_frame = self.page.frame_locator("iframe[src*='captcha']")

                # 等待滑块出现（最多5秒）
                try:
                    await slider_frame.locator(".geetest_slider_button").wait_for(
                        timeout=5000
                    )
                except Exception:
                    # 没有验证码，正常情况
                    logger.debug("未检测到滑块验证码")
                    return True

                logger.info("检测到B站滑块验证码")

                # 获取滑块和背景图
                bg_element = slider_frame.locator(".geetest_canvas_bg")
                slider_element = slider_frame.locator(".geetest_canvas_slice")

                bg_bytes = await bg_element.screenshot()
                slider_bytes = await slider_element.screenshot()

                # 检测缺口位置
                gap_x = self.gap_detector.detect_gap_by_edge(bg_bytes, slider_bytes)

                if not gap_x:
                    # 尝试备用方法
                    gap_x = self.gap_detector.detect_gap_by_contrast(bg_bytes)

                if not gap_x:
                    logger.error("无法检测缺口位置")
                    return False

                logger.info(f"缺口位置: {gap_x}px")

                # 执行拖拽
                await self._drag_slider(slider_frame, gap_x)

                # 等待验证结果
                await asyncio.sleep(2)

                # 检查是否成功
                try:
                    await slider_frame.locator(".geetest_success").wait_for(
                        timeout=3000
                    )
                    logger.info("B站滑块验证码通过")
                    return True
                except Exception:
                    logger.warning("B站滑块验证码验证失败")
                    return False

            except Exception as e:
                logger.error(f"B站滑块验证码处理异常: {e}")
                return False

        async def _drag_slider(self, frame: FrameLocator, distance: int):
            """
            执行拖拽操作

            Args:
                frame: 验证码iframe
                distance: 拖拽距离
            """
            slider_btn = frame.locator(".geetest_slider_button")
            box = await slider_btn.bounding_box()

            if not box:
                raise Exception("无法获取滑块位置")

            start_x = box['x'] + box['width'] / 2
            start_y = box['y'] + box['height'] / 2

            # 生成人类轨迹（随机选择算法）
            trajectory_method = random.choice([
                self.trajectory_gen.generate_bezier_trajectory,
                self.trajectory_gen.generate_physics_trajectory
            ])
            trajectory = trajectory_method(distance)

            # 移动到滑块位置
            await self.page.mouse.move(start_x, start_y)
            await asyncio.sleep(random.uniform(0.1, 0.2))

            # 按下鼠标
            await self.page.mouse.down()
            await asyncio.sleep(random.uniform(0.05, 0.1))

            # 沿轨迹移动
            last_time = 0
            for x, y, time_point in trajectory:
                delay = time_point - last_time
                if delay > 0:
                    await asyncio.sleep(delay)
                last_time = time_point

                await self.page.mouse.move(start_x + x, start_y + y)

            # 松开鼠标
            await asyncio.sleep(random.uniform(0.05, 0.1))
            await self.page.mouse.up()

            logger.info(f"滑块拖拽完成，距离: {distance}px")


# ============== 演示入口 ==============

async def demo_rate_limiter():
    """演示频率控制器"""
    logger.info("=" * 50)
    logger.info("B站频率控制器演示")
    logger.info("=" * 50)

    limiter = BilibiliRateLimiter(
        requests_per_minute=20,
        min_delay=2.0,
        max_delay=5.0
    )

    logger.info("模拟发送10个请求...")

    for i in range(10):
        await limiter.wait()
        logger.info(f"请求 {i+1} 发送，剩余可用: {limiter.remaining_requests}")

    logger.info("频率控制演示完成")


async def demo_trajectory_generator():
    """演示轨迹生成"""
    logger.info("=" * 50)
    logger.info("人类轨迹生成器演示")
    logger.info("=" * 50)

    generator = HumanTrajectoryGenerator()
    distance = 200

    # 基础轨迹
    traj1 = generator.generate_trajectory(distance)
    logger.info(f"基础轨迹: {len(traj1)} 个点")

    # 贝塞尔轨迹
    traj2 = generator.generate_bezier_trajectory(distance)
    logger.info(f"贝塞尔轨迹: {len(traj2)} 个点")

    # 物理轨迹
    traj3 = generator.generate_physics_trajectory(distance)
    logger.info(f"物理轨迹: {len(traj3)} 个点")

    # 展示轨迹示例
    logger.info("\n贝塞尔轨迹前5个点:")
    for i, (x, y, t) in enumerate(traj2[:5]):
        logger.info(f"  {i+1}. x={x}, y={y}, t={t:.3f}s")


async def demo_captcha_prevention():
    """演示验证码预防策略"""
    logger.info("=" * 50)
    logger.info("B站验证码预防策略")
    logger.info("=" * 50)

    logger.info("""
B站验证码预防建议：

1. 请求频率控制
   - 每分钟请求数 < 30
   - 建议使用 BilibiliRateLimiter

2. 随机延迟
   - 最小延迟: 2秒
   - 最大延迟: 5秒
   - 使用正态分布随机

3. 登录态保持
   - 使用有效Cookie
   - 定期验证Cookie有效性

4. IP策略
   - 使用高匿代理
   - 实现代理轮换

5. 行为模拟
   - 添加随机鼠标移动
   - 页面滚动
   - 适当停留时间
    """)


async def main():
    """主演示函数"""
    logger.info("\n" + "=" * 60)
    logger.info("B站验证码处理实战示例")
    logger.info("=" * 60)

    # 1. 频率控制演示
    await demo_rate_limiter()

    print("\n")

    # 2. 轨迹生成演示
    await demo_trajectory_generator()

    print("\n")

    # 3. 预防策略说明
    await demo_captcha_prevention()


if __name__ == "__main__":
    asyncio.run(main())
