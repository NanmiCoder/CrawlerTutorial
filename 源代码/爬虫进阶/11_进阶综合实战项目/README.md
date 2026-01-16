# 第11章：进阶综合实战项目

完整的书籍电商数据采集工具，爬取 **books.toscrape.com**（专门的爬虫练习网站）。

## 快速开始

### 使用 uv 安装依赖

```bash
cd 11_进阶综合实战项目

# 安装依赖
uv sync

# 安装可选功能（配置管理增强）
uv sync --extra all

# 安装Playwright浏览器驱动
uv run playwright install chromium

# 运行项目
uv run python main.py
```

### 目标网站

- **网站**：http://books.toscrape.com
- **类型**：专门用于爬虫练习的合法网站
- **特点**：电商结构完整，50页书籍数据，无需登录

### 核心依赖

- `playwright` - 浏览器自动化
- `httpx` - HTTP客户端
- `pydantic` - 数据验证
- `loguru` - 日志系统
- `pandas` - 数据分析
- `jieba` + `wordcloud` - 词云生成

## 项目结构

```
11_进阶综合实战项目/
├── config/          # 配置模块
├── core/            # 核心模块（浏览器管理）
├── login/           # 登录模块
├── crawler/         # 爬虫模块
├── store/           # 存储模块
├── proxy/           # 代理池模块
├── analysis/        # 分析模块
└── main.py          # 主程序入口
```

## 功能特性

- ✅ 浏览器自动化采集
- ✅ 反检测技术（stealth.js）
- ✅ 多格式数据存储（JSON/CSV）
- ✅ 词云和统计报告生成
- ✅ 代理池支持（可选）

## 运行结果

运行成功后会在 `output/` 目录下生成：
- `data_*.json` 或 `data_*.csv` - 采集的数据
- `report.md` - 数据分析报告
- `wordcloud.png` - 词云图片
