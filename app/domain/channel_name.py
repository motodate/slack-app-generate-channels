import re
import unicodedata


class ChannelName:
    """Value object for Slack channel name.

    Normalizes input according to existing behavior:
    - NFKC normalization (fullwidth -> halfwidth)
    - lowercasing
    - collapse whitespace to single '-'
    - remove characters except [a-z0-9_-]
    - enforce max length 80
    """

    def __init__(self, value: str):
        if len(value) > 80:
            raise ValueError("チャンネル名は80文字以内である必要があります")
        self.value = value

    @classmethod
    def from_raw_string(cls, name: str) -> "ChannelName":
        # Normalize wide chars
        s = unicodedata.normalize("NFKC", name)
        # Lowercase
        s = s.lower()
        # Collapse whitespace to '-'
        s = re.sub(r"\s+", "-", s)
        # Keep only allowed characters
        s = re.sub(r"[^a-z0-9_-]", "", s)
        # Length check happens in ctor
        return cls(s)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value
