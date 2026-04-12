"""Auto task descriptions without description_user_set are cleared on API read."""
from app.api.v1.endpoints.tasks import _should_clear_non_user_auto_task_description


def test_clear_when_auto_no_user_set_and_nonempty():
    assert _should_clear_non_user_auto_task_description("any junk", True, False) is True


def test_keep_when_auto_and_user_set():
    assert _should_clear_non_user_auto_task_description("User note", True, True) is False


def test_keep_when_auto_no_user_set_but_empty_description():
    assert _should_clear_non_user_auto_task_description(None, True, False) is False
    assert _should_clear_non_user_auto_task_description("", True, False) is False
    assert _should_clear_non_user_auto_task_description("   ", True, False) is False


def test_keep_when_not_auto_even_with_junk():
    assert _should_clear_non_user_auto_task_description("=== Meeting meeting_id=x ===", False, False) is False


def test_short_stt_still_cleared_without_user_set():
    assert _should_clear_non_user_auto_task_description(
        "Kartik ready will support the and database optimization", True, False
    ) is True
