# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个 Python 爬虫教程仓库，包含从入门到高级的爬虫技术教学内容。作者是 MediaCrawler 开源项目的作者。

## 常用命令

```bash
# 安装依赖
npm install

# 启动文档开发服务器
npm run docs:dev

# 构建文档
npm run docs:build

# 预览构建后的文档
npm run docs:preview
```

## 项目结构

- `docs/` - VitePress 文档源文件（Markdown 格式）
  - `docs/.vitepress/` - VitePress 配置和主题
  - `docs/爬虫入门/` - 入门教程文档
  - `docs/爬虫进价/` - 进阶教程文档（待完善）
  - `docs/高级爬虫/` - 高级教程文档（待完善）
- `源代码/` - 教程对应的 Python 示例代码
  - 每个实战章节有独立目录，包含同步和异步两种实现版本

## Python 示例代码依赖

示例代码使用以下主要库：
- `httpx` - HTTP 请求库
- `aiomysql` - 异步 MySQL 客户端
- `aiofiles` - 异步文件操作
- `pydantic` - 数据验证

## 文档站点

在线文档: https://nanmicoder.github.io/CrawlerTutorial/
