# import asyncio
# import logging
# import os
# from flask import Flask, request, jsonify
# from yookassa import Configuration, Payment
#
# from bot_instance import bot, BOT_TOKEN
# from .api_payments_db import update_payment_status, update_has_paid_subscription_db
#
# # Инициализация Flask
# from flask import Flask
#
# # Создаем экземпляр Flask приложения
# app = Flask(__name__)
#
#
#
#
#
# #delete_payments_by_user(1388513042)
#
#
#
#
# def send_message(chat_id, text, requests=None):
#     url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
#     payload = {
#         'chat_id': chat_id,
#         'text': text
#     }
#     response = requests.post(url, json=payload)
#     return response.json()
#
# # Маршрут для вебхука от Юкассы
# @app.route('/webhook', methods=['POST'])
# def webhook():
#
#     data = request.json
#
#     if data and 'event' in data:
#         payment_info = data['object']
#         payment_id = payment_info['id']
#         status = data['event']
#         amount = payment_info['amount']['value']
#         currency = payment_info['amount']['currency']
#         user_id = payment_info.get('metadata', {}).get('user_id', None)
#         payment_method_id = payment_info.get('payment_method', {}).get('id', '0')
#
#
#         # Обновление информации о платеже в базе данных
#         update_payment_status(payment_id, user_id, amount, currency, status, payment_method_id)
#
#         if status == 'payment.succeeded' and user_id:
#             update_has_paid_subscription_db(user_id,status)
#             send_message(user_id, "Ваш платёж был успешно завершён. Спасибо за покупку!")
#
#
#
#
#     return jsonify({"status": "ok"}), 200
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
