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
