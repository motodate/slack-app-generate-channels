"""
仕様: チャンネル名の正規化
"""


def test_valid_channel_name_returns_as_is():
    """正常系: 英小文字、数字、ハイフン、アンダースコアのみの有効なチャンネル名は、
    そのまま返される"""
    from app.channel_name_normalizer import normalize_channel_name

    result = normalize_channel_name("my-channel_123")
    assert result == "my-channel_123"


def test_fullwidth_to_halfwidth_conversion():
    """変換系: 全角の英数字は半角に変換される"""
    from app.channel_name_normalizer import normalize_channel_name

    result = normalize_channel_name("ｃｈａｎｎｅｌ-０１")
    assert result == "channel-01"


def test_uppercase_to_lowercase_conversion():
    """変換系: 大文字は小文字に変換される"""
    from app.channel_name_normalizer import normalize_channel_name

    result = normalize_channel_name("My-Channel")
    assert result == "my-channel"


def test_whitespace_to_hyphen_conversion():
    """変換系: 1つ以上の空白は1つのハイフンに変換される"""
    from app.channel_name_normalizer import normalize_channel_name

    result = normalize_channel_name("my  new   channel")
    assert result == "my-new-channel"


def test_invalid_characters_removal():
    """除去系: 許可されていない文字は除去される"""
    from app.channel_name_normalizer import normalize_channel_name

    result = normalize_channel_name("my_channel@!")
    assert result == "my_channel"


def test_length_limit_80_characters_raises_error():
    """文字数制限: 80文字を超える場合は例外を発生させる"""
    import pytest

    from app.channel_name_normalizer import normalize_channel_name

    long_name = "a" * 85  # 85文字
    with pytest.raises(ValueError, match="80文字"):
        normalize_channel_name(long_name)
