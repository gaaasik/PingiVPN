# traffic_update_handler.py
import json
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

# Настройка логирования
logger = logging.getLogger("traffic_update_handler")

# Создаём роутер
router = APIRouter()

# Модель данных для JSON
class UserTrafficUpdate(BaseModel):
    name_protocol: str
    chat_id: int
    server_ip: str
    user_ip: str
    enable: bool


# Endpoint для обработки JSON
@router.post("/api/traffic_update")
async def traffic_update(request: Request):
    try:
        # Читаем тело запроса
        payload = await request.json()

        # Логируем полученный JSON
        logger.info(f"Получен JSON: {json.dumps(payload, indent=4)}")

        # Добавляем поле с датой обновления
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        payload["data_update_traffic"] = current_time

        # Логируем обновленный JSON
        logger.info(f"Обновленный JSON с датой: {json.dumps(payload, indent=4)}")

        # Возвращаем результат
        return {"status": "ok", "received_data": payload}

    except Exception as e:
        logger.error(f"Ошибка обработки запроса: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")