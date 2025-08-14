import os
import time
from app.services.oauth_service import OAuthService
from app.services.oauth_service import OAuthError
from app.db import models
from sqlalchemy.orm import Session
import pytest
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from google.oauth2.credentials import Credentials
from prometheus_client import CollectorRegistry, generate_latest
import re


def test_state_store_capacity_pruning():
    # Arrange: set fake client credentials
    os.environ['GOOGLE_CLIENT_ID'] = 'cid'
    os.environ['GOOGLE_CLIENT_SECRET'] = 'csecret'
    svc = OAuthService()
    # ensure clean store
    if hasattr(svc.state_store, 'raw'):
        svc.state_store.raw.clear()
    # inject deterministic time provider
    virtual = [0.0]
    if hasattr(svc.state_store, 'time_provider'):
        svc.state_store.time_provider = lambda: virtual[0]

    # Act: generate many states beyond capacity threshold (expect pruning)
    for _ in range(101):
        svc.start_google_auth("http://localhost/callback")
        virtual[0] += 0.001

    # Assert: capacity enforced
    # Updated: use underlying state_store (MemoryStateStore)
    assert svc.state_store.size() <= 50, f"state store size exceeded limit: {svc.state_store.size()}"


def test_state_store_ttl_pruning():
    # Arrange
    os.environ['GOOGLE_CLIENT_ID'] = 'cid'
    os.environ['GOOGLE_CLIENT_SECRET'] = 'csecret'
    svc = OAuthService()
    # ensure clean store
    if hasattr(svc.state_store, 'raw'):
        svc.state_store.raw.clear()
    # inject deterministic time provider
    virtual = [0.0]
    if hasattr(svc.state_store, 'time_provider'):
        svc.state_store.time_provider = lambda: virtual[0]
    # 短い TTL を設定（インスタンスに上書き）
    svc._STATE_TTL_SECONDS = 0.02

    first = svc.start_google_auth("http://localhost/callback")
    first_state = first['state']
    # advance virtual clock beyond TTL
    virtual[0] += 0.06

    # Act: 次の start 呼び出しで古い state が pruning されるはず
    svc.start_google_auth("http://localhost/callback")

    # Assert
    # Access underlying raw dict via .raw property
    assert first_state not in svc.state_store.raw, "期限切れ state が pruning されていない"
    assert svc.state_store.size() <= 2  # 新しいものだけ（理想は1）


def test_exchange_invalid_state(monkeypatch, tmp_path):
    os.environ['GOOGLE_CLIENT_ID'] = 'cid'
    os.environ['GOOGLE_CLIENT_SECRET'] = 'csecret'
    svc = OAuthService()

    # ダミー DB セッションをモック (Session を受け取るが使われないパスで例外になる想定)
    class DummySession:
        def query(self, *a, **k):
            raise AssertionError("Should not query DB when state is invalid")

    # Act & Assert
    with pytest.raises(OAuthError) as exc:
        svc.exchange_google_code(DummySession(), user_id="u1", code="dummy", redirect_uri="http://localhost/cb", state="nonexistent")
    assert exc.value.code == "OAUTH_STATE_INVALID"


def test_token_refresh(monkeypatch):
    os.environ['GOOGLE_CLIENT_ID'] = 'cid'
    os.environ['GOOGLE_CLIENT_SECRET'] = 'csecret'
    svc = OAuthService()

    # IntegrationAccount を作成 (expires_at を過去に設定)
    past = datetime.now(timezone.utc) - timedelta(minutes=10)
    integ = models.IntegrationAccount(
        id="int1",
        user_id="u1",
        provider="google",
        scopes=svc.GOOGLE_SCOPES,
        access_token_hash=svc._hash_token("old_access"),
        refresh_token_hash=svc._hash_token("old_refresh"),
        expires_at=past,
        sync_token=None,
        revoked_at=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # ダミー DB セッション: commit だけ受け取る
    class DummyDB:
        def commit(self):
            pass
    db = DummyDB()

    # google Credentials.refresh をモック
    def fake_refresh(self, request):
        # 新しい token と expiry に差し替える
        object.__setattr__(self, 'token', 'new_access')
        object.__setattr__(self, 'expiry', datetime.now(timezone.utc) + timedelta(hours=1))

    monkeypatch.setattr("google.oauth2.credentials.Credentials.refresh", fake_refresh)

    # refresh 判定を確実に True にするため expired プロパティを常に True にパッチ
    monkeypatch.setattr(Credentials, 'expired', property(lambda self: True))
    integ.expires_at = past

    # expired をシミュレートするため credentials.expired True になるよう expires_at 過去の値を使う
    before = integ.expires_at
    creds = svc.get_valid_credentials(db, integ)
    # アップデートされたはず: expiry が更新 (strict に過去値より後)
    assert integ.expires_at and integ.expires_at > before
    # トークンは _hash_token で new_access のハッシュに更新されている必要
    assert integ.access_token_hash == svc._hash_token('new_access')


def test_revoke_integration_blocks_future_use(monkeypatch):
    os.environ['GOOGLE_CLIENT_ID'] = 'cid'
    os.environ['GOOGLE_CLIENT_SECRET'] = 'csecret'
    svc = OAuthService()

    future = datetime.now(timezone.utc) + timedelta(hours=1)
    integ = models.IntegrationAccount(
        id="int2",
        user_id="u2",
        provider="google",
        scopes=svc.GOOGLE_SCOPES,
        access_token_hash=svc._hash_token("access_tok"),
        refresh_token_hash=None,
        expires_at=future,
        sync_token=None,
        revoked_at=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    class DummyDB:
        def commit(self):
            pass
    db = DummyDB()

    # requests.post をダミー化（失敗しても無視されるが念のため）
    monkeypatch.setattr("requests.post", lambda *a, **k: None)

    # まだ revoked でないので資格情報取得できる
    creds_before = svc.get_valid_credentials(db, integ)
    assert creds_before is not None

    # Revoke 実行
    svc.revoke_integration(db, integ)
    assert integ.revoked_at is not None

    # 以後の利用は拒否されるべき
    with pytest.raises(OAuthError) as exc:
        svc.get_valid_credentials(db, integ)
    assert exc.value.code == "INTEGRATION_REVOKED"


def test_unhash_token_placeholder_identity():
    """_unhash_token は現状ハッシュ値を復号せずそのまま返す (プレースホルダ) ことを明示。

    将来 AES 等で暗号化格納 + 復号に変更した際、このテストは削除/更新予定。
    """
    os.environ['GOOGLE_CLIENT_ID'] = 'cid'
    os.environ['GOOGLE_CLIENT_SECRET'] = 'csecret'
    svc = OAuthService()
    original = 'secret-token'
    hashed = svc._hash_token(original)
    recovered = svc._unhash_token(hashed)
    # 現状: recovered は original ではなく hashed と一致 (本来のトークン値は失われる)
    assert recovered == hashed
    assert recovered != original


def test_oauth_metrics_exposed(monkeypatch):
    os.environ['GOOGLE_CLIENT_ID'] = 'cid'
    os.environ['GOOGLE_CLIENT_SECRET'] = 'csecret'
    svc = OAuthService()
    # start -> increments start counter
    svc.start_google_auth("http://localhost/cb")

    # exchange (force error path to increment outcome=error)
    class DummyDB: pass
    with pytest.raises(OAuthError):
        svc.exchange_google_code(DummyDB(), user_id='u', code='bad', redirect_uri='http://localhost/cb', state=None)

    # metrics text (global registry) を取得
    metrics_text = generate_latest().decode('utf-8')
    assert 'schedule_concierge_oauth_start_total' in metrics_text
    assert 'schedule_concierge_oauth_exchange_total' in metrics_text
    # レーベル outcome="error" が含まれる
    assert 'outcome="error"' in metrics_text
    # State size gauge (may be 1 after start)
    assert 'schedule_concierge_oauth_state_store_size' in metrics_text


def test_integration_stores_encrypted_tokens(monkeypatch):
    os.environ['GOOGLE_CLIENT_ID'] = 'cid'
    os.environ['GOOGLE_CLIENT_SECRET'] = 'csecret'
    svc = OAuthService()

    # モック Flow.fetch_token を差し替えて credentials 相当を注入
    class DummyCreds:
        def __init__(self):
            self.token = 'access123'
            self.refresh_token = 'refresh123'
            self.expiry = datetime.now(timezone.utc) + timedelta(hours=1)

    class DummyFlow:
        def __init__(self, *a, **k):
            self.credentials = DummyCreds()
        def fetch_token(self, **k):
            pass

    monkeypatch.setattr('app.services.oauth_service.Flow.from_client_config', lambda *a, **k: DummyFlow())

    class DummyDB:
        def __init__(self):
            self._added = []
        def query(self, *a, **k):
            class Q:
                def filter(self2, *aa, **kk):
                    class R:
                        def first(self3):
                            return None
                    return R()
            return Q()
        def add(self, obj):
            self._added.append(obj)
        def commit(self):
            pass
    db = DummyDB()

    integ = svc.exchange_google_code(db, user_id='u1', code='x', redirect_uri='http://cb')
    assert integ.access_token_encrypted is not None
    assert integ.refresh_token_encrypted is not None
    # 平文は保存されていない（ハッシュとの差異で弱いが: encrypted 文字列は元より長い想定）
    assert 'access123' not in integ.access_token_encrypted
