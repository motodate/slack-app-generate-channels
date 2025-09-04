"""
構造テスト: SlackClient Facade が存在し、公開メソッドの形が期待どおりである
"""

import importlib
import inspect


def test_slack_client_class_and_ctor_signature():
    """構造: `SlackClient` が存在し、`__init__(self, web_client)` を公開する"""
    mod = importlib.import_module("app.infrastructure.slack_client")
    assert hasattr(mod, "SlackClient"), "SlackClient クラスが見つかりません"

    cls = mod.SlackClient
    # __init__(self, web_client)
    sig = inspect.signature(cls.__init__)
    params = list(sig.parameters.values())
    assert len(params) >= 2, "SlackClient.__init__ は web_client を1引数で受け取る想定"
    assert params[1].name == "web_client"


def test_slack_client_public_methods_exist():
    """構造: 必須の公開メソッドが存在し、インスタンスから参照できる"""
    mod = importlib.import_module("app.infrastructure.slack_client")
    sc = mod.SlackClient(web_client=object())

    # 必須の公開メソッドが存在すること
    for name in (
        "open_view",
        "update_view",
        "create_channel",
        "invite_users",
        "post_message",
        "lookup_user_by_email",
    ):
        assert hasattr(sc, name), f"SlackClient.{name} が存在しません"
