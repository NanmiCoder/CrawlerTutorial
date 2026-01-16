# 第07章：登录认证 - 扫码与短信登录实现

展示扫码登录和短信登录的技术框架和实现思路。

## 快速开始

```bash
cd 07_登录认证_扫码与短信登录实现

# 安装基础依赖
uv sync

# 安装二维码功能（可选）
uv sync --extra qrcode

# 安装浏览器
uv run playwright install chromium

# 运行示例
uv run python qrcode_login.py
uv run python sms_login.py
uv run python login_factory.py
```

### 重要说明

⚠️ 本章代码提供的是**技术框架**而非特定网站实战，因为没有公开的练习网站提供真实扫码/短信登录功能。

代码展示了：
- 扫码登录的技术原理和流程
- 短信登录的实现模式
- 登录工厂模式设计

实际使用时需要根据目标网站适配具体的：
- 二维码选择器
- 状态轮询机制
- Cookie获取方式
