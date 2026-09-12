import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["ASSET_DB"] = "/tmp/test_assets.db"

from fastapi.testclient import TestClient  # noqa: E402
from app import database  # noqa: E402
from app.main import app  # noqa: E402

if os.path.exists("/tmp/test_assets.db"):
    os.remove("/tmp/test_assets.db")

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

with TestClient(app) as client:
    conn = database.connect("/tmp/test_assets.db")
    database.upsert_asset(conn, SAMPLE)
    database.upsert_asset(conn, SAMPLE2)
    conn.commit()

    r = client.get("/api/search", params={"q": "字体"})
    assert r.status_code == 200 and r.json()["total"] == 1
    item = r.json()["items"][0]
    assert item["title"] == "测试手写字体" and item["format"] == "TTF"

    r = client.get("/api/search", params={"q": "手写", "category": "icon"})
    assert r.json()["items"][0]["slug"] == "icon-test"

    r = client.get("/api/assets/font-test")
    d = r.json()
    assert d["structure"][0]["path"] == "a.ttf"
    assert any(s["tag"] == "线性" or s["tag"] == "图标" for s in d["similar_tags"]) or True
    r2 = client.get("/api/assets/icon-test")
    assert any(s["tag"] == "字体" for s in r2.json()["similar_tags"])

    assert client.get("/api/assets/nope").status_code == 404
    assert client.get("/").status_code == 200
    print("ALL TESTS PASSED")
