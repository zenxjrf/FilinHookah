from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def booking_actions_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    """Клавиатура с действиями для брони."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить",
                    callback_data=f"booking_confirm_{booking_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=f"booking_cancel_{booking_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🟢 Закрыть (клиент ушел)",
                    callback_data=f"booking_close_{booking_id}",
                ),
            ],
        ]
    )


def booking_minimal_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    """Минимальная клавиатура для завершенных броней."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🟢 Закрыть",
                    callback_data=f"booking_close_{booking_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=f"booking_cancel_{booking_id}",
                ),
            ],
        ]
    )
