# RPA Python 开发模板

这是影刀 RPA 调度的 Python Code 项目模板。影刀负责页面操作、文件准备和调度；Python 负责稳定的业务处理、日志、异常分类和标准结果输出；AI 负责在 Code 项目内实现和维护业务代码。

## 当前契约

影刀可以通过 `run.bat` 或直接调用 `runner.py` 启动本项目。

```bat
run.bat {run_id} {work_dir} {input_file}
```

`input_file` 可选：

- 推荐传入 `input_{run_id}.json`：`runner.py` 读取 `tasks` 数组，按 `type` 路由到对应 handler
- 不传 `input_file`：`runner.py` 不读取输入文件，业务代码按默认逻辑执行
- 固定文件名 `input.json` 仅适合单实例串行运行；并发场景必须使用每次运行独立的输入文件

默认输出：

- `runner_{run_id}.json`：输出到项目根目录。
- `logs/run_{run_id}.log`：Python 运行日志。
- `crash_snapshots/crash_{run_id}.json`：系统异常快照。
- `data/`：业务输入、业务输出和临时文件目录。

## 推荐输入结构

推荐将 `input_{run_id}.json` 放在项目根目录，业务文件放在 `data/` 下。

```json
{
  "project": "开发模板",
  "tasks": [
    {
      "id": "calc-001",
      "name": "计算汇总",
      "type": "calc_summary",
      "payload": {
        "numbers": [10, 25, 33, 47, 58],
        "output_file": "data/output/calc_result.json"
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

`run_id` 不写入输入文件。影刀或 BAT 通过命令行传给 `runner.py`，用于生成 `runner_{run_id}.json`、日志和结果中的 `data.run_id`。即使输入文件中出现顶层 `run_id`，Python 也以命令行参数为准。

## 文档导航

| 文档 | 用途 |
| --- | --- |
| [docs/SHADOWBOT_INPUT_CONTRACT.md](docs/SHADOWBOT_INPUT_CONTRACT.md) | 影刀输入文件、`payload`、`data/` 输入输出约定 |
| [docs/OPERATION_GUIDE.md](docs/OPERATION_GUIDE.md) | 调度工作模式、使用方式和人机配合注意事项 |
| [docs/RPA_PYTHON_BOUNDARY.md](docs/RPA_PYTHON_BOUNDARY.md) | 影刀、Python、AI 的职责边界 |
| [docs/INTERFACE_EXAMPLES.md](docs/INTERFACE_EXAMPLES.md) | 输入输出协议示例 |
| [docs/REQUIREMENT_TEMPLATE.md](docs/REQUIREMENT_TEMPLATE.md) | 给 AI 开发业务代码时的需求模板 |
| [docs/ISSUE_FIX_WORKFLOW.md](docs/ISSUE_FIX_WORKFLOW.md) | 运行失败后的修复闭环 |
| [docs/ACCEPTANCE_CHECKLIST.md](docs/ACCEPTANCE_CHECKLIST.md) | 修改和上线前验收清单 |
| [docs/PROJECT_ARCHITECTURE_OVERVIEW.md](docs/PROJECT_ARCHITECTURE_OVERVIEW.md) | 项目结构和执行流程 |
| [.rpa_ai/workflow.template.json](.rpa_ai/workflow.template.json) | AI 工作区 Gate、模板版本和 Skill 兼容声明 |
| [schemas/](schemas/) | 输入、工作流和 handoff 的机器可读 Schema |
| [tools/doctor.py](tools/doctor.py) | 跨机器初始化后的模板自检脚本 |
| [tools/handoff.py](tools/handoff.py) | AI 工作区交接文件的初始化、校验、推进和归档工具 |
| [rpa-dev-template-skills](https://github.com/redballoom/rpa-dev-template-skills) | 外部可安装 AI Skills：初始化、业务契约接入、故障修复 |

## 推荐协作方式

1. 影刀准备业务文件和参数，写入 `input_{run_id}.json` 的 `tasks[].payload`。
2. 影刀调用 `run.bat`，传入本次运行独立的 `input_file`。
3. Python 读取输入、执行业务、写入业务输出到 `data/output/`。
4. Python 输出 `runner_{run_id}.json`。
5. 影刀只消费 `runner_{run_id}.json` 的 `status`、`message` 和 `data`，不直接解析 Python 堆栈。
6. AI 后续只在 Code 项目内修改 Python 业务代码、测试和文档，默认不改影刀 UI 流程。

## 配套 Skills

配套 Skills 维护在独立远程仓库，便于在任意电脑、任意项目初始化前安装使用：

- `rpa-project-bootstrap`：从远程模板初始化新项目。
- `rpa-contract-business`：新业务需求进入时，先做输入输出契约，再实现 handler。
- `rpa-fix-loop`：运行失败后，基于结果、日志和快照进入修复闭环。

远程地址：`https://github.com/redballoom/rpa-dev-template-skills`

## 可迁移与升级底座

模板包含一组机器可读的协作文件，用于让不同电脑、不同 Agent 和不同项目之间保持一致。

- `VERSION`：当前模板版本。
- `.rpa_ai/workflow.template.json`：声明工作区 Gate、模板版本、所需 Skill 和 handoff 位置。
- `schemas/input.schema.json`：约束影刀输入文件的基本结构。
- `schemas/handoff.schema.json`：约束 AI 工作区之间的交接产物。
- `schemas/workflow.schema.json`：约束工作流声明本身。
- `tools/doctor.py`：初始化或升级后运行，检查必需文件、JSON、版本对齐、运行产物忽略规则和本机路径污染。
- `tools/handoff.py`：生成、校验、推进和归档 `.rpa_ai/handoff/current.json`。

推荐在新项目初始化后执行：

```bat
python tools\doctor.py
```

如果 `doctor` 返回 `failed`，先修复底座问题，再进入业务契约和 handler 开发。

常用 handoff 命令：

```bat
python tools\handoff.py init --workspace contract_review
python tools\handoff.py validate
python tools\handoff.py advance
python tools\handoff.py archive --label reviewed
```

## 状态码

| status | 含义 | 影刀动作 |
| --- | --- | --- |
| `success` | 处理成功 | 继续后续流程 |
| `warning` | 有业务跳过或非阻断异常 | 记录后继续 |
| `retryable_error` | 可重试系统异常 | 延迟后重试 |
| `pending_fix` | 需要修复的系统问题 | 停止并进入修复闭环 |
| `failed` | 不可恢复失败 | 停止并通知人工 |
| `locked` | 并发锁冲突 | 等待后重试；runner 默认先等待 5 秒 |
| `fatal` | 入口、配置或输入级错误 | 停止并通知维护 |
