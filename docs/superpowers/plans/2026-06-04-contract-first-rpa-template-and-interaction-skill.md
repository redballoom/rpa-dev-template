# Contract-First RPA Template and Interaction Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the RPA Python template into a contract-first AI business implementation template and create a reusable interaction skill for generating business contracts before implementation.

**Architecture:** Keep the current `runner.py + core/entry.py` execution contract stable. Add template documentation, a small standard handler example, tests, and a local interaction skill that references the template contract rather than duplicating Python protocol details.

**Tech Stack:** Python 3, pytest, Markdown docs, Codex skill `SKILL.md`.

---

## Scope Check

The approved spec contains two related parts: template optimization and interaction skill creation. They are implemented in one sequential plan because the skill depends on the template docs as its authoritative protocol source. Do not create the skill before the template contract docs exist.

## File Structure

- Create: `docs/任务设计模板.md`
  - Responsibility: standard contract template for each new business task.
- Create: `docs/处理器实现规范.md`
  - Responsibility: handler structure, routing, payload validation, path handling, result summary, exception semantics.
- Create: `docs/AI交付检查清单.md`
  - Responsibility: checklist for AI delivery before handoff to RPA developer.
- Create: `docs/自动修复闭环说明.md`
  - Responsibility: failure ticket context, AI repair inputs, repair outputs, human review gates.
- Modify: `README.md`
  - Responsibility: surface the contract-first workflow and standard deliverables.
- Modify: `docs/REQUIREMENT_TEMPLATE.md`
  - Responsibility: align request format with the task contract.
- Modify: `docs/ACCEPTANCE_CHECKLIST.md`
  - Responsibility: add contract-first acceptance checks.
- Modify: `docs/ISSUE_FIX_WORKFLOW.md`
  - Responsibility: add structured repair context and post-fix handoff requirements.
- Create: `core/handlers/__init__.py`
  - Responsibility: package marker and future handler namespace.
- Create: `core/handlers/record_filter.py`
  - Responsibility: standard example handler that reads JSON records, filters by status, writes output, returns summary.
- Modify: `core/entry.py`
  - Responsibility: route `filter_records` to the example handler while preserving existing `calc_summary` and `template_demo`.
- Create: `docs/examples/input_filter_records.json`
  - Responsibility: runnable contract example for the standard handler.
- Create: `tests/test_record_filter_handler.py`
  - Responsibility: test normal success, business warning, and invalid input path for the standard handler.
- Create: `C:/Users/redballoon/.agents/skills/rpa-contract-first/SKILL.md`
  - Responsibility: local reusable skill that drives business understanding, boundary alignment, and contract generation.

## Task 1: Contract Layer Docs

**Files:**
- Create: `docs/任务设计模板.md`
- Create: `docs/处理器实现规范.md`
- Create: `docs/AI交付检查清单.md`
- Modify: `README.md`
- Modify: `docs/REQUIREMENT_TEMPLATE.md`
- Modify: `docs/ACCEPTANCE_CHECKLIST.md`

- [ ] **Step 1: Create the task design template**

Create `docs/任务设计模板.md` with this structure:

```markdown
# 任务设计模板

用于在 AI 实现业务 handler 前，先沉淀可审查的业务契约。

## 任务概览

| 项目 | 内容 |
| --- | --- |
| 任务名称 |  |
| `tasks[].type` |  |
| 业务目标 |  |
| 是否允许修改影刀流程 | 默认否 |
| Python 输出是否需要影刀读取业务文件 |  |

## 职责边界

| 角色 | 职责 |
| --- | --- |
| 影刀 | 页面操作、登录、下载、上传、人工确认、生成 `input.json`、调用 `run.bat` 或 `runner.py` |
| Python | 读取结构化输入、处理业务数据、写业务输出、记录日志、分类异常、输出 `runner_{run_id}.json` |
| AI | 实现和维护 Python 业务逻辑、测试、示例输入和文档 |
| 人工 | 确认业务路径、验收结果、决定是否推送或合并 |

## 输入契约

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
| `payload.input_file` | string | 是 |  | 相对路径以 `repo_path` 为基准 |
| `payload.output_file` | string | 否 | `data/output/<task>.json` | 相对路径以 `repo_path` 为基准 |

## 业务步骤

1. 校验 `payload`。
2. 解析输入路径。
3. 读取业务数据。
4. 执行业务规则。
5. 写入业务输出。
6. 返回结果摘要。

## 输出契约

| 输出 | 说明 |
| --- | --- |
| 业务输出文件 |  |
| `results[].data` |  |
| `runner_{run_id}.json.status` |  |

## 异常契约

| 场景 | 异常类型 | 状态码 | 处理建议 |
| --- | --- | --- | --- |
| 输入数据为空 | `BusinessException` | `warning` | 记录并跳过任务 |
| 输入文件不存在 | `SystemException` | `pending_fix` | 检查影刀下载或路径配置 |
| 外部依赖超时 | `SystemException(retryable=True)` | `retryable_error` | 延迟重试 |

## 验收标准

- 示例输入可以运行。
- 输出文件位于 `data/output/` 或 `payload.output_file` 指定位置。
- `runner_{run_id}.json` 保持稳定顶层协议。
- warning 和 system error 口径符合本契约。
- 已补充测试或说明未测试原因。
```

- [ ] **Step 2: Create the handler implementation guide**

Create `docs/处理器实现规范.md` with this content:

```markdown
# 处理器实现规范

## 基本原则

- 业务路由键必须来自 `tasks[].type`。
- handler 只从 `task["payload"]` 读取业务参数。
- 相对路径统一以 `context["repo_path"]` 为基准解析。
- 业务输出默认写入 `data/output/`。
- 未实现的非空 `tasks[].type` 必须返回 `SystemException`，不允许假成功。
- `template_demo` 仅用于模板状态码演示，不作为真实业务路由。

## 推荐目录

```text
core/
  entry.py
  handlers/
    __init__.py
    your_task.py
```

## handler 函数格式

```python
def process_your_task(task, context):
    """处理 <业务名称>。

    业务路径：
      1. 校验 payload。
      2. 读取 data/input/ 或 payload 指定文件。
      3. 执行业务规则。
      4. 写入 data/output/。
      5. 返回 results[].data 摘要。
    """
    payload = task.get("payload") or {}
    repo_path = context.get("repo_path") or "."
    project = context.get("project", "RPA")
```

## 异常语义

- 可接受的业务问题使用 `BusinessException`。
- 代码缺陷、环境问题、依赖故障、规则缺失使用 `SystemException`。
- 可重试系统异常设置 `retryable=True`。
- 不可重试系统异常通常返回 `pending_fix`。

## 结果摘要

`results[].data` 应返回小而稳定的摘要，例如：

```json
{
  "input_file": "data/input/orders.json",
  "output_file": "data/output/orders_filtered.json",
  "total_count": 100,
  "matched_count": 12,
  "skipped_count": 88
}
```
```

- [ ] **Step 3: Create the AI delivery checklist**

Create `docs/AI交付检查清单.md` with this content:

```markdown
# AI 交付检查清单

## 实现前

- 已复述业务目标。
- 已明确影刀、Python、人工职责边界。
- 已确认 `tasks[].type`。
- 已确认 `payload` 字段、必填性、默认值和路径规则。
- 已确认业务输出文件和 `results[].data` 摘要。
- 已确认 warning / error 场景。

## 实现中

- 业务逻辑位于 Python 侧。
- handler 只读取 `task["payload"]`。
- 相对路径以 `repo_path` 为基准。
- 输出目录由 Python 创建。
- 不硬编码个人路径、账号、密钥、cookie 或 webhook。

## 交付前

- 已更新示例输入。
- 已更新相关文档。
- 已补充测试。
- 已运行可执行测试命令。
- 已说明业务输出文件路径。
- 已说明 `runner_{run_id}.json.status` 预期值。
- 已保留人工决定推送、合并和上线的节点。
```

- [ ] **Step 4: Update README with standard deliverables**

Modify `README.md` by adding this section after “推荐协作方式”:

```markdown
## AI 开发业务的标准交付物

新增或修改业务任务时，优先采用契约优先流程：

1. 先按 `docs/任务设计模板.md` 明确任务契约。
2. 再按 `docs/处理器实现规范.md` 实现 handler。
3. 补充 `docs/examples/input_*.json` 示例输入。
4. 补充或更新测试。
5. 按 `docs/AI交付检查清单.md` 输出交付摘要。

RPA 开发者主要审查业务路径、输入输出契约、结果摘要和验收点。是否推送远程、是否合并分支、是否上线仍由人工决定。
```

- [ ] **Step 5: Update requirement template**

Modify `docs/REQUIREMENT_TEMPLATE.md` so it includes these sections:

```markdown
## 任务契约

- 任务名称：
- `tasks[].type`：
- handler 职责：
- 业务处理步骤：
- 人工确认点：

## Payload 字段

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |
|  |  |  |  |  |
```

- [ ] **Step 6: Update acceptance checklist**

Modify `docs/ACCEPTANCE_CHECKLIST.md` by adding this section:

```markdown
## 契约优先验收

- 已有任务设计说明，且 `tasks[].type` 与实现路由一致。
- `payload` 字段说明与示例输入一致。
- handler 职责说明能映射业务路径。
- `results[].data` 摘要字段稳定、可供影刀或人工审查。
- warning / error 场景与异常类型一致。
- 人工验收、推送、合并、上线节点没有被自动化替代。
```

- [ ] **Step 7: Commit contract docs**

Run:

```powershell
python -m pytest tests/test_routing.py::test_unknown_task_type_pending_fix tests/test_routing.py::test_missing_task_type_pending_fix -v
git add README.md docs/任务设计模板.md docs/处理器实现规范.md docs/AI交付检查清单.md docs/REQUIREMENT_TEMPLATE.md docs/ACCEPTANCE_CHECKLIST.md
git commit -m "docs: add contract-first delivery guidelines"
```

Expected: selected routing tests pass, then commit succeeds.

## Task 2: Standard Handler Example

**Files:**
- Create: `core/handlers/__init__.py`
- Create: `core/handlers/record_filter.py`
- Modify: `core/entry.py`
- Create: `docs/examples/input_filter_records.json`
- Create: `tests/test_record_filter_handler.py`

- [ ] **Step 1: Write failing handler tests**

Create `tests/test_record_filter_handler.py`:

```python
import json
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.entry import run_tasks
from core.exceptions import SystemException


def _mock_send_summary(*args, **kwargs):
    return True


def _write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


@patch("core.entry.send_execution_summary", _mock_send_summary)
def test_filter_records_success(tmp_path):
    repo_path = str(tmp_path)
    input_file = tmp_path / "data" / "input" / "records.json"
    output_file = "data/output/filtered_records.json"
    _write_json(str(input_file), {
        "records": [
            {"id": "a", "status": "ready"},
            {"id": "b", "status": "skip"},
            {"id": "c", "status": "ready"}
        ]
    })

    result = run_tasks(
        run_id="filter-success",
        project="测试",
        repo_path=repo_path,
        tasks=[{
            "id": "filter-001",
            "name": "筛选 ready 记录",
            "type": "filter_records",
            "payload": {
                "input_file": "data/input/records.json",
                "output_file": output_file,
                "status_field": "status",
                "match_value": "ready"
            }
        }]
    )

    assert result["status"] == "success"
    data = result["data"]["results"][0]["data"]
    assert data["total_count"] == 3
    assert data["matched_count"] == 2
    assert data["skipped_count"] == 1

    output_path = tmp_path / output_file
    with open(output_path, "r", encoding="utf-8") as f:
        output = json.load(f)
    assert [item["id"] for item in output["records"]] == ["a", "c"]


@patch("core.entry.send_execution_summary", _mock_send_summary)
def test_filter_records_empty_records_warning(tmp_path):
    repo_path = str(tmp_path)
    input_file = tmp_path / "data" / "input" / "records.json"
    _write_json(str(input_file), {"records": []})

    result = run_tasks(
        run_id="filter-empty",
        project="测试",
        repo_path=repo_path,
        tasks=[{
            "id": "filter-empty",
            "name": "空数据",
            "type": "filter_records",
            "payload": {"input_file": "data/input/records.json"}
        }]
    )

    assert result["status"] == "warning"
    assert result["data"]["warnings"][0]["code"] == "DATA_EMPTY"


def test_filter_records_missing_file_system_exception(tmp_path):
    from core.handlers.record_filter import process_filter_records

    try:
        process_filter_records(
            {
                "id": "filter-missing",
                "name": "缺失输入文件",
                "type": "filter_records",
                "payload": {"input_file": "data/input/missing.json"}
            },
            {"repo_path": str(tmp_path), "project": "测试"}
        )
    except SystemException as exc:
        info = exc.notify(extra_payload={"run_id": "unit"}, repo_path=str(tmp_path))
        assert info["code"] == "INPUT_FILE_MISSING"
        assert info["exc_category"] == "ENVIRONMENT_ISSUE"
    else:
        raise AssertionError("expected SystemException")
```

- [ ] **Step 2: Run the failing tests**

Run:

```powershell
python -m pytest tests/test_record_filter_handler.py -v
```

Expected: fail because `filter_records` routing and `core.handlers.record_filter` do not exist.

- [ ] **Step 3: Create handlers package**

Create `core/handlers/__init__.py`:

```python
"""Business handlers for task.type routes."""
```

- [ ] **Step 4: Implement `record_filter` handler**

Create `core/handlers/record_filter.py`:

```python
import json
import os

from core.exceptions import BusinessException, SystemException


def _resolve_path(repo_path, path):
    if os.path.isabs(path):
        return path
    return os.path.join(repo_path, path)


def process_filter_records(task, context):
    """Filter JSON records by field value and write a stable output summary.

    Business path:
      1. Validate payload.
      2. Read a JSON file containing `records`.
      3. Keep records where `status_field` equals `match_value`.
      4. Write filtered records to `payload.output_file`.
      5. Return a compact results[].data summary.
    """
    payload = task.get("payload") or {}
    repo_path = context.get("repo_path") or "."
    project = context.get("project", "RPA")

    input_file = payload.get("input_file")
    if not input_file:
        raise BusinessException(
            "payload.input_file is required",
            project=project,
            context={"payload": payload},
            code="DATA_EMPTY",
            suggested_action="请在 payload.input_file 中传入 JSON 输入文件路径",
        )

    status_field = payload.get("status_field") or "status"
    match_value = payload.get("match_value") or "ready"
    output_file = payload.get("output_file") or "data/output/filtered_records.json"

    input_path = _resolve_path(repo_path, input_file)
    output_path = _resolve_path(repo_path, output_file)

    if not os.path.exists(input_path):
        raise SystemException(
            message="Input file not found: %s" % input_file,
            project=project,
            payload=payload,
            action="读取记录筛选输入文件",
            expected="输入文件存在且可读取",
            actual="文件不存在: %s" % input_file,
            code="INPUT_FILE_MISSING",
            exc_category="ENVIRONMENT_ISSUE",
            run_context=context,
        )

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            source = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemException(
            message="Failed to read JSON input: %s" % input_file,
            project=project,
            payload={"input_file": input_file, "error": str(exc)},
            action="解析记录筛选输入文件",
            expected="输入文件是 UTF-8 JSON",
            actual=str(exc),
            code="INPUT_FILE_INVALID",
            exc_category="DATA_QUALITY",
            run_context=context,
        )

    records = source.get("records")
    if not isinstance(records, list) or not records:
        raise BusinessException(
            "input records is empty",
            project=project,
            context={"input_file": input_file},
            code="DATA_EMPTY",
            suggested_action="请确认输入 JSON 中包含非空 records 数组",
        )

    matched = [item for item in records if item.get(status_field) == match_value]
    result = {"records": matched}

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return {
        "input_file": input_file,
        "output_file": output_file,
        "status_field": status_field,
        "match_value": match_value,
        "total_count": len(records),
        "matched_count": len(matched),
        "skipped_count": len(records) - len(matched),
    }
```

- [ ] **Step 5: Route `filter_records` in entry**

Modify `core/entry.py`:

```python
from core.handlers.record_filter import process_filter_records
```

Add this route after `calc_summary`:

```python
    if task_type == "filter_records":
        return process_filter_records(task, context or {})
```

- [ ] **Step 6: Add example input**

Create `docs/examples/input_filter_records.json`:

```json
{
  "project": "开发模板",
  "tasks": [
    {
      "id": "filter-001",
      "name": "筛选待处理记录",
      "type": "filter_records",
      "payload": {
        "input_file": "data/input/records.json",
        "output_file": "data/output/filtered_records.json",
        "status_field": "status",
        "match_value": "ready"
      }
    }
  ],
  "context": {
    "operator": "yingdao",
    "env": "test",
    "source": "shadowbot",
    "app_name": "开发模板"
  }
}
```

- [ ] **Step 7: Run handler tests**

Run:

```powershell
python -m pytest tests/test_record_filter_handler.py -v
```

Expected: all tests pass.

- [ ] **Step 8: Run routing tests**

Run:

```powershell
python -m pytest tests/test_entry.py tests/test_routing.py -v
```

Expected: existing status and routing tests pass.

- [ ] **Step 9: Commit standard handler example**

Run:

```powershell
git add core/entry.py core/handlers/__init__.py core/handlers/record_filter.py docs/examples/input_filter_records.json tests/test_record_filter_handler.py
git commit -m "feat: add standard contract-first handler example"
```

Expected: commit succeeds.

## Task 3: Repair Loop Docs

**Files:**
- Create: `docs/自动修复闭环说明.md`
- Modify: `docs/ISSUE_FIX_WORKFLOW.md`

- [ ] **Step 1: Create repair loop guide**

Create `docs/自动修复闭环说明.md`:

```markdown
# 自动修复闭环说明

## 目标

当 Python 运行返回 `pending_fix` 或不可恢复的系统异常时，模板应提供足够上下文，让 AI 可以接手定位、修复、验证，并把结果交回人工验收。

## 故障上下文最小字段

| 字段 | 说明 |
| --- | --- |
| `run_id` | 本次运行 ID |
| `project` | 项目名称 |
| `tasks[]` | 触发异常的任务 |
| `tasks[].type` | 路由键 |
| `tasks[].payload` | 业务输入参数 |
| `runner_{run_id}.json` | 标准执行结果 |
| `logs/run_{run_id}.log` | 运行日志 |
| `crash_snapshots/crash_{run_id}.json` | 系统异常快照 |
| 业务输入文件 | 位于 `data/input/` 或 payload 指定路径 |

## AI 修复前必须读取

1. `README.md`
2. `docs/SHADOWBOT_INPUT_CONTRACT.md`
3. `docs/RPA_PYTHON_BOUNDARY.md`
4. `docs/PROJECT_ARCHITECTURE_OVERVIEW.md`
5. `docs/任务设计模板.md`
6. `docs/处理器实现规范.md`
7. `docs/ISSUE_FIX_WORKFLOW.md`
8. 相关 `runner_{run_id}.json`、日志和 crash snapshot

## AI 修复后必须交付

- 根因说明。
- 修改文件摘要。
- 新增或更新的测试。
- 已运行的验证命令和结果。
- 业务输出文件路径。
- `runner_{run_id}.json.status` 的预期值。
- 剩余风险。

## 人工验收节点

- 是否接受修复。
- 是否重跑影刀流程。
- 是否推送远程。
- 是否合并主分支。
- 是否上线。
```

- [ ] **Step 2: Update issue fix workflow**

Modify `docs/ISSUE_FIX_WORKFLOW.md` by adding this section:

```markdown
## 结构化故障工单要求

故障工单至少包含：

- `run_id`
- 项目名称
- 触发异常的 `tasks[].type`
- 触发异常的 `payload`
- `runner_{run_id}.json` 路径或内容摘要
- 日志路径
- crash snapshot 路径
- 期望业务结果
- 当前实际结果
- 是否允许修改影刀流程，默认否

AI 修复完成后，必须提供根因、修改摘要、验证命令、验证结果和剩余风险。是否推送、合并和上线由人工决定。
```

- [ ] **Step 3: Commit repair docs**

Run:

```powershell
git add docs/自动修复闭环说明.md docs/ISSUE_FIX_WORKFLOW.md
git commit -m "docs: document automated repair loop"
```

Expected: commit succeeds.

## Task 4: Interaction Skill

**Files:**
- Create: `C:/Users/redballoon/.agents/skills/rpa-contract-first/SKILL.md`

- [ ] **Step 1: Create the skill directory**

Run:

```powershell
New-Item -ItemType Directory -Force 'C:/Users/redballoon/.agents/skills/rpa-contract-first'
```

Expected: directory exists. This writes outside the repo and may require approval.

- [ ] **Step 2: Create `SKILL.md`**

Create `C:/Users/redballoon/.agents/skills/rpa-contract-first/SKILL.md`:

```markdown
---
name: rpa-contract-first
description: Use when turning an RPA business requirement into a contract-first Python implementation plan. Guides AI to understand the business path, align ShadowBot/Python/human boundaries, design tasks[].type and payload, define outputs and exceptions, and produce a reviewable task contract before implementation.
---

# RPA Contract-First Business Interaction

## Purpose

Use this skill before implementing a new RPA Python business handler or changing an existing business handler. The goal is to convert a fuzzy business request into a reviewable task contract.

## Hard Gate

Do not write handler code before the user has reviewed the business contract, unless the user explicitly asks to skip contract review.

## Required Repository Context

Read these files first when they exist:

1. `README.md`
2. `docs/SHADOWBOT_INPUT_CONTRACT.md`
3. `docs/RPA_PYTHON_BOUNDARY.md`
4. `docs/PROJECT_ARCHITECTURE_OVERVIEW.md`
5. `docs/任务设计模板.md`
6. `docs/处理器实现规范.md`
7. `docs/AI交付检查清单.md`

## Workflow

1. Restate the business goal in plain language.
2. Identify the business objects, input files, output files, and success condition.
3. Align responsibility boundaries:
   - ShadowBot: UI operation, login, download, upload, human confirmation, input generation, runner invocation.
   - Python: structured input reading, business processing, output writing, logging, exception classification, runner result.
   - Human: business confirmation, acceptance, push/merge/release decision.
4. Design `tasks[].type`.
5. Design `payload` fields with type, requiredness, default value, and path rule.
6. Design `results[].data` summary.
7. Define warning scenarios.
8. Define system error scenarios.
9. Define acceptance checks.
10. Present the contract and wait for user approval before implementation.

## Contract Output Format

```markdown
# 业务任务契约

## 任务概览

- 任务名称：
- `tasks[].type`：
- 业务目标：

## 职责边界

- 影刀：
- Python：
- 人工：

## Payload

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | :---: | --- | --- |

## 业务步骤

1.

## 输出

- 业务输出文件：
- `results[].data`：
- `runner_{run_id}.json.status`：

## 异常

| 场景 | 类型 | 状态 | 建议 |
| --- | --- | --- | --- |

## 验收

-
```

## Handoff

After approval, implement using the repository template docs. Update examples, tests, and delivery checklist. Preserve the runner output protocol.
```

- [ ] **Step 3: Verify skill file exists**

Run:

```powershell
Get-Content 'C:/Users/redballoon/.agents/skills/rpa-contract-first/SKILL.md' -Encoding UTF8 -TotalCount 40
```

Expected: frontmatter contains `name: rpa-contract-first`.

- [ ] **Step 4: Record skill creation in final handoff**

Final handoff must mention:

```text
Created local skill: C:/Users/redballoon/.agents/skills/rpa-contract-first/SKILL.md
This skill drives contract-first business interaction and references the template docs as the protocol source.
```

## Task 5: Full Verification

**Files:**
- Verify: all files changed by Tasks 1-4

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m pytest tests/test_record_filter_handler.py tests/test_entry.py tests/test_routing.py -v
```

Expected: all selected tests pass.

- [ ] **Step 2: Run all tests**

Run:

```powershell
python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 3: Check docs for placeholders**

Run:

```powershell
$pattern = "TB" + "D|TO" + "DO|待" + "定|占" + "位"
Select-String -Path 'README.md','docs/*.md','docs/superpowers/plans/*.md','docs/superpowers/specs/*.md' -Pattern $pattern -Encoding UTF8
```

Expected: no matches in newly created contract docs or plan/spec docs. Existing unrelated matches, if any, must be reviewed and explained.

- [ ] **Step 4: Check git status**

Run:

```powershell
git status --short
```

Expected: only intentional files remain changed or untracked.

- [ ] **Step 5: Final delivery summary**

Final response must include:

```text
新增或修改的任务类型：filter_records
示例 input.json：docs/examples/input_filter_records.json
业务输出路径：data/output/filtered_records.json
预期 runner status：success for valid records, warning for empty records, pending_fix for missing input file
测试命令：python -m pytest tests/ -v
剩余风险：local skill writes outside repo and may require manual reload/restart depending on Codex skill discovery behavior
```
