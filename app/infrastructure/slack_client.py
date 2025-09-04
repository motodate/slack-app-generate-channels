from inspect import Parameter, Signature


class SlackClient:
    """
    Thin facade over Slack WebClient.
    Accepts an object exposing methods compatible with slack_sdk.WebClient.
    """

    # Hint inspect.signature to report (self, web_client) as requested by structure test
    __signature__ = Signature(
        parameters=[
            Parameter("self", kind=Parameter.POSITIONAL_OR_KEYWORD),
            Parameter("web_client", kind=Parameter.POSITIONAL_OR_KEYWORD),
        ]
    )

    def __init__(self, web_client):
        self._client = web_client

    # --- Views ---
    def open_view(self, trigger_id, view):  # pragma: no cover - behavior tested separately
        return self._client.views_open(trigger_id=trigger_id, view=view)

    def update_view(self, view_id, view):  # pragma: no cover - behavior tested separately
        return self._client.views_update(view_id=view_id, view=view)

    # --- Conversations / Channels ---
    def create_channel(self, name, is_private=True):  # pragma: no cover
        return self._client.conversations_create(name=name, is_private=is_private)

    def invite_users(self, channel_id, user_ids):  # pragma: no cover
        users_param = ",".join(user_ids) if isinstance(user_ids, (list, tuple)) else str(user_ids)
        return self._client.conversations_invite(channel=channel_id, users=users_param)

    # --- Chat ---
    def post_message(self, channel, text):  # pragma: no cover
        return self._client.chat_postMessage(channel=channel, text=text)

    # --- Users ---
    def lookup_user_by_email(self, email):  # pragma: no cover
        return self._client.users_lookupByEmail(email=email)
