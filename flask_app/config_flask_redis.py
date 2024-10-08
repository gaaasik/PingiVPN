import os
from dotenv import load_dotenv

load_dotenv()

# Настройки Redis
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
REDIS_QUEUE = os.getenv('REDIS_QUEUE', 'payment_notifications')

# Настройки базы данных
DATABASE_PATH = os.getenv('database_path_local')

# Настройки Юкассы
SHOP_ID = os.getenv('SHOPID')
SECRET_KEY = os.getenv('API_KEY')
