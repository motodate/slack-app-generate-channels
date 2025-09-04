def normalize_channel_name(name):
    """既存互換シグネチャを維持しつつ、VOで正規化を委譲"""
    from app.domain.channel_name import ChannelName

    return ChannelName.from_raw_string(name).value
