# 第10章：数据分析与可视化

展示Pandas数据分析、词云生成、图表制作等数据处理功能。

## 快速开始

```bash
cd 10_数据分析与可视化

# 安装基础依赖
uv sync

# 安装交互式图表功能（可选）
uv sync --extra interactive

# 运行示例
uv run python pandas_analysis.py
uv run python wordcloud_generator.py
uv run python chart_demo.py
```

### 核心依赖
- `pandas` - 数据分析
- `jieba` - 中文分词
- `wordcloud` - 词云生成
- `matplotlib` - 图表绘制
- `pyecharts`（可选）- 交互式图表
