"""Domain: ChannelName value object"""

import pytest

from app.domain.channel_name import ChannelName


def test_from_raw_string_normalizes_fullwidth_uppercase_whitespace_and_symbols():
    cn = ChannelName.from_raw_string(" ｃｈａｎｎｅｌ  -  ０１ /@!")
    # 既存の規則に合わせて、先頭/連続ハイフンは温存される
    assert cn.value == "-channel---01-"


def test_from_raw_string_preserves_valid_characters():
    cn = ChannelName.from_raw_string("my-channel_123")
    assert cn.value == "my-channel_123"


def test_from_raw_string_raises_on_length_over_80():
    long_name = "a" * 85
    with pytest.raises(ValueError, match="80"):
        ChannelName.from_raw_string(long_name)
