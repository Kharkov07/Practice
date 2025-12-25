import re
import requests
from telegram.ext import Updater, CommandHandler

BOT_TOKEN = "8588255327:AAG5FxweplaX0mi6yA9QZmN7EPOvdDWDc4o"
SITE_URL = "http://127.0.0.1:8000"
BOT_SHARED_SECRET = "wertyuioplkjhgfdsa1243"

LINK_RE = re.compile(r"^link_([0-9a-fA-F-]{36})$")


def start(update, context):
    if not context.args:
        update.message.reply_text(
            "Привет 👋\n\n"
            "1️⃣ На сайте нажми «Подтвердить через Telegram»\n"
            "2️⃣ Вернись сюда и нажми Start по ссылке\n\n"
            "Для получения кода входа используй команду:\n"
            "/code"
        )
        return
    payload = context.args[0]
    match = LINK_RE.match(payload)
    if not match:
        update.message.reply_text("❌ Неверная ссылка. Перейди в бота через кнопку на сайте.")
        return
    token = match.group(1)
    chat_id = str(update.effective_chat.id)
    try:
        response = requests.post(
            f"{SITE_URL}/bot/confirm-link/",
            headers={"X-Bot-Secret": BOT_SHARED_SECRET},
            data={"token": token, "chat_id": chat_id},
            timeout=10,
        )
    except Exception as e:
        update.message.reply_text(f"❌ Не могу подключиться к сайту:\n{e}")
        return
    if response.status_code == 200:
        safe_send(update, "✅ Telegram успешно привязан!\n\nВернись на сайт и нажми «Проверить статус».")
    else:
        safe_send(update, f"❌ Ошибка привязки ({response.status_code}):\n{response.text}")


def code(update, context):
    chat_id = str(update.effective_chat.id)
    try:
        response = requests.get(
            f"{SITE_URL}/bot/get-login-code/",
            headers={"X-Bot-Secret": BOT_SHARED_SECRET},
            params={"chat_id": chat_id},
            timeout=10,
        )
    except Exception as e:
        update.message.reply_text(f"❌ Не могу подключиться к сайту:\n{e}")
        return
    if response.status_code != 200:
        update.message.reply_text(
            f"❌ Ошибка ({response.status_code}):\n{response.text}"
        )
        return
    data = response.json()
    if not data.get("ok"):
        reason = data.get("reason")
        if reason == "not_linked":
            update.message.reply_text("❌ Telegram не привязан к аккаунту.")
        elif reason == "no_code":
            update.message.reply_text("ℹ️ Кода ещё нет. Сначала войди на сайте.")
        elif reason == "expired":
            update.message.reply_text("⌛ Код истёк. Войди на сайте заново.")
        else:
            update.message.reply_text(f"❌ Ошибка: {data}")
        return
    update.message.reply_text(
        f"🔐 Код для входа:\n\n{data['code']}\n\n"
        "⏱ Действует ~5 минут"
    )


MAX_LEN = 3500


def safe_send(update, text: str):
    if len(text) > MAX_LEN:
        text = text[:MAX_LEN] + "\n\n…(обрезано)"
    update.message.reply_text(text)


def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    updater.dispatcher.add_handler(CommandHandler("start", start))
    updater.dispatcher.add_handler(CommandHandler("code", code))
    print("🤖 Telegram bot started")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
