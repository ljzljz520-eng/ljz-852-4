"""SQLite FTS5 存储层：建表、写入、搜索、详情、相近标签。"""
import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS assets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    slug        TEXT UNIQUE NOT NULL,
    title       TEXT NOT NULL,
    category    TEXT NOT NULL,            -- poster / font / icon / template
    tags        TEXT NOT NULL,            -- JSON array
    format      TEXT NOT NULL,            -- PSD / AI / TTF / SVG ...
    size_bytes  INTEGER NOT NULL,
    license     TEXT NOT NULL DEFAULT 'CC0',
    source_url  TEXT,
    structure   TEXT NOT NULL DEFAULT '[]', -- JSON: 资源结构（文件/图层树）
    updated_at  TEXT NOT NULL             -- ISO 8601
);

CREATE VIRTUAL TABLE IF NOT EXISTS assets_fts USING fts5(
    title, category, tags_text, format,
    content='assets', content_rowid='id',
    tokenize='unicode61'
);

CREATE TRIGGER IF NOT EXISTS assets_ai AFTER INSERT ON assets BEGIN
    INSERT INTO assets_fts(rowid, title, category, tags_text, format)
    VALUES (new.id, new.title, new.category,
            (SELECT group_concat(value, ' ') FROM json_each(new.tags)), new.format);
END;
CREATE TRIGGER IF NOT EXISTS assets_ad AFTER DELETE ON assets BEGIN
    INSERT INTO assets_fts(assets_fts, rowid, title, category, tags_text, format)
    VALUES ('delete', old.id, old.title, old.category,
            (SELECT group_concat(value, ' ') FROM json_each(old.tags)), old.format);
END;
CREATE TRIGGER IF NOT EXISTS assets_au AFTER UPDATE ON assets BEGIN
    INSERT INTO assets_fts(assets_fts, rowid, title, category, tags_text, format)
    VALUES ('delete', old.id, old.title, old.category,
            (SELECT group_concat(value, ' ') FROM json_each(old.tags)), old.format);
    INSERT INTO assets_fts(rowid, title, category, tags_text, format)
    VALUES (new.id, new.title, new.category,
            (SELECT group_concat(value, ' ') FROM json_each(new.tags)), new.format);
END;
"""


def connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)  # FastAPI 线程池复用
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def upsert_asset(conn: sqlite3.Connection, a: dict) -> None:
    conn.execute(
        """INSERT INTO assets (slug,title,category,tags,format,size_bytes,license,source_url,structure,updated_at)
           VALUES (:slug,:title,:category,:tags,:format,:size_bytes,:license,:source_url,:structure,:updated_at)
           ON CONFLICT(slug) DO UPDATE SET
             title=excluded.title, category=excluded.category, tags=excluded.tags,
             format=excluded.format, size_bytes=excluded.size_bytes, license=excluded.license,
             source_url=excluded.source_url, structure=excluded.structure, updated_at=excluded.updated_at""",
        {
            "slug": a["slug"],
            "title": a["title"],
            "category": a["category"],
            "tags": json.dumps(a.get("tags", []), ensure_ascii=False),
            "format": a["format"],
            "size_bytes": int(a.get("size_bytes", 0)),
            "license": a.get("license", "CC0"),
            "source_url": a.get("source_url", ""),
            "structure": json.dumps(a.get("structure", []), ensure_ascii=False),
            "updated_at": a["updated_at"],
        },
    )


def _row_to_summary(r: sqlite3.Row) -> dict:
    return {
        "slug": r["slug"],
        "title": r["title"],
        "category": r["category"],
        "tags": json.loads(r["tags"]),
        "format": r["format"],
        "size_bytes": r["size_bytes"],
        "updated_at": r["updated_at"],
    }


def search(conn, query: str, category: str | None, limit: int, offset: int) -> dict:
    where, params = [], []
    if query:
        # 每个词加前缀通配，空格分词后 AND
        terms = [t for t in query.replace('"', " ").split() if t]
        if terms:
            where.append("assets_fts MATCH " + " AND ".join("?" for _ in terms))
            params.extend(f'"{t}"*' for t in terms)
    if category:
        where.append("a.category = ?")
        params.append(category)
    cond = ("WHERE " + " AND ".join(where)) if where else ""
    base = f"FROM assets a JOIN assets_fts f ON a.id = f.rowid {cond}" if query else f"FROM assets a {cond}"
    total = conn.execute(f"SELECT count(*) {base}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT a.* {base} ORDER BY " + ("bm25(assets_fts), " if query else "") + "a.updated_at DESC LIMIT ? OFFSET ?",
        params + [limit, offset],
    ).fetchall()
    return {"total": total, "items": [_row_to_summary(r) for r in rows]}


def get_detail(conn, slug: str) -> dict | None:
    r = conn.execute("SELECT * FROM assets WHERE slug = ?", (slug,)).fetchone()
    if not r:
        return None
    d = _row_to_summary(r)
    d.update({
        "license": r["license"],
        "source_url": r["source_url"],
        "structure": json.loads(r["structure"]),
        "similar_tags": similar_tags(conn, json.loads(r["tags"]), r["slug"]),
    })
    return d


def similar_tags(conn, tags: list[str], exclude_slug: str, top: int = 8) -> list[dict]:
    """相近标签：与本资源标签共现次数最多的其他标签。"""
    if not tags:
        return []
    q_marks = ",".join("?" for _ in tags)
    rows = conn.execute(
        f"SELECT tags FROM assets WHERE slug != ? AND EXISTS "
        f"(SELECT 1 FROM json_each(assets.tags) je WHERE je.value IN ({q_marks}))",
        [exclude_slug, *tags],
    ).fetchall()
    own = set(tags)
    counts: dict[str, int] = {}
    for (tjson,) in rows:
        for t in json.loads(tjson):
            if t not in own:
                counts[t] = counts.get(t, 0) + 1
    return [{"tag": t, "co_count": c} for t, c in sorted(counts.items(), key=lambda x: -x[1])[:top]]
