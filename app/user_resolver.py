class AllUsersNotFoundError(Exception):
    """全てのユーザーが見つからなかった場合の例外"""

    pass


def resolve_users(slack_client, email_list):
    user_ids = []
    not_found_emails = []

    for email in email_list:
        response = slack_client.users_lookupByEmail(email)
        if response["ok"] and not response["user"]["deleted"]:
            user_ids.append(response["user"]["id"])
        else:
            not_found_emails.append(email)

    # 全員が見つからなかった場合は例外を発生
    if len(user_ids) == 0 and len(not_found_emails) > 0:
        raise AllUsersNotFoundError("All users not found")

    return user_ids, not_found_emails
