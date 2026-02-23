from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


def main_menu_keyboard(webapp_url: str) -> InlineKeyboardMarkup:
    if webapp_url.lower().startswith("https://"):
        open_app_button = InlineKeyboardButton(
            text="Открыть мини-приложение",
            web_app=WebAppInfo(url=webapp_url),
        )
        booking_button = InlineKeyboardButton(
            text="Забронировать",
            web_app=WebAppInfo(url=webapp_url),
        )
    else:
        open_app_button = InlineKeyboardButton(
            text="Открыть мини-приложение",
            callback_data="booking_link_unavailable",
        )
        booking_button = InlineKeyboardButton(
            text="Забронировать",
            callback_data="booking_link_unavailable",
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [open_app_button],
            [
                InlineKeyboardButton(text="🎁 Акции", callback_data="promotions"),
                InlineKeyboardButton(text="🕐 График", callback_data="schedule"),
            ],
            [
                InlineKeyboardButton(text="📍 Контакты", callback_data="contacts"),
                InlineKeyboardButton(text="🦉 Меню", callback_data="hookah_menu"),
            ],
            [booking_button],
            [
                InlineKeyboardButton(text="📋 Мои брони", callback_data="my_bookings"),
                InlineKeyboardButton(text="💎 Бонусы", callback_data="loyalty"),
            ],
        ]
    )
