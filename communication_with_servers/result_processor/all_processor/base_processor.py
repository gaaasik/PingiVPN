
class BaseResultProcessor:
    def __init__(self, redis_client):
        self.redis_client = redis_client

    async def process(self, task_data: dict):
        raise NotImplementedError("Метод process должен быть реализован в подклассе.")
