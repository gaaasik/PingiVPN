# # bot/utils/config.py
# from pydantic_settings import BaseSettings
# from pydantic import Field
# from dotenv import load_dotenv
# import os
#
# # Убедитесь, что переменные окружения загружаются до определения классов
# load_dotenv()  # Загружаем переменные окружения из файла .env
#
# # class BotConfig(BaseSettings):
# #     token: str = Field(..., "7036736465:AAEOlcvkYEp3MrEaS1Md0iR8Xilgti6cFuU")
#
# class DatabaseConfig(BaseSettings):
#     url: str = Field(..., env="DATABASE_URL")
#
# class Config(BaseSettings):
#    # bot: BotConfig = BotConfig()
#     db: DatabaseConfig = DatabaseConfig()
#
# def load_config(path: str) -> Config:
#     # Убедитесь, что load_dotenv вызывается перед загрузкой настроек
#     load_dotenv(path)
#     return Config(_env_file=path, _env_file_encoding="utf-8")
