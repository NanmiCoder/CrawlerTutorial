# 第01章：工程化爬虫开发规范

展示日志系统、配置管理、异常处理等工程化实践。

## 快速开始

### 使用 uv 安装依赖

```bash
# 进入本章目录
cd 01_工程化爬虫开发规范

# 安装依赖
uv sync

# 运行示例
uv run python logger_demo.py
uv run python exception_demo.py
uv run python refactored_crawler/main.py
```

### 核心依赖

- `httpx` - 异步HTTP客户端
- `pydantic` - 数据验证
- `parsel` - HTML解析
- `loguru` - 日志系统

## 主要文件

- `logger_demo.py` - 日志系统演示
- `exception_demo.py` - 异常处理演示
- `refactored_crawler/` - 工程化改造后的完整爬虫项目
