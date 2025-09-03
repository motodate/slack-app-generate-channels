# Slack プライベートチャンネル作成アプリ

Slack上で特定のメンバーを含む新しい**プライベートチャンネル専用**の作成アプリです（パブリックチャンネルは作成しません）。

## 機能

- ショートカットからモーダルUIでプライベートチャンネル作成
- メンバーのメールアドレスを一括入力してSlackユーザーを自動解決
- 入力内容の事前確認ステップで誤入力を防止
- **プライベートチャンネル限定**の作成とメンバー招待
- 作成完了通知のDM送信

> **注意**: このアプリはプライベートチャンネルのみを作成します。パブリックチャンネルは作成されません。

## 技術仕様

- **言語**: Python 3.13
- **フレームワーク**: Slack Bolt for Python
- **実行環境**: pipenv
- **実行モード**: ソケットモード（プロトタイプ段階）

## セットアップ

### 1. 環境準備

```bash
# リポジトリをクローン
git clone <repository-url>
cd slack-app-generate-channels

# 仮想環境の作成と依存関係のインストール
pipenv install --dev

# 仮想環境の有効化
pipenv shell
```

### 2. Slack App の作成と設定

#### 2.1 Slack App の作成

1. [Slack API](https://api.slack.com/apps) にアクセス
2. 「Create New App」→「From scratch」を選択
3. App Name と Development Slack Workspace を入力して作成

#### 2.2 Bot Token Scopes の設定

「OAuth & Permissions」ページで以下のスコープを追加:

- `groups:write` - **プライベートチャンネル作成（必須）**
- `chat:write` - DM送信
- `users:read` - ユーザー情報取得
- `users:read.email` - メールアドレスからユーザー解決

> **重要**: `channels:manage` は不要です。このアプリはプライベートチャンネル専用のため `groups:write` のみが必要です。

#### 2.3 Socket Mode の有効化

1. 「Socket Mode」ページで Socket Mode を有効化
2. 「App-Level Tokens」で新しいトークンを作成
   - Token Name: 任意（例: `websocket_connection`）
   - Scope: `connections:write`
   - 生成されたトークンをメモ（`SLACK_APP_TOKEN`で使用）

#### 2.4 Global Shortcuts の追加

「Interactivity & Shortcuts」ページで:

1. Interactivity を有効化（Request URLは一時的に任意のURLでOK）
2. 「Create New Shortcut」→「Global」を選択
3. 設定:
   - Name: `チャンネル作成`
   - Short Description: `新しいプライベートチャンネルを作成`
   - Callback ID: `create_channel_shortcut`

#### 2.5 Bot Token の取得

「OAuth & Permissions」ページで:
1. 「Install to Workspace」をクリック
2. 生成された「Bot User OAuth Token」をメモ（`SLACK_BOT_TOKEN`で使用）

### 3. 環境変数の設定

```bash
# .env.example をコピー
cp .env.example .env

# .env ファイルを編集してトークンを設定
# SLACK_BOT_TOKEN=xoxb-your-actual-bot-token
# SLACK_APP_TOKEN=xapp-your-actual-app-token
```

## 実行方法

```bash
# モジュールとして実行（推奨）
pipenv run python -m app.slack_app
```

成功すると以下のメッセージが表示されます:
```
⚡️ Slack app is running in socket mode!
```

## 使用方法

1. Slackで任意のチャンネルまたはDMを開く
2. ショートカット（⚡️アイコンまたは `/` コマンド）から「チャンネル作成」を選択
3. モーダルで**プライベートチャンネル**名とメンバーのメールアドレスを入力
4. 確認画面で内容を確認して「作成」ボタンをクリック
5. **プライベートチャンネル**が作成され、完了のDMが送信されます

> **作成されるチャンネル**: 必ずプライベートチャンネル（🔒アイコン付き）として作成されます。

## 開発・テスト

### テスト実行

```bash
# 全テストを実行
pipenv run pytest -q

# 特定のテストファイルを実行
pipenv run pytest tests/test_slack_app_interactions.py -v
```

### コード品質チェック

```bash
# Ruffによるリンティング
pipenv run ruff check

# 自動修正
pipenv run ruff check --fix

# 複雑性チェック
pipenv run flake8 --select=C
```

## プロジェクト構造

```
slack-app-generate-channels/
├── app/
│   ├── slack_app.py              # メインアプリケーション
│   ├── channel_name_normalizer.py # チャンネル名正規化
│   ├── email_address_parser.py   # メールアドレス解析
│   └── user_resolver.py          # Slackユーザー解決
├── tests/                        # テストファイル
├── docs/spec/                    # 設計仕様書
├── .env.example                  # 環境変数テンプレート
├── Pipfile                       # 依存関係定義
└── README.md                     # このファイル
```

## トラブルシューティング

### よくあるエラー

**`SLACK_BOT_TOKEN environment variable is required`**
- `.env` ファイルが作成されていない、またはトークンが設定されていません

**`invalid_auth` エラー**
- Bot Token が無効または期限切れです。Slack App 設定を確認してください

**権限エラー**
- 必要なスコープが付与されていない可能性があります。「OAuth & Permissions」を確認してください

**Socket Mode 接続エラー**
- App-Level Token が無効、または `connections:write` スコープが不足しています

### ログの確認

アプリケーションの実行時にログが出力されるので、エラーの詳細を確認できます:

```bash
python app/slack_app.py
# 2024-01-01 12:00:00 - slack_bolt.app - INFO - ⚡️ Bolt app is running!
```

## ライセンス

[ライセンス情報をここに記載]