import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["ASSET_DB"] = "/tmp/test_assets.db"

from fastapi.testclient import TestClient  # noqa: E402
from app import database  # noqa: E402
from app.main import app  # noqa: E402

DB_PATH = "/tmp/test_assets.db"

SAMPLE = {
    "slug": "font-test", "title": "测试手写字体", "category": "font",
    "tags": ["字体", "手写"], "format": "TTF", "size_bytes": 1024,
    "structure": [{"path": "a.ttf", "type": "file"}], "updated_at": "2026-09-01T00:00:00Z",
}
SAMPLE2 = {
    "slug": "icon-test", "title": "测试线性图标", "category": "icon",
    "tags": ["图标", "手写", "线性"], "format": "SVG", "size_bytes": 2048,
    "structure": [], "updated_at": "2026-09-02T00:00:00Z",
}


@pytest.fixture(scope="module")
def client():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    with TestClient(app) as c:
        conn = database.connect(DB_PATH)
        database.upsert_asset(conn, SAMPLE)
        database.upsert_asset(conn, SAMPLE2)
        conn.commit()
        conn.close()
        yield c


def test_search_by_keyword(client):
    r = client.get("/api/search", params={"q": "字体"})
    assert r.status_code == 200
    assert r.json()["total"] == 1
    item = r.json()["items"][0]
    assert item["title"] == "测试手写字体" and item["format"] == "TTF"


def test_search_with_category_filter(client):
    r = client.get("/api/search", params={"q": "手写", "category": "icon"})
    assert r.status_code == 200
    assert r.json()["items"][0]["slug"] == "icon-test"


def test_asset_detail_structure_and_similar_tags(client):
    r = client.get("/api/assets/font-test")
    d = r.json()
    assert d["structure"][0]["path"] == "a.ttf"

    r2 = client.get("/api/assets/icon-test")
    assert any(s["tag"] == "字体" for s in r2.json()["similar_tags"])


def test_detail_not_found(client):
    assert client.get("/api/assets/nope").status_code == 404


def test_index_page(client):
    assert client.get("/").status_code == 200
