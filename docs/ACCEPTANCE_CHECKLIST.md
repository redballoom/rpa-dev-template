# 验收清单

每次修改 Code 项目前按此清单验收。

## 输入契约

- 推荐输入文件命名为 `input_{run_id}.json`，并位于项目根目录。
- 输入信封包含 `schema_version: "1.0"`。
- 固定 `input.json` 仅允许单实例串行流程使用。
- 业务差异集中在 `payload`。
- 业务输入文件位于 `data/input/` 或 `payload` 明确指定的位置。
- `run_id` 不写入输入文件，由影刀或 BAT 通过命令行传入。
- 未传 `input_file`、版本不受支持或任务结构不合法时，`runner.py` 返回 `fatal`。
- `context.env=prod` 时应按生产环境处理；`context.env=test/dev/local/staging` 时不创建生产工单。

## 输出契约

- `runner_{run_id}.json` 默认输出到项目根目录。
- 业务输出写入 `data/output/`。
- 日志写入 `logs/`。
- 系统异常快照写入 `crash_snapshots/`。
- 影刀 `RunEvidence` 能读取并记录 `runner_{run_id}.json`；如业务依赖状态分支，已另行验证影刀显式分支，而不是假设观察器会传播失败。
- `evidence/runs/{run_id}.summary.json` 已生成，并通过 `.venv\Scripts\python.exe tools\evidence.py` 校验。
- 摘要只包含白名单字段；原始输入、runner、日志、snapshot 和业务输出仍未提交。

## 代码

- `runner.py` 支持 `--run_id`、`--repo_path`、`--input_file`、`--work_dir`、`--project`，其中前四项为命令行必填。
- `run.bat` 只使用项目 `.venv`，缺失时明确失败；摘要入口标记为 `run.bat`。
- 输入文件使用标准 `tasks` 数组格式，`type` 决定路由。
- 业务代码不硬编码影刀临时路径。
- 输入上下文不能覆盖命令行确定的 `repo_path`、`project` 和 `run_id`。
- 业务输出路径经过校验并保持在 `data/output/`。
- 飞书、Linear 和 AI 只有在 `integrations.<name>.enabled=true` 时才访问外部服务。
- `retryable_error` 没有被影刀误解为整次运行自动重放指令。
- 需要重试的业务已经说明 Python 内部重试范围、上限、退避、幂等与断点恢复策略。
- 密钥、webhook、账号信息不写死在模板代码中。

## 文档

- README 与当前运行契约一致。
- 根目录 `ARCHITECTURE.md` 已与实际 `xbot_robot` 流程、变量和开关核对。
- 接口示例与 `runner.py` 实际行为一致。
- 需求模板、修复流程、职责边界文档没有仍要求强制旧输入文件名。

## 验证

- 至少做语法检查。
- 重要业务变更补测试。
- 不能运行测试时，需要说明原因和剩余风险。
