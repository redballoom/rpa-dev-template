# 问题修复闭环

当影刀运行后发现 Python 业务处理失败，按此流程交给 AI 或人工修复。

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

## AI 修复步骤

1. 阅读 `docs/SHADOWBOT_INPUT_CONTRACT.md` 和 `docs/RPA_PYTHON_BOUNDARY.md`。
2. 读取 `input.json`，确认 `payload` 字段含义。
3. 复现问题或构造最小复现样例。
4. 修改 Python 业务代码，不默认修改影刀流程。
5. 补充或更新测试、示例输入和文档。
6. 给出验证方式和剩余风险。

## 修复完成定义

- 问题原因明确。
- Code 项目代码已修复。
- 业务输出符合预期。
- `runner_{run_id}.json.status` 符合约定。
- 文档和示例与代码保持一致。
