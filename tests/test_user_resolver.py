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
                "user": {"id": user_info["id"], "deleted": user_info.get("deleted", False)},
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
    user_ids, not_found_emails = resolve_users(fake_client, email_list)

    # 期待結果：見つかったユーザーIDのリストと、見つからなかったメールアドレスの空リスト
    assert user_ids == ["U1234", "U5678"]
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
    user_ids, not_found_emails = resolve_users(fake_client, email_list)

    # 期待結果：見つかったユーザーと見つからなかったメールの両方が返る
    assert user_ids == ["U1234"]
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
    user_ids, not_found_emails = resolve_users(fake_client, email_list)

    # 期待結果：削除済みユーザーは見つからなかったメールとして扱う
    assert user_ids == ["U1234"]
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
