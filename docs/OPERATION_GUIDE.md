# 调度工作模式与人机配合说明

本文档用于后续使用本模板时快速对齐：影刀、Python、AI 分别做什么，调度怎么跑，哪些地方和旧约定不同，以及哪些小错误最容易踩坑。

## 当前工作模式

本项目是影刀 RPA 调度的 Python Code 模板，不是具体业务项目。

整体职责：

- 影刀负责页面操作、登录、下载、上传、人工确认、生成输入文件、调用 `run.bat` 或 `runner.py`。
- Python 负责读取结构化输入、执行可测试的业务逻辑、写业务输出、分类异常、生成 `runner_{run_id}.json`。
- AI 负责在本 Code 项目内实现和维护 Python 业务 handler、测试、示例输入和文档。

默认原则：

- 影刀流程保持薄，不承载复杂业务规则。
- Python 承载可复现、可测试、可沉淀的规则。
- AI 不在未确认输入输出契约前直接写真实业务 handler。

## 一次运行的标准流程

1. 影刀生成本次运行 ID，例如 `1782039800`。
2. 影刀准备业务文件，通常放到 `data/input/`。
3. 影刀生成本次独立输入文件，推荐命名为 `input_{run_id}.json`。
4. 影刀调用：

```bat
run.bat {run_id} {work_dir} {input_file}
```

示例：

```bat
run.bat rpa_20260619_001 C:\RPA\Demo\data C:\RPA\Demo\input_rpa_20260619_001.json
```

5. `runner.py` 读取输入文件，按 `tasks[].type` 路由到对应 handler。
6. Python 把业务输出写入 `data/output/`，并生成 `runner_{run_id}.json`。
7. 影刀读取 `runner_{run_id}.json.status`，按状态码决定继续、重试、告警或进入修复闭环。

## 输入文件怎么写

推荐结构：

```json
{
  "project": "业务项目名",
  "tasks": [
    {
      "id": "task-001",
      "name": "任务显示名",
      "type": "your_task_type",
      "payload": {
        "input_file": "data/input/source.xlsx",
        "output_file": "data/output/result.xlsx"
      }
    }
  ],
  "context": {
    "operator": "yingdao",
    "env": "test",
    "source": "shadowbot",
    "app_name": "业务项目名"
  }
}
```

关键约定：

- `run_id` 不写入输入文件，由命令行参数传入。
- 即使输入文件里出现顶层 `run_id`，Python 也会忽略它。
- `tasks[].type` 是业务路由键，新增业务能力时必须实现对应 handler。
- `payload` 是业务参数区，handler 只能从这里读取业务输入。
- 路径字段如果是相对路径，默认以项目根目录为基准。

## 与旧约定相比的变化

这次优化后，需要特别注意以下变化：

- 推荐输入文件从固定 `input.json` 改为 `input_{run_id}.json`，避免并发运行时互相覆盖。
- 固定 `input.json` 仍兼容，但只适合单实例串行运行。
- `run_id` 只认命令行参数，不再允许输入文件覆盖。
- 并发锁拿不到时，runner 会先等待 5 秒，再返回 `locked`。
- Linear 工单是否创建优先看 `context.env`，不是只看 Git 分支。
- `context.env=prod` 或 `production` 时按生产环境处理。
- `context.env=test/dev/local/staging` 时不创建生产工单。
- 系统异常默认仍中断后续任务，但可以通过 `context.fail_fast=false` 支持独立批任务继续执行。
- 单个任务也可以设置 `continue_on_error=true`，允许该任务失败后继续后续任务。
- AI 分析默认关闭。启用时必须在本地 `project.json` 配置 `base_url`、`api_key`、`model` 和 `api_format`。
- `ai.api_format` 支持 `chat_completions` 与 `responses`；`base_url` 只填写 API 根地址，例如 `https://api.openai.com/v1`，不要附加 endpoint。

OpenAI-compatible Chat Completions 代理示例：

```json
{
  "ai": {
    "enabled": true,
    "base_url": "https://proxy.example.com/v1",
    "api_key": "local-secret",
    "model": "model-name",
    "api_format": "chat_completions",
    "timeout": 30
  }
}
```

DashScope/Qwen 可参考 `docs/examples/project.dashscope.example.json`。使用时复制到本地 `project.json`，只在本地填入真实 `ai.api_key`、`linear.api_key` 和 `linear.team_id`，不要提交真实密钥。

Responses API 代理只需将格式切换为：

```json
{
  "ai": {
    "api_format": "responses"
  }
}
```

程序会按格式分别请求 `/chat/completions` 或 `/responses`。兼容代理若返回 Chat Completions 的 `choices[].message.content`、Responses 顶层 `output_text`，或 `output[].content[].text`，都会归一化为同一种文本分析结果。

## 状态码与影刀动作

| status | 含义 | 影刀建议动作 |
| --- | --- | --- |
| `success` | 全部成功 | 继续后续流程 |
| `warning` | 有业务跳过，无系统错误 | 记录明细后继续 |
| `retryable_error` | 全部系统错误都可重试 | 延迟后重试 |
| `pending_fix` | 存在不可重试系统问题 | 停止，进入修复闭环 |
| `locked` | 并发锁冲突 | 等待后重试 |
| `fatal` | 入口、配置或输入级错误 | 停止并通知维护 |

注意：

- 影刀只消费 `runner_{run_id}.json`，不要解析 Python 堆栈。
- `retryable_error` 和 `locked` 优先由影刀重试，不应直接让 AI 改代码。
- `pending_fix` 才是典型的代码修复入口。

## 批任务是否继续执行

默认模式是保守的：

```json
"context": {
  "fail_fast": true
}
```

默认行为：

- `BusinessException` 记为 warning，继续后续任务。
- `SystemException` 记为 error，并中断后续任务。

独立批任务可以改成：

```json
"context": {
  "fail_fast": false
}
```

适用场景：

- 50 个 Excel 文件独立处理。
- 第 3 个文件坏了，不应该影响第 4 到第 50 个。
- 最终仍会返回 `pending_fix` 或 `retryable_error`，但结果里会保留更多已执行任务的明细。

谨慎使用场景：

- 后一个任务依赖前一个任务输出。
- 失败后继续执行可能导致重复上传、重复写入或数据污染。
- 不确定任务依赖关系时，保持默认 `fail_fast=true`。

## AI 接到业务需求时怎么配合

推荐流程：

1. 用户说明业务目标和影刀已经完成的动作。
2. AI 先拟定 `input_{run_id}.json` 的 `tasks[].type`、`payload`、输出文件、异常语义和验收标准。
3. 用户确认输入输出契约。
4. AI 再实现 handler、补示例输入、补测试、更新文档。
5. AI 执行测试，说明 `runner_{run_id}.json.status` 的预期结果。

不要跳过第 2 和第 3 步。这个模板的核心是契约优先：先确定影刀给什么、Python 出什么，再写业务代码。

项目安装 Trellis 时，本地进度优先保存在当前 task：

- `task.json.meta.progress`：当前 Gate、当前工作、最近检查点、下一步、责任方和阻塞信息。
- `progress.md`：任务内追加式检查点历史。
- PRD、Design、Implement：需求、契约和计划。
- Git、runner：代码和运行证据。

每个 Gate 或关键里程碑完成时，AI 应先显式询问：

```text
当前 Gate 是否验收通过，并记录到 Trellis？
```

用户确认后，先更新并回读 Trellis 本地进度，再推进到下一 Gate。配置了项目管理 Base 时，再询问是否同时同步 Base 的 `当前Gate`、`下一步建议` 和对应里程碑事件。

没有 Base 的项目仍可完成需求、开发、联调、验收和归档。不要因为代码、测试或 runner 已通过，就跳过本地进度记录；也不要因为缺少 Base 链接而阻塞本地闭环。

`当前Gate` 表示当前等待关闭的 Gate。阻塞是独立属性：保持 Gate 不变，记录阻塞原因、责任方和解除条件，不要用一个通用“阻塞 Gate”覆盖真实进度。

## Skill 在哪个环节使用

配套 Skills 维护在独立远程仓库：`https://github.com/redballoom/rpa-dev-template-skills`。

它们不是业务代码，而是帮助 AI 按正确顺序使用模板。初始化 Skill 在项目创建前使用；业务接入、修复和交付收尾 Skill 在项目创建后配合本模板文档使用。

| 阶段 | 使用 Skill | 目标 |
| --- | --- | --- |
| 初始化项目 | `rpa-project-bootstrap` | 从远程模板创建干净项目，替换项目身份，清理密钥，执行核心自检 |
| 新业务接入 | `rpa-contract-business` | 先拟定 `tasks[].type`、`payload`、输出和异常语义，用户确认后再写代码 |
| 运行失败修复 | `rpa-fix-loop` | 读取 `runner_{run_id}.json`、日志和快照，判断边界后修复并测试 |
| 本地检查点 / Gate关闭 / 交付收尾 | `rpa-delivery-close` | 记录 Trellis 本地进度，按用户验收推进 Gate，并在配置时投影到 Base；业务验收后校准 Git、runner、影刀结果 |

理想配合方式：

- 人负责提供业务目标、确认契约、决定是否上线或合并。
- Skill 负责约束 AI 的工作顺序。
- AI 负责实现、测试、解释风险。
- 模板负责稳定输入输出、异常语义和运行产物。

交付收尾 Skill 可以读取和更新 Trellis 等外部 Harness 的任务证据，但这些工具不是模板运行依赖。`run.bat`、`runner.py` 和业务 handler 不应为了进度记录或交付归档而依赖任何 Agent 状态文件。

## 新会话如何恢复项目

项目使用 Trellis 时，AI 按以下顺序恢复：

1. 当前 task 或用户指定 task 的 `task.json`。
2. `task.json.meta.progress` 当前快照。
3. task 目录中 `progress.md` 的最后一个检查点。
4. PRD、Design、Implement。
5. 最近 Git 提交和相关 `runner_{run_id}.json`。

恢复后应能直接回答当前 Gate、最近完成内容、下一步、责任方、阻塞和证据。飞书 Base 可以展示这些摘要，但不是恢复项目的必要条件。

## 初始化和升级后的自检

为了让模板满足可复用、可迁移、可升级，项目根目录提供了机器可读的运行契约和自检脚本：

- `VERSION`：模板版本。
- `schemas/input.schema.json`：影刀输入文件 Schema。
- `tools/doctor.py`：检查模板底座是否完整。

新项目初始化后、模板升级后、或把项目迁移到另一台电脑后，先运行：

```bat
python tools\doctor.py
```

通过后再进入业务契约阶段。若失败，优先修复自检报告中的必需文件、JSON 结构、忽略规则或本机绝对路径问题。

模板不强制安装特定 Agent/Harness。使用 Trellis 时，推荐以上本地进度契约；使用其他 Harness 时应提供等价的当前快照、检查点历史和证据引用。这些工具不得成为 `run.bat`、runner 或业务代码的运行依赖。

## 最容易犯的小错误

- 把 `run_id` 写进输入文件，并期望它覆盖命令行参数。
- 多个影刀流程共用同一个固定 `input.json`。
- 新增了 `tasks[].type`，但没有实现对应 handler。
- handler 根据 `task.name` 分支，而不是根据 `task.type` 分支。
- 把真实密钥、cookie、webhook 写进模板代码或提交到仓库。
- 把可测试的字段映射、清洗规则、判断逻辑塞回影刀 UI 流程。
- 生产运行时调用 `git_controller.py` 切分支。
- `context.env` 漏填，导致工单环境判断只能退回 Git 分支。
- 使用 `fail_fast=false` 处理有依赖关系的任务。
- 工作已完成，但没有更新本地 Gate、下一步和责任方。
- 把 Base 当成唯一进度源，导致离线或无权限时无法恢复项目。

## 使用前检查

每次接入新业务前至少确认：

- 输入文件是否使用 `input_{run_id}.json` 或其他本次运行独立路径。
- 命令行 `run_id` 是否和期望输出 `runner_{run_id}.json` 一致。
- `context.env` 是否明确填写 `test` 或 `prod`。
- `tasks[].type` 是否已有 handler。
- `payload` 的每个字段是否说明了含义、必填性、默认值和路径规则。
- 业务输出是否写到 `data/output/`。
- 影刀是否处理 `locked` 和 `retryable_error` 的重试分支。
- 修改后是否执行 `python -m pytest tests/ -v`。
