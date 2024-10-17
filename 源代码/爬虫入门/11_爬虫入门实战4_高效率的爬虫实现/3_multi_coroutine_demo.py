# -*- coding: utf-8 -*-
import asyncio

async def worker(num):
    print(f"Coroutine {num} started")
    await asyncio.sleep(2)
    print(f"Coroutine {num} finished")

async def main():
    tasks = [asyncio.create_task(worker(i)) for i in range(5)]
    await asyncio.gather(*tasks)

asyncio.run(main())
print("All coroutines completed")