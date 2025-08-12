import os, sys
import pytest
from fastapi.testclient import TestClient
import tempfile
import uuid

# Ensure app import path
# ルート(backend)を sys.path 先頭に追加しローカル app パッケージを優先
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from app.main import app  # noqa: E402
from app.db.session import engine, Base  # noqa: E402

@pytest.fixture(scope="function")  # Changed to function scope for fresh DB per test
def client():
    # Create fresh database for each test
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    return TestClient(app)
