# 问题修复闭环

当影刀运行后发现 Python 业务处理失败，按此流程交给 AI 或人工修复。

## 触发条件

- `runner_{run_id}.json.status == "pending_fix"`
- `runner_{run_id}.json.status == "fatal"`
- 同类 `warning` 高频出现并影响业务稳定性
- 业务输出文件缺失、字段错误、数据不符合预期

`locked` 可由影刀等待后重试，因为尚未取得 Python 执行锁。`retryable_error` 只说明错误具有暂时性，影刀默认不重放整个 `tasks[]`；应由具体 Python handler/service 按业务契约执行有限重试、断点恢复或转人工处理。重复失败再进入代码或依赖排查。

## 证据包

修复前尽量收集：

- 本次运行的输入文件，例如 `input_{run_id}.json`
- `runner_{run_id}.json`
- `logs/run_{run_id}.log`
- `crash_snapshots/crash_{run_id}.json`
- `data/input/` 中的脱敏样本
- `data/output/` 中的错误输出或缺失说明

## AI 修复步骤

1. 阅读 `docs/SHADOWBOT_INPUT_CONTRACT.md` 和 `docs/RPA_PYTHON_BOUNDARY.md`。
2. 读取本次运行的输入文件，确认 `payload` 字段含义。
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
