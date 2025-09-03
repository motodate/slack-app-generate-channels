"""
仕様: Slackユーザーの解決
"""


class FakeSlackClient:
    """SlackAPIクライアントのモック実装"""

    def __init__(self, user_db=None):
        # メールアドレス -> ユーザー情報のマッピング
        self.user_db = user_db or {}

    def users_lookupByEmail(self, email):
        """users.lookupByEmail APIのモック"""
        if email in self.user_db:
            user_info = self.user_db[email]
            return {
                "ok": True,
                "user": {
                    "id": user_info["id"],
                    "deleted": user_info.get("deleted", False),
                    "profile": {"display_name": user_info.get("display_name", "")},
                },
            }
        else:
            return {"ok": False, "error": "users_not_found"}


def test_resolve_existing_emails_returns_user_ids_and_empty_not_found():
    """正常系: 存在するメールアドレスのリストを渡すと、
    SlackユーザーIDのリストと「見つからなかったメールアドレス」の空リストが返ってくる"""
    from app.user_resolver import resolve_users

    # テストデータ：存在するユーザー
    fake_client = FakeSlackClient(
        {"user1@example.com": {"id": "U1234"}, "user2@example.com": {"id": "U5678"}}
    )

    email_list = ["user1@example.com", "user2@example.com"]
    user_info_list, not_found_emails = resolve_users(fake_client, email_list)

    # 期待結果：見つかったユーザー情報のリストと、見つからなかったメールアドレスの空リスト
    assert len(user_info_list) == 2
    assert user_info_list[0]["id"] == "U1234"
    assert user_info_list[1]["id"] == "U5678"
    assert not_found_emails == []


def test_resolve_mixed_emails_returns_found_ids_and_not_found_list():
    """一部不在: 存在しないメールアドレスが含まれている場合、
    見つかったユーザーIDのリストと、見つからなかったメールアドレスのリストが正しく返ってくる"""
    from app.user_resolver import resolve_users

    # テストデータ：1つは存在、1つは存在しない
    fake_client = FakeSlackClient(
        {
            "user1@example.com": {"id": "U1234"}
            # user2@example.com は存在しない
        }
    )

    email_list = ["user1@example.com", "user2@example.com"]
    user_info_list, not_found_emails = resolve_users(fake_client, email_list)

    # 期待結果：見つかったユーザーと見つからなかったメールの両方が返る
    assert len(user_info_list) == 1
    assert user_info_list[0]["id"] == "U1234"
    assert not_found_emails == ["user2@example.com"]


def test_resolve_all_not_found_raises_exception():
    """全員不在: 渡されたメールアドレスがすべて存在しない場合、
    「全員が見つからなかった」ことを示す特別な状態（例外）が返ってくる"""
    import pytest

    from app.user_resolver import AllUsersNotFoundError, resolve_users

    # テストデータ：全て存在しない
    fake_client = FakeSlackClient({})

    email_list = ["user1@example.com", "user2@example.com"]

    # 期待結果：AllUsersNotFoundError例外が発生
    with pytest.raises(AllUsersNotFoundError, match="All users not found"):
        resolve_users(fake_client, email_list)


def test_resolve_deleted_users_treated_as_not_found():
    """退会済み: 退会・無効化されたユーザーのメールアドレスは、
    「見つからなかったメールアドレス」として扱われる"""
    from app.user_resolver import resolve_users

    # テストデータ：1つは有効、1つは削除済み
    fake_client = FakeSlackClient(
        {
            "active@example.com": {"id": "U1234", "deleted": False},
            "deleted@example.com": {"id": "U5678", "deleted": True},
        }
    )

    email_list = ["active@example.com", "deleted@example.com"]
    user_info_list, not_found_emails = resolve_users(fake_client, email_list)

    # 期待結果：削除済みユーザーは見つからなかったメールとして扱う
    assert len(user_info_list) == 1
    assert user_info_list[0]["id"] == "U1234"
    assert not_found_emails == ["deleted@example.com"]


def test_resolve_users_handles_api_errors():
    """APIエラー: Slack API呼び出しでエラーが発生した場合、適切に処理される"""
    import pytest
    from slack_sdk.errors import SlackApiError

    from app.user_resolver import AllUsersNotFoundError, resolve_users

    class ErrorSlackClient:
        def users_lookupByEmail(self, email):
            # Slack APIエラーをシミュレート
            raise SlackApiError(
                "The request to the Slack API failed", response={"error": "user_not_found"}
            )

    error_client = ErrorSlackClient()
    email_list = ["error@example.com"]

    # 期待結果：APIエラーで全員見つからない場合、AllUsersNotFoundError例外が発生
    with pytest.raises(AllUsersNotFoundError, match="All users not found"):
        resolve_users(error_client, email_list)


def test_resolve_users_returns_user_info_with_display_names():
    """表示名取得: ユーザー解決時に表示名付きのユーザー情報が返される"""
    from app.user_resolver import resolve_users

    # テストデータ：表示名付きのユーザー
    fake_client = FakeSlackClient(
        {
            "user1@example.com": {"id": "U1234", "display_name": "田中太郎"},
            "user2@example.com": {"id": "U5678", "display_name": "佐藤花子"},
        }
    )

    email_list = ["user1@example.com", "user2@example.com"]
    user_info_list, not_found_emails = resolve_users(fake_client, email_list)

    # 期待結果：表示名付きのユーザー情報が返される
    assert len(user_info_list) == 2
    assert not_found_emails == []

    # 最初のユーザー
    assert user_info_list[0]["id"] == "U1234"
    assert user_info_list[0]["display_name"] == "田中太郎"

    # 2番目のユーザー
    assert user_info_list[1]["id"] == "U5678"
    assert user_info_list[1]["display_name"] == "佐藤花子"
