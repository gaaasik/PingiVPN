import redis
import json
from flask_app.config_flask_redis import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_QUEUE


# Подключение к Redis
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD)

def send_to_redis(queue, message):
    """Добавление сообщения в очередь Redis."""
    try:
        redis_client.lpush(queue, json.dumps(message))
        print(f"Сообщение добавлено в очередь {queue}: {message}")
    except Exception as e:
        print(f"Ошибка отправки сообщения в Redis: {e}")
