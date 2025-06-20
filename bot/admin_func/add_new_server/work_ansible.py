









# ---------- Функция обработки сервера ----------
async def process_server_setup(ip_address: str, password: str, server_type: str, message: Message, asyncssh=None):
    try:
        async with asyncssh.connect(ip_address, username='root', password=password, known_hosts=None) as conn:
            result = await conn.run('cat /etc/ssl/certs/ssl-cert.pem', check=True)
            cert_content = result.stdout

            # Здесь можно сохранить сертификат локально
            # Важно: пароль нигде не сохраняем!

            await message.answer("✅ Сертификат успешно получен!")

    except (asyncssh.Error, OSError) as ssh_error:
        await message.answer(f"❌ Ошибка SSH: {ssh_error}")
        return

    #Запуск Ansible Playbook
    #await run_ansible_playbook(ip_address, server_type, message)