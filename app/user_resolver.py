from app.infrastructure.slack_client import SlackClient


class AllUsersNotFoundError(Exception):
    """全てのユーザーが見つからなかった場合の例外"""

    pass


def resolve_users(slack_client, email_list):
    """互換APIを維持したラッパー: 内部でサービスを呼び出す"""
    from app.application.user_resolver_service import UserResolverService
    from app.domain.email_address_list import EmailAddressList

    api = SlackClient(slack_client)
    service = UserResolverService(slack_api=api)
    user_info_list, not_found_emails = service.resolve(EmailAddressList(email_list))

    # 全員が見つからなかった場合は例外を発生（従来仕様）
    if not user_info_list and not_found_emails:
        raise AllUsersNotFoundError("All users not found")

    return user_info_list, not_found_emails
