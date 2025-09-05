"""
仕様: Slack BoltアプリのUI/インタラクション機能
"""

import json
from unittest.mock import Mock

from slack_bolt import BoltRequest
from slack_sdk.errors import SlackApiError


class MockBoltRequest(BoltRequest):
    """テスト用のBoltRequestモック"""

    def __init__(self, body_dict):
        # 親の初期化をスキップし、必要な属性のみ設定
        self.body = body_dict
        self.context = {}


def test_shortcut_triggers_initial_channel_creation_modal():
    """起動: ショートカットが実行されると、初期のチャンネル作成モーダルが正しく表示される"""
    # ハンドラー関数を直接テスト（Appインスタンス化をスキップ）
    from app.slack_app import handle_shortcut

    # ack()とclientのモック
    ack = Mock()
    client = Mock()
    shortcut = {
        "type": "shortcut",
        "callback_id": "create_channel_shortcut",
        "user": {"id": "U123456"},
        "trigger_id": "123456.987654.abcdef",
    }

    # ハンドラー関数を直接実行
    handle_shortcut(ack=ack, shortcut=shortcut, client=client)

    # 期待結果：ack()が呼ばれ、初期モーダルが表示される
    ack.assert_called_once()
    client.views_open.assert_called_once()

    # モーダルの内容検証
    modal_call_args = client.views_open.call_args
    call_kwargs = modal_call_args[1] if modal_call_args[1] else modal_call_args[0][0]

    assert call_kwargs["trigger_id"] == "123456.987654.abcdef"

    view = call_kwargs["view"]
    assert view["type"] == "modal"
    assert "チャンネル作成" in view["title"]["text"]
    assert view["callback_id"] == "channel_creation_modal"


def test_modal_submission_integrates_user_resolution_and_confirmation_display():
    """統合テスト: フォーム送信→ユーザー解決→確認モーダル表示の完全フロー"""
    from unittest.mock import patch

    from app.slack_app import handle_modal_submission

    # ack()とclientのモック
    ack = Mock()
    client = Mock()
    view = {
        "id": "V123456",
        "callback_id": "channel_creation_modal",
        "state": {
            "values": {
                "channel_name_input": {"channel_name": {"value": "test-channel"}},
                "member_emails_input": {
                    "member_emails": {"value": "user1@example.com,user2@example.com"}
                },
            }
        },
    }
    body = {"user": {"id": "U123456"}, "trigger_id": "123456.987654.abcdef"}

    # UserResolverをモック化
    with patch("app.slack_app.resolve_users") as mock_resolve_users:
        mock_resolve_users.return_value = (
            [
                {"id": "U111", "display_name": "ユーザー1"},
                {"id": "U222", "display_name": "ユーザー2"},
            ],
            [],
        )

        # モーダル送信ハンドラーを実行
        handle_modal_submission(ack=ack, view=view, client=client, body=body)

    # 期待結果：ack()が呼ばれ、ユーザー解決処理が実行され、確認モーダルが表示される
    ack.assert_called_once()
    mock_resolve_users.assert_called_once_with(client, ["user1@example.com", "user2@example.com"])
    client.views_open.assert_called_once()

    # 確認モーダルの内容検証
    modal_call_args = client.views_open.call_args
    call_kwargs = modal_call_args[1] if modal_call_args[1] else modal_call_args[0][0]

    assert call_kwargs["trigger_id"] == "123456.987654.abcdef"

    view_data = call_kwargs["view"]
    assert view_data["type"] == "modal"
    assert "確認" in view_data["title"]["text"]
    assert view_data["callback_id"] == "channel_creation_confirmation"

    # チャンネル名とユーザー情報、確認ボタンが含まれていることを確認
    blocks = view_data["blocks"]
    assert len(blocks) > 0

    # チャンネル名、ユーザー情報、アクションボタンの存在確認
    channel_info_found = False
    user_info_found = False
    action_buttons_found = False

    for block in blocks:
        if "text" in block:
            text_content = block["text"]["text"]
            if "test-channel" in text_content:
                channel_info_found = True
            if "ユーザー1" in text_content or "ユーザー2" in text_content:
                user_info_found = True
        if block["type"] == "actions":
            action_buttons_found = True

    assert channel_info_found, "チャンネル名が確認モーダルに表示されていません"
    assert user_info_found, "ユーザー情報が確認モーダルに表示されていません"
    assert action_buttons_found, "確認ボタンが表示されていません"

    # private_metadataにチャンネル情報が保存されていることを確認
    import json

    metadata = json.loads(view_data["private_metadata"])
    assert metadata["channel_name"] == "test-channel"
    assert metadata["user_ids"] == ["U111", "U222"]


def test_modal_submission_with_not_found_emails():
    """統合テスト（不在ユーザーあり）: フォーム送信→ユーザー解決→不在メール一覧表示"""
    from unittest.mock import patch

    from app.slack_app import handle_modal_submission

    # ack()とclientのモック
    ack = Mock()
    client = Mock()
    view = {
        "id": "V123456",
        "callback_id": "channel_creation_modal",
        "state": {
            "values": {
                "channel_name_input": {"channel_name": {"value": "test-channel"}},
                "member_emails_input": {
                    "member_emails": {"value": "user1@example.com,notfound@example.com"}
                },
            }
        },
    }
    body = {"user": {"id": "U123456"}, "trigger_id": "123456.987654.abcdef"}

    # UserResolver：一部のユーザーが見つからない場合をモック化
    with patch("app.slack_app.resolve_users") as mock_resolve_users:
        mock_resolve_users.return_value = (
            [{"id": "U111", "display_name": "ユーザー1"}],
            ["notfound@example.com"],
        )

        # モーダル送信ハンドラーを実行
        handle_modal_submission(ack=ack, view=view, client=client, body=body)

    # 期待結果：ack()が呼ばれ、ユーザー解決処理が実行され、確認モーダルが表示される
    ack.assert_called_once()
    mock_resolve_users.assert_called_once_with(
        client, ["user1@example.com", "notfound@example.com"]
    )
    client.views_open.assert_called_once()

    # 確認モーダルの内容検証
    modal_call_args = client.views_open.call_args
    call_kwargs = modal_call_args[1] if modal_call_args[1] else modal_call_args[0][0]

    assert call_kwargs["trigger_id"] == "123456.987654.abcdef"

    view_data = call_kwargs["view"]
    assert view_data["type"] == "modal"
    assert "確認" in view_data["title"]["text"]

    # チャンネル名、見つかったユーザー、見つからなかったメールが含まれていることを確認
    blocks = view_data["blocks"]
    assert len(blocks) > 0

    # 各情報の存在確認
    channel_info_found = False
    user_info_found = False
    not_found_info_found = False
    action_buttons_found = False

    for block in blocks:
        if "text" in block:
            text_content = block["text"]["text"]
            if "test-channel" in text_content:
                channel_info_found = True
            if "ユーザー1" in text_content:
                user_info_found = True
            if "notfound@example.com" in text_content:
                not_found_info_found = True
        if block["type"] == "actions":
            action_buttons_found = True

    assert channel_info_found, "チャンネル名が確認モーダルに表示されていません"
    assert user_info_found, "見つかったユーザー情報が確認モーダルに表示されていません"
    assert not_found_info_found, "見つからなかったメール情報が確認モーダルに表示されていません"
    assert action_buttons_found, "確認ボタンが表示されていません"


def test_confirmation_button_successful_channel_creation():
    """確認ボタンアクション（成功）: ボタンクリック→作成中表示→チャンネル作成→完了表示→DM送信"""
    from app.slack_app import handle_confirmation_button

    # ack()とclientのモック
    ack = Mock()
    client = Mock()

    # 成功レスポンスを設定
    client.conversations_create.return_value = {"channel": {"id": "C987654321"}}
    client.conversations_invite.return_value = {"ok": True}
    client.chat_postMessage.return_value = {"ok": True}

    action = {"action_id": "confirm_creation"}
    body = {
        "user": {"id": "U123456"},
        "view": {
            "id": "V123456",
            "private_metadata": '{"channel_name": "test-channel", "user_ids": ["U111", "U222"]}',
        },
    }

    # 確認ボタンハンドラーを実行
    handle_confirmation_button(ack=ack, action=action, body=body, client=client)

    # 期待結果：ack()が呼ばれ、2回のモーダル更新が行われる（作成中→完了）
    ack.assert_called_once()
    assert client.views_update.call_count == 2

    # チャンネル作成とメンバー招待が実行される
    client.conversations_create.assert_called_once_with(name="test-channel", is_private=True)
    client.conversations_invite.assert_called_once_with(
        channel="C987654321", users="U111,U222,U123456"
    )

    # 完了通知DMが送信される
    client.chat_postMessage.assert_called()
    dm_call = client.chat_postMessage.call_args
    assert dm_call[1]["channel"] == "U123456"
    assert "test-channel" in dm_call[1]["text"]

    # 最終モーダルが完了状態になっている
    final_modal_call = client.views_update.call_args_list[-1]
    final_view = final_modal_call[1]["view"]
    assert "完了" in final_view["title"]["text"]
    assert "test-channel" in str(final_view["blocks"])


def test_confirmation_button_name_taken_error():
    """確認ボタンアクション（チャンネル名重複エラー）: name_takenエラー→エラー表示"""
    from app.slack_app import handle_confirmation_button

    # ack()とclientのモック
    ack = Mock()
    client = Mock()

    # name_takenエラーを設定
    error_response = SlackApiError("name_taken", {"error": "name_taken"})
    error_response.response = {"error": "name_taken"}
    client.conversations_create.side_effect = error_response

    action = {"action_id": "confirm_creation"}
    body = {
        "user": {"id": "U123456"},
        "view": {
            "id": "V123456",
            "private_metadata": '{"channel_name": "test-channel", "user_ids": ["U111", "U222"]}',
        },
    }

    # 確認ボタンハンドラーを実行
    handle_confirmation_button(ack=ack, action=action, body=body, client=client)

    # 期待結果：ack()が呼ばれ、2回のモーダル更新が行われる（作成中→エラー）
    ack.assert_called_once()
    assert client.views_update.call_count == 2

    # エラーモーダルが表示される
    error_modal_call = client.views_update.call_args_list[-1]
    error_view = error_modal_call[1]["view"]
    assert "エラー" in error_view["title"]["text"]
    assert "既に使用されています" in str(error_view["blocks"])


def test_confirmation_button_permission_error():
    """確認ボタンアクション（権限不足エラー）: 権限エラー→エラー表示→DM通知"""
    from app.slack_app import handle_confirmation_button

    # ack()とclientのモック
    ack = Mock()
    client = Mock()

    # 権限エラーを設定
    client.conversations_create.side_effect = Exception("permission denied")

    action = {"action_id": "confirm_creation"}
    body = {
        "user": {"id": "U123456"},
        "view": {
            "id": "V123456",
            "private_metadata": '{"channel_name": "test-channel", "user_ids": ["U111", "U222"]}',
        },
    }

    # 確認ボタンハンドラーを実行
    handle_confirmation_button(ack=ack, action=action, body=body, client=client)

    # 期待結果：ack()が呼ばれ、2回のモーダル更新が行われる（作成中→エラー）
    ack.assert_called_once()
    assert client.views_update.call_count == 2

    # エラーモーダルが表示される
    error_modal_call = client.views_update.call_args_list[-1]
    error_view = error_modal_call[1]["view"]
    assert "エラー" in error_view["title"]["text"]
    assert "権限がありません" in str(error_view["blocks"])

    # 権限不足DM通知が送信される
    client.chat_postMessage.assert_called()
    dm_call = client.chat_postMessage.call_args
    assert dm_call[1]["channel"] == "U123456"
    assert "権限がありません" in dm_call[1]["text"]


def test_modal_submission_uses_views_open_not_update():
    """モーダル送信時: views.updateではなくviews.openで新しいモーダルを表示する"""
    from unittest.mock import patch

    from app.slack_app import handle_modal_submission

    # ack()とclientのモック
    ack = Mock()
    client = Mock()
    view = {
        "id": "V123456",
        "callback_id": "channel_creation_modal",
        "state": {
            "values": {
                "channel_name_input": {"channel_name": {"value": "test-channel"}},
                "member_emails_input": {"member_emails": {"value": "user1@example.com"}},
            }
        },
    }
    body = {"user": {"id": "U123456"}, "trigger_id": "123456.987654.abcdef"}

    # UserResolverをモック化
    with patch("app.slack_app.resolve_users") as mock_resolve_users:
        mock_resolve_users.return_value = ([{"id": "U111", "display_name": "ユーザー1"}], [])

        # モーダル送信ハンドラーを実行
        handle_modal_submission(ack=ack, view=view, client=client, body=body)

    # 期待結果：views.updateではなくviews.openが呼ばれる
    ack.assert_called_once()
    client.views_update.assert_not_called()
    client.views_open.assert_called_once()

    # 新しいモーダルの内容検証
    modal_call_args = client.views_open.call_args
    call_kwargs = modal_call_args[1] if modal_call_args[1] else modal_call_args[0][0]

    assert call_kwargs["trigger_id"] == "123456.987654.abcdef"
    view_data = call_kwargs["view"]
    assert view_data["callback_id"] == "channel_creation_confirmation"


def test_modal_submission_handles_all_users_not_found_error():
    """全ユーザー不在エラー: AllUsersNotFoundError例外が発生した場合、エラーモーダルを表示する"""
    from unittest.mock import patch

    from app.slack_app import handle_modal_submission

    # ack()とclientのモック
    ack = Mock()
    client = Mock()
    view = {
        "id": "V123456",
        "callback_id": "channel_creation_modal",
        "state": {
            "values": {
                "channel_name_input": {"channel_name": {"value": "test-channel"}},
                "member_emails_input": {"member_emails": {"value": "notfound@example.com"}},
            }
        },
    }
    body = {"user": {"id": "U123456"}, "trigger_id": "123456.987654.abcdef"}

    # UserResolverで全ユーザー不在例外をモック化
    with patch("app.slack_app.resolve_users") as mock_resolve_users:
        from app.user_resolver import AllUsersNotFoundError

        mock_resolve_users.side_effect = AllUsersNotFoundError("All users not found")

        # モーダル送信ハンドラーを実行
        handle_modal_submission(ack=ack, view=view, client=client, body=body)

    # 期待結果：ack() が response_action="update" で返され、エラー表示に差し替えられる
    ack.assert_called_once()
    kwargs = ack.call_args.kwargs
    assert kwargs.get("response_action") == "update"
    view_data = kwargs.get("view")
    assert view_data and "エラー" in view_data["title"]["text"]
    assert "見つかりませんでした" in str(view_data["blocks"])
    # API側の views_update は呼ばれない（ackで差し替え）
    client.views_update.assert_not_called()


def test_confirmation_modal_shows_display_names_not_user_ids():
    """確認モーダル表示（表示名）: ユーザー解決後、
    解決されたユーザーがUserIDではなく表示名で表示される
    """
    from unittest.mock import patch

    from app.slack_app import handle_modal_submission

    # ack()とclientのモック
    ack = Mock()
    client = Mock()
    view = {
        "id": "V123456",
        "callback_id": "channel_creation_modal",
        "state": {
            "values": {
                "channel_name_input": {"channel_name": {"value": "test-channel"}},
                "member_emails_input": {"member_emails": {"value": "user1@example.com"}},
            }
        },
    }
    body = {"user": {"id": "U123456"}, "trigger_id": "123456.987654.abcdef"}

    # UserResolverをモック化して、表示名付きのユーザー情報を返す
    with patch("app.slack_app.resolve_users") as mock_resolve_users:
        mock_resolve_users.return_value = ([{"id": "U111", "display_name": "田中太郎"}], [])

        # モーダル送信ハンドラーを実行
        handle_modal_submission(ack=ack, view=view, client=client, body=body)

    # 期待結果：確認モーダルに表示名が表示される
    ack.assert_called_once()
    client.views_open.assert_called_once()

    # モーダルの内容検証
    modal_call_args = client.views_open.call_args
    call_kwargs = modal_call_args[1] if modal_call_args[1] else modal_call_args[0][0]

    view_data = call_kwargs["view"]
    blocks_text = str(view_data["blocks"])

    # UserID（U111）ではなく表示名（田中太郎）が表示されることを確認
    assert "田中太郎" in blocks_text
    assert "U111" not in blocks_text


def test_channel_creator_automatically_added_to_invite_list():
    """作成者自動参加: チャンネル作成者は自動的に招待リストに含まれる"""

    from app.slack_app import handle_confirmation_button

    # ack()とclientのモック
    ack = Mock()
    client = Mock()
    action = Mock()

    # private_metadataに作成者以外のユーザーIDのみ含まれる状況を設定
    metadata = {"channel_name": "test-channel", "user_ids": ["U111", "U222"]}
    body = {
        "user": {"id": "U123456"},  # 作成者のUserID
        "view": {"id": "V123456", "private_metadata": json.dumps(metadata)},
    }

    # チャンネル作成API成功をモック化
    client.conversations_create.return_value = {"ok": True, "channel": {"id": "C987654321"}}
    client.conversations_invite.return_value = {"ok": True}

    # 確認ボタンハンドラーを実行
    handle_confirmation_button(ack=ack, action=action, body=body, client=client)

    # 期待結果：作成者も招待リストに含まれる
    client.conversations_invite.assert_called_once()
    call_args = client.conversations_invite.call_args[1]
    invited_users = call_args["users"].split(",")

    # 作成者（U123456）が招待リストに含まれていることを確認
    assert "U123456" in invited_users
    # 元々のユーザーも含まれることを確認
    assert "U111" in invited_users
    assert "U222" in invited_users


def test_channel_creator_deduplication_when_explicitly_specified():
    """重複排除（作成者）: 作成者が明示的にメールアドレスリストに含まれている場合でも重複しない"""
    from unittest.mock import patch

    from app.slack_app import handle_modal_submission

    # ack()とclientのモック
    ack = Mock()
    client = Mock()
    view = {
        "id": "V123456",
        "callback_id": "channel_creation_modal",
        "state": {
            "values": {
                "channel_name_input": {"channel_name": {"value": "test-channel"}},
                "member_emails_input": {
                    "member_emails": {"value": "creator@example.com, user1@example.com"}
                },
            }
        },
    }
    body = {"user": {"id": "U123456"}, "trigger_id": "123456.987654.abcdef"}

    # UserResolverをモック化（作成者も含む）
    with patch("app.slack_app.resolve_users") as mock_resolve_users:
        mock_resolve_users.return_value = (
            [
                {"id": "U123456", "display_name": "作成者"},  # 作成者
                {"id": "U111", "display_name": "田中太郎"},
            ],
            [],
        )

        # モーダル送信ハンドラーを実行
        handle_modal_submission(ack=ack, view=view, client=client, body=body)

    # private_metadataから作成者の重複が排除されていることを確認
    modal_call_args = client.views_open.call_args
    call_kwargs = modal_call_args[1] if modal_call_args[1] else modal_call_args[0][0]

    import json

    metadata = json.loads(call_kwargs["view"]["private_metadata"])
    user_ids = metadata["user_ids"]

    # 作成者が1回だけ含まれることを確認（重複しない）
    creator_count = user_ids.count("U123456")
    assert creator_count == 1


def test_cancel_button_updates_modal_back_to_initial():
    """キャンセルボタン: 入力モーダルに差し替える（views_update を使う）"""
    from app.slack_app import handle_cancel_button

    ack = Mock()
    client = Mock()
    action = {"action_id": "cancel_creation"}
    body = {"user": {"id": "U123456"}, "view": {"id": "V123456"}}

    handle_cancel_button(ack=ack, action=action, body=body, client=client)

    # ack され、views_update が呼ばれることを検証
    ack.assert_called_once()
    client.views_update.assert_called_once()
    args, kwargs = client.views_update.call_args
    assert kwargs["view"]["callback_id"] == "channel_creation_modal"
    client.conversations_create.assert_not_called()
    client.conversations_invite.assert_not_called()
