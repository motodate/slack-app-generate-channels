from app.domain.channel_name import ChannelName


def normalize_channel_name(name: str) -> str:
    """既存互換シグネチャを維持しつつ、VOで正規化を委譲"""
    return ChannelName.from_raw_string(name).value
