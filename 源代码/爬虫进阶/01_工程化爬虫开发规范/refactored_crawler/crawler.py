# -*- coding: utf-8 -*-
# @Desc: 爬虫核心逻辑

import asyncio
from typing import List
from loguru import logger

from .config import settings
from .client import CrawlerClient
from .parser import BBSParser
from .models import NoteItem, NoteDetail, CrawlResult
from .exceptions import CrawlerException


class BBSCrawler:
    """
    BBS 论坛爬虫

    工程化特性:
    - 配置驱动
    - 完善的日志记录
    - 优雅的异常处理
    - 资源自动管理
    """

    def __init__(self):
        self.client = CrawlerClient()
        self.parser = BBSParser()
        self.result = CrawlResult()

    async def run(self) -> CrawlResult:
        """
        运行爬虫

        Returns:
            爬取结果
        """
        logger.info(f"开始爬取任务 - 目标: 前 {settings.first_n_page} 页")

        async with self.client:
            # Step 1: 获取分页信息
            previous_number = await self._get_previous_page_number()

            # Step 2: 爬取帖子列表
            note_items = await self._crawl_note_list(previous_number)

            # Step 3: 爬取帖子详情
            await self._crawl_note_details(note_items)

        logger.info(
            f"爬取完成 - 成功: {self.result.success_count}, "
            f"失败: {self.result.fail_count}"
        )

        return self.result

    async def _get_previous_page_number(self) -> int:
        """获取上一页分页号"""
        logger.info("获取分页信息...")

        url = f"{settings.base_host}/bbs/Stock/index.html"
        response = await self.client.get(url)
        page_number = self.parser.parse_previous_page_number(response.text)

        logger.info(f"当前最新分页号: {page_number + 1}")
        return page_number

    async def _crawl_note_list(self, previous_number: int) -> List[NoteItem]:
        """爬取帖子列表"""
        logger.info(f"开始爬取帖子列表...")

        all_notes: List[NoteItem] = []
        start_page = previous_number + 1
        end_page = start_page - settings.first_n_page

        for page_num in range(start_page, end_page, -1):
            try:
                url = f"{settings.base_host}/bbs/Stock/index{page_num}.html"
                logger.info(f"爬取第 {page_num} 页...")

                response = await self.client.get(url)
                notes = self.parser.parse_note_list(response.text)
                all_notes.extend(notes)

                logger.info(f"第 {page_num} 页获取 {len(notes)} 个帖子")

                # 请求间隔
                await asyncio.sleep(settings.request_delay)

            except CrawlerException as e:
                logger.warning(f"第 {page_num} 页爬取失败: {e}")
                continue

        self.result.total_pages = settings.first_n_page
        self.result.total_notes = len(all_notes)
        logger.info(f"帖子列表爬取完成, 共 {len(all_notes)} 个帖子")

        return all_notes

    async def _crawl_note_details(self, note_items: List[NoteItem]):
        """爬取帖子详情"""
        logger.info(f"开始爬取帖子详情, 共 {len(note_items)} 个...")

        for idx, note_item in enumerate(note_items, 1):
            try:
                url = f"{settings.base_host}{note_item.detail_link}"
                logger.debug(f"[{idx}/{len(note_items)}] 爬取: {note_item.title[:30]}...")

                response = await self.client.get(url)
                detail = self.parser.parse_note_detail(response.text, note_item)

                self.result.notes.append(detail)
                self.result.success_count += 1

                # 请求间隔
                await asyncio.sleep(settings.request_delay)

            except CrawlerException as e:
                logger.warning(f"帖子详情爬取失败: {note_item.title[:20]}... - {e}")
                self.result.fail_count += 1
                continue

            except Exception as e:
                logger.exception(f"未知错误: {e}")
                self.result.fail_count += 1
                continue

            # 每 10 个帖子输出一次进度
            if idx % 10 == 0:
                logger.info(f"进度: {idx}/{len(note_items)}")

    async def cleanup(self):
        """清理资源"""
        logger.debug("执行清理...")
        await self.client.close()
