# 部署文档

## 1. 环境要求

- Python ≥ 3.11（使用了 `X | None` 类型语法）
- SQLite 需启用 FTS5（Python 官方发行版自带；`python -c "import sqlite3;print(sqlite3.sqlite_version)"` 验证）
- 或 Docker ≥ 20.10

## 2. 本地 / 裸机部署

```bash
git clone <repo> && cd design-asset-search
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 导入元数据（可重复执行，按 slug 幂等更新）
python scripts/import_assets.py data/sample_assets.json --db data/assets.db

# 启动服务
ASSET_DB=data/assets.db uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

> 注意：多 worker 下 SQLite 适合读多写少场景。每次导入后无需重启（连接在请求级复用同一文件）。

### systemd 单元（/etc/systemd/system/asset-search.service）

```ini
[Unit]
Description=Design Asset Metadata Search
After=network.target

[Service]
WorkingDirectory=/opt/design-asset-search
Environment=ASSET_DB=/opt/design-asset-search/data/assets.db
ExecStart=/opt/design-asset-search/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
User=www-data

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now asset-search
```

## 3. Docker 部署

```bash
# 方式一：Dockerfile（构建时自动导入示例数据）
docker build -t asset-search .
docker run -d -p 8000:8000 -v asset-data:/srv/app/data --name asset-search asset-search

# 方式二：compose
docker compose up -d --build
```

导入新数据到运行中的容器：

```bash
docker cp new_assets.json asset-search:/tmp/
docker exec asset-search python scripts/import_assets.py /tmp/new_assets.json
```

## 4. 反向代理（Nginx，可选）

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

## 5. 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `ASSET_DB` | `data/assets.db` | SQLite 数据库文件路径 |

## 6. 验证

```bash
curl 'http://127.0.0.1:8000/api/search?q=海报'
curl 'http://127.0.0.1:8000/api/assets/poster-summer-music-festival'
python -m pytest tests/          # 运行测试
```

## 7. 备份与升级

- 备份：直接复制 `data/assets.db`（建议先 `sqlite3 assets.db "PRAGMA wal_checkpoint;"` 或使用 `.backup`）。
- 升级：拉取代码 → `pip install -r requirements.txt` → 重启服务；表结构变更由 `database.py` 中的 `CREATE ... IF NOT EXISTS` 自动处理。
