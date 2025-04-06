import os
from dotenv import load_dotenv
import redis.asyncio as redis
import logging
# Загружаем переменные окружения из .env redis_client = redis.Redis(
load_dotenv()


# Инициализация асинхронного клиента Redis
redis_client_main = redis.Redis(
    host=os.getenv('ip_redis_server'),
    port=int(os.getenv('port_redis')),
    password=os.getenv('password_redis'),
    decode_responses=True
)

# Параметры логирования
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_FILE = os.getenv("LOG_FILE", "logs/main_server_task_processor.log")

# Настройка логирования

