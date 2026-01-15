# -*- coding: utf-8 -*-
# @Desc: OCR 图片验证码识别

import io
from typing import Optional
from loguru import logger

# 可选依赖
try:
    import ddddocr
    HAS_DDDDOCR = True
except ImportError:
    HAS_DDDDOCR = False
    logger.warning("ddddocr 未安装，部分功能不可用。安装: pip install ddddocr")

try:
    from PIL import Image, ImageFilter, ImageEnhance
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("pillow 未安装，图片预处理不可用。安装: pip install pillow")


class CaptchaPreprocessor:
    """验证码图片预处理器"""

    def __init__(self):
        if not HAS_PIL:
            raise ImportError("需要安装 pillow: pip install pillow")

    def to_grayscale(self, image_bytes: bytes) -> bytes:
        """
        转为灰度图

        Args:
            image_bytes: 图片字节

        Returns:
            处理后的图片字节
        """
        img = Image.open(io.BytesIO(image_bytes))
        gray = img.convert('L')

        buffer = io.BytesIO()
        gray.save(buffer, format='PNG')
        return buffer.getvalue()

    def binarize(self, image_bytes: bytes, threshold: int = 127) -> bytes:
        """
        二值化

        Args:
            image_bytes: 图片字节
            threshold: 阈值 (0-255)，小于阈值变黑，大于变白

        Returns:
            处理后的图片字节
        """
        img = Image.open(io.BytesIO(image_bytes))
        gray = img.convert('L')

        # 二值化
        binary = gray.point(lambda x: 255 if x > threshold else 0)

        buffer = io.BytesIO()
        binary.save(buffer, format='PNG')
        return buffer.getvalue()

    def remove_noise(self, image_bytes: bytes, size: int = 3) -> bytes:
        """
        去噪点（中值滤波）

        Args:
            image_bytes: 图片字节
            size: 滤波器大小

        Returns:
            处理后的图片字节
        """
        img = Image.open(io.BytesIO(image_bytes))
        denoised = img.filter(ImageFilter.MedianFilter(size=size))

        buffer = io.BytesIO()
        denoised.save(buffer, format='PNG')
        return buffer.getvalue()

    def enhance_contrast(self, image_bytes: bytes, factor: float = 2.0) -> bytes:
        """
        增强对比度

        Args:
            image_bytes: 图片字节
            factor: 对比度因子，>1 增强，<1 降低

        Returns:
            处理后的图片字节
        """
        img = Image.open(io.BytesIO(image_bytes))
        enhancer = ImageEnhance.Contrast(img)
        enhanced = enhancer.enhance(factor)

        buffer = io.BytesIO()
        enhanced.save(buffer, format='PNG')
        return buffer.getvalue()

    def enhance_sharpness(self, image_bytes: bytes, factor: float = 2.0) -> bytes:
        """
        增强锐度

        Args:
            image_bytes: 图片字节
            factor: 锐度因子

        Returns:
            处理后的图片字节
        """
        img = Image.open(io.BytesIO(image_bytes))
        enhancer = ImageEnhance.Sharpness(img)
        enhanced = enhancer.enhance(factor)

        buffer = io.BytesIO()
        enhanced.save(buffer, format='PNG')
        return buffer.getvalue()

    def resize(self, image_bytes: bytes, scale: float = 2.0) -> bytes:
        """
        缩放图片

        Args:
            image_bytes: 图片字节
            scale: 缩放比例

        Returns:
            处理后的图片字节
        """
        img = Image.open(io.BytesIO(image_bytes))
        new_size = (int(img.width * scale), int(img.height * scale))
        resized = img.resize(new_size, Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        resized.save(buffer, format='PNG')
        return buffer.getvalue()

    def full_preprocess(
        self,
        image_bytes: bytes,
        threshold: int = 150
    ) -> bytes:
        """
        完整预处理流程

        Args:
            image_bytes: 原始图片
            threshold: 二值化阈值

        Returns:
            处理后的图片
        """
        # 灰度化
        processed = self.to_grayscale(image_bytes)
        # 增强对比度
        processed = self.enhance_contrast(processed, factor=1.5)
        # 去噪
        processed = self.remove_noise(processed)
        # 二值化
        processed = self.binarize(processed, threshold)

        return processed


class OCRCaptchaSolver:
    """OCR 验证码识别器"""

    def __init__(self, preprocess: bool = True, show_ad: bool = False):
        """
        Args:
            preprocess: 是否进行预处理
            show_ad: 是否显示 ddddocr 广告
        """
        if not HAS_DDDDOCR:
            raise ImportError("需要安装 ddddocr: pip install ddddocr")

        self.ocr = ddddocr.DdddOcr(show_ad=show_ad)
        self.preprocess = preprocess

        if preprocess and HAS_PIL:
            self.preprocessor = CaptchaPreprocessor()
        else:
            self.preprocessor = None

    def solve(self, image_bytes: bytes) -> Optional[str]:
        """
        识别验证码

        Args:
            image_bytes: 图片字节

        Returns:
            识别结果
        """
        try:
            # 预处理
            if self.preprocess and self.preprocessor:
                image_bytes = self.preprocessor.full_preprocess(image_bytes)

            # 识别
            result = self.ocr.classification(image_bytes)
            logger.debug(f"验证码识别结果: {result}")
            return result

        except Exception as e:
            logger.error(f"验证码识别失败: {e}")
            return None

    def solve_raw(self, image_bytes: bytes) -> Optional[str]:
        """
        不预处理直接识别

        Args:
            image_bytes: 图片字节

        Returns:
            识别结果
        """
        try:
            return self.ocr.classification(image_bytes)
        except Exception as e:
            logger.error(f"验证码识别失败: {e}")
            return None

    def solve_with_multiple_thresholds(
        self,
        image_bytes: bytes,
        thresholds: list = None,
        min_length: int = 4
    ) -> Optional[str]:
        """
        尝试不同阈值识别

        Args:
            image_bytes: 图片字节
            thresholds: 要尝试的阈值列表
            min_length: 最小结果长度

        Returns:
            最佳识别结果
        """
        if not self.preprocessor:
            return self.solve_raw(image_bytes)

        thresholds = thresholds or [100, 127, 150, 180]
        best_result = None
        best_confidence = 0

        for threshold in thresholds:
            try:
                processed = self.preprocessor.full_preprocess(
                    image_bytes,
                    threshold=threshold
                )
                result = self.ocr.classification(processed)

                if result and len(result) >= min_length:
                    # 简单的置信度评估：结果长度和字符类型
                    confidence = len(result)
                    if result.isalnum():
                        confidence += 2

                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_result = result

            except Exception as e:
                logger.debug(f"阈值 {threshold} 识别失败: {e}")
                continue

        return best_result


def demo():
    """演示 OCR 验证码识别"""
    print("=" * 50)
    print("OCR 验证码识别演示")
    print("=" * 50)

    if not HAS_DDDDOCR:
        print("请先安装 ddddocr: pip install ddddocr")
        return

    # 创建识别器
    solver = OCRCaptchaSolver(preprocess=True, show_ad=False)

    # 演示：使用测试图片
    # 实际使用时，从网页获取验证码图片
    print("\n1. 基本识别演示:")
    print("   实际使用时，传入验证码图片的字节数据")
    print("   示例: result = solver.solve(image_bytes)")

    # 演示预处理器
    if HAS_PIL:
        print("\n2. 图片预处理演示:")
        preprocessor = CaptchaPreprocessor()
        print("   支持的预处理方法:")
        print("   - to_grayscale(): 转灰度图")
        print("   - binarize(): 二值化")
        print("   - remove_noise(): 去噪点")
        print("   - enhance_contrast(): 增强对比度")
        print("   - full_preprocess(): 完整预处理流程")

    print("\n" + "=" * 50)
    print("演示完成")
    print("=" * 50)


if __name__ == "__main__":
    demo()
