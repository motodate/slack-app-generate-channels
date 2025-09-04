"""
Presentation: modal_builder functions
"""


def test_build_initial_modal_structure():
    from app.presentation.modal_builder import build_initial_modal

    view = build_initial_modal()
    assert view["type"] == "modal"
    assert view["callback_id"] == "channel_creation_modal"
    assert "チャンネル作成" in view["title"]["text"]


def test_build_confirmation_modal_includes_channel_users_and_optionally_not_found():
    from app.presentation.modal_builder import build_confirmation_modal

    view = build_confirmation_modal(
        channel_name="test-channel",
        users=[{"id": "U111", "display_name": "太郎"}],
        not_found_emails=["nf@example.com"],
        private_metadata_json='{"channel_name": "test-channel", "user_ids": ["U111"]}',
    )
    assert view["type"] == "modal"
    assert view["callback_id"] == "channel_creation_confirmation"
    blocks_text = str(view["blocks"])
    assert "test-channel" in blocks_text
    assert "太郎" in blocks_text
    assert "nf@example.com" in blocks_text


def test_build_processing_modal_and_success_and_error():
    from app.presentation.modal_builder import (
        build_error_modal,
        build_processing_modal,
        build_success_modal,
    )

    processing = build_processing_modal()
    assert processing["type"] == "modal"
    assert "作成中" in processing["title"]["text"]

    success = build_success_modal("chan")
    assert "chan" in str(success["blocks"]) and "完了" in success["title"]["text"]

    error = build_error_modal("oops")
    assert "エラー" in error["title"]["text"]
    assert "oops" in str(error["blocks"])
