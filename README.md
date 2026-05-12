# 开发模板

RPA 项目开发模板，基于影刀 RPA + Python + AI 自愈架构。

## 文档导航

以下文档用于把“影刀 + Python + AI 修复闭环”固化成长期可运转的协作契约：

| 文档 | 用途 |
|------|------|
| [docs/RPA_PYTHON_BOUNDARY.md](D:\CraftPJ\开发模板\docs\RPA_PYTHON_BOUNDARY.md) | 定义影刀、Python、AI 的职责边界和拆分判断规则 |
| [docs/REQUIREMENT_TEMPLATE.md](D:\CraftPJ\开发模板\docs\REQUIREMENT_TEMPLATE.md) | 给 AI 提需求时的标准输入模板 |
| [docs/ISSUE_FIX_WORKFLOW.md](D:\CraftPJ\开发模板\docs\ISSUE_FIX_WORKFLOW.md) | 定义工单生成、AI 修复、测试、验收、合并流程 |
| [docs/ACCEPTANCE_CHECKLIST.md](D:\CraftPJ\开发模板\docs\ACCEPTANCE_CHECKLIST.md) | 每次修复或上线前的固定验收门槛 |
| [docs/INTERFACE_EXAMPLES.md](D:\CraftPJ\开发模板\docs\INTERFACE_EXAMPLES.md) | 输入输出协议样例说明 |
| [docs/PROJECT_ARCHITECTURE_OVERVIEW.md](D:\CraftPJ\开发模板\docs\PROJECT_ARCHITECTURE_OVERVIEW.md) | 项目架构图、主执行流程图、Craft Agent 修复闭环图 |
| [docs/examples](D:\CraftPJ\开发模板\docs\examples) | `input_*.json` / `runner_*.json` 真实样例库 |

建议使用顺序：

1. 先看职责边界，确认需求拆分。
2. 再按需求模板整理输入。
3. 开发或修复时参考接口样例。
4. 工单修复按闭环流程执行。
5. 合并前按验收清单逐项检查。

## 标准工作流入口

### 新需求

1. 先根据 [docs/RPA_PYTHON_BOUNDARY.md](D:\CraftPJ\开发模板\docs\RPA_PYTHON_BOUNDARY.md) 拆分影刀职责和 Python 职责。
2. 再按 [docs/REQUIREMENT_TEMPLATE.md](D:\CraftPJ\开发模板\docs\REQUIREMENT_TEMPLATE.md) 整理需求输入。
3. AI 只在明确授权范围内实现 Python、测试和文档。
4. 开发完成后按 [docs/ACCEPTANCE_CHECKLIST.md](D:\CraftPJ\开发模板\docs\ACCEPTANCE_CHECKLIST.md) 验收。

### 新 Bug / 新工单

1. 先收集 `runner_{run_id}.json`、`logs/run_{run_id}.log`、`crash_snapshots/crash_{run_id}.json`。
2. 按 [docs/ISSUE_FIX_WORKFLOW.md](D:\CraftPJ\开发模板\docs\ISSUE_FIX_WORKFLOW.md) 补齐工单字段。
3. AI 修复时必须补测试，并给出复现和验收方式。
4. 验收通过后再合并到 `main`。

### 新会话给 AI 的推荐开场

可直接把下面这段作为新会话的起始说明：

```text
请先阅读以下文档后再开始工作：
1. docs/RPA_PYTHON_BOUNDARY.md
2. docs/REQUIREMENT_TEMPLATE.md
3. docs/ISSUE_FIX_WORKFLOW.md
4. docs/ACCEPTANCE_CHECKLIST.md
5. docs/INTERFACE_EXAMPLES.md

工作要求：
- 先按职责边界判断影刀与 Python 的分工
- 如果是写 Python 功能，先按需求模板理解输入输出和异常规则
- 如果是修 bug，先读取 runner json、log、crash snapshot，再修复并补测试
- 未经明确允许，不修改影刀职责范围
- 完成后给出验收命令和结果说明
```

## 架构

```
开发模板/
├── git_controller.py       # Git 部署辅助工具（非运行时）
├── runner.py                # 影刀调度入口，读取输入 → 配置自检 → 执行 → 输出结果
├── run.bat                  # Windows 一键启动脚本
├── project.template.json    # 配置模板（默认值，提交到 Git）
├── project.json             # 本地配置（覆盖模板，不提交）
├── core/
│   ├── __init__.py
│   ├── entry.py             # 业务执行入口（统一输出协议）
│   ├── exceptions.py        # 异常路由分流器（编码体系 + crash snapshot）
│   ├── notifier.py          # 告警网关（飞书汇总 + Linear 工单 + 指派人 + 标签）
│   ├── ai_analyzer.py       # AI 崩溃分析（分类统一到 SYSTEM_CATEGORIES）
│   ├── config.py            # 配置集中管理（template + json 深度合并 + 运行前自检）
│   └── logger.py            # 运行日志记录器
├── commands/                # 可插拔业务命令模块（规划中）
├── tests/
│   ├── test_config.py       # 配置加载 & 自检测试
│   ├── test_exceptions.py   # 异常编码 & 分类映射测试
│   ├── test_entry.py        # entry 模块 & 状态码测试
│   ├── test_ai_analyzer.py  # AI 分析 & 分类归一化测试
│   ├── test_routing.py      # 全链路集成测试
│   └── ...
├── logs/                    # 运行日志（.gitignore 忽略）
├── crash_snapshots/         # 崩溃快照（.gitignore 忽略）
├── data/                    # 运行数据（.gitignore 忽略）
├── .gitignore
└── requirements.txt
```

## 职责边界

| 角色 | 职责 |
|------|------|
| **影刀** | 组织输入参数 → 调用 run.bat → 读取结果 JSON → 按 status 分支 |
| **Python** | 加载配置 → 配置自检 → 读取输入 → 执行业务 → 异常分类 → 输出结果 → 写日志 → 通知 |
| **AI** | 分析崩溃快照 → 分类到 SYSTEM_CATEGORIES → 生成根因/置信度/修复建议 |

详细边界和拆分判断规则见：

- [docs/RPA_PYTHON_BOUNDARY.md](D:\CraftPJ\开发模板\docs\RPA_PYTHON_BOUNDARY.md)
- [docs/INTERFACE_EXAMPLES.md](D:\CraftPJ\开发模板\docs\INTERFACE_EXAMPLES.md)

## 输入协议

影刀在执行前写出 `input_{run_id}.json`：

```json
{
  "run_id": "ORDER_20260512_001",
  "project": "海外仓补货",
  "tasks": [
    {
      "id": "task-001",
      "name": "抓取订单",
      "intent": "抓取海外仓订单数据",
      "rule_context": "跳过取消订单",
      "payload": {"shop_id": "S001", "date": "2026-05-12"}
    }
  ],
  "context": {
    "operator": "yingdao",
    "env": "prod",
    "source": "yingdao"
  }
}
```

## 输出协议

Python 输出 `runner_{run_id}.json`：

```json
{
  "status": "success|warning|retryable_error|pending_fix|failed|locked|fatal",
  "message": "简要说明",
  "data": {
    "run_id": "ORDER_20260512_001",
    "results": [],
    "warnings": [
      {
        "task": {},
        "message": "跳过原因",
        "context": {},
        "category": "business",
        "code": "DATA_INVALID",
        "retryable": false,
        "suggested_action": "跳过并记录"
      }
    ],
    "errors": [
      {
        "task": {},
        "message": "错误信息",
        "category": "system",
        "error_type": "SystemException",
        "code": "LOGIC_DEFECT",
        "exc_category": "LOGIC_DEFECT",
        "retryable": false,
        "issue_url": "https://linear.app/...",
        "confidence": 0.85,
        "need_human_review": false,
        "test_suggestion": "建议测试用例"
      }
    ],
    "retryable": false,
    "crash_snapshot_dir": "crash_snapshots/",
    "log_path": "logs/run_ORDER_20260512_001.log"
  }
}
```

### 状态码说明

| 状态 | 含义 | 影刀动作 |
|------|------|----------|
| `success` | 全部完成 | 继续下游流程 |
| `warning` | 有跳过但无中断 | 记录后继续 |
| `retryable_error` | 可重试的异常（网络超时、依赖故障等） | 延迟 30s 后重试，最多 3 次；3 次仍失败则标记异常 |
| `pending_fix` | 不可重试的系统异常（已建/待建工单） | 标记待修复后停止当前流程 |
| `failed` | 不可恢复的异常 | 通知人工介入 |
| `locked` | 并发锁冲突 | 等待 5-10s 后重试 |
| `fatal` | 入口级崩溃（配置错误、输入缺失等） | 通知运维/开发 |

#### retryable_error 判定逻辑

```
SystemException(retryable=True)  →  _determine_status  →  retryable_error
                               ↳ exc_category=DEPENDENCY_FAILURE
                               ↳ code=NETWORK_TIMEOUT 等
```

影刀重试策略：
1. 读取 `data.retryable == true` + `data.errors[0].exc_category == "DEPENDENCY_FAILURE"`
2. 等待 30 秒
3. 重新调用 `run.bat` 执行同一次 run_id
4. 最多重试 3 次，3 次后仍失败则标记为异常

## 异常编码体系

### 业务异常编码（BusinessException）

| 编码 | 含义 | retryable |
|------|------|-----------|
| `DATA_EMPTY` | 数据为空 | False |
| `DATA_INVALID` | 数据不合法 | False |
| `ORDER_NOT_FOUND` | 订单未找到 | False |
| `DUPLICATE_RECORD` | 重复记录 | False |
| `RULE_BLOCKED` | 规则阻断 | False |

### 系统异常分类（SystemException）— 与 AI 分类统一

AI 分析与系统异常共享同一套 `SYSTEM_CATEGORIES`，确保 AI 输出可直接对齐：

| 分类 | 含义 | retryable | AI 映射来源 |
|------|------|-----------|-------------|
| `UI_CHANGED` | 页面结构变更 | False | 直通 |
| `DATA_QUALITY` | 数据质量问题 | False | ← `DATA_NON_STANDARD`（旧 AI 分类） |
| `RULE_MISSING` | 规则缺失 | False | 直通 |
| `DEPENDENCY_FAILURE` | 依赖故障（可重试） | True | 直通 |
| `ENVIRONMENT_ISSUE` | 环境问题 | False | 直通 |
| `LOGIC_DEFECT` | 逻辑缺陷 | False | ← `LOGIC_ERROR`（旧 AI 分类） |
| `THIRD_PARTY_LIMIT` | 第三方限制 | False | ← `NETWORK_BLOCK`（旧 AI 分类） |

## AI 分析输出结构

AI 返回的 JSON 包含以下字段：

| 字段 | 必需 | 类型 | 说明 |
|------|------|------|------|
| `root_cause` | ✅ | string | 根因分析 |
| `suggested_fix` | ✅ | string | 修复建议 |
| `severity` | ✅ | string | 严重级别：critical/high/medium/low |
| `category` | ✅ | string | SYSTEM_CATEGORIES 中的 7 种分类 |
| `priority` | ✅ | string | 优先级：urgent/high/medium/low |
| `summary` | ✅ | string | 一行摘要（用于工单标题） |
| `confidence` | 可选 | float | 置信度 0.0-1.0（默认 0.5） |
| `need_human_review` | 可选 | bool | 是否需人工复核（默认 False） |
| `test_suggestion` | 可选 | string | 测试建议用例 |

分类归一化规则：
- 合法分类（SYSTEM_CATEGORIES 中的 7 种）直通
- 旧 AI 分类自动映射（`DATA_NON_STANDARD` → `DATA_QUALITY` 等）
- 未知分类回退到 `LOGIC_DEFECT`

## 配置校验（运行前自检）

runner.py 在执行业务前自动调用 `validate_config()`：

| 字段 | 必须 | 缺失后果 |
|------|------|----------|
| `project` | ✅ | fatal：配置校验失败 |
| `feishu_webhook` | 可选 | 警告：飞书通知不可用 |
| `linear.api_key` | 可选 | 警告：工单创建不可用 |
| `linear.team_id` | 可选 | 警告：工单创建不可用 |
| `ai.enabled` + `ai.api_key` | 可选 | 警告：AI 分析已启用但 Key 未配置 |

缺失必须字段 → `status=fatal`，错误信息明确指出缺失字段名。

## 告警与工单路由

| 异常类型 | 通知动作 | 后续处理 |
|----------|----------|----------|
| `BusinessException` | 收集 → 飞书汇总（黄色卡片） | 跳过当前任务，继续执行 |
| `SystemException` | 创建 Linear 工单 + 收集 → 飞书汇总（红色卡片） | 强制中断，流程终止 |
| 全部成功 | **不发通知**（静默） | 继续 |

## notifier 模块职责分层

| 区段 | 职责 | 主要函数 |
|------|------|----------|
| §1 飞书通知 | 批量汇总卡片 | `send_execution_summary()`, `_feishu_post()` |
| §2 Linear API 底层 | GraphQL 请求封装 | `_linear_request()` |
| §3 Linear 资源管理 | 项目/标签/指派人自动查找或创建 | `_ensure_linear_project()`, `_ensure_linear_label()`, `_ensure_linear_assignee()` |
| §4 Linear 工单创建 | 系统 Bug 工单 + AI 增强 | `create_linear_issue()` |
| §5 辅助工具 | Git 分支/提交信息 | `_get_current_branch()`, `_get_current_commit()`, `_is_production_env()` |

## 配置加载

```
project.template.json（默认值，提交到 Git）
        ↓ 深度合并
project.json（本地覆盖，不提交）
```

关键字段：`project`、`feishu_webhook`、`linear.api_key`、`linear.team_id`、`ai.enabled`、`ai.api_key`

## 分支策略

| 分支 | 用途 | 说明 |
|------|------|------|
| `main` | 生产环境 | 稳定版本，创建 Linear 工单 |
| `fix/bug-test` | 测试/调试 | 不创建 Linear 工单 |
| `fix/*` | Bug 修复 | AI 自动创建 + PR |
| `feat/*` | 功能开发 | 人类开发者使用 |

补充规则：

- `main` 只放验收通过代码
- 每个 bug 单独使用一个 `fix/{issue_id}` 分支
- 合并前必须测试全绿
- 合并后应更新版本号或变更说明
- 影刀生产环境只运行已发布版本，不在运行时切 Git

## 部署与执行分离

- **部署期**：`git_controller.py` 负责 clone / 切分支 / pull
- **执行期**：`runner.py` 只做业务，不自动切 Git

## 使用方式

### 影刀内调用

```
1. 生成 run_id
2. 写出 input_{run_id}.json
3. 调用 run.bat: run.bat {run_id} input_{run_id}.json
4. 读取 runner_{run_id}.json
5. 按 status 分支
```

### AI 参与开发 / 修复

1. 新功能先按 [docs/REQUIREMENT_TEMPLATE.md](D:\CraftPJ\开发模板\docs\REQUIREMENT_TEMPLATE.md) 整理需求。
2. 修复工单先按 [docs/ISSUE_FIX_WORKFLOW.md](D:\CraftPJ\开发模板\docs\ISSUE_FIX_WORKFLOW.md) 收集证据和复现信息。
3. 开发完成后按 [docs/ACCEPTANCE_CHECKLIST.md](D:\CraftPJ\开发模板\docs\ACCEPTANCE_CHECKLIST.md) 验收。
4. 输入输出协议参考 [docs/examples](D:\CraftPJ\开发模板\docs\examples)。

### 本地测试

```bash
python -m pytest tests/ -v          # 全量测试（41 个用例）
python -m pytest tests/test_config.py -v    # 配置测试
python -m pytest tests/test_ai_analyzer.py -v  # AI 分析测试
python core/entry.py                     # 业务逻辑测试
python git_controller.py                 # Git 切换测试（部署工具）
```
