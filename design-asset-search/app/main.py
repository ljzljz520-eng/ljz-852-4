"""设计素材元数据搜索服务（FastAPI）。"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import database

DB_PATH = os.environ.get("ASSET_DB", "data/assets.db")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = database.connect(DB_PATH)
    yield
    app.state.db.close()


app = FastAPI(title="Design Asset Metadata Search", version="1.0.0", lifespan=lifespan)


@app.get("/api/search")
def api_search(
    q: str = Query("", description="关键词，如：海报 / 字体 / icon / 模板"),
    category: str | None = Query(None, description="poster|font|icon|template"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """返回标题、标签、格式、大小、更新时间。"""
    return database.search(app.state.db, q.strip(), category, limit, offset)


@app.get("/api/assets/{slug}")
def api_detail(slug: str):
    """详情：资源结构 + 相近标签。"""
    d = database.get_detail(app.state.db, slug)
    if not d:
        raise HTTPException(404, "asset not found")
    return d


@app.get("/api/categories")
def api_categories():
    rows = app.state.db.execute(
        "SELECT category, count(*) c FROM assets GROUP BY category ORDER BY c DESC"
    ).fetchall()
    return [{"category": r["category"], "count": r["c"]} for r in rows]


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
