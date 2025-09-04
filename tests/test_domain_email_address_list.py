"""Domain: EmailAddressList value object"""


def test_from_raw_string_parses_commas_and_newlines_and_normalizes():
    from app.domain.email_address_list import EmailAddressList

    input_text = " user1@example.com,USER1@example.com\nuser2@example.com,, user3@ex.com "
    emails = EmailAddressList.from_raw_string(input_text)
    assert emails.values == [
        "user1@example.com",
        "user2@example.com",
        "user3@ex.com",
    ]


def test_from_raw_string_ignores_empty_entries():
    from app.domain.email_address_list import EmailAddressList

    emails = EmailAddressList.from_raw_string(
        "user@example.com,,,\nadmin@company.org,\n\n,other@test.com"
    )
    assert emails.values == [
        "user@example.com",
        "admin@company.org",
        "other@test.com",
    ]
