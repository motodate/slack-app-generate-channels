import logging
import os

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from app.email_address_parser import parse_email_addresses
from app.user_resolver import resolve_users


def handle_shortcut(ack, shortcut, client):
    """ショートカットハンドラー"""
    ack()

    # 初期チャンネル作成モーダルを表示
    client.views_open(
        trigger_id=shortcut["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "channel_creation_modal",
            "title": {"type": "plain_text", "text": "チャンネル作成"},
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
        },
    )


def handle_modal_submission(ack, view, client, body):
    """モーダル送信ハンドラー：ユーザー解決から確認モーダル表示まで統合"""
    ack()

    try:
        # フォームデータを抽出
        channel_name = view["state"]["values"]["channel_name_input"]["channel_name"]["value"]
        emails_text = view["state"]["values"]["member_emails_input"]["member_emails"]["value"]

        # メールアドレスを解析
        emails = parse_email_addresses(emails_text)

        # ユーザー解決処理を実行
        user_ids, not_found_emails = resolve_users(client, emails)
    except Exception as e:
        from app.user_resolver import AllUsersNotFoundError

        # エラーメッセージを設定
        if isinstance(e, AllUsersNotFoundError):
            error_message = (
                "入力されたメールアドレスに対応するユーザーが見つかりませんでした。"
                "メールアドレスを確認してください。"
            )
        else:
            error_message = f"ユーザー解決でエラーが発生しました: {str(e)}"

        # エラーモーダルを表示
        client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                "title": {"type": "plain_text", "text": "エラー"},
                "blocks": [
                    {"type": "section", "text": {"type": "mrkdwn", "text": f"❌ {error_message}"}}
                ],
            },
        )
        return

    # 確認モーダルのブロックを構築
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*チャンネル名:* {channel_name}"}},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*招待するユーザー:*\n• {', '.join(user_ids)}"},
        },
    ]

    # 見つからなかったメールアドレスがある場合は表示
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

    # 確認ボタンを追加
    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "作成"},
                    "action_id": "confirm_creation",
                    "style": "primary",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "キャンセル"},
                    "action_id": "cancel_creation",
                },
            ],
        }
    )

    # チャンネル情報をprivate_metadataに保存
    import json

    metadata = {"channel_name": channel_name, "user_ids": user_ids}

    # 確認モーダルを表示（新しいモーダルとして開く）
    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "channel_creation_confirmation",
            "title": {"type": "plain_text", "text": "作成確認"},
            "private_metadata": json.dumps(metadata),
            "blocks": blocks,
        },
    )


def _get_error_message(e):
    """例外からユーザー向けエラーメッセージを生成"""
    if hasattr(e, "response") and e.response.get("error") == "name_taken":
        return "このチャンネル名は既に使用されています。"
    elif "permission" in str(e).lower():
        return "チャンネル作成の権限がありません。管理者にお問い合わせください。"
    else:
        return f"チャンネル作成に失敗しました: {str(e)}"


def handle_confirmation_button(ack, action, body, client):
    """確認ボタンアクションハンドラー：チャンネル作成から成功・失敗処理まで統合"""
    ack()

    logging.info("確認ボタンが押されました")

    # 「作成中...」モーダルに更新
    view = body["view"]
    logging.info(f"モーダル更新: view_id={view['id']}")
    client.views_update(
        view_id=view["id"],
        view={
            "type": "modal",
            "title": {"type": "plain_text", "text": "作成中..."},
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "plain_text", "text": "チャンネルを作成しています..."},
                }
            ],
        },
    )

    # private_metadataからチャンネル情報を取得
    import json

    metadata = json.loads(view.get("private_metadata", "{}"))
    channel_name = metadata.get("channel_name")
    user_ids = metadata.get("user_ids", [])
    user_id = body["user"]["id"]

    logging.info(f"チャンネル作成開始: name={channel_name}, user_ids={user_ids}")

    try:
        # チャンネル作成処理
        logging.info(f"conversations_create実行: name={channel_name}, is_private=True")
        response = client.conversations_create(name=channel_name, is_private=True)
        channel_id = response["channel"]["id"]
        logging.info(f"チャンネル作成成功: channel_id={channel_id}")

        # メンバー招待
        if user_ids:
            logging.info(f"メンバー招待実行: channel_id={channel_id}, users={user_ids}")
            client.conversations_invite(channel=channel_id, users=",".join(user_ids))
            logging.info("メンバー招待完了")

        # 成功モーダルを表示
        client.views_update(
            view_id=view["id"],
            view={
                "type": "modal",
                "title": {"type": "plain_text", "text": "完了"},
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"✅ チャンネル `#{channel_name}` を作成しました！",
                        },
                    }
                ],
            },
        )

        # 完了通知DMを送信
        client.chat_postMessage(
            channel=user_id, text=f"チャンネル「#{channel_name}」の作成が完了しました。"
        )

    except Exception as e:
        # エラーログを出力
        logging.error(f"チャンネル作成エラー: {type(e).__name__}: {str(e)}")
        if hasattr(e, "response"):
            logging.error(f"Slack APIレスポンス: {e.response}")

        # エラーメッセージを取得
        error_message = _get_error_message(e)

        # エラーモーダルを表示
        client.views_update(
            view_id=view["id"],
            view={
                "type": "modal",
                "title": {"type": "plain_text", "text": "エラー"},
                "blocks": [
                    {"type": "section", "text": {"type": "mrkdwn", "text": f"❌ {error_message}"}}
                ],
            },
        )

        # 権限不足の場合はDMでも通知
        if "permission" in str(e).lower():
            client.chat_postMessage(
                channel=user_id,
                text="チャンネル作成の権限がありません。ワークスペース管理者にお問い合わせください。",
            )


def create_app():
    """Slack Boltアプリケーションを作成"""
    app = App()

    # ショートカットハンドラー
    app.shortcut("create_channel_shortcut")(handle_shortcut)

    # モーダル送信ハンドラー
    app.view("channel_creation_modal")(handle_modal_submission)

    # 確認ボタンアクションハンドラー
    app.action("confirm_creation")(handle_confirmation_button)

    return app


if __name__ == "__main__":
    # ログ設定
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # 環境変数の確認
    slack_bot_token = os.environ.get("SLACK_BOT_TOKEN")
    slack_app_token = os.environ.get("SLACK_APP_TOKEN")

    if not slack_bot_token:
        raise ValueError("SLACK_BOT_TOKEN environment variable is required")
    if not slack_app_token:
        raise ValueError("SLACK_APP_TOKEN environment variable is required")

    # アプリケーションを作成
    app = create_app()

    # ソケットモードで起動
    handler = SocketModeHandler(app, slack_app_token)
    print("⚡️ Slack app is running in socket mode!")
    handler.start()
