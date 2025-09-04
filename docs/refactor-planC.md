# Plan C‑Lite: 実装順序最適化リファクタリング計画（段階縮小版）

## 概要
Plan C（DDD/レイヤー分離）を現状コード規模に合わせて縮小し、互換性を最優先に段階導入する計画。既存テスト（特に `tests/test_slack_app_interactions.py` のパッチ前提）を壊さず、将来の本格分割に繋がる「境界の固定」を先に行う。

## 現状の観測（2025-09-04 時点）
- Slack API 直接呼び出しの実測箇所（計10件）
  - `app/slack_app.py`: `views_open`(16, 85, 151), `views_update`(182, 224, 256), `conversations_create`(213), `conversations_invite`(220), `chat_postMessage`(242, 269)
  - `app/user_resolver.py`: `users_lookupByEmail`(15) → 合計11箇所（アプリ本体10 + user_resolver 1）
- テスト前提の互換制約
  - `patch("app.slack_app.resolve_users")` を前提にしているため、短期的に `resolve_users` 関数は残す。
  - 「モーダル送信は `views_open` を使う」ことを検証しているテストがある（`test_modal_submission_uses_views_open_not_update`）。
  - UI文言・ackタイミング（冒頭即時）を維持する必要あり。

## 設計方針（要点）
1) 先に「Slack API 境界」を固定（薄いFacade導入）。
2) 値オブジェクト（VO）は導入するが、既存の関数APIはラッパーとして残して互換維持。
3) サービス抽出は小さく始め、ハンドラの外形を変えない（DIコンテナ導入は後段）。
4) UIはまず関数ビルダーに集約（クラス化は後段）。

---
## 実施計画

### Phase 1: インフラ（SlackClient Facade）
**目的**: API呼び出しの集約とテスト容易性の向上（互換破壊なし）。

- [x] 追加: `app/infrastructure/slack_client.py`
- [x] メソッド（最小6個）
  - `open_view(trigger_id, view)` → `client.views_open`
  - `update_view(view_id, view)` → `client.views_update`
  - `create_channel(name, is_private=True)` → `client.conversations_create`
  - `invite_users(channel_id, user_ids: list[str])` → `client.conversations_invite`
  - `post_message(channel, text)` → `client.chat_postMessage`
  - `lookup_user_by_email(email)` → `client.users_lookupByEmail`
- [x] 置換（内部のみ）: `app/slack_app.py` と `app/user_resolver.py` からの直接呼び出しをFacade経由に変更（関数シグネチャは維持）。
- [x] テスト: 既存テストは変更不要。必要に応じてFacadeの単体テストを追加（モック）。

### Phase 2: ドメイン（VO導入＋関数ラップ）
**目的**: ビジネスルールの明確化。既存APIの互換維持。

- [ ] 追加: `app/domain/channel_name.py`（`ChannelName`）
- [ ] 追加: `app/domain/email_address_list.py`（`EmailAddressList`）
- [ ] 既存関数をラッパー化
  - `normalize_channel_name(name)` → 内部で `ChannelName.from_raw_string` を呼ぶ。
  - `parse_email_addresses(text)` → 内部で `EmailAddressList.from_raw_string` を呼ぶ。
- [ ] UI統合: `handle_modal_submission` 内で VO を使用（表示は従来どおり）。
- [ ] テスト: 既存の関数テストは不変。VOの追加テストを別途用意。

### Phase 3: アプリケーション（サービス分割・小さく開始）
**目的**: ハンドラからビジネス処理を切り出して複雑度を下げる。

- [ ] 追加: `app/application/user_resolver_service.py`
  - `UserResolverService.resolve(email_list: EmailAddressList)` を実装（Facade注入）。
  - 既存 `resolve_users(slack_client, email_list)` はラッパーとして残し、内部でサービスを呼ぶ。
- [ ] 追加: `app/application/channel_creation_service.py`（最小実装）
  - `create_private_channel(name: ChannelName, user_ids: list[str])`
  - Facade経由で create→invite→（将来）初期メッセージ。
  - 例外→UIメッセージ変換は当面 `_get_error_message` に委譲。
- [ ] テスト: サービス単体のモックテストを追加（既存UIテストは不変）。

### Phase 4: プレゼンテーション（モーダルビルダー関数）
**目的**: UI断片を一箇所に集約し、文言と構造のブレを防ぐ。

- [ ] 追加: `app/presentation/modal_builder.py`
  - `build_initial_modal()`
  - `build_confirmation_modal(channel_name, users, not_found_emails)`
  - `build_processing_modal()`
  - `build_success_modal(channel_name)`
  - `build_error_modal(error_message)`
- [ ] ハンドラはビルダー関数を呼ぶだけに変更（`views_open`/`views_update` の使い分けは現状維持）。

### Phase 5: 統合・クリーンアップ
**目的**: 重複・未使用の整理と基準線の確立。

- [ ] `_get_error_message` の責務見直し（Facade/Serviceに寄せる是非をレビュー）。
- [ ] 未使用ヘルパ・重複ロジック削除、import整頓。
- [ ] E2E/回帰テスト実行、ログの粒度調整。

---
## 互換性コミットメント（既存テストを壊さないための約束）
- `resolve_users` 関数のモジュール・名前を維持（内部でサービス呼び出しへ移行）。
- `normalize_channel_name` / `parse_email_addresses` の関数シグネチャを維持（内部でVO使用）。
- `handle_modal_submission` は `views_open` を使用（テストの期待準拠）。
- `ack()` は各ハンドラ冒頭で即時実行（レスポンス3秒制約対策）。
- 既存のユーザー向け文言を変更しない（変更が必要な場合は別PRで反映）。

---
## 成功基準（現実的トーン）
- 既存の全テストがグリーン（互換性維持）。
- Slack API呼び出しが100% `SlackClient` Facade経由に集約。
- 変更差分に対するカバレッジ 80%以上（全体90%は次段）。
- `handle_confirmation_button` の分岐/長さが目視で簡潔化（サービス委譲で複雑度低下）。

---
## リスクと対策
- パス変更/名前変更でモックが効かなくなる
  - 対策: 外形APIは段階中は維持。削除/リネームは「クリーンアップPR」で一括。
- UI文言の微変更でスナップショット崩れ
  - 対策: 文字列は流用。ビルダー導入時は既存文字列をそのまま組み立て。
- 過度な抽象化によるオーバーヘッド
  - 対策: Facadeは薄く、VO/Serviceも最小機能から。YAGNIを徹底。

---
## レビュー所見とフォローアップ方針（2025-09-04）
外部レビュー（motodate/Claude Code）の要点をPlan C‑Liteに反映。

### 強み（現状維持）
- Facade 集約は適切で単一責任を満たす。
- 互換性（既存テスト・UI文言・`views_open` 使用）を維持。
- Facade は薄く、モック容易性とパフォーマンスに問題なし。

### 改善提案と対応（優先度順）
1) 小リファクタ（安全・挙動不変）
   - `SlackClient(client)` の重複生成をやめ、各ハンドラ内で1回だけ生成して再利用。
   - 対応: Phase 5 のクリーンアップで実施（`app/slack_app.py`）。
2) 型ヒントの追加（安全・挙動不変）
   - Facade の公開メソッドと `user_resolver` の戻り値等に型注釈を付与。
   - 対応: 独立の小PR（`chore(types)`）として早期に実施可。
3) `__signature__` オーバーライドの解消（低優先）
   - 構造テストを `inspect.signature(cls.__init__)` で検証する形に見直し、ハックを撤廃。
   - 対応: Phase 5 のテスト整備時に実施。

---
## 実装スケジュールとPR分割（目安）
| PR | 内容 | 依存 | 目安工数 |
|---|---|---|---|
| PR1 | SlackClient Facade導入＋内部置換 | なし | 1.5–2.0h |
| PR2 | VO導入＋既存関数ラッパー化 | PR1 | 1.0–1.5h |
| PR3 | UserResolverService抽出＋`resolve_users` ラッパー化 | PR1–2 | 1.5–2.0h |
| PR4 | ChannelCreationService最小実装＋ハンドラ内部委譲 | PR1–3 | 2.0–2.5h |
| PR5 | modal_builder関数化＋統合・整頓 | PR1–4 | 1.0–1.5h |

合計: 7–9.5h（従来Plan Cの14–19hから圧縮）。

### 補助PR（小粒・随時）
- PR-aux1: chore(refactor) SlackClient インスタンス再利用（各ハンドラで1回生成）
- PR-aux2: chore(types) Facade/Resolver に型ヒントを段階追加
- PR-aux3: test/cleanup `__signature__` ハック撤廃（構造テスト見直し）

---
## 次のステップ
1. 本ドキュメント（Plan C‑Lite）の承認。
2. PR1のレビューとマージ（実装済み: Facade導入＋内部置換、振る舞い不変）。
3. 互換性確認（可能ならローカルでテスト実行／CI 上で確認）。
4. PR-aux1/PR-aux2 の実施タイミングを決定（小PRで安全に先行可）。
5. PR2の着手: VO導入＋既存関数ラッパー化（`ChannelName`, `EmailAddressList`）。

---
## 参考（前版Plan Cとの差分）
- 層の新設は同じだが、導入順を「Facade→VO→Service→UI関数」に限定。
- DIコンテナ/イベントハンドラクラス化は本計画のスコープ外（将来のPlan C‑Proへ）。
- ロールバック/リトライなどの高度化は保留。まずは境界の固定と複雑度の減殺を優先。
