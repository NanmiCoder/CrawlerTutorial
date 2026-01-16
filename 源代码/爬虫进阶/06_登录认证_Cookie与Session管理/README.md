# 第06章：登录认证 - Cookie与Session管理

展示Cookie管理、登录状态检测、真实网站登录演示。

## 快速开始

```bash
cd 06_登录认证_Cookie与Session管理
uv sync
uv run python cookie_manager.py
uv run python login_state_checker.py
uv run python session_demo.py  # 包含 quotes.toscrape.com 真实登录演示
```

### 新增功能
✨ **真实登录演示**：`session_demo.py` 中的 `demo_real_login()` 函数演示了完整的 quotes.toscrape.com 登录流程。

### 核心依赖
- `httpx` - HTTP客户端
- `loguru` - 日志系统
- `cryptography`（可选）- Cookie加密
