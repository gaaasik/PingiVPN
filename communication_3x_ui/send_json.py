import aioredis
import aiohttp
import asyncio
import json

async def send_json_to_3xui(data):
    url = "http://192.87.208.18:6222/api/update-enable"
    headers = {"Content-Type": "application/json"}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as response:
            if response.status == 200:
                print("JSON успешно отправлен на сервер 3x-ui.")
            else:
                print(f"Ошибка отправки JSON: {response.status}")
                error_text = await response.text()
                print("Ответ сервера:", error_text)

# Функция обработки очереди задач
async def process_task_queue():
    """Функция для обработки задач из очереди Redis и отправки их на сервер 3x-ui."""
    redis = aioredis.from_url("redis://localhost", db=1)

    try:
        while True:
            task_json = await redis.lpop("send_3x_ui")
            if task_json:
                task_data = json.loads(task_json)
                await send_json_to_3xui(task_data)
            else:
                await asyncio.sleep(5)
    finally:
        await redis.close()
#
# async def send_json_to_3xui(data):
#     url = "http://192.87.208.18:6222/api/update-enable"
#     headers = {"Content-Type": "application/json"}
#
#     async with aiohttp.ClientSession() as session:
#         async with session.post(url, json=data, headers=headers) as response:
#             if response.status == 200:
#                 print("JSON успешно отправлен на сервер 3x-ui.")
#             else:
#                 print(f"Ошибка отправки JSON: {response.status}")
#                 error_text = await response.text()
#                 print("Ответ сервера:", error_text)
#
#
# async def process_task_queue():
#     """Функция для обработки задач из очереди Redis и отправки их на сервер 3x-ui."""
#     redis = aioredis.from_url("redis://localhost", db=1)
#
#     try:
#         while True:
#             try:
#                 # Извлекаем задачу из очереди
#                 task_json = await redis.lpop("send_3x_ui")
#
#                 if task_json:
#                     # Преобразуем задачу из JSON в Python-словарь
#                     task_data = json.loads(task_json)
#
#                     # Пытаемся отправить задачу на сервер 3x-ui
#                     await send_json_to_3xui(task_data)
#
#                 else:
#                     # Если задач нет, ждем перед следующей проверкой
#                     await asyncio.sleep(5)
#
#             except Exception as e:
#                 print(f"Ошибка обработки задачи: {e}")
#                 await asyncio.sleep(5)  # Ждем перед повторной попыткой
#
#     finally:
#         await redis.close()
