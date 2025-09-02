def parse_email_addresses(text):
    import re

    # カンマと改行の両方で分割
    emails = re.split(r"[,\n]", text)
    # 前後の空白をトリミングし、小文字に統一
    emails = [email.strip().lower() for email in emails]
    # 空文字列を除去し、重複を除去（順序を保持）
    unique_emails = []
    for email in emails:
        if email and email not in unique_emails:
            unique_emails.append(email)
    return unique_emails
