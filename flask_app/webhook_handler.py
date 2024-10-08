# import hashlib
# import hmac
#
# from flask import request, jsonify
# import asyncio
# from bot.utils import logger
# from flask_app.config_flask_redis import SECRET_KEY
#
# def verify_signature(data, signature):
#     """Проверка подписи HMAC для безопасности вебхуков."""
#     try:
#         hash_digest = hmac.new(SECRET_KEY.encode('utf-8'), data.encode('utf-8'), hashlib.sha256).hexdigest()
#         return hmac.compare_digest(hash_digest, signature)
#     except Exception as e:
#         logger.error(f"Ошибка при проверке подписи: {e}")
#         return False
#
