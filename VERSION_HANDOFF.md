# HeatScope 版本管理交接文档

更新日期：2026-09-13  
权威本地仓库：`F:\LST_AGENT\LST_AGENT_v1.0`  
远程仓库：`https://github.com/tianyalvke-blip/Tokyo-HeatScope.git`

> **当前整合发布（v1.2.3）**：请从干净工作区
> `F:\LST_AGENT\HeatScope-main-build` 的 `codex/heatscope-main-build` 分支发布。
> 它将“东京 23 区 / 町级边界图层”与“可编辑 RF 情景折线图”合并，且不带入原
> 工作区的未提交实验修改。完成审阅后，此分支的提交将成为新的本地 `main`。
>
> 版本组成：App `v1.2.1`、UI `v1.2.2`、Agent `v1.2.2`。边界 GeoJSON 已随 Git
> 追踪；200m/400m 网格、RF 模型和 PMTiles 底图仍是部署资产，见
> `RUNTIME_ASSETS.md`。下文的 v1.0/v1.1 记录是历史评测与回滚说明。

## 1. 先记住这四层

| 层 | 管什么 | 当前用于评测的版本 |
|---|---|---|
| UI | 地图、聊天框、视觉与交互呈现 | `ui-v1.1.0` |
| App | 地图工具、MCP、空间分析运行时、数据加载 | 两个 Stack 都是 `current` App |
| Agent | Prompt、意图准入、工具白名单、Evidence check | `v1.0` 与 `v1.1` 对比 |
| Evaluator | 测试集运行、工具/参数/轨迹评分 | `evaluator-v1.0.0` |

`Stack` 是一次可复现实验真正使用的组合，即 **App + Data + Agent**。UI
不改变工具行为，所以目前不放进 Stack；UI 的 Git tag 仍独立保留。

## 2. Git 当前状态

### 分支和远程

| 项目 | 当前值 |
|---|---|
| 当前本地分支 | `codex/intent-gateway` |
| 当前本地 HEAD | `e0f19f9` — `feat: add local Phoenix trace export` |
| 对应远程分支 | `origin/codex/intent-gateway`，停在 `d8b131c` |
| 同步状态 | 本地比远程 **ahead 5**，尚未推送 |
| 默认主分支 | `main`，停在 `e866dc8` |
| 原始视觉分支 | `visual-original`，也停在 `e866dc8` |
| 新视觉历史分支 | `feat/new-visual`，远程已存在 |

本地尚未推送的五次提交依次加入了评测基础设施、App/Data/Stack registry、
Evaluator registry、改进过的本地评测 UI，以及 Phoenix 导出器。推送前应先
检查 diff；不要把下面列出的地图工作区修改一起提交。

### 未提交的用户工作区修改（保留，未纳入版本）

```text
app/data/catalog.json
app/layers-input.json
app/main.js
```

这些文件属于当前地图/数据工作，提交版本管理文档或评测代码时始终使用精确
`git add -- <file>`，不要使用 `git add -A`。

## 3. 已冻结的 Git 标签

| 维度 | 版本 | 标签 | 基准提交 | 含义 |
|---|---|---|---|---|
| 原始视觉 | 原始版 | `visual-original-20260910` | `e866dc8` | 原视觉方案恢复点 |
| UI | v1.0.0 | `ui-v1.0.0` | `e866dc8` | 原始 UI |
| UI | v1.1.0 | `ui-v1.1.0` | `d31f232` | 当前视觉重设计 |
| App | v1.0.0 | `app-v1.0.0` | `e866dc8` | 原始运行时 |
| App | v1.1.0 | `app-v1.1.0` | `dc970d8` | 当前共享运行时的发布点 |
| Agent | v1.0.0 | `agent-v1.0.0` | `e866dc8` | 无 Intent Gateway 的原始行为 |
| Agent | v1.1.0 | `agent-v1.1.0` | `657f9bc` | Intent Gateway + Evidence check |
| Evaluator | v1.0.0 | `evaluator-v1.0.0` | `f9ca7e4` | 初始确定性评分器 |
| 项目文档 | v1.1.0 | `project-v1.1.0` | `d8b131c` | 项目/UI 发布说明 |

标签是不可变的“历史快照”；registry 中的 `current` / `latest` 是可移动的
“当前指针”。不要把两者混用。

## 4. 当前 Registry 与评测组合

### Agent registry

`agents/registry.yaml`：

| 名称/别名 | 实际版本 | 配置 | 行为 |
|---|---|---|---|
| `gateway_off` | `v1.0` | `configs/agents/v1.0.yaml` | 当前 App 中关闭 Intent Gateway，走原始自由工具循环 |
| `gateway_on` | `v1.1` | `configs/agents/v1.1.yaml` | 开启 Intent Gateway、Task Frame、白名单与 Evidence check |

重要：评测里的 `v1.0` 是**受控消融版本**——用相同的当前 App/Data，只关闭
Gateway；它不是把整个项目 checkout 回 2026-09-10。这样比较到的差异才主要
来自 Agent 架构，而不是数据、工具或 UI。

### App、Data 与 Stack registry

| Stack | App | Data | Agent | 用途 |
|---|---|---|---|---|
| `stack-v1.0` / `baseline` | `current` | `current` | `v1.0` | 基线 |
| `stack-v1.1` / `latest` | `current` | `current` | `v1.1` | Intent Gateway 实验组 |

App manifest：`configs/apps/current.yaml`  
Data manifest：`configs/data/current.yaml`

当前 Data 标识为 `tokyo-lst-current`：200m LST grid、`eStat-2020` 边界、
`rf_current` 与 `policy_rag_v1`。当前 App/Data 均是可移动的 `current`，尚未
冻结为下一次发布标签。**当你新增数据、工具、模型或数据加载方式时，必须先
创建 App/Data 新 manifest（例如 `v1.2`），再创建新的 Stack；不能只改
`current` 后继续拿旧 Stack 作公平比较。**

### Evaluator registry

`evaluator-v1.0.0` 只包含无外部模型的确定性规则：

1. `tool_selection`
2. `tool_arguments`
3. `execution_success`
4. `trace_completeness`

它还没有地理合理性、数值正确性、LST/气温表述或边界正确性的领域评分。
这些应在你定义 Rubric 后作为 `evaluator-v1.1` 新增，不应修改旧评分含义。

## 5. 评测与 Phoenix

### 原有本地 Benchmark

```powershell
# 相同 App/Data 下，对比两个 Agent
.venv\Scripts\python evaluation\benchmark.py --stacks stack-v1.0 stack-v1.1 --dataset core_v1 --workers 4

# 旧的轻量浏览页（端口 8844）
.venv\Scripts\python evaluation\dashboard.py
```

测试集：`evaluation/datasets/core_v1.jsonl`  
结果库：`evaluation/results/runs.duckdb`（本地、Git 忽略）  
原始轨迹：`evaluation/results/raw/<run_id>/`（本地、Git 忽略）

没有 `HEATSCOPE_LLM_ENDPOINT` 与 `HEATSCOPE_LLM_API_KEY` 时，评测会使用
fixture mode。它只能验证工具链/评分器接线，**不能证明真实模型质量**。

### Phoenix（当前推荐的交互查看界面）

地址：`http://127.0.0.1:6006`  
本地项目名：`HeatScope Evaluation`

已安装在独立目录 `evaluation/.phoenix-venv/`，该目录被 Git 忽略，不污染
HeatScope 运行时 `.venv`。已经导入过一组 `stack-v1.0` 对 `stack-v1.1` 的
benchmark trace；在 Phoenix 的 Trace 页面用 `heatscope.stack_id`、
`heatscope.case_id`、`heatscope.run_id` 筛选即可对比。

每次跑完后导入：

```powershell
evaluation\.phoenix-venv\Scripts\python.exe evaluation\phoenix_export.py --run <run_id>
```

Phoenix 仅在本机运行，未接入云端 API、未上传 HeatScope trace。当前安装的
Phoenix 20.11.0 在 Windows 首次启动会尝试下载一个可选 WASM sandbox 文件，
导致启动卡住；为本机 `.phoenix-venv` 中的 vendor 文件做了一个**未纳入 Git 的
本地补丁**，跳过该 sandbox 预取。它不影响 Trace、Dataset、Experiment 与人工
标注；但重建 `.phoenix-venv` 后需重新处理这个启动问题。

## 6. 日常版本发布流程

### 仅改 Agent（Prompt、Intent、白名单、Evidence check）

1. 新建 `configs/agents/v1.x.yaml`。
2. 在 `agents/registry.yaml` 注册；检查 `gateway_on/latest` 指向。
3. 更新 `AGENT_VERSIONING.md`。
4. 测试 `node test/test_intent_gateway.mjs`，再对 `stack-v1.0` / 新 Stack 跑相同数据集。
5. 只暂存 Agent 相关文件，提交、打 `agent-v1.x.0` 标签。

### 改 App / Data / Tool / 模型

1. 新建 `configs/apps/v1.x.yaml` 和/或 `configs/data/v1.x.yaml`。
2. 更新 `apps/registry.yaml`；若 Data 有 registry，也更新 Data 指针。
3. 新建 `stacks/registry.yaml` 条目，例如 `stack-v1.2`，不要覆盖旧 Stack。
4. 运行旧/新 Stack 对比；提交、打 `app-v1.x.0`（必要时另打 data 标签）。

### 仅改 UI

1. 不改 Agent/App registry。
2. 提交视觉文件，更新 UI 说明。
3. 打 `ui-v1.x.0` 标签。

### 改评分标准

1. 在 `evaluation/evaluators/` 新增实现，创建 `configs/evaluators/v1.x.yaml`。
2. 注册到 `evaluators/registry.yaml`，不要篡改 `v1.0` 的分数含义。
3. 用既有 raw trace 重评分或重新跑 benchmark。
4. 打 `evaluator-v1.x.0` 标签。

## 7. 推送与服务器注意事项

### GitHub

当前分支比 `origin/codex/intent-gateway` 多 5 个提交。确认无误后再执行：

```powershell
git push origin codex/intent-gateway
git push origin --tags
```

不要盲推 `main`；先通过 Pull Request 或确认后再合并。推送前应确保上述三个
未提交的地图文件仍未被暂存。

### 服务器

上一次交接记录显示服务器是长期 `scp` 部署，且其 Git HEAD 可能落后于实际
运行文件。因此服务器部署状态**本次未重新核验**；不要在服务器项目目录盲目
执行 `git pull`，以免覆盖已直接部署的修改。部署前先备份，明确选择要部署的
Git commit/标签，再同步对应文件与重启服务。

## 8. 下一位维护者的起点

1. 先运行 `git status --short --branch`，确认那三个地图文件仍是用户工作。
2. 若要继续 Agent 实验，优先用 Phoenix Trace 查看失败 case，而非只看通过率。
3. 由领域专家定义地理/LST/边界 Rubric 后，新增 `evaluator-v1.1`。
4. 数据或工具变更时先冻结新的 App/Data/Stack，再开始比较。
5. 确认后再推送当前 5 个本地提交。
