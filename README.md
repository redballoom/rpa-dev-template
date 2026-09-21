# RPA Python 开发模板

这是影刀 RPA 调度的 Python Code 项目模板。影刀负责页面操作、文件准备和调度；Python 负责稳定的业务处理、日志、异常分类和标准结果输出；AI 负责在 Code 项目内实现和维护业务代码。

## 当前契约

影刀生产流程通过 `run.bat` 启动本项目。直接调用 `runner.py` 仅用于本地诊断和测试，并且必须提供与 BAT 相同的 `run_id`、`work_dir` 和 `input_file`。

```bat
run.bat {run_id} {work_dir} {input_file}
```

三个位置参数均为必填。`input_file` 应指向本次运行独立的 `input_{run_id}.json`；缺失、不可读、版本不受支持或任务结构不合法时，runner 返回 `fatal`。固定文件名 `input.json` 只保留为旧单实例流程的兼容命名，最新影刀模板不使用它。

生产入口只使用项目 `.venv\Scripts\python.exe`。虚拟环境不存在时 `run.bat` 直接失败，不回退系统 Python。

默认输出：

- `runner_{run_id}.json`：输出到项目根目录。
- `evidence/runs/{run_id}.summary.json`：可提交/上传的脱敏运行摘要，包含 commit、真实入口、解释器、计数和输入/runner 哈希。
- `logs/run_{run_id}.log`：Python 运行日志。
- `crash_snapshots/crash_{run_id}.json`：系统异常快照。
- `data/`：业务输入、业务输出和临时文件目录。

## 推荐输入结构

推荐将 `input_{run_id}.json` 放在项目根目录，业务文件放在 `data/` 下。

```json
{
  "schema_version": "1.0",
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
| [ARCHITECTURE.md](ARCHITECTURE.md) | 已按实际 `xbot_robot` 核对的影刀侧流程、开关、证据与已知限制 |
| [docs/SHADOWBOT_INPUT_CONTRACT.md](docs/SHADOWBOT_INPUT_CONTRACT.md) | 影刀输入文件、`payload`、`data/` 输入输出约定 |
| [docs/OPERATION_GUIDE.md](docs/OPERATION_GUIDE.md) | 调度工作模式、使用方式和人机配合注意事项 |
| [docs/DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md) | `handlers/services/infrastructure` 分层和安全路径写入规范 |
| [docs/UPGRADE_GUIDE.md](docs/UPGRADE_GUIDE.md) | 旧项目升级到当前模板时的边界和步骤 |
| [docs/RPA_PYTHON_BOUNDARY.md](docs/RPA_PYTHON_BOUNDARY.md) | 影刀、Python、AI 的职责边界 |
| [docs/INTERFACE_EXAMPLES.md](docs/INTERFACE_EXAMPLES.md) | 输入输出协议示例 |
| [docs/REQUIREMENT_TEMPLATE.md](docs/REQUIREMENT_TEMPLATE.md) | 给 AI 开发业务代码时的需求模板 |
| [docs/ISSUE_FIX_WORKFLOW.md](docs/ISSUE_FIX_WORKFLOW.md) | 运行失败后的修复闭环 |
| [docs/ACCEPTANCE_CHECKLIST.md](docs/ACCEPTANCE_CHECKLIST.md) | 修改和上线前验收清单 |
| [docs/PORTABLE_RUN_EVIDENCE.md](docs/PORTABLE_RUN_EVIDENCE.md) | 可迁移脱敏证据的字段白名单、哈希和复核方式 |
| [docs/PROJECT_ARCHITECTURE_OVERVIEW.md](docs/PROJECT_ARCHITECTURE_OVERVIEW.md) | 项目结构和执行流程 |
| [schemas/input.schema.json](schemas/input.schema.json) | 影刀输入文件的机器可读 Schema |
| [schemas/output.schema.json](schemas/output.schema.json) | `runner_{run_id}.json` 统一信封的机器可读 Schema |
| [schemas/evidence-summary.schema.json](schemas/evidence-summary.schema.json) | 可迁移脱敏证据摘要 Schema |
| [tools/doctor.py](tools/doctor.py) | 跨机器初始化后的模板自检脚本 |

## 推荐协作方式

1. 影刀准备业务文件和参数，写入 `input_{run_id}.json` 的 `tasks[].payload`。
2. 影刀调用 `run.bat`，传入本次运行独立的 `input_file`。
3. Python 读取输入、执行业务、写入业务输出到 `data/output/`。
4. Python 输出 `runner_{run_id}.json`。
5. Python 同时输出 `evidence/runs/{run_id}.summary.json`；原始 runner 保持私有，摘要可用于跨机器复核。
6. 影刀的 `RunEvidence` 读取并记录 `runner_{run_id}.json` 的状态，不直接解析 Python 堆栈。当前影刀模板不会把 Python 非成功状态自动转成影刀主流程失败；若业务需要停止、重试或告警，必须在影刀侧增加显式状态分支。
7. AI 后续只在 Code 项目内修改 Python 业务代码、测试和文档，默认不改影刀 UI 流程。

## 可迁移与升级底座

模板包含一组机器可读的工程文件，用于让不同电脑、不同 Agent 和不同项目之间保持一致。模板不维护 Agent 项目状态机；任务、记忆和会话流程由使用者选择的 Agent 或 Harness 管理。

- `VERSION`：当前模板版本。
- `schemas/input.schema.json`：约束影刀输入文件的基本结构。
- `schemas/output.schema.json`：约束 runner 输出的统一控制字段，业务结果保留在 `data.results[].data`。
- `schemas/evidence-summary.schema.json`：封闭白名单的可迁移运行证据契约。
- `tools/doctor.py`：初始化或升级后运行，检查必需文件、JSON、模板版本、运行产物忽略规则和本机路径污染。

推荐在新项目初始化后执行：

```bat
python tools\doctor.py
```

如果 `doctor` 返回 `failed`，先修复底座问题，再进入业务契约和 handler 开发。

外部 Agent、Skill 或项目管理工具可以辅助开发，但不是运行依赖，也不得改变 `run.bat → runner.py → core.entry` 的行为。

## 可选外部集成

飞书通知、Linear 工单和 AI 分析均保留，但默认关闭。只有在本地 `project.json` 中把对应 `integrations.<name>.enabled` 显式设为 `true` 时才会访问外部服务。示例与注意事项见 `docs/OPERATION_GUIDE.md`。

## 状态码

| status | 含义 | 影刀动作 |
| --- | --- | --- |
| `success` | 处理成功 | 继续后续流程 |
| `warning` | 有业务跳过或非阻断异常 | 记录后继续 |
| `retryable_error` | 错误具有暂时性，但不代表整个运行可安全重放 | Python 按业务设计处理；影刀默认停止并记录 |
| `pending_fix` | 需要修复的系统问题 | 停止并进入修复闭环 |
| `locked` | 并发锁冲突 | 等待后重试；runner 默认先等待 5 秒 |
| `fatal` | 入口、配置或输入级错误 | 停止并通知维护 |

`data.retryable=true` 只描述错误性质，不授权影刀自动重放整个 `tasks[]`。除 `locked` 等确认尚未进入业务执行的场景外，是否重试、重试哪一步以及如何保证幂等，由具体 Python handler/service 设计决定。
