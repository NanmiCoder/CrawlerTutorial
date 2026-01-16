# 第08章：验证码识别与处理

展示图片验证码OCR识别、滑块验证码处理、人类轨迹生成等。

## 快速开始

```bash
cd 08_验证码识别与处理

# 安装基础依赖
uv sync

# 安装OCR功能
uv sync --extra ocr

# 安装图像处理功能
uv sync --extra cv

# 安装验证码生成功能
uv sync --extra generate

# 安装轨迹可视化功能
uv sync --extra viz

# 或安装所有功能
uv sync --extra all

# 运行示例
uv run python ocr_captcha.py
uv run python slider_captcha.py
```

### 可选依赖说明
- `ddddocr` - OCR识别引擎
- `opencv-python` - 图像处理（滑块验证码）
- `captcha` - 本地验证码生成
- `matplotlib` - 轨迹可视化
