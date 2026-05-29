from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 баланс"), KeyboardButton(text="📝 Создать сделку")],
            [KeyboardButton(text="📋 Мои сделки"), KeyboardButton(text="🏦 Реквизиты")],
            [KeyboardButton(text="❓ Помощь"), KeyboardButton(text="💸 Вывод")],
            [KeyboardButton(text="🛠 Тех.поддержка")]
        ],
        resize_keyboard=True
    )
    return kb

def back_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="◀️ Назад в меню")]],
        resize_keyboard=True
    )
    return kb

def role_buttons():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👑 Продавец", callback_data="role_seller")],
        [InlineKeyboardButton(text="🛒 Покупатель", callback_data="role_buyer")]
    ])
    return kb

def currency_buttons():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 USDT", callback_data="cur_USDT")],
        [InlineKeyboardButton(text="🇷🇺 RUB", callback_data="cur_RUB")],
        [InlineKeyboardButton(text="🪙 TON", callback_data="cur_TON")],
        [InlineKeyboardButton(text="⭐ STAR", callback_data="cur_STAR")]
    ])
    return kb

def rekv_types():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Карта (RUB)", callback_data="rekv_RUB")],
        [InlineKeyboardButton(text="🪙 Криптокошелек (TON)", callback_data="rekv_TON")],
        [InlineKeyboardButton(text="💵 Кошелек (USDT)", callback_data="rekv_USDT")],
        [InlineKeyboardButton(text="👤 Username (STARS)", callback_data="rekv_STAR")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="rekv_back")]
    ])
    return kb

def rekv_manage_buttons(currency, has_rekv):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    if has_rekv:
        kb.inline_keyboard.append([InlineKeyboardButton(text="✏️ Изменить реквизиты", callback_data=f"rekv_edit_{currency}")])
        kb.inline_keyboard.append([InlineKeyboardButton(text="🗑 Удалить реквизиты", callback_data=f"rekv_delete_{currency}")])
    else:
        kb.inline_keyboard.append([InlineKeyboardButton(text="➕ Добавить реквизиты", callback_data=f"rekv_add_{currency}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="rekv_back_main")])
    return kb

def payment_confirmation_kb():
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Я оплатил")], [KeyboardButton(text="◀️ Назад в меню")]],
        resize_keyboard=True
    )
    return kb

def product_sent_kb():
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📦 Товар передан")], [KeyboardButton(text="◀️ Назад в меню")]],
        resize_keyboard=True
    )
    return kb

def cancel_deal_kb(deal_number):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить сделку", callback_data=f"cancel_deal_{deal_number}")]
    ])
    return kb


def admin_panel_kb():
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="👑 Админ панель")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return kb