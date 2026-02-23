from datetime import datetime

from app.db.crud import _is_overlap


def test_overlap_true() -> None:
    start_a = datetime(2026, 1, 1, 18, 0)
    start_b = datetime(2026, 1, 1, 19, 0)
    assert _is_overlap(start_a, 120, start_b, 120) is True


def test_overlap_false() -> None:
    start_a = datetime(2026, 1, 1, 18, 0)
    start_b = datetime(2026, 1, 1, 20, 0)
    assert _is_overlap(start_a, 120, start_b, 120) is False

