from typing import List, Union

try:  # for type checkers only; avoids runtime import cycle
    from app.domain.channel_name import ChannelName  # noqa: F401
except Exception:  # pragma: no cover - type hint only
    ChannelName = object  # type: ignore


class ChannelCreationService:
    """Create a private channel and invite users via SlackClient facade.

    Exceptions are not caught here; UI layer is responsible for user-facing messages.
    """

    def __init__(self, slack_api):
        self._api = slack_api

    def create_private_channel(self, name: Union[str, "ChannelName"], user_ids: List[str]) -> str:
        channel_name = name.value if hasattr(name, "value") else name
        resp = self._api.create_channel(name=channel_name, is_private=True)
        channel_id = resp["channel"]["id"]
        if user_ids:
            self._api.invite_users(channel_id=channel_id, user_ids=user_ids)
        return channel_id
