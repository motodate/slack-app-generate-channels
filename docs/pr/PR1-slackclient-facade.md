# PR1: SlackClient Facade 導入＋内部置換（Plan C‑Lite / Phase 1）

## 目的
- Slack API 呼び出し経路を `SlackClient` Facade に集約し、テスト容易性と将来の責務分割の基盤を作る。
- 互換性維持（既存テストの振る舞い・文言を変えない）。

## 変更点
- 追加: `app/infrastructure/slack_client.py`
  - 公開メソッド: `open_view`, `update_view`, `create_channel`, `invite_users`, `post_message`, `lookup_user_by_email`
- 内部置換: `app/slack_app.py`, `app/user_resolver.py` からの Slack SDK 直接呼び出しを Facade 経由に変更。
- ドキュメント更新: Phase 1 から「エラー整形の方針」タスクを削除（Phase 5 で責務見直し）。

## 非変更点（互換性コミットメント）
- エラー文言と判定ロジックは UI 層（`_get_error_message`）に維持。
- ハンドラの `ack()` タイミング・UI 文言・`views_open` 使用の期待は従来どおり。

## 背景と判断
- Phase 1 の目的は「経路集約のみ」。Facade にエラー整形を持たせると文言／判定の変化リスクがあり、互換維持の観点で Phase 5 に先送り。

## テスト戦略
- 既存 UI/インテグレーションテストは変更不要。
- Facade 構造テストを追加済み（署名と公開メソッドの存在確認）。

## リスクと対策
- リスク: 置換漏れによる直接 SDK 呼び出しの残存。
  - 対策: `views_open|views_update|conversations_.*|chat_postMessage|users_lookupByEmail` で全検索し、Facade 内にのみ存在することを確認。

## 次のステップ（参考）
- PR2: VO 導入＋既存関数ラッパー化（`ChannelName`, `EmailAddressList`）。
- PR3: `UserResolverService` 抽出（`resolve_users` はラッパー化）。

