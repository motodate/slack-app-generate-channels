## 全般
- @docs/spec 内に本システムの要件 や TDDを実践するためのテストリストが記載されている。
- 重要: 情報の2重管理は修正漏れの危険性があるため、CLAUDE.md (本ドキュメント) にはプロジェクトにフォーカスした概要、各資料の場所、開発方針を記載するする。
- プロジェクト変更があった際には @docs 側の資料を修正する。
- 技術仕様はmcpのcontext7を参照する


## 開発方針 (BDD)

- 振る舞いをテストで固定し、最小実装で前進する。原則は **「1シナリオ＝1振る舞い＝1期待結果」**。
- テストは **「1テスト＝1失敗理由」** を守る。ただし、同一振る舞いの不可分な観測点（例: 返り値と副作用）は、同一テスト内で複数 `assert` を用いてよい。

### フロー

1. @docs/spec/unit_test_cases.md にある振る舞いの一つを確認するテストを書く。 **1失敗理由** に収まるなら複数 `assert` 可。
2. RED を確認する。失敗メッセージを次の作業境界とする。`pytest -q` を実行し、**最初の失敗**だけに対処する。
3. 最小実装で GREEN にする。先読み実装は禁止。1回の変更は**1ファイル・数行**に限定し、毎回テストを再実行する。
4. このフェーズは、4-A (自動チェック) → 4-B (CLASSIFY実行) で進行します。
4-A: CLASSIFY候補の確認のため、以下の2つのコマンド実行する。同じ関数が、C901 (McCabe) > 10 と C90 (認知的複雑度) > 7 の両方に違反している場合には 4-B でCLASSIFY を実行してください。それ以外の場合は 5. に進んでください。
  - 自動チェックコマンド:
    - ruff check --select C901
    - flake8 --select=C
  - *重要*: この段階では違反していても修正してはいけない
4-B: CLASSIFYの実行 
  - *重要*: 4-A の判断で CLASSIFY する判断になっていること。
  - プロセス: 指示に従い、以下の手順を1ステップずつ実行します。
    - 構造テストの追加: 新しく作るクラスの存在と公開メソッドを検証するテストを作成し、REDにします。生成AIがリファクタを素通りしないための措置です。
    - 骨格クラスの作成: 構造テストをパスさせるための、空のクラスとメソッドの骨格を実装します。
    - ロジックの段階的移行: 元の関数からロジックを少しずつ新しいクラスのメソッドへ移動させ、テストが常にGREENを維持することを確認します。
    - ラッパーの削除: すべてのロジックの移行が完了したら、元の関数を削除または新しいクラスを呼び出すだけのラッパーにします。最終的に呼び出し元をすべて修正し、ラッパーも削除します。
  - してはいけないこと: 上記のステップを一度に実行すること。必ず人間の指示に従い、一歩ずつ進めます。
5. 完了したテストケースにチェックを入れてコミットする。
  - pre-commit を導入しているので、品質チェックツールのエラーが出た場合には対処する。
  - コミットログは変更内容ではなく、意図を記載すること
  - *重要*: 修正後は必ず、すべてのユニットテストでパスすることを確認する

```python: 構造テストの追加例
# tests/test_arch_user_service_structure.py
"""
仕様: UserService クラスが存在し、create(name) を公開し、外部依存を注入できること。
"""
import importlib
import inspect

def test_user_service_class_must_exist_and_be_constructible():
    mod = importlib.import_module("app.user_service")
    # クラス定義の存在
    assert hasattr(mod, "UserService")
    cls = mod.UserService
    # コンストラクタに repo と eventbus を受け取れる
    sig = inspect.signature(cls)
    params = list(sig.parameters)
    assert params[0] == "repo" and params[1] == "eventbus"

def test_user_service_must_expose_create_method():
    mod = importlib.import_module("app.user_service")
    svc = mod.UserService(repo=object(), eventbus=object())  # ダミーでよい
    assert hasattr(svc, "create")
```


次の兆候が2つ以上出たら CLASSIFY を提案してほしい
* 同じ引数セットが複数の関数を連鎖的に通過している。
* 同じ前処理が複数テストで繰り返されている（3回以上、または30行規模）。
* 状態と不変条件を守る必要がある（例: セッション寿命、検証→更新→イベント発行）。
* 例外や副作用が“同じ対象の状態”に依存する。


---

### 例外の扱い

例外は「そのシナリオの期待結果が例外」のときだけ扱う。正常系と異常系を同一テストに混在させない。
`pytest.raises` は型に加え、`match=` でメッセージ要点も検証する。

---

### 良い例（複数 `assert` を**不可分な観測点**として共有する）

以下は「ユーザー作成が**保存**され、**イベント**が発行される」までを**1つの振る舞い**として検証する。返り値と副作用は不可分なので、2つの `assert` を同一テストに置く。

```python
# tests/test_user_creation.py

"""
仕様: create(name) はユーザーを保存し、そのIDを返し、UserCreated イベントを発行する。
"""

class FakeRepo:
    def __init__(self): self._db = {}
    def save(self, user): self._db[user["id"]] = user
    def get(self, uid): return self._db[uid]

class FakeEventBus:
    def __init__(self): self.last_event = None
    def publish(self, name, payload): self.last_event = (name, payload)

# （クラス化後の想定：UserService を使用）
from app.user_service import UserService  # 実装は必要最小限でよい

def test_create_user_persists_and_publishes():
    repo, bus = FakeRepo(), FakeEventBus()
    svc = UserService(repo=repo, eventbus=bus)

    uid = svc.create(name="Alice")

    # 不可分な観測点（結果＋副作用）を一つの振る舞いとして検証
    assert repo.get(uid)["name"] == "Alice"                      # 保存の確認（結果）
    assert bus.last_event == ("UserCreated", {"id": uid})        # イベント副作用
```

異常系は期待結果が異なるため別テストにする。

```python
import pytest

def test_create_user_rejects_empty_name():
    repo, bus = FakeRepo(), FakeEventBus()
    svc = UserService(repo=repo, eventbus=bus)

    with pytest.raises(ValueError, match="empty"):
        svc.create(name="")
```

---

### 悪い例（避けるべきパターン）

**過剰分割**や**期待結果の混在**は、失敗理由の特定を遅らせ、メンテナンス性を下げる。

```python
# 1) 同一振る舞いの過剰分割（悪い）
def test_create_user_returns_id_only(): ...
def test_create_user_persists_only(): ...
def test_create_user_publishes_only(): ...
# → どれか一つが壊れても「作成という一つの振る舞い」が成功か失敗かを判断しづらい。
#    前処理が重複し、生成AIも修正対象を見誤りやすい。

# 2) 正常系と異常系の混在（悪い）
def test_create_user_mixed_success_and_failure(repo, bus):
    svc = UserService(repo, bus)
    uid = svc.create("Alice")
    assert uid
    with pytest.raises(ValueError):
        svc.create("")    # 正常と異常が同居し読みづらい。失敗時の境界も不明瞭。

# 3) parametrize で期待結果を混在（悪い）
import pytest
@pytest.mark.parametrize("name, should_raise", [("Alice", False), ("", True)])
def test_create_user_mixed_parametrize(repo, bus, name, should_raise):
    svc = UserService(repo, bus)
    if should_raise:
        with pytest.raises(ValueError):  # 分岐で期待が切り替わり、REDの意味が薄まる
            svc.create(name)
    else:
        assert svc.create(name)
```

---

### `parametrize` の指針

最初期の RED では代表値や境界の **2〜3ケースのみ** 使ってよい。網羅の拡張は GREEN 後に行う。正常系と異常系を同じ `parametrize` に混ぜない。

---

### fixture 導入の判断

同じ前処理が 3箇所以上か 30行規模になったら fixture 化する。
fixture は意図が推測できる英語名にし、過度なネストは避ける。
