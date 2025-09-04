from typing import Any, Dict, List

from app.presentation.constants import ACTION_IDS, MODAL_TITLES


def build_initial_modal() -> Dict[str, Any]:
    return {
        "type": "modal",
        "callback_id": "channel_creation_modal",
        "title": {"type": "plain_text", "text": MODAL_TITLES["CREATE"]},
        "submit": {"type": "plain_text", "text": "確認する"},
        "close": {"type": "plain_text", "text": "キャンセル"},
        "blocks": [
            {
                "type": "input",
                "block_id": "channel_name_input",
                "label": {"type": "plain_text", "text": "チャンネル名"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "channel_name",
                    "placeholder": {"type": "plain_text", "text": "例: project-alpha"},
                    "max_length": 80,
                },
            },
            {
                "type": "input",
                "block_id": "member_emails_input",
                "label": {"type": "plain_text", "text": "招待するメンバーのメールアドレス"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "member_emails",
                    "multiline": True,
                    "placeholder": {
                        "type": "plain_text",
                        "text": (
                            "user1@example.com, user2@example.com\n"
                            "（カンマまたは改行区切りで複数入力可能）"
                        ),
                    },
                },
            },
        ],
    }


def _users_text(users: List[Dict[str, Any]]) -> str:
    names = [u["display_name"] for u in users]
    return f"*招待するユーザー:*\n• {', '.join(names)}"


def build_confirmation_modal(
    channel_name: str,
    users: List[Dict[str, Any]],
    not_found_emails: List[str],
    private_metadata_json: str,
) -> Dict[str, Any]:
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*チャンネル名:* {channel_name}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": _users_text(users)}},
    ]
    if not_found_emails:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*見つからなかったメール:*\n• {', '.join(not_found_emails)}",
                },
            }
        )

    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "作成"},
                    "action_id": ACTION_IDS["CONFIRM"],
                    "style": "primary",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "キャンセル"},
                    "action_id": ACTION_IDS["CANCEL"],
                },
            ],
        }
    )

    return {
        "type": "modal",
        "callback_id": "channel_creation_confirmation",
        "title": {"type": "plain_text", "text": MODAL_TITLES["CONFIRM"]},
        "private_metadata": private_metadata_json,
        "blocks": blocks,
    }


def build_processing_modal() -> Dict[str, Any]:
    return {
        "type": "modal",
        "title": {"type": "plain_text", "text": MODAL_TITLES["PROCESSING"]},
        "blocks": [
            {
                "type": "section",
                "text": {"type": "plain_text", "text": "チャンネルを作成しています..."},
            }
        ],
    }


def build_success_modal(channel_name: str) -> Dict[str, Any]:
    return {
        "type": "modal",
        "title": {"type": "plain_text", "text": MODAL_TITLES["SUCCESS"]},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"✅ チャンネル `#{channel_name}` を作成しました！",
                },
            }
        ],
    }


def build_error_modal(error_message: str) -> Dict[str, Any]:
    return {
        "type": "modal",
        "title": {"type": "plain_text", "text": MODAL_TITLES["ERROR"]},
        "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": f"❌ {error_message}"}}],
    }
