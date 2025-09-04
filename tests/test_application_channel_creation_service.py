"""
Application: ChannelCreationService
"""


class FacadeStub:
    def __init__(self):
        self.created = []
        self.invited = []

    def create_channel(self, name, is_private=True):
        self.created.append((name, is_private))
        return {"ok": True, "channel": {"id": "C123"}}

    def invite_users(self, channel_id, user_ids):
        self.invited.append((channel_id, tuple(user_ids)))
        return {"ok": True}


def test_create_private_channel_and_invite_users_returns_id():
    from app.application.channel_creation_service import ChannelCreationService
    from app.domain.channel_name import ChannelName

    stub = FacadeStub()
    svc = ChannelCreationService(slack_api=stub)
    ch_id = svc.create_private_channel(ChannelName("team-x"), ["U1", "U2"])

    assert ch_id == "C123"
    assert stub.created == [("team-x", True)]
    assert stub.invited == [("C123", ("U1", "U2"))]
