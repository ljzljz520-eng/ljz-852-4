#!/usr/bin/env python3
"""素材元数据导入脚本。

用法:
    python scripts/import_assets.py data/sample_assets.json
    python scripts/import_assets.py assets.csv --db data/assets.db

支持 JSON（对象数组）与 CSV。必填字段: slug,title,category,format,updated_at
可选字段: tags(数组或 ; 分隔), size_bytes, license, source_url, structure(数组或JSON字符串)
"""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import database  # noqa: E402

REQUIRED = ["slug", "title", "category", "format", "updated_at"]
CATEGORIES = {"poster", "font", "icon", "template"}


def normalize(rec: dict, lineno: int) -> dict:
    missing = [k for k in REQUIRED if not rec.get(k)]
    if missing:
        raise ValueError(f"第 {lineno} 条缺少字段: {missing}")
    if rec["category"] not in CATEGORIES:
        raise ValueError(f"第 {lineno} 条 category 非法: {rec['category']}")
    tags = rec.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(";") if t.strip()]
    structure = rec.get("structure") or []
    if isinstance(structure, str):
        structure = json.loads(structure)
    return {
        "slug": rec["slug"].strip(),
        "title": rec["title"].strip(),
        "category": rec["category"],
        "tags": tags,
        "format": rec["format"].strip(),
        "size_bytes": int(rec.get("size_bytes") or 0),
        "license": rec.get("license") or "CC0",
        "source_url": rec.get("source_url") or "",
        "structure": structure,
        "updated_at": rec["updated_at"],
    }


def load(path: Path) -> list[dict]:
    if path.suffix.lower() == ".csv":
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("JSON 顶层必须是数组")
    return data


def main() -> int:
    ap = argparse.ArgumentParser(description="导入设计素材元数据")
    ap.add_argument("file", help="JSON 或 CSV 文件路径")
    ap.add_argument("--db", default="data/assets.db", help="SQLite 数据库路径")
    args = ap.parse_args()

    records = load(Path(args.file))
    conn = database.connect(args.db)
    ok, fail = 0, 0
    with conn:
        for i, rec in enumerate(records, 1):
            try:
                database.upsert_asset(conn, normalize(rec, i))
                ok += 1
            except Exception as e:  # noqa: BLE001
                fail += 1
                print(f"[跳过] {e}", file=sys.stderr)
    print(f"导入完成: 成功 {ok} 条, 失败 {fail} 条 -> {args.db}")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
