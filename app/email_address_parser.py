from typing import List

from app.domain.email_address_list import EmailAddressList


def parse_email_addresses(text: str) -> List[str]:
    """既存互換シグネチャを維持しつつ、VOで正規化を委譲"""
    return EmailAddressList.from_raw_string(text).values
