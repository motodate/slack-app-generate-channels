# PR2: ドメインVO導入＋既存関数ラッパー化（Plan C‑Lite / Phase 2）

## 目的（意図）
- チャンネル名とメールアドレス一覧の正規化ルールを明文化し、テスト可能な境界（VO）に固定する。
- 既存の公開関数シグネチャとUIの振る舞いは変えず、内部委譲で将来の変更耐性を高める。

## 変更の要点
- 追加: `app/domain/channel_name.py`（`ChannelName`）
- 追加: `app/domain/email_address_list.py`（`EmailAddressList`）
- ラッパー化: 既存関数がVOへ委譲
  - `normalize_channel_name(name)` → `ChannelName.from_raw_string(name).value`
  - `parse_email_addresses(text)` → `EmailAddressList.from_raw_string(text).values`
- UI統合: `handle_modal_submission` でチャンネル名を正規化（既存ラッパー経由、文言・振る舞い不変）
- テスト: VOのユニットテストを追加（既存テストは不変・全GREEN）

## 非目標（互換性）
- UI文言、ackタイミング、`views_open`/`views_update` の使い分けは変更しない。
- 呼び出し元の関数シグネチャは現状維持。

## リスクと低減
- リスク: 正規化ルールの差異
  - 対策: 既存テストの期待に合わせたルールをVOへ転写し、回帰をテストで担保。

## 次のステップ
- PR3: `UserResolverService` 抽出（`resolve_users` はラッパー化）。
- 併行可: PR-aux2（型ヒントの段階導入）。

