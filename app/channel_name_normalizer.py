def normalize_channel_name(name):
    # 全角→半角変換
    import re
    import unicodedata

    name = unicodedata.normalize("NFKC", name)
    # 大文字→小文字変換
    name = name.lower()
    # 1つ以上の空白→ハイフン変換
    name = re.sub(r"\s+", "-", name)
    # 許可されていない文字を除去（英小文字、数字、ハイフン、アンダースコアのみ残す）
    name = re.sub(r"[^a-z0-9_-]", "", name)
    # 80文字制限チェック
    if len(name) > 80:
        raise ValueError("チャンネル名は80文字以内である必要があります")
    return name
