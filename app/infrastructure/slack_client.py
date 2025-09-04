from typing import Any, Dict, List


class SlackClient:
    """
    Thin facade over Slack WebClient.
    Accepts an object exposing methods compatible with slack_sdk.WebClient.
    """

    def __init__(self, web_client: Any):
        self._client = web_client

    # --- Views ---
    def open_view(
        self, trigger_id: str, view: Dict[str, Any]
    ) -> Dict[str, Any]:  # pragma: no cover - behavior tested separately
        return self._client.views_open(trigger_id=trigger_id, view=view)

    def update_view(
        self, view_id: str, view: Dict[str, Any]
    ) -> Dict[str, Any]:  # pragma: no cover - behavior tested separately
        return self._client.views_update(view_id=view_id, view=view)

    # --- Conversations / Channels ---
    def create_channel(
        self, name: str, is_private: bool = True
    ) -> Dict[str, Any]:  # pragma: no cover
        return self._client.conversations_create(name=name, is_private=is_private)

    def invite_users(
        self, channel_id: str, user_ids: List[str] | str
    ) -> Dict[str, Any]:  # pragma: no cover
        users_param = ",".join(user_ids) if isinstance(user_ids, (list, tuple)) else str(user_ids)
        return self._client.conversations_invite(channel=channel_id, users=users_param)

    # --- Chat ---
    def post_message(self, channel: str, text: str) -> Dict[str, Any]:  # pragma: no cover
        return self._client.chat_postMessage(channel=channel, text=text)

    # --- Users ---
    def lookup_user_by_email(self, email: str) -> Dict[str, Any]:  # pragma: no cover
        return self._client.users_lookupByEmail(email=email)
