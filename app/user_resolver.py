from app.infrastructure.slack_client import SlackClient


class AllUsersNotFoundError(Exception):
    """全てのユーザーが見つからなかった場合の例外"""

    pass


def _extract_display_name(user_data):
    """ユーザーデータから表示名を抽出（空文字の場合はユーザーIDを使用）"""
    return user_data.get("profile", {}).get("display_name", "") or user_data["id"]


def _process_user_email(slack_api: SlackClient, email):
    """メールアドレスからユーザー情報を取得"""
    try:
        response = slack_api.lookup_user_by_email(email=email)
        if response["ok"] and not response["user"]["deleted"]:
            user_data = response["user"]
            display_name = _extract_display_name(user_data)
            return {"id": user_data["id"], "display_name": display_name}, None
        else:
            return None, email
    except Exception:
        return None, email


def resolve_users(slack_client, email_list):
    user_info_list = []
    not_found_emails = []
    api = SlackClient(slack_client)

    for email in email_list:
        user_info, not_found_email = _process_user_email(api, email)
        if user_info:
            user_info_list.append(user_info)
        if not_found_email:
            not_found_emails.append(not_found_email)

    # 全員が見つからなかった場合は例外を発生
    if not user_info_list and not_found_emails:
        raise AllUsersNotFoundError("All users not found")

    return user_info_list, not_found_emails
