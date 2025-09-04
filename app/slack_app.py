import logging
import os

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from app.application.channel_creation_service import ChannelCreationService
from app.channel_name_normalizer import normalize_channel_name
from app.email_address_parser import parse_email_addresses
from app.infrastructure.slack_client import SlackClient
from app.presentation.modal_builder import (
    build_confirmation_modal,
    build_error_modal,
    build_initial_modal,
    build_processing_modal,
    build_success_modal,
)
from app.user_resolver import resolve_users


def handle_shortcut(ack, shortcut, client):
    """ショートカットハンドラー"""
    ack()

    # 初期チャンネル作成モーダルを表示（ビルダー経由）
    SlackClient(client).open_view(trigger_id=shortcut["trigger_id"], view=build_initial_modal())


def handle_modal_submission(ack, view, client, body):
    """モーダル送信ハンドラー：ユーザー解決から確認モーダル表示まで統合"""
    ack()

    try:
        # フォームデータを抽出
        channel_name = view["state"]["values"]["channel_name_input"]["channel_name"]["value"]
        # Phase 2: VO 仕様に基づく正規化（既存ラッパー経由 / 挙動不変）
        channel_name = normalize_channel_name(channel_name)
        emails_text = view["state"]["values"]["member_emails_input"]["member_emails"]["value"]

        # メールアドレスを解析
        emails = parse_email_addresses(emails_text)

        # ユーザー解決処理を実行
        user_info_list, not_found_emails = resolve_users(client, emails)
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

        # エラーモーダルを表示（ビルダー）
        SlackClient(client).open_view(
            trigger_id=body["trigger_id"], view=build_error_modal(error_message)
        )
        return

    # 確認モーダルのブロックを構築
    # 表示名のリストを生成
    display_names = [user_info["display_name"] for user_info in user_info_list]
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*チャンネル名:* {channel_name}"}},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*招待するユーザー:*\n• {', '.join(display_names)}",
            },
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

    # UserIDのリストを抽出
    user_ids = [user_info["id"] for user_info in user_info_list]
    metadata = {"channel_name": channel_name, "user_ids": user_ids}

    # 確認モーダルを表示（ビルダー）
    SlackClient(client).open_view(
        trigger_id=body["trigger_id"],
        view=build_confirmation_modal(
            channel_name=channel_name,
            users=user_info_list,
            not_found_emails=not_found_emails,
            private_metadata_json=json.dumps(metadata),
        ),
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
    SlackClient(client).update_view(view_id=view["id"], view=build_processing_modal())

    # private_metadataからチャンネル情報を取得
    import json

    metadata = json.loads(view.get("private_metadata", "{}"))
    channel_name = metadata.get("channel_name")
    user_ids = metadata.get("user_ids", [])
    user_id = body["user"]["id"]

    # 作成者を招待リストに追加（重複排除）
    if user_id not in user_ids:
        user_ids.append(user_id)

    logging.info(f"チャンネル作成開始: name={channel_name}, user_ids={user_ids}")

    try:
        # チャンネル作成処理（サービスへ委譲）
        logging.info(f"conversations_create実行: name={channel_name}, is_private=True")
        service = ChannelCreationService(SlackClient(client))
        channel_id = service.create_private_channel(channel_name, user_ids)
        logging.info(f"チャンネル作成成功: channel_id={channel_id}")

        # 成功モーダルを表示
        SlackClient(client).update_view(view_id=view["id"], view=build_success_modal(channel_name))

        # 完了通知DMを送信
        SlackClient(client).post_message(
            channel=user_id, text=f"チャンネル「#{channel_name}」の作成が完了しました。"
        )

    except Exception as e:
        # エラーログを出力
        logging.error(f"チャンネル作成エラー: {type(e).__name__}: {str(e)}")
        if hasattr(e, "response"):
            logging.error(f"Slack APIレスポンス: {e.response}")

        # エラーメッセージを取得
        error_message = _get_error_message(e)

        # エラーモーダルを表示（ビルダー）
        SlackClient(client).update_view(view_id=view["id"], view=build_error_modal(error_message))

        # 権限不足の場合はDMでも通知
        if "permission" in str(e).lower():
            SlackClient(client).post_message(
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
