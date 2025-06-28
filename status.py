import asyncio
import datetime
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
import os

API_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = -1002626775922

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

URL = "http://127.0.0.1:5005/ping"
monitoring_enabled = asyncio.Event()
monitoring_enabled.set()

last_panic_time = None 

def now():
    return datetime.datetime.now().strftime("%-d.%m.%y %H:%M")

async def send(msg):
    await bot.send_message(CHANNEL_ID, f"{now()} | {msg}")

async def sticker_goodbye():
    await bot.send_sticker(CHANNEL_ID, sticker='CAACAgIAAxkBAAEOtS9oT-mofCuD2UQYpMQoXesiJb0IwQACIBAAAjnv6EnsxqRNmVO_mTYE')

async def sticker_server():
    await bot.send_sticker(CHANNEL_ID, sticker='CAACAgIAAxkBAAEOt9BoUUxTwjcIc6U4U8hhrGBaH7ZXJAACq04AAnJrGEm88RKLlho8-DYE')

@dp.message(Command('monitoring'))
async def monitoring_command(message: Message):
    status = "🟢 ВКЛЮЧЁН" if monitoring_enabled.is_set() else "🔴 ВЫКЛЮЧЕН (техработы)"
    panic = last_panic_time if last_panic_time else "– ещё не было"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔧 Включить тех работы", callback_data="monitoring_off")],
        [InlineKeyboardButton(text="✅ Завершить тех работы", callback_data="monitoring_on")]
    ])

    text = f"❤️‍🔥 <b>AquaBank Heartbeat</b>\n\n" \
           f"📅 Последняя паника: <b>{panic}</b>\n" \
           f"⚙️ Статус мониторинга: <b>{status}</b>"

    await message.answer(text, parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data.in_(['monitoring_on', 'monitoring_off']))
async def monitoring_buttons(callback: types.CallbackQuery):
    if callback.data == 'monitoring_off':
        if not monitoring_enabled.is_set():
            await callback.answer("Техработы уже включены", show_alert=True)
            return
        monitoring_enabled.clear()
        await send("🔧 Начались технические работы на сервере. AquaBank будет недоступен некоторое время")
        await sticker_server()
        await callback.answer("Техработы включены ✅")

    elif callback.data == 'monitoring_on':
        if monitoring_enabled.is_set():
            await callback.answer("Мониторинг уже включён", show_alert=True)
            return
        monitoring_enabled.set()
        await send("✅ Технические работы завершены. AquaBank снова доступен")
        await callback.answer("Мониторинг включён ✅")

    await monitoring_command(callback.message)

async def monitor_server():
    global last_panic_time
    connected = True
    status_500 = False

    while True:
        await monitoring_enabled.wait()

        try:
            r = requests.get(URL, timeout=5)
            if r.status_code == 200:
                if not connected:
                    await send("✅ Соединение с сервером восстановлено")
                    connected = True
                if status_500:
                    await send("✅ Сервер вернул статус 200")
                    status_500 = False
                await asyncio.sleep(10)

            elif r.status_code == 500:
                await send("🍽️ Сервер вернул статус 500")
                status_500 = True
                await asyncio.sleep(10)

            else:
                await send(f"⚠️ Неожиданный статус: {r.status_code}")
                await asyncio.sleep(10)

        except requests.RequestException:
            if connected:
                await send("⚠️ Перебой в работе")
                last_panic_time = now()
                connected = False

            for i in range(5):
                if not monitoring_enabled.is_set():
                    break
                await send(f"⚠️⏳ Попытка вернуть соединение с сервером, {i+1} из 5")
                try:
                    r = requests.get(URL, timeout=5)
                    if r.status_code == 200:
                        await send("✅ Соединение с сервером восстановлено")
                        connected = True
                        break
                    elif r.status_code == 500:
                        await send("🍽️ Сервер вернул статус 500")
                        status_500 = True
                except:
                    pass
                await asyncio.sleep(10)

            if not connected and monitoring_enabled.is_set():
                await send("❌ Сервер aquabank умер")
                await sticker_goodbye()

                while monitoring_enabled.is_set():
                    await asyncio.sleep(5)
                    try:
                        r = requests.get(URL, timeout=5)
                        if r.status_code == 200:
                            await send("✅ Соединение с сервером восстановлено")
                            connected = True
                            break
                        elif r.status_code == 500:
                            await send("🍽️ Сервер вернул статус 500")
                            status_500 = True
                    except:
                        pass

async def main():
    asyncio.create_task(monitor_server())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())