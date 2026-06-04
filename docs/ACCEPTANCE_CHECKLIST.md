# 验收清单

每次修改 Code 项目前按此清单验收。

## 输入契约

- `input.json` 位于项目根目录。
- 业务差异集中在 `payload`。
- 业务输入文件位于 `data/input/` 或 `payload` 明确指定的位置。
- `run_id` 不强制写入 `input.json`，可由影刀或 BAT 通过命令行传入。
- 未传 `input_file` 时，`runner.py` 不读取 `input.json`。

## 输出契约

- `runner_{run_id}.json` 默认输出到项目根目录。
- 业务输出写入 `data/output/`。
- 日志写入 `logs/`。
- 系统异常快照写入 `crash_snapshots/`。
- 影刀只依赖 `runner_{run_id}.json` 做流程分支。

## 契约优先验收

- 已有任务设计说明，且 `tasks[].type` 与实现路由一致。
- `payload` 字段说明与示例输入一致。
- handler 职责说明能映射业务路径。
- `results[].data` 摘要字段稳定、可供影刀或人工审查。
- warning / error 场景与异常类型一致。
- 人工验收、推送、合并、上线节点没有被自动化替代。

## 代码

- `runner.py` 支持 `--run_id`、`--repo_path`、`--input_file`、`--work_dir`、`--project`。
- `input.json` 使用标准 `tasks` 数组格式，`type` 决定路由。
- 业务代码不硬编码影刀临时路径。
- 密钥、webhook、账号信息不写死在模板代码中。

## 文档

- README 与当前运行契约一致。
- 接口示例与 `runner.py` 实际行为一致。
- 需求模板、修复流程、职责边界文档没有仍要求强制旧输入文件名。

## 验证

- 至少做语法检查。
- 重要业务变更补测试。
- 不能运行测试时，需要说明原因和剩余风险。
