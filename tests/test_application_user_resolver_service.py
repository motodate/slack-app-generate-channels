"""
Application: UserResolverService
"""

from typing import Any, Dict

from slack_sdk.errors import SlackApiError


class FacadeStub:
    """Minimal facade stub exposing lookup_user_by_email like SlackClient facade."""

    def __init__(self, user_db=None, raises: Dict[str, Exception] | None = None):
        self.user_db = user_db or {}
        self.raises = raises or {}

    def lookup_user_by_email(self, email: str) -> Dict[str, Any]:
        if email in self.raises:
            raise self.raises[email]
        if email in self.user_db:
            data = self.user_db[email]
            return {
                "ok": True,
                "user": {
                    "id": data.get("id", "U???"),
                    "deleted": data.get("deleted", False),
                    "profile": {"display_name": data.get("display_name", "")},
                },
            }
        return {"ok": False, "error": "users_not_found"}


def test_resolve_returns_found_users_and_not_found_list():
    from app.application.user_resolver_service import UserResolverService
    from app.domain.email_address_list import EmailAddressList

    facade = FacadeStub(
        {
            "user1@example.com": {"id": "U111", "display_name": "太郎"},
        }
    )

    service = UserResolverService(slack_api=facade)
    email_list = EmailAddressList(["user1@example.com", "nf@example.com"])  # order preserved

    users, not_found = service.resolve(email_list)

    assert users == [{"id": "U111", "display_name": "太郎"}]
    assert not_found == ["nf@example.com"]


def test_resolve_treats_api_errors_as_not_found():
    from app.application.user_resolver_service import UserResolverService
    from app.domain.email_address_list import EmailAddressList

    err = SlackApiError("boom", response={"error": "user_not_found"})
    facade = FacadeStub(raises={"err@example.com": err})

    service = UserResolverService(slack_api=facade)
    email_list = EmailAddressList(["err@example.com"])  # one email

    users, not_found = service.resolve(email_list)

    assert users == []
    assert not_found == ["err@example.com"]
