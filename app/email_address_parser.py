def parse_email_addresses(text):
    """既存互換シグネチャを維持しつつ、VOで正規化を委譲"""
    from app.domain.email_address_list import EmailAddressList

    return EmailAddressList.from_raw_string(text).values
