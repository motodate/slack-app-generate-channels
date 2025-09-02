"""
仕様: メールアドレスの解析
"""


def test_parse_comma_and_newline_separated_emails():
    """正常系: カンマ区切り、改行区切り、またはその両方が混在した文字列から、
    メールアドレスのリストを正しく抽出できる"""
    from app.email_address_parser import parse_email_addresses

    input_text = "user1@example.com,user2@example.com\nuser3@example.com,user4@example.com"
    result = parse_email_addresses(input_text)
    expected = [
        "user1@example.com",
        "user2@example.com",
        "user3@example.com",
        "user4@example.com",
    ]
    assert result == expected


def test_trim_whitespace_around_emails():
    """正規化: 各メールアドレスの前後の空白はトリミングされる"""
    from app.email_address_parser import parse_email_addresses

    input_text = " user@example.com , another@example.com "
    result = parse_email_addresses(input_text)
    assert result == ["user@example.com", "another@example.com"]


def test_normalize_email_case_to_lowercase():
    """正規化: メールアドレス内の大文字は小文字に統一される"""
    from app.email_address_parser import parse_email_addresses

    input_text = "User@Example.com,ADMIN@COMPANY.ORG"
    result = parse_email_addresses(input_text)
    assert result == ["user@example.com", "admin@company.org"]


def test_remove_duplicate_emails():
    """一意性: 重複したメールアドレスは1つにまとめられる"""
    from app.email_address_parser import parse_email_addresses

    input_text = "user@example.com,user@example.com,admin@company.org,USER@EXAMPLE.COM"
    result = parse_email_addresses(input_text)
    assert result == ["user@example.com", "admin@company.org"]


def test_ignore_empty_entries_and_extra_separators():
    """堅牢性: 空の行や余分な区切り文字は無視され、リストに含まれない"""
    from app.email_address_parser import parse_email_addresses

    input_text = "user@example.com,,,\nadmin@company.org,\n\n,other@test.com"
    result = parse_email_addresses(input_text)
    expected = ["user@example.com", "admin@company.org", "other@test.com"]
    assert result == expected
