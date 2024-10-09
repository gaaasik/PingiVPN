import os
from dotenv import load_dotenv

load_dotenv()



# Настройки базы данных
DATABASE_PATH = os.getenv('database_path_local')

# Настройки Юкассы
SHOP_ID = os.getenv('SHOPID')
SECRET_KEY = os.getenv('API_KEY')
