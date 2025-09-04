"""
振る舞いテスト: SlackClient が下位の WebClient に正しく委譲する
"""

from unittest.mock import Mock

from app.infrastructure.slack_client import SlackClient


def test_open_view_delegates_to_web_client():
    """委譲: `open_view()` が `views_open` に引数をそのまま渡す"""
    web = Mock()
    sc = SlackClient(web)

    sc.open_view(trigger_id="T123", view={"type": "modal"})

    web.views_open.assert_called_once_with(trigger_id="T123", view={"type": "modal"})


def test_update_view_delegates_to_web_client():
    """委譲: `update_view()` が `views_update` に引数をそのまま渡す"""
    web = Mock()
    sc = SlackClient(web)

    sc.update_view(view_id="V123", view={"type": "modal"})

    web.views_update.assert_called_once_with(view_id="V123", view={"type": "modal"})


def test_create_channel_delegates_to_conversations_create_and_returns_response():
    """委譲: `create_channel()` が `conversations_create` を呼び、レスポンスを返す"""
    web = Mock()
    web.conversations_create.return_value = {"ok": True, "channel": {"id": "C1"}}
    sc = SlackClient(web)

    resp = sc.create_channel(name="my-channel", is_private=True)

    web.conversations_create.assert_called_once_with(name="my-channel", is_private=True)
    assert resp["channel"]["id"] == "C1"


def test_invite_users_joins_ids_and_delegates():
    """整形+委譲: user_ids をカンマ連結し `conversations_invite` に渡す"""
    web = Mock()
    sc = SlackClient(web)

    sc.invite_users(channel_id="C1", user_ids=["U1", "U2", "U3"])

    web.conversations_invite.assert_called_once_with(channel="C1", users="U1,U2,U3")


def test_post_message_delegates_to_chat_postMessage():
    """委譲: `post_message()` が `chat_postMessage` を呼び出す"""
    web = Mock()
    sc = SlackClient(web)

    sc.post_message(channel="U1", text="hi")

    web.chat_postMessage.assert_called_once_with(channel="U1", text="hi")


def test_lookup_user_by_email_delegates():
    """委譲: `lookup_user_by_email()` が `users_lookupByEmail` を呼び出す"""
    web = Mock()
    sc = SlackClient(web)

    sc.lookup_user_by_email(email="user@example.com")

    web.users_lookupByEmail.assert_called_once_with(email="user@example.com")
