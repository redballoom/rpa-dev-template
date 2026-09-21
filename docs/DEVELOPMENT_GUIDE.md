# Python 业务开发指南

## 分层

- `core/entry.py`：只根据 `tasks[].type` 路由并汇总状态。
- `core/handlers/`：校验 payload、编排步骤、返回业务摘要。
- `core/services/`：浏览器、HTTP、飞书、数据库、持久化状态和可复用领域逻辑。
- `core/infrastructure/`：与具体业务无关的路径、写入、脱敏等能力。

简单需求也应创建一个小 handler，不要继续扩大 `entry.py`。当 handler 出现外部系统、多步骤重试、断点恢复或明显复用时，再拆 service。

## Handler 契约

```python
def process_your_task(task, context):
    payload = task.get("payload") or {}
    repo_path = context["repo_path"]
    run_id = context["run_id"]
    project = context["project"]
    # 校验 -> 调用 service -> 写输出 -> 返回摘要
```

`repo_path`、`run_id` 和 `project` 由运行入口强制注入，不能相信输入文件中的同名字段。业务参数只能从 `task["payload"]` 读取。

## 文件规则

- 输入默认位于 `data/input/`。
- 输出必须位于 `data/output/`。
- 默认输出名包含 `run_id`，例如 `data/output/result_{run_id}.json`。
- 使用 `resolve_project_path()` 防止绝对路径、`..` 或目录逃逸。
- JSON 使用 `atomic_write_json()` 写入，避免中断后留下半文件。

## 两种推荐模式

普通处理型：handler 完成校验、转换和一次性输出。

可恢复批处理型：handler 负责批次编排，service 负责外部调用和持久化状态；状态文件或 SQLite 放在运行时目录，不提交仓库。每条记录应有稳定业务键、尝试次数和最终状态。

## 重试设计

`SystemException(retryable=True)` 只表示错误具有暂时性，不表示整个 `tasks[]` 可以安全重复执行。

- 优先在 service 内重试最小的失败调用，不重新执行已经成功的业务步骤。
- 重试必须设置最大次数、退避和超时。
- 有副作用的操作必须使用稳定业务键、幂等键、upsert 或完成状态记录。
- 无法证明安全时，返回 `retryable_error` 供记录和人工判断，但不要要求影刀自动重跑 BAT。
- 只有业务契约明确声明整次运行可重复时，影刀才可以重放。

## 外部集成

飞书通知、Linear 工单和 AI 分析均默认关闭。它们是旁路增强，不是业务成功条件。外发前会对常见 secret、token、cookie、webhook 和 API key 字段脱敏，但业务代码仍不得把凭据放入 payload 或异常消息。

## 最低测试

- 正常成功。
- 业务 warning。
- 系统异常或外部依赖失败。
- 输出路径越界。
- 涉及批处理时测试恢复、重复执行和部分失败。
