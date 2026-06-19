# 问题修复闭环

当影刀运行后发现 Python 业务处理失败，按此流程交给 AI 或人工修复。

## 目标

当 Python 运行返回 `pending_fix` 或不可恢复的系统异常时，模板应提供足够上下文，让 AI 可以接手定位、修复、验证，并把结果交回人工验收。

## 触发条件

- `runner_{run_id}.json.status == "pending_fix"`
- `runner_{run_id}.json.status == "fatal"`
- `runner_{run_id}.json.status == "failed"`
- 同类 `warning` 高频出现并影响业务稳定性
- 业务输出文件缺失、字段错误、数据不符合预期

`retryable_error` 和 `locked` 优先由影刀重试，不直接进入代码修复，除非重复失败。

## 证据包

修复前尽量收集：

- `input.json`
- `runner_{run_id}.json`
- `logs/run_{run_id}.log`
- `crash_snapshots/crash_{run_id}.json`
- `data/input/` 中的脱敏样本
- `data/output/` 中的错误输出或缺失说明

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
| `fix_target` | 修复目标：`python`、`rpa` 或 `upstream` |
| 业务输入文件 | 位于 `data/input/` 或 payload 指定路径 |

## 修复目标分支

| `fix_target` | 含义 | 处理方式 |
| --- | --- | --- |
| `python` | Python 代码、payload 校验、数据处理或重试降级可修复 | AI 可进入代码修复流程 |
| `rpa` | 影刀流程、下载上传、选择器、人工操作或路径准备问题 | 优先检查影刀流程，AI 不默认修改 Python |
| `upstream` | 上游数据源、第三方系统或外部负责人问题 | 联系上游或等待外部恢复 |

## AI 修复步骤

1. 阅读 `docs/SHADOWBOT_INPUT_CONTRACT.md` 和 `docs/RPA_PYTHON_BOUNDARY.md`。
2. 读取 `input.json`，确认 `payload` 字段含义。
3. 复现问题或构造最小复现样例。
4. 读取 `runner_{run_id}.json.data.errors[].fix_target` 或 crash snapshot 中的 `fix_target`。
5. 仅当 `fix_target=python` 时进入 Python 代码修复；`rpa` 或 `upstream` 应先说明非 Python 处理动作。
6. 补充或更新测试、示例输入和文档。
7. 给出验证方式和剩余风险。

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

## 修复完成定义

- 问题原因明确。
- Code 项目代码已修复。
- 业务输出符合预期。
- `runner_{run_id}.json.status` 符合约定。
- 文档和示例与代码保持一致。
