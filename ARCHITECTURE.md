# ARCHITECTURE 影刀侧编排蓝图

本文档描述**影刀（ShadowBot）RPA 侧**的设计蓝图：触发与调度、流程职责、数据契约、可观测性与外部代码桥接协议。

核对来源为影刀应用目录 `apps/<app_uuid>/xbot_robot` 中的 `package.json`、生成后的流程 Python 代码与 `.dev/*.flow.json`。该目录的实际名称是 `xbot_robot`。

- Python 侧（本仓库）的结构与执行流程见 `docs/PROJECT_ARCHITECTURE_OVERVIEW.md`。
- 输入/输出契约见 `docs/SHADOWBOT_INPUT_CONTRACT.md`；影刀与 Python 的职责边界见 `docs/RPA_PYTHON_BOUNDARY.md`。

对应影刀应用：`开发模板-迭代测试`
当前规模：16 个流程（2 个可视化主干 + 1 个子流程 + 13 个 CodeFlow 能力模块）、14 个全局变量、1 个资源文件。

---

## 1. 定位

**「影刀壳 + 可版本化外部工程」的通用交付模板。**

- 影刀侧只负责：触发、编排、留证、通知、桥接。
- 业务逻辑放在本 Git 仓库：按分支检出、按 JSON 契约交接、按 `run_id` 隔离。
- 目标：可复制、可追溯、失败可见。

---

## 2. 分层蓝图

```text
┌────────────────────── 影刀平台（触发 / 调度） ──────────────────────┐
│ 编辑器触发 dev │ 管理界面触发 manual │ 触发器触发 schedule │ 任务计划 assistant │
└──────────────────────────────┬────────────────────────────────────┘
                               ▼  process.get_app_params(XBOT_PARAMS_TRIGGER_MODE)
┌───────────────────────────────────────────────────────────────────────────┐
│ main（唯一入口 · 编排层）                                                    │
│  begin生命周期 → 身份/触发/日期 → 注入凭据 → 准备代码工程                    │
│  → 应用入口(子流程) → 外部结果观察（不传播状态）→ 收尾                         │
└───┬───────────────────┬──────────────────────┬────────────────────────────┘
    │ process.run        │ process.run           │ 直接调用（模块 helper）
    ▼                    ▼                       ▼
┌─────────────┐  ┌──────────────┐   ┌─────────────────────────────────────┐
│ 准备代码工程  │  │  应用入口      │   │ 能力层（CodeFlow helper 库）          │
│ (VisualFlow) │  │ (VisualFlow)  │   │ Secrets / Tools / Initialization     │
│ 目录+Git+    │  │ 网页演示       │   │ git_check / RunEvidence              │
│ project.json │  │ +外部代码桥接   │   │ RunLedger / RpaDiagnostics /         │
└─────────────┘  └──────┬───────┘   │ FinalizeRun / feishu_* / config      │
                        ▼            └─────────────────────────────────────┘
              ┌───────────────────┐
              │ 本仓库（外部工程）   │  input_{run_id}.json → run.bat → runner_{run_id}.json
              └───────────────────┘
```

关键原则：**影刀只做编排，业务规则不下沉到可视化流程**（与 `AGENTS.md` 一致）。

---

## 3. 流程清单

| 流程 | 类型 | 角色 |
| --- | --- | --- |
| `main` | VisualFlow | **唯一入口/编排**：生命周期、身份、调度转发、通知、收尾 |
| `准备代码工程` | VisualFlow | 建目录 → Git 同步 → 生成 `project.json`；In 4 / Out 1 |
| `应用入口` | VisualFlow | 网页演示 + 外部代码桥接；In 2 |
| `Secrets` | CodeFlow | 资源文件读取（webhook / linear / ai） |
| `FinalizeRun` | CodeFlow | 远端运行记录 + 本地台账 |
| `Tools` | CodeFlow | JSON 读写等通用工具 |
| `Initialization` | CodeFlow | 目录创建 / 数据整形 |
| `git_check` | CodeFlow | 仓库克隆 / 同步 / 校验 |
| `RunEvidence` | CodeFlow | 本地证据（handoff / result / finish） |
| `RunLedger` | CodeFlow | 运行台账写入 |
| `RpaDiagnostics` | CodeFlow | 失败现场采集（步骤 / 元素 / 截图） |
| `feishu_openapi_sdk` | CodeFlow | 飞书 SDK 封装 |
| `feishu_run` | CodeFlow | 应用状态查询（**当前无调用方**） |
| `config` | CodeFlow | 配置读取（资源文件版） |
| `config_legacy` | CodeFlow | 历史配置模块（转发 `config`，**当前无调用方**） |
| `record_executor` | CodeFlow | 远端运行记录写入 |

约定：CodeFlow 一律以 `def main(args):` 为入口；被具名调用的 helper 采用普通函数名（如 `record_executor.record_run`、`FinalizeRun.finalize`），避免把业务入口与 helper 混名。

---

## 4. 调度与运行标识

- **触发**：`process.get_app_params("XBOT_PARAMS_TRIGGER_MODE")` → `触发type`，经字典归一：

  | 原始值 | 归一含义 |
  | --- | --- |
  | `dev` | 编辑器触发 |
  | `manual` | 管理界面触发 |
  | `schedule` | 触发器触发 |
  | `assistant` | 任务计划触发 |

- **调度**：真正的定时/触发器调度由影刀平台承担；模板本身不做定时器，只把触发来源写入**台账与通知**，并把执行顺序的调度权交给 `main` 的 `process.run`。
- **运行标识**：`run_id`（即 `运行开始时间`，取自 `rpa_runtime['started_at']`，如 `1789959527341`）贯穿日志、`input_{run_id}.json`、`runner_{run_id}.json`、本地证据与台账。

---

## 5. 数据契约

```text
运行级数据 → In 参数
    应用入口      : 项目代码目录、运行开始时间
    准备代码工程   : 代码工程根目录、应用名称、代码仓库地址、代码分支  → Out: 代码工程目录

跨运行稳定 → 全局变量
    is_test、是否执行外部代码、本地运行证据启用
    应用名称、帐号名称、应用UUID、today_date、rpa_pj_path
    code_git_url、code_git_branch、run_record_url、code_pj_path、code_pj_path_result

敏感 / 环境配置 → 资源文件（影刀应用内 resources/secrets.json）
    feishu(app_id/app_secret/bitable_*)、webhook(test/prod)、linear、ai
```

规则：**运行级数据走 In 参数，跨运行稳定的配置走全局变量，敏感信息走资源文件**，源码与流程内不内联明文。该规则同时写在 `main` 顶部的「【数据契约】」注释块中。

注意：资源文件位于影刀应用内部，**不在本仓库**，因此不随本仓库版本化。

---

## 6. 控制开关

| 开关（全局变量） | 默认 | 作用 |
| --- | --- | --- |
| `is_test` | `True` | 通知追加「测试环境」标记；跳过远端运行记录 |
| `是否执行外部代码` | `True` | 是否执行 `input_{run_id}.json → run.bat → 回收 runner_{run_id}.json` |
| `本地运行证据启用` | `True` | 证据/台账落盘开关（fail-open：失败不影响业务） |

用这套开关，模板可以在无外部依赖的环境中受控空跑。

---

## 7. 可观测性

三通道并行：

1. **日志**：实时输出，可导出为 `日志文件-<ts>.txt`。
2. **本地证据 + 台账**：`RPA应用空间/<应用名>/<date>/`
   - `runs/<run_id>.events.jsonl`、`<run_id>.summary.json`、`<run_id>.code.json`
   - 汇总台账 `runs.jsonl`
   - 失败时另有 `diagnostics/`（由 `RpaDiagnostics` 采集现场）
3. **飞书通知**：起 / 成 / 败各一条，统一由 `_notify` 出口发送（含测试环境标记与重试）。

`summary.json` 关键字段：`status`（影刀主流程的运行成功/运行失败）、`failure_domain`、以及外部代码观测结果 `external_success` / `external_failed` 等。两者并不等价：当前观察器不会用 Python 状态改写影刀主流程状态。

---

## 8. 外部代码桥接协议

```text
main
  → 应用入口（受「是否执行外部代码」门控）
      → 写 input_{run_id}.json
        { schema_version, project, tasks[], context{ repo_path, env, app_name, ... } }
      → system.run_or_open(run.bat, 参数: run_id work_dir input_path)
      → 读 runner_{run_id}.json { status, message, data.results[] }
      → RunEvidence.observe_external_result → 台账 outcome=external_success/external_failed
```

- `run_id` 由影刀通过命令行传入，Python 侧以命令行参数为准。
- 输入信封固定包含 `schema_version: "1.0"`；`run_id` 不写入输入信封。
- 业务输出默认写 `data/output/`；影刀只读 `runner_{run_id}.json`（以及约定的业务输出文件）。
- `observe_external_result()` 明确采用观察模式，不抛出 Python 业务失败；若要让 `retryable_error/pending_fix/fatal` 影响影刀主流程，必须在影刀侧增加显式状态分支。

---

## 9. 设计说明与已知取舍

**设计意图**

1. 业务与平台解耦：影刀里只留"壳"，业务进 Git，可 review、可单测、可回滚。
2. 每次运行可追溯：`run_id` 一条线串起日志 / 证据 / 台账 / 通知，失败必留现场。
3. 可复制：换应用只需改全局变量与 `secrets.json`，主干不动。

**已知取舍与风险**

1. `应用入口` 的网页演示段硬编码 `console.yingdao.com` 且需要登录，是主干中最脆弱的一环，且目前不受开关门控。
2. `main` 中仍有若干 `programing.snippet` 承担协议胶水（通知出口、身份初始化、收尾），协议逻辑宜继续下沉为具名 CodeFlow。
3. 外部 runner 的非成功状态只被记录为 `external_failed`，不会阻止 `main` 随后把 `运行状态` 设为“运行成功”。需要业务闭环时必须补显式分支。
4. `main` 在调用 `应用入口` 前无条件检查 `run.bat`；因此即使 `是否执行外部代码=False`，缺少 `run.bat` 仍会失败，与“关闭外部代码后空跑”的预期不完全一致。
5. 写入输入上下文的 `trigger_mode` 当前固定为 `dev`，没有使用 `main` 读取到的真实触发来源。
6. 运行级数据仅部分显式化（当前为目录类）。若需要并发或多实例运行，`today_date`、`code_pj_path_result` 等应继续参数化。
7. `main` 未声明 Out 参数，上层无法直接获取 `运行状态 / 台账路径`。
8. 死代码：`feishu_run`、`config_legacy`。
9. 失败分支（网页失败留证、Git 失败早爆）目前为逻辑审查通过、运行未覆盖。

---

## 10. 扩展点（改配置即可，不动主干）

| 目标 | 改哪里 |
| --- | --- |
| 换 Git 仓库 / 分支 | 全局变量 `code_git_url` / `code_git_branch` |
| 换远端记录表 | 全局变量 `run_record_url`（或 `secrets.json` 中的对应段落） |
| 换飞书应用 / 群通知 / AI / Linear | `secrets.json` |
| 新增业务任务 | 影刀侧新增 `tasks[]` payload；Python 侧实现对应 `tasks[].type` handler |
| 新增流程阶段 | 在 `main` 编排区追加 `process.run`，显式声明 In / 回收 Out |

---

## 11. 更新记录

| 日期 | 变更 |
| --- | --- |
| 2026-09-21 | 与实际 `xbot_robot` 复核：补充输入版本、外部结果只观察不传播、外部开关前置校验和触发来源固定值等限制。 |
| 2026-09-21 | 初版：代码工程准备与收尾抽取为子流程；运行级数据改走 In 参数；通知收敛为单一出口；凭据移入资源文件 `secrets.json`。 |
