import asyncio
import json
import logging
import traceback

from models.UserCl import UserCl


async def update_users_keys():
    try:
        json_file_path = "models/new_key.json"
        with open(json_file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if "users" not in data or not isinstance(data["users"], list):
            print("Ошибка: В JSON нет ключа 'users' или он не является списком")
            return

        for user_data in data["users"]:
            try:
                chat_id = user_data.get("chat_id")
                url = user_data.get("url")

                if chat_id is None or not isinstance(chat_id, int):
                    print(f"Ошибка: chat_id отсутствует или некорректен: {user_data}")
                    continue

                if not isinstance(url, str) or not url.startswith("vless://"):
                    print(f"Ошибка: Некорректный URL {url} у пользователя {chat_id}")
                    continue

                user = await UserCl.load_user(chat_id)  # Загружаем пользователя
                if user is None:
                    print(f"Ошибка: Не удалось загрузить пользователя с chat_id {chat_id}")
                    continue

                # Проверяем, есть ли этот URL в истории пользователя
                is_duplicate = False
                if url == await user.active_server.url_vless.get():
                    is_duplicate = True


                if is_duplicate:
                    continue  # Пропускаем обновление

                await user.update_key_to_vless(url)  # Обновляем ключ
                print(f"✅ Успешно обновлен ключ для пользователя {chat_id}")

            except Exception as e:
                print(f"❌ Ошибка при обработке пользователя с chat_id {chat_id}: {e}")
                traceback.print_exc()

    except Exception as e:
        print(f"🔥 Глобальная ошибка при обработке JSON: {e}")
        traceback.print_exc()




# async def update_users_keys():
#     """
#     Обновляет ключи пользователей, используя данные из Excel-файла.
#     """
#     file_path = "models/new_key.json"
#
#     try:
#         df = pd.read_excel(file_path, engine='openpyxl')
#     except Exception as e:
#         logging.error(f"Ошибка при чтении файла {file_path}: {e}")
#         return
#
#
#     required_columns = {"chat_id", "url"}
#     if not required_columns.issubset(df.columns):
#         logging.error(f"Файл Excel не содержит необходимые столбцы: {', '.join(required_columns)}")
#         return
#
#
#     for _, row in df.iterrows():
#         chat_id = row["chat_id"]
#         url = row["url"]
#
#         try:
#             user = await UserCl.load_user(chat_id)
#             if user:
#                 logging.info(f"Обновляем ключ для пользователя {chat_id}")
#                 await user.update_key_to_vless(url)
#             else:
#                 logging.warning(f"Пользователь {chat_id} не найден в базе данных")
#         except Exception as e:
#             logging.error(f"Ошибка при обновлении ключа для пользователя {chat_id}: {e}")