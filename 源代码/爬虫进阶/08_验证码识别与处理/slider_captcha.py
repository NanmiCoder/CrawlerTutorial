# -*- coding: utf-8 -*-
# @Desc: 滑块验证码处理

import asyncio
import random
import math
from typing import Optional, List, Tuple
from loguru import logger

# 可选依赖
try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    logger.warning("opencv-python 未安装，缺口检测不可用。安装: pip install opencv-python")


class SliderGapDetector:
    """滑块缺口位置检测器"""

    def __init__(self):
        if not HAS_CV2:
            raise ImportError("需要安装 opencv-python: pip install opencv-python")

    def detect_by_template_match(
        self,
        background_bytes: bytes,
        slider_bytes: bytes
    ) -> Optional[int]:
        """
        通过模板匹配找缺口位置

        Args:
            background_bytes: 背景图片字节
            slider_bytes: 滑块图片字节

        Returns:
            缺口 x 坐标
        """
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
        result = cv2.matchTemplate(
            bg_edges,
            slider_edges,
            cv2.TM_CCOEFF_NORMED
        )
        _, _, _, max_loc = cv2.minMaxLoc(result)

        gap_x = max_loc[0]
        logger.debug(f"模板匹配检测到缺口位置: x={gap_x}")
        return gap_x

    def detect_by_contour(
        self,
        background_bytes: bytes,
        min_area: int = 1000
    ) -> Optional[int]:
        """
        通过轮廓检测找缺口位置

        某些滑块验证码的缺口有明显的轮廓

        Args:
            background_bytes: 背景图片
            min_area: 最小轮廓面积

        Returns:
            缺口 x 坐标
        """
        bg = cv2.imdecode(
            np.frombuffer(background_bytes, np.uint8),
            cv2.IMREAD_COLOR
        )

        # 转灰度
        gray = cv2.cvtColor(bg, cv2.COLOR_BGR2GRAY)

        # 高斯模糊
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # 边缘检测
        edges = cv2.Canny(blurred, 50, 150)

        # 找轮廓
        contours, _ = cv2.findContours(
            edges,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        # 筛选合适的轮廓
        candidates = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > min_area:
                x, y, w, h = cv2.boundingRect(contour)
                # 缺口通常在图片中间偏右
                if x > bg.shape[1] * 0.2:
                    candidates.append((x, area))

        if candidates:
            # 选择面积最大的
            candidates.sort(key=lambda c: c[1], reverse=True)
            return candidates[0][0]

        return None

    def detect_by_color_diff(
        self,
        background_bytes: bytes,
        threshold: int = 50
    ) -> Optional[int]:
        """
        通过颜色差异找缺口

        缺口区域通常颜色较暗

        Args:
            background_bytes: 背景图片
            threshold: 颜色阈值

        Returns:
            缺口 x 坐标
        """
        bg = cv2.imdecode(
            np.frombuffer(background_bytes, np.uint8),
            cv2.IMREAD_COLOR
        )

        # 转灰度
        gray = cv2.cvtColor(bg, cv2.COLOR_BGR2GRAY)

        # 二值化（找暗色区域）
        _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)

        # 找轮廓
        contours, _ = cv2.findContours(
            binary,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        if contours:
            # 找最大轮廓
            largest = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest)
            return x

        return None


class HumanTrajectoryGenerator:
    """人类轨迹生成器"""

    @staticmethod
    def generate_linear(
        distance: int,
        duration: float = 0.5
    ) -> List[Tuple[int, int, float]]:
        """
        生成线性轨迹（简单但容易被检测）

        Args:
            distance: 移动距离
            duration: 持续时间

        Returns:
            轨迹点列表 [(x, y, time), ...]
        """
        trajectory = []
        steps = 20
        step_time = duration / steps

        for i in range(steps + 1):
            progress = i / steps
            x = int(distance * progress)
            y = 0
            t = step_time * i
            trajectory.append((x, y, t))

        return trajectory

    @staticmethod
    def generate_ease_out(
        distance: int,
        duration: float = 0.5
    ) -> List[Tuple[int, int, float]]:
        """
        生成缓出轨迹（先快后慢）

        Args:
            distance: 移动距离
            duration: 持续时间

        Returns:
            轨迹点列表
        """
        trajectory = []
        steps = random.randint(25, 35)
        step_time = duration / steps

        for i in range(steps + 1):
            t = i / steps
            # 二次缓出
            eased = t * (2 - t)

            x = int(distance * eased)
            y = random.randint(-2, 2)  # 小幅度 Y 抖动
            time_point = step_time * i + random.uniform(-0.005, 0.005)

            trajectory.append((x, y, max(0, time_point)))

        return trajectory

    @staticmethod
    def generate_bezier(
        distance: int,
        duration: float = 0.5
    ) -> List[Tuple[int, int, float]]:
        """
        使用贝塞尔曲线生成自然轨迹

        Args:
            distance: 移动距离
            duration: 持续时间

        Returns:
            轨迹点列表
        """
        trajectory = []

        # 控制点（随机生成更自然）
        p0 = (0, 0)
        p1 = (distance * random.uniform(0.2, 0.4), random.randint(-15, 15))
        p2 = (distance * random.uniform(0.6, 0.8), random.randint(-8, 8))
        p3 = (distance, 0)

        steps = random.randint(30, 45)

        for i in range(steps + 1):
            t = i / steps

            # 三阶贝塞尔曲线
            x = (
                (1-t)**3 * p0[0] +
                3*(1-t)**2*t * p1[0] +
                3*(1-t)*t**2 * p2[0] +
                t**3 * p3[0]
            )
            y = (
                (1-t)**3 * p0[1] +
                3*(1-t)**2*t * p1[1] +
                3*(1-t)*t**2 * p2[1] +
                t**3 * p3[1]
            )

            # 时间加随机偏移
            time_point = duration * t + random.uniform(-0.003, 0.003)
            trajectory.append((int(x), int(y), max(0, time_point)))

        return trajectory

    @staticmethod
    def generate_human_like(
        distance: int,
        duration: float = 0.5
    ) -> List[Tuple[int, int, float]]:
        """
        生成模拟人类的轨迹（综合多种特征）

        包含：加速、微调、抖动等人类特征

        Args:
            distance: 移动距离
            duration: 持续时间

        Returns:
            轨迹点列表
        """
        trajectory = []

        # 分阶段：加速 -> 匀速 -> 减速 -> 微调
        phases = [
            (0.3, 0.2),   # 加速阶段
            (0.5, 0.4),   # 匀速阶段
            (0.15, 0.3),  # 减速阶段
            (0.05, 0.1),  # 微调阶段
        ]

        current_x = 0
        current_time = 0

        for phase_distance_ratio, phase_duration_ratio in phases:
            phase_distance = distance * phase_distance_ratio
            phase_duration = duration * phase_duration_ratio
            phase_steps = random.randint(5, 10)
            step_time = phase_duration / phase_steps

            for i in range(phase_steps):
                progress = (i + 1) / phase_steps
                x = current_x + int(phase_distance * progress)
                y = random.randint(-3, 3)
                t = current_time + step_time * (i + 1) + random.uniform(-0.002, 0.002)

                trajectory.append((x, y, max(0, t)))

            current_x += int(phase_distance)
            current_time += phase_duration

        # 确保最后到达目标
        trajectory.append((distance, 0, duration))

        return trajectory


class SliderCaptchaSolver:
    """滑块验证码解决器（需要配合 Playwright 使用）"""

    def __init__(self):
        if HAS_CV2:
            self.gap_detector = SliderGapDetector()
        else:
            self.gap_detector = None

        self.trajectory_generator = HumanTrajectoryGenerator()

    def detect_gap(
        self,
        background_bytes: bytes,
        slider_bytes: bytes = None
    ) -> Optional[int]:
        """
        检测缺口位置

        Args:
            background_bytes: 背景图片
            slider_bytes: 滑块图片（可选）

        Returns:
            缺口 x 坐标
        """
        if not self.gap_detector:
            logger.error("缺口检测需要 opencv-python")
            return None

        if slider_bytes:
            return self.gap_detector.detect_by_template_match(
                background_bytes,
                slider_bytes
            )
        else:
            return self.gap_detector.detect_by_contour(background_bytes)

    def generate_trajectory(
        self,
        distance: int,
        style: str = "human"
    ) -> List[Tuple[int, int, float]]:
        """
        生成拖拽轨迹

        Args:
            distance: 拖拽距离
            style: 轨迹风格 (linear/ease_out/bezier/human)

        Returns:
            轨迹点列表
        """
        generators = {
            "linear": self.trajectory_generator.generate_linear,
            "ease_out": self.trajectory_generator.generate_ease_out,
            "bezier": self.trajectory_generator.generate_bezier,
            "human": self.trajectory_generator.generate_human_like
        }

        generator = generators.get(style, self.trajectory_generator.generate_human_like)
        return generator(distance)


async def demo():
    """滑块验证码处理演示"""
    print("=" * 50)
    print("滑块验证码处理演示")
    print("=" * 50)

    # 演示轨迹生成
    print("\n1. 轨迹生成演示:")
    generator = HumanTrajectoryGenerator()

    distance = 200  # 200像素

    styles = {
        "linear": generator.generate_linear,
        "ease_out": generator.generate_ease_out,
        "bezier": generator.generate_bezier,
        "human": generator.generate_human_like
    }

    for style_name, style_func in styles.items():
        trajectory = style_func(distance)
        print(f"\n   {style_name} 轨迹:")
        print(f"   - 点数: {len(trajectory)}")
        print(f"   - 起点: {trajectory[0]}")
        print(f"   - 终点: {trajectory[-1]}")

    # 演示缺口检测
    if HAS_CV2:
        print("\n2. 缺口检测演示:")
        print("   支持的检测方法:")
        print("   - detect_by_template_match(): 模板匹配")
        print("   - detect_by_contour(): 轮廓检测")
        print("   - detect_by_color_diff(): 颜色差异检测")
    else:
        print("\n2. 缺口检测需要安装 opencv-python:")
        print("   pip install opencv-python")

    # 演示完整流程
    print("\n3. 完整使用流程:")
    print("""
    # 1. 获取背景和滑块图片
    bg_bytes = await page.locator("#bg-image").screenshot()
    slider_bytes = await page.locator("#slider-image").screenshot()

    # 2. 检测缺口位置
    solver = SliderCaptchaSolver()
    gap_x = solver.detect_gap(bg_bytes, slider_bytes)

    # 3. 生成轨迹
    trajectory = solver.generate_trajectory(gap_x, style="human")

    # 4. 执行拖拽（Playwright）
    slider = page.locator("#slider-btn")
    box = await slider.bounding_box()
    start_x = box['x'] + box['width'] / 2
    start_y = box['y'] + box['height'] / 2

    await page.mouse.move(start_x, start_y)
    await page.mouse.down()

    for x, y, t in trajectory:
        await asyncio.sleep(t - last_t)
        await page.mouse.move(start_x + x, start_y + y)

    await page.mouse.up()
    """)

    print("\n" + "=" * 50)
    print("演示完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(demo())
