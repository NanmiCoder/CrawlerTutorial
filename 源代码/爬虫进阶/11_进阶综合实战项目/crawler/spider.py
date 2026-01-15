# -*- coding: utf-8 -*-
# @Desc: 爬虫模块

import asyncio
import random
from typing import List, Dict, Any
from datetime import datetime
from loguru import logger


class BaseCrawler:
    """爬虫基类"""

    def __init__(
        self,
        delay_min: float = 1.0,
        delay_max: float = 3.0,
        max_pages: int = 10
    ):
        """
        初始化爬虫

        Args:
            delay_min: 最小延迟（秒）
            delay_max: 最大延迟（秒）
            max_pages: 最大爬取页数
        """
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.max_pages = max_pages
        self._results: List[Dict] = []

    async def random_delay(self):
        """随机延迟"""
        delay = random.uniform(self.delay_min, self.delay_max)
        await asyncio.sleep(delay)

    async def crawl(self, page) -> List[Dict]:
        """执行爬取（子类实现）"""
        raise NotImplementedError

    def get_results(self) -> List[Dict]:
        """获取结果"""
        return self._results

    def clear_results(self):
        """清空结果"""
        self._results = []


class ContentCrawler(BaseCrawler):
    """内容爬虫 - 适用于分页列表"""

    def __init__(
        self,
        start_url: str,
        item_selector: str,
        fields: Dict[str, str],
        next_page_selector: str = None,
        **kwargs
    ):
        """
        初始化内容爬虫

        Args:
            start_url: 起始 URL
            item_selector: 列表项选择器
            fields: 字段映射 {字段名: 选择器}
                    选择器以 @ 开头表示获取属性，如 @href
            next_page_selector: 下一页按钮选择器
        """
        super().__init__(**kwargs)
        self.start_url = start_url
        self.item_selector = item_selector
        self.fields = fields
        self.next_page_selector = next_page_selector

    async def extract_item(self, element) -> Dict:
        """提取单个项目的数据"""
        data = {'crawl_time': datetime.now().isoformat()}

        for field_name, selector in self.fields.items():
            try:
                if selector.startswith('@'):
                    # 属性选择器
                    attr = selector[1:]
                    value = await element.get_attribute(attr)
                elif '|' in selector:
                    # 带属性的选择器，格式：选择器|属性名
                    sel, attr = selector.split('|', 1)
                    sub_element = await element.query_selector(sel)
                    if sub_element:
                        value = await sub_element.get_attribute(attr)
                    else:
                        value = None
                else:
                    # 文本选择器
                    sub_element = await element.query_selector(selector)
                    if sub_element:
                        value = await sub_element.inner_text()
                    else:
                        value = None

                data[field_name] = value.strip() if value else None
            except Exception as e:
                logger.debug(f"提取字段 {field_name} 失败: {e}")
                data[field_name] = None

        return data

    async def crawl(self, page) -> List[Dict]:
        """执行爬取"""
        self._results = []
        current_page = 0

        # 访问起始页
        await page.goto(self.start_url, wait_until='networkidle')
        logger.info(f"访问: {self.start_url}")

        while current_page < self.max_pages:
            current_page += 1
            logger.info(f"正在爬取第 {current_page} 页")

            # 等待列表加载
            try:
                await page.wait_for_selector(self.item_selector, timeout=10000)
            except Exception:
                logger.warning(f"第 {current_page} 页未找到列表项")
                break

            # 提取数据
            items = await page.query_selector_all(self.item_selector)
            page_data = []
            for item in items:
                data = await self.extract_item(item)
                page_data.append(data)
                self._results.append(data)

            logger.info(f"第 {current_page} 页提取 {len(page_data)} 条数据")

            # 翻页
            if self.next_page_selector and current_page < self.max_pages:
                try:
                    next_btn = await page.query_selector(self.next_page_selector)
                    if next_btn:
                        # 检查是否可点击
                        is_disabled = await next_btn.get_attribute('disabled')
                        if is_disabled:
                            logger.info("已到最后一页")
                            break

                        await next_btn.click()
                        await self.random_delay()
                        # 等待页面加载
                        await page.wait_for_load_state('networkidle')
                    else:
                        logger.info("没有更多页面")
                        break
                except Exception as e:
                    logger.warning(f"翻页失败: {e}")
                    break

        logger.info(f"爬取完成，共 {len(self._results)} 条数据")
        return self._results


class ScrollCrawler(BaseCrawler):
    """滚动加载爬虫 - 适用于无限滚动页面"""

    def __init__(
        self,
        start_url: str,
        item_selector: str,
        fields: Dict[str, str] = None,
        scroll_count: int = 10,
        scroll_pause: float = 1.5,
        **kwargs
    ):
        """
        初始化滚动爬虫

        Args:
            start_url: 起始 URL
            item_selector: 列表项选择器
            fields: 字段映射（可选，为空则只提取文本内容）
            scroll_count: 滚动次数
            scroll_pause: 滚动后暂停时间
        """
        super().__init__(**kwargs)
        self.start_url = start_url
        self.item_selector = item_selector
        self.fields = fields
        self.scroll_count = scroll_count
        self.scroll_pause = scroll_pause

    async def crawl(self, page) -> List[Dict]:
        """执行爬取"""
        self._results = []
        seen_ids = set()

        await page.goto(self.start_url, wait_until='networkidle')
        logger.info(f"访问: {self.start_url}")

        for i in range(self.scroll_count):
            logger.info(f"滚动加载第 {i + 1}/{self.scroll_count} 次")

            # 提取当前页面数据
            items = await page.query_selector_all(self.item_selector)
            new_count = 0

            for item in items:
                try:
                    content = await item.inner_text()
                    content_id = hash(content)

                    if content_id not in seen_ids:
                        seen_ids.add(content_id)
                        new_count += 1

                        if self.fields:
                            # 按字段提取
                            data = {'crawl_time': datetime.now().isoformat()}
                            for field_name, selector in self.fields.items():
                                try:
                                    sub_el = await item.query_selector(selector)
                                    if sub_el:
                                        data[field_name] = (await sub_el.inner_text()).strip()
                                    else:
                                        data[field_name] = None
                                except Exception:
                                    data[field_name] = None
                        else:
                            data = {
                                'content': content.strip(),
                                'crawl_time': datetime.now().isoformat()
                            }

                        self._results.append(data)
                except Exception as e:
                    logger.debug(f"提取项目失败: {e}")

            logger.info(f"本次滚动新增 {new_count} 条数据")

            # 滚动到底部
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(self.scroll_pause)

            # 检查是否到达底部
            is_at_bottom = await page.evaluate('''
                () => {
                    return window.innerHeight + window.scrollY >= document.body.scrollHeight - 100;
                }
            ''')

            if is_at_bottom and new_count == 0:
                logger.info("已到达页面底部，没有更多内容")
                break

        logger.info(f"爬取完成，共 {len(self._results)} 条数据")
        return self._results
