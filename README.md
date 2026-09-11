# Tokyo HeatScope / 智慧城市热分析平台 HeatScope

> 交接版（2026-09-12）。以下以当前本地仓库和线上运行状态为准。部署主机信息不写入公开仓库。

## 当前状态

- 线上地址：<https://heatscope.cloud>；`/` 为 Cal-inspired 浅色首页，`/?mode=map` 进入地图工作台。
- 地图包含东京 200 m LST 网格、400 m 预览、昼/夜图层、空间统计、RF 情景预测和政策 RAG。
- 3D planning scenario model 已接入：建筑高度/亮度变化及内部建筑随机减少动画，外围建筑保持不动。
- 结果图层已修复分类解析、颜色映射、填充透明度和桌面端图例同步问题。

## 权威代码与 Git 警告

真实本地仓库：`F:\LST_AGENT\LST_AGENT_v1.0`（有 `.git`）。不要使用同级不完整目录 `F:\LST_AGENT_v1.0`。

- GitHub：<https://github.com/tianyalvke-blip/Tokyo-HeatScope>
- 默认分支：`main`；正式版本以 Git tag 为准。
- 服务器工作区可能由部署流程直接更新，**不要在服务器上盲目 `git pull`**；更新前先做快照并核对差异。

## 线上服务器

| 项目 | 值 |
|---|---|
| 环境 | 受保护的 Linux 部署主机 |
| 资源 | 由部署环境配置管理 |
| 项目路径 | 由部署脚本配置，不写入公开仓库 |
| Python | 系统 Python；项目虚拟环境按依赖文件创建 |
| 域名 | 由部署环境配置管理 |

```text
浏览器 → Caddy :443/:80（HTTPS、gzip）
             ├─ /mcp → 127.0.0.1:8765 → heatscope-mcp.service
             └─ 其他 → 127.0.0.1:8100 → heatscope-web.service
```

- `heatscope-mcp.service`：`server/mcp_data_server.py`，FastMCP 数据/分析工具。
- `heatscope-web.service`：`server/serve.py`，静态文件、gzip、Range/CORS、`/api/geocode`、`/api/llm` 代理。
- 反向代理和 systemd 配置由部署环境管理，不纳入公开仓库。
- LLM 密钥通过运行环境注入；服务器不要放 `app/config.json`。

```bash
sudo systemctl status heatscope-mcp.service heatscope-web.service
sudo systemctl restart heatscope-mcp.service heatscope-web.service
sudo journalctl -u heatscope-mcp.service -f
sudo journalctl -u heatscope-web.service -f
```

## 关键文件

- `app/index.html`：营销首页；`app/map.html`：地图工作台。
- `app/cal-ui.css`：统一 Cal 风格视觉层。
- `app/map-manager.js`：MapLibre、Protomaps、LST 栅格、道路/水体和图例。
- `app/result-layer-manager.js`：分析结果图层、分类/连续色带和图例。
- `app/i18n.js`：EN / 日本語 / 中文文案。
- `app/agent.js`、`app/chat-ui.js`、`app/tool-registry.js`：自然语言 Agent。
- `app/viewer/index.html`、`app/viewer/viewer.js`：3D planning scenario model。
- `app/layers-input.json`：图层和模型输入声明。

前端是原生 ES modules，无构建步骤。修改后使用 Ctrl+Shift+R；本地 `8780` 端口只是临时预览。

### 数据与模型

```text
app/data/tokyo_lst_grid.geojson       200 m，约 14,896 格
app/data/tokyo_lst_grid_400m.geojson  400 m，约 4,055 格
app/data/tokyo_lst_grid.parquet       DuckDB / 空间分析
app/data/basemap/*.pmtiles            东京 OSM Protomaps 底图
app/data/models/rf/rf_day.joblib      昼间 RF
app/data/models/rf/rf_night.joblib    夜间 RF
server/cache/analysis-results/        结果 GeoJSON 与 metadata
```

LST 是 land surface temperature（地表温度），不是空气温度；因果结论必须有真实分析支持。

## 本地启动

```powershell
cd F:\LST_AGENT\LST_AGENT_v1.0
.\start.ps1
```

或：

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements-spatial.txt -r requirements-ingest.txt tqdm
.venv\Scripts\python scripts\start_servers.py
```

打开 <http://localhost:8100/>；停止：`.venv\Scripts\python scripts\stop_servers.py`。

## 安全部署与回滚

采用“备份后上传文件”的方式，不直接用服务器 Git 覆盖工作区。以下仅为占位示例：

```powershell
$server = "<deployment-host>"
$remoteRoot = "<project-root>"
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
ssh $server "mkdir -p $remoteRoot/backups/ui-$stamp/app"
ssh $server "cp $remoteRoot/app/map.html $remoteRoot/backups/ui-$stamp/app/map.html"
scp "app\map.html" "$server`:$remoteRoot/app/map.html"
ssh $server "sudo systemctl restart heatscope-web.service"
```

回滚明确文件：

```bash
ssh <deployment-host> "cp <project-root>/backups/<目录>/app/map.html <project-root>/app/map.html && sudo systemctl restart heatscope-web.service"
```

服务器备份由部署环境保存；本地原 UI 备份在 `app/_local-ui-backup-20260910-201247-files/`。

## 结果图层排错

```text
自然语言 → query/local_moran/rf_predict/run_python
         → analysis_id + GeoJSON → create_result_layer
         → set_style/show_layer → 地图填充与图例
```

分类元数据兼容：`categories` 为颜色对象、对象数组，或字符串数组搭配 `colors`/`color`。此前“只有边框没有填充”是数组被错误地用 `Object.entries` 解析，生成无效 MapLibre `match`；现已修复。分类默认 opacity 为 `0.92`，`set_style` 后图例从实际颜色表达式同步。若再次出现灰色/空白：强刷、重建结果图层，检查 `server/cache/analysis-results/*.meta.json` 和 GeoJSON properties，再查看浏览器控制台及 MCP 日志。

## Python 无限循环边界

`server/python_runner.py` 在独立子进程中运行 Python，默认 `timeout=30` 秒，超时会终止本次运行，所以默认 `while True` 通常不会直接弄崩网页。但它不是完整沙箱：可传更长 timeout，且与服务共用 CPU/内存；高负载可能导致 MCP 变慢、OOM 或 systemd 重启。不要在 SSH 中直接运行无保护无限循环。建议后续限制最大 timeout（如 60 秒）、按进程组终止，并为服务设置 `MemoryMax`/`CPUQuota`。

## 验收清单

- 首页、地图和 3D viewer 均返回 200，语言切换标题正确。
- 底图、400 m→200 m 网格、昼/夜图例正常。
- 九类昼夜结果显示彩色填充和九项图例，不仅有边框。
- 水体为较深半透明灰蓝色，道路位于水体下方，无额外河流中心线。
- 3D 高度变化稳定，变化建筑高亮，外围建筑不减少。
- `heatscope-mcp.service`、`heatscope-web.service`、Caddy 均为 `active`。
- logrotate 只轮转 `.systemd.log`，不要处理 `server/cache/*.parquet`。

## 数据重建与测试

```powershell
.venv\Scripts\python scripts\prepare_data.py
.venv\Scripts\python scripts\build_400m.py
python scripts/policy_ingestion/qa.py
PYTHONPATH=. python test/test_policy_retrieval.py
python server/test_mcp.py
```

重建会覆盖生成数据，执行前确认输入文件和备份。

## 待办与限制

- 3 Mbps 多人使用时可能偏慢，可评估升级 5 Mbps。
- 搜索引擎可能缓存旧标题，需要单独更新收录。
- 服务器 Git 与工作区仍需择机整理，整理前保留线上快照。
- 数值型规划结论必须来自真实 RF 运行结果和地图证据，拒绝猜测。

本地 `HANDOFF.md` 仅供交接使用，不应上传到公开仓库。
