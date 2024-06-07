# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Name    : 程序员阿江-Relakkes
# @Time    : 2024/6/7 17:09
# @Desc    :

from async_db import AsyncMysqlDB
from common import SymbolContent


async def insert_symbol_content(db: AsyncMysqlDB, symbol_content: SymbolContent) -> int:
    """
    插入数据
    :param db:
    :param symbol_content:
    :return:
    """
    item = symbol_content.model_dump()
    return await db.item_to_table("symbol_content", item)


async def update_symbol_content(db: AsyncMysqlDB, symbol_content: SymbolContent) -> int:
    """
    更新数据
    :param db:
    :param symbol_content:
    :return:
    """
    item = symbol_content.model_dump()
    return await db.update_table("symbol_content", item, "symbol", symbol_content.symbol)


async def query_symbol_content_by_symbol(db: AsyncMysqlDB, symbol: str) -> SymbolContent:
    """
    查询数据
    :param db:
    :param symbol:
    :return:
    """
    sql = f"select * from symbol_content where symbol = '{symbol}'"
    rows = await db.query(sql)
    if len(rows) > 0:
        return SymbolContent(**rows[0])
    return SymbolContent()
