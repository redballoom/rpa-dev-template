# AGENTS 工作规范

本文档面向接手本仓库的 AI Agent。目标是把业务需求稳定落到本 RPA Python 开发模板中，并保持影刀、Python、AI 三方职责清晰。

## 项目定位

这是影刀 RPA 调度的 Python Code 项目模板。

- 影刀负责页面操作、登录、下载、上传、人工确认、生成本次运行独立的输入文件、调用 `run.bat` 或 `runner.py`。
- Python 负责读取结构化输入、处理业务数据、写业务输出、记录日志、分类异常、输出 `runner_{run_id}.json`。
- AI 负责在本 Code 项目内实现和维护 Python 业务逻辑、测试、示例输入和文档。

默认不要修改影刀 UI 流程。除非用户明确要求，否则所有可复现、可测试、可沉淀的业务规则都应放在 Python 侧。

## 接到业务需求后的工作流

1. 先读契约文档
   - `README.md`
   - `docs/OPERATION_GUIDE.md`
   - `docs/SHADOWBOT_INPUT_CONTRACT.md`
   - `docs/RPA_PYTHON_BOUNDARY.md`
   - `docs/PROJECT_ARCHITECTURE_OVERVIEW.md`
   - `docs/examples/input_*.json`
   - 如是故障修复，再读 `docs/ISSUE_FIX_WORKFLOW.md`
   - 注意：`calc_summary` 和 `template_demo` 是模板内置可运行示例；其他业务型示例用于说明 payload 形态，接入前必须实现对应 handler。

2. 明确输入输出
   - 确认输入文件的 `tasks[]` 结构。推荐使用 `input_{run_id}.json`，固定 `input.json` 仅适合单实例串行运行。
   - 确认 `run_id` 由影刀或 BAT 通过命令行传入，不写入输入文件；即使输入文件中出现顶层 `run_id`，Python 也以命令行参数为准。
   - 确认新增或修改的 `tasks[].type` 路由键。
   - 确认 `payload` 每个字段的业务含义、必填性、默认值和路径规则。
   - 确认 `context.env` 是否明确为 `test` 或 `prod`，生产工单判断优先使用该字段。
   - 确认是否需要 `context.fail_fast=false` 或 `tasks[].continue_on_error=true` 支持独立批任务继续执行。
   - 确认业务输入文件是否位于 `data/input/`，业务输出是否写到 `data/output/`。
   - 确认影刀只需要读取 `runner_{run_id}.json`，还是还需要读取某个业务输出文件。
   - 如果用户只给业务目标、没有给完整输入契约，AI 应先设计 `tasks[].type` 和 `payload` 示例，再按该契约实现 handler。

3. 设计路由和 handler
   - 小需求可以直接在 `core/entry.py` 增加 `_process_xxx()` 并在 `_process_single_task()` 中按 `task.type` 路由。
   - 中大型需求应创建独立业务模块，例如 `core/handlers/xxx.py` 或 `core/services/xxx.py`，再由 `entry.py` 调用。
   - 路由键必须来自 `tasks[].type`，不要依赖任务名称做业务分支。
   - handler 接收 `task` 和 `context`，业务参数只从 `task["payload"]` 读取。
   - 按当前 `core/entry.py` 实现，`run_tasks()` 会在调用 handler 前通过 `context.setdefault()` 补入 `repo_path` 和 `project`。直接单测 handler 时，也要显式提供这两个上下文字段或接受默认值。
   - 未实现的非空 `tasks[].type` 应返回系统异常，不允许假成功。`template_demo` 只用于模板示例和状态码演示，不要作为真实业务路由。

4. 实现业务逻辑
   - 路径字段支持相对路径时，应以 `repo_path` 为基准解析。
   - 输出目录不存在时由 Python 创建。
   - 业务输出默认写到 `data/output/`。
   - 不要硬编码影刀临时目录、个人绝对路径、真实账号、密钥、cookie 或 webhook。
   - 不要把可测试的数据清洗、字段映射、规则判断塞回影刀流程。

5. 使用统一异常语义
   - 可接受的业务问题使用 `BusinessException`，例如空数据、单条记录不合法、业务规则阻断。此类异常会进入 `warnings`，通常最终状态为 `warning`。
   - 代码缺陷、环境问题、依赖故障、规则缺失等使用 `SystemException`。此类异常会进入 `errors`，默认中断后续任务。
   - 独立批任务可通过 `context.fail_fast=false` 或单任务 `continue_on_error=true` 在系统异常后继续执行；有依赖关系的任务不要开启。
   - 可重试的系统异常设置 `retryable=True`，通常返回 `retryable_error`。
   - 不可重试的系统异常通常返回 `pending_fix`，用于触发修复闭环。
   - 输入文件缺失、入口崩溃、配置致命错误由 `runner.py` 返回 `fatal`。
   - `SystemException` 的 `rule_context` 和 `intent` 属于兼容字段，当前只会进入快照和 AI 分析上下文。新业务默认不要使用它们；业务数据仍应放在 `payload`。

6. 保持输出协议稳定
   - 最终必须输出 `runner_{run_id}.json`。
   - 顶层字段保持 `status`、`message`、`data`。
   - `data` 中保持 `run_id`、`results`、`warnings`、`errors`、`retryable`、`crash_snapshot_dir`、`log_path`。
   - 业务结果可以追加到单个 result 的 `data` 字段中。
   - 不要让影刀直接解析 Python 堆栈。

7. 更新样例和文档
   - 新增任务类型时，补充或更新 `docs/examples/input_*.json`。
   - 如果 `payload` 协议变化，更新 `docs/SHADOWBOT_INPUT_CONTRACT.md` 或 `docs/INTERFACE_EXAMPLES.md`。
   - 如果是通用业务开发需求，按 `docs/REQUIREMENT_TEMPLATE.md` 补齐输入、输出、异常和验收说明。

8. 补充测试并验证
   - 至少覆盖正常成功、业务 warning、系统异常或关键边界条件。
   - 优先在 `tests/` 中增加小而明确的单元测试。
   - 涉及 runner 输入输出时，增加端到端测试或手动运行示例。
   - 可运行时执行 `python -m pytest tests/ -v`。
   - 不能运行测试时，必须说明原因和剩余风险。

## 代码修改原则

- 优先遵循现有结构：`runner.py` 负责调度，`core/entry.py` 负责任务路由，业务模块负责具体处理。
- 不为单个简单需求过早抽象；当 handler 变长、复用明显或有多种业务类型时再拆模块。
- 不修改 `runner.py` 的输出协议，除非需求明确要求且同步更新测试和文档。
- 不修改 `run.bat` 的参数契约，除非影刀调用方式同步变化。
- 新增 `tasks[].type` 时必须同步实现 handler、示例输入和测试；不要只更新文档。
- 不提交运行产物，例如 `runner_*.json`、`input*.json`、`logs/`、`crash_snapshots/`、`data/`。
- 不提交或泄露 `project.json` 中的真实密钥、webhook、Linear 配置。

## 推荐实现模板

在 `core/entry.py` 中增加路由：

```python
def _process_single_task(task, project, context=None):
    task_type = task.get("type", "")

    if task_type == "your_task_type":
        return _process_your_task(task, context or {})

    # 保留既有示例和异常模拟逻辑
```

新增 handler 时遵循：

```python
def _process_your_task(task, context):
    payload = task.get("payload") or {}
    # 当前 run_tasks() 会通过 context.setdefault() 补入 repo_path/project；
    # 直接单测 handler 时需要自行提供或接受默认值。
    repo_path = context.get("repo_path") or "."
    project = context.get("project", "RPA")

    # 1. 校验 payload
    # 2. 读取 data/input/ 或 payload 指定文件
    # 3. 执行业务处理
    # 4. 写入 data/output/
    # 5. 返回可放入 results[].data 的摘要
```

校验失败示例：

```python
raise BusinessException(
    "payload.xxx is required",
    project=project,
    context={"payload": payload},
    code="DATA_EMPTY",
    suggested_action="请在输入文件的 payload.xxx 中传入必要参数",
)
```

系统异常示例：

```python
raise SystemException(
    message="外部接口超时",
    project=project,
    payload=payload,
    action="调用外部接口",
    expected="接口在超时时间内返回成功响应",
    actual="请求超时",
    code="NETWORK_TIMEOUT",
    exc_category="DEPENDENCY_FAILURE",
    retryable=True,
    run_context=context,
)
```

## 验收标准

完成业务实现前，不要只停留在代码修改。交付时至少说明：

- 新增或修改了哪些任务类型。
- 输入文件的示例结构，推荐按 `input_{run_id}.json` 命名。
- 业务输出文件路径和结果摘要。
- `runner_{run_id}.json.status` 的预期值。
- 已执行的测试命令和结果。
- 未验证项或剩余风险。

如果需求信息不足，优先从现有文档和代码推断；只有在输入文件格式、业务规则或输出标准无法合理判断时，才向用户提问。
