# 第04章：Playwright浏览器自动化入门

展示Playwright基本操作、元素定位、等待策略等。

## 快速开始

```bash
cd 04_Playwright浏览器自动化入门
uv sync
uv run playwright install chromium  # 安装浏览器
uv run python basic_operations.py
uv run python wait_strategies.py
uv run python spa_crawler.py
```

### 目标网站
- **quotes.toscrape.com** - 静态版本
- **quotes.toscrape.com/js/** - SPA版本（需要JavaScript渲染）
