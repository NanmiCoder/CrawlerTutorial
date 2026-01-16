# 第03章：代理IP的使用与管理

展示代理池设计、代理检测、多URL测试等代理管理功能。

## 快速开始

```bash
cd 03_代理IP的使用与管理
uv sync
uv run python proxy_demo.py
```

### 核心依赖
- `httpx` - HTTP客户端
- `loguru` - 日志系统

## 测试URL
- `httpbin.org/ip` - IP检测
- `api.ipify.org` - IP服务
- `ip-api.com/json/` - IP地理位置
