# 设计素材元数据搜索

输入海报、字体、图标或模板关键词，返回公开素材的**标题、标签、格式、大小、更新时间**；
详情页展示**资源结构**并推荐**相近标签**（基于标签共现）。

## 功能

| 模块 | 说明 |
|---|---|
| 搜索服务 | FastAPI + SQLite FTS5，支持关键词前缀匹配与分类过滤 |
| 前端页面 | `/` 单页搜索界面，点击卡片查看详情 |
| 导入脚本 | `scripts/import_assets.py`，支持 JSON / CSV，幂等 upsert |
| 部署 | Dockerfile / docker-compose / 裸机 systemd，见 `docs/DEPLOYMENT.md` |

## 快速开始

```bash
pip install -r requirements.txt
python scripts/import_assets.py data/sample_assets.json
uvicorn app.main:app --reload
# 打开 http://127.0.0.1:8000
```

## API

### `GET /api/search`
参数：`q`（关键词）、`category`（poster|font|icon|template）、`limit`、`offset`

```json
{
  "total": 3,
  "items": [{
    "slug": "poster-summer-music-festival",
    "title": "夏日音乐节海报",
    "category": "poster",
    "tags": ["海报", "音乐节", "夏日", "渐变", "插画"],
    "format": "PSD",
    "size_bytes": 48234496,
    "updated_at": "2026-08-20T10:30:00Z"
  }]
}
```

### `GET /api/assets/{slug}`
在摘要基础上额外返回 `license`、`source_url`、`structure`（资源结构树）、`similar_tags`（相近标签及共现次数）。

### `GET /api/categories`
各分类素材数量。

## 元数据格式

| 字段 | 必填 | 说明 |
|---|---|---|
| slug | ✓ | 唯一标识，用于 upsert |
| title | ✓ | 标题 |
| category | ✓ | poster / font / icon / template |
| tags | | 标签数组（CSV 中用 `;` 分隔） |
| format | ✓ | PSD / AI / TTF / OTF / SVG / PNG / Figma / Sketch … |
| size_bytes | | 文件大小（字节） |
| license | | CC0 / CC-BY / OFL …，默认 CC0 |
| source_url | | 公开来源链接 |
| structure | | 资源结构（文件/目录/图层树，JSON 数组） |
| updated_at | ✓ | ISO 8601 时间 |

## 项目结构

```
app/main.py            FastAPI 服务与路由
app/database.py        SQLite FTS5 存储层（搜索/详情/相近标签）
app/static/index.html  搜索页面
scripts/import_assets.py  导入脚本（JSON/CSV）
data/sample_assets.json   示例数据（10 条）
docs/DEPLOYMENT.md     部署文档
tests/test_api.py      接口测试
```
