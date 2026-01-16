# 第05章：Playwright进阶 - 反检测与性能优化

展示stealth.js注入、CDP模式、浏览器指纹伪装、性能优化等高级技术。

## 快速开始

```bash
cd 05_Playwright进阶_反检测与性能优化
uv sync
uv run playwright install chromium
uv run python stealth_demo.py
uv run python cdp_mode.py
uv run python performance_optimization.py
```

### 测试网站
- **bot.sannysoft.com** - 最佳的反检测测试网站

### 核心技术
- stealth.js注入 - 隐藏自动化特征
- CDP模式 - 直接调用Chrome DevTools Protocol
- 资源拦截 - 阻止不必要的资源加载
- 浏览器上下文池 - 复用提升性能
