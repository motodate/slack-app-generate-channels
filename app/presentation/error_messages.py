from typing import Tuple


def get_error_message_and_dm(exc: Exception) -> Tuple[str, bool]:
    """Map exception to user-facing message and whether to send a DM as well.

    Policy (compatible with current behavior):
    - name_taken: show error modal only
    - permission* errors: show error modal and send DM
    - others: show error modal only
    """

    msg: str
    send_dm = False

    # Slack SDK style: exc.response.get("error")
    if hasattr(exc, "response") and isinstance(getattr(exc, "response"), dict):
        if exc.response.get("error") == "name_taken":
            msg = "このチャンネル名は既に使用されています。"
            return msg, False

    # Fallback string inspection
    if "permission" in str(exc).lower():
        msg = "チャンネル作成の権限がありません。管理者にお問い合わせください。"
        send_dm = True
    else:
        msg = f"チャンネル作成に失敗しました: {str(exc)}"

    return msg, send_dm
