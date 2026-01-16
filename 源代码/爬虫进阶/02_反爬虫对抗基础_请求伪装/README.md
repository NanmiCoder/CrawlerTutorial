# 第02章：反爬虫对抗基础 - 请求伪装

展示User-Agent轮换、请求头伪装、速率控制等反爬技术。

## 快速开始

### 使用 uv 安装依赖

```bash
cd 02_反爬虫对抗基础_请求伪装

# 安装基础依赖
uv sync

# 安装高级功能（TLS指纹伪装，可选）
uv sync --extra advanced

# 运行示例
uv run python ua_rotator.py
uv run python headers_builder.py
uv run python rate_limiter.py
uv run python anti_detection_crawler.py
```

### 核心依赖

- `httpx` - 异步HTTP客户端
- `loguru` - 日志系统
- `fake-useragent` - User-Agent生成
- `curl-cffi`（可选）- TLS指纹伪装

## 主要文件

- `ua_rotator.py` - User-Agent轮换器
- `headers_builder.py` - 请求头构建器
- `rate_limiter.py` - 速率限制器
- `anti_detection_crawler.py` - 完整反检测爬虫示例
