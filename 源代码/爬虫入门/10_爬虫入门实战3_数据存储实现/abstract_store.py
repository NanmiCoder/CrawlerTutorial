# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Name    : 程序员阿江-Relakkes
# @Time    : 2024/6/7 14:56
# @Desc    :
from abc import ABC, abstractmethod

from common import SymbolContent


class AbstractStore(ABC):
    @abstractmethod
    async def save(self, save_item: SymbolContent):
        """
        存储数据
        :param save_item:
        :return:
        """
        raise NotImplementedError
