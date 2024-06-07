# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/3/24 16:35
# @Desc    :

import asyncio

import httpx


async def post_data():
    data = {'name': '程序员阿江','email':'relakkes@gmail.com'}
    async with httpx.AsyncClient() as client:
        response = await client.post('https://httpbin.org/post', data=data)
        print(response.json())

asyncio.run(post_data())