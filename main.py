
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import logging

API_TOKEN = '8179992230:AAEfAZTD6MYyHWgESBvaB3_sur85Qrn9Chk'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

conn = sqlite3.connect('orders.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS orders
             (id INTEGER PRIMARY KEY, description TEXT, accepted_by TEXT, price INTEGER)''')
conn.commit()

# Команда додавання замовлення
@dp.message_handler(commands=['add'])
async def add_order(message: types.Message):
    text = message.get_args()
    if not text:
        await message.reply("Напиши опис замовлення: /add Заміна розетки")
        return

    c.execute("INSERT INTO orders (description, accepted_by, price) VALUES (?, ?, ?)", (text, None, None))
    order_id = c.lastrowid
    conn.commit()

    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✅ Прийняти", callback_data=f"accept_{order_id}")
    )
    await bot.send_message(chat_id='@your_channel_username', text=f"🔧 ЗАМОВЛЕННЯ #{order_id}
{text}", reply_markup=keyboard)

# Прийняття замовлення
@dp.callback_query_handler(lambda c: c.data.startswith('accept_'))
async def accept_order(callback_query: types.CallbackQuery):
    order_id = int(callback_query.data.split("_")[1])
    username = callback_query.from_user.username or callback_query.from_user.full_name

    c.execute("SELECT accepted_by FROM orders WHERE id=?", (order_id,))
    row = c.fetchone()
    if row and row[0]:
        await callback_query.answer("Це замовлення вже хтось взяв!", show_alert=True)
        return

    c.execute("UPDATE orders SET accepted_by=? WHERE id=?", (username, order_id))
    conn.commit()

    await callback_query.message.edit_reply_markup(reply_markup=None)
    await bot.send_message(callback_query.from_user.id, f"🔒 Ви прийняли замовлення #{order_id}")
    await callback_query.answer("Замовлення прийнято!")

# Завершення замовлення
@dp.message_handler(commands=['done'])
async def finish_order(message: types.Message):
    args = message.get_args().split()
    if len(args) != 2:
        await message.reply("Приклад: /done 5 1200")
        return

    order_id, price = args
    username = message.from_user.username or message.from_user.full_name

    c.execute("SELECT accepted_by FROM orders WHERE id=?", (order_id,))
    row = c.fetchone()
    if not row:
        await message.reply("Замовлення не знайдено.")
        return

    if row[0] != username:
        await message.reply("Це замовлення приймав інший майстер.")
        return

    c.execute("UPDATE orders SET price=? WHERE id=?", (price, order_id))
    conn.commit()
    await message.reply(f"✅ Замовлення #{order_id} завершено. Зароблено {price} грн.")

# Список всіх замовлень
@dp.message_handler(commands=['all'])
async def list_orders(message: types.Message):
    c.execute("SELECT * FROM orders")
    orders = c.fetchall()
    if not orders:
        await message.reply("Немає замовлень.")
        return

    text = ""
    for o in orders:
        text += f"#{o[0]} | {o[1]}
Прийняв: {o[2] or '❌'} | Сума: {o[3] or '❌'} грн

"
    await message.reply(text)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
