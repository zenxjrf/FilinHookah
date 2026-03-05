from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


def main_menu_keyboard(webapp_url: str) -> InlineKeyboardMarkup:
    # Всегда создаём WebApp кнопки
    open_app_button = InlineKeyboardButton(
        text="🦉 Открыть мини-приложение",
        web_app=WebAppInfo(url=webapp_url),
    )
    call_button = InlineKeyboardButton(
        text="📞 Забронировать стол (звонок)",
        url="tel:+79504333434",
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [open_app_button],
            [call_button],
            [
                InlineKeyboardButton(text="🎁 Акции", callback_data="promotions"),
                InlineKeyboardButton(text="🕐 График", callback_data="schedule"),
            ],
            [
                InlineKeyboardButton(text="📍 Контакты", callback_data="contacts"),
                InlineKeyboardButton(text="🦉 Меню", callback_data="hookah_menu"),
            ],
            [
                InlineKeyboardButton(text="💎 Бонусы", callback_data="loyalty"),
            ],
        ]
    )
