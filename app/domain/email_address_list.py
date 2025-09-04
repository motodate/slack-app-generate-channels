import re
from typing import List


class EmailAddressList:
    """Value object for a normalized, unique list of email addresses.

    - splits by comma and newline
    - trims whitespace, lowercases
    - removes empties
    - preserves original order while removing duplicates
    """

    def __init__(self, values: List[str]):
        self.values = values

    @classmethod
    def from_raw_string(cls, text: str) -> "EmailAddressList":
        parts = re.split(r"[,\n]", text)
        parts = [p.strip().lower() for p in parts]
        unique: List[str] = []
        for p in parts:
            if p and p not in unique:
                unique.append(p)
        return cls(unique)

    def to_list(self) -> List[str]:  # pragma: no cover - alias
        return list(self.values)
