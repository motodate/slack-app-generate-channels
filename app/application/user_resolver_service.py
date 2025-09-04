from typing import TYPE_CHECKING, Any, Dict, List, Protocol, Sequence, Tuple, Union

if TYPE_CHECKING:  # for typing only
    from app.domain.email_address_list import EmailAddressList


class SlackAPIProtocol(Protocol):
    def lookup_user_by_email(self, email: str) -> Dict[str, Any]: ...


class UserResolverService:
    """Resolve Slack users by emails using a SlackClient-like facade.

    The facade must expose `lookup_user_by_email(email)`.
    This service returns (user_info_list, not_found_emails) and leaves
    policy (e.g., raising exceptions) to the wrapper for compatibility.
    """

    def __init__(self, slack_api: SlackAPIProtocol):
        self._api = slack_api

    @staticmethod
    def _extract_display_name(user_data):
        return user_data.get("profile", {}).get("display_name", "") or user_data["id"]

    def _process_email(self, email: str) -> Tuple[Dict[str, str] | None, str | None]:
        try:
            response = self._api.lookup_user_by_email(email=email)
            if response.get("ok") and not response["user"].get("deleted", False):
                user = response["user"]
                display_name = self._extract_display_name(user)
                return {"id": user["id"], "display_name": display_name}, None
            return None, email
        except Exception:
            return None, email

    def resolve(
        self, email_list: Union["EmailAddressList", Sequence[str]]
    ) -> Tuple[List[dict], List[str]]:
        # Accept EmailAddressList or plain sequence[str]
        emails: Sequence[str] = getattr(email_list, "values", email_list)

        users: List[dict] = []
        not_found: List[str] = []

        for email in emails:
            info, nf = self._process_email(email)
            if info:
                users.append(info)
            if nf:
                not_found.append(nf)

        return users, not_found
