import logging
import os

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from app.application.channel_creation_service import ChannelCreationService
from app.channel_name_normalizer import normalize_channel_name
from app.email_address_parser import parse_email_addresses
from app.infrastructure.slack_client import SlackClient
from app.presentation.constants import ACTION_IDS
from app.presentation.error_messages import get_error_message_and_dm
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
    sc = SlackClient(client)
    sc.open_view(trigger_id=shortcut["trigger_id"], view=build_initial_modal())


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
        sc = SlackClient(client)
        sc.open_view(trigger_id=body["trigger_id"], view=build_error_modal(error_message))
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

    # private_metadata が長すぎる場合はトークン参照に切り替え
    pm = json.dumps(metadata)
    if len(pm) > 2800:  # Slack 制限 3000 の手前でガード
        from app.presentation.metadata_store import store as store_meta

        token = store_meta(metadata)
        pm = json.dumps({"token": token})

    # 確認モーダルを表示（ビルダー）
    sc = SlackClient(client)
    sc.open_view(
        trigger_id=body["trigger_id"],
        view=build_confirmation_modal(
            channel_name=channel_name,
            users=user_info_list,
            not_found_emails=not_found_emails,
            private_metadata_json=pm,
        ),
    )


def handle_confirmation_button(ack, action, body, client):
    """確認ボタンアクションハンドラー：チャンネル作成から成功・失敗処理まで統合"""
    ack()

    logging.info("確認ボタンが押されました")

    # 「作成中...」モーダルに更新
    view = body["view"]
    logging.info(f"モーダル更新: view_id={view['id']}")
    sc = SlackClient(client)
    sc.update_view(view_id=view["id"], view=build_processing_modal())

    # private_metadataからチャンネル情報を取得
    import json

    metadata = json.loads(view.get("private_metadata", "{}"))
    if "token" in metadata:
        from app.presentation.metadata_store import retrieve as load_meta

        loaded = load_meta(metadata["token"]) or {}
        metadata = loaded
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
        service = ChannelCreationService(sc)
        channel_id = service.create_private_channel(channel_name, user_ids)
        logging.info(f"チャンネル作成成功: channel_id={channel_id}")

        # 成功モーダルを表示
        sc.update_view(view_id=view["id"], view=build_success_modal(channel_name))

        # 完了通知DMを送信
        sc.post_message(
            channel=user_id, text=f"チャンネル「#{channel_name}」の作成が完了しました。"
        )

    except Exception as e:
        # エラーログを出力
        logging.error(f"チャンネル作成エラー: {type(e).__name__}: {str(e)}")
        if hasattr(e, "response"):
            logging.error(f"Slack APIレスポンス: {e.response}")

        # エラーメッセージとDM方針を取得
        error_message, send_dm = get_error_message_and_dm(e)

        # エラーモーダルを表示（ビルダー）
        sc.update_view(view_id=view["id"], view=build_error_modal(error_message))

        # 方針に応じてDMでも通知
        if send_dm:
            sc.post_message(channel=user_id, text=error_message)


def handle_cancel_button(ack, action, body, client):
    """キャンセルボタン: 確認画面 → 入力画面に戻す（モーダルを更新）。"""
    # 入力用の初期モーダルに差し替え（Stackは維持しつつ画面を戻す）
    ack(response_action="update", view=build_initial_modal())


def create_app():
    """Slack Boltアプリケーションを作成"""
    app = App()

    # ショートカットハンドラー
    app.shortcut("create_channel_shortcut")(handle_shortcut)

    # モーダル送信ハンドラー
    app.view("channel_creation_modal")(handle_modal_submission)

    # 確認/キャンセル ボタンアクションハンドラー
    app.action(ACTION_IDS["CONFIRM"])(handle_confirmation_button)
    app.action(ACTION_IDS["CANCEL"])(handle_cancel_button)

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
