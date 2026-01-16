# 第09章：数据清洗与预处理

展示文本清洗、数据标准化、去重算法等数据处理技术。

## 快速开始

```bash
cd 09_数据清洗与预处理

# 安装依赖（本章主要使用Python标准库）
uv sync

# 安装SimHash去重功能（可选）
uv sync --extra simhash

# 运行示例
uv run python text_cleaner.py
uv run python data_normalizer.py
uv run python deduplication.py
```

### 主要功能

- **文本清洗**
  - HTML标签移除
  - 空白字符处理
  - 特殊字符清理
  - 编码问题修复

- **数据标准化**
  - 日期时间格式统一
  - 数值单位换算
  - 文本规范化

- **去重算法**
  - 精确去重
  - 模糊去重（编辑距离、Jaccard相似度）
  - SimHash去重（大规模文本）

### 依赖说明

本章主要使用Python标准库，`simhash` 为可选依赖，用于大规模文本去重。
