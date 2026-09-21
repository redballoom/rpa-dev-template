# 项目结构与执行流程

## 目录结构

```text
开发模板/
  ARCHITECTURE.md
  runner.py
  run.bat
  project.json
  project.template.json
  input_{run_id}.json
  core/
    entry.py
    handlers/
      calc_summary.py
    services/
    infrastructure/
      files.py
      redaction.py
    config.py
    exceptions.py
    logger.py
    notifier.py
    ai_analyzer.py
  data/
    input/
    output/
    temp/
  logs/
  crash_snapshots/
  evidence/
    runs/
  docs/
  schemas/
    input.schema.json
  tools/
    doctor.py
  tests/
```

`input_{run_id}.json` 是推荐的单次业务输入命名，用于并发隔离。固定 `input.json` 仅作为单实例串行兼容写法。
`data/` 是业务文件目录。  
`runner_{run_id}.json` 默认输出在项目根目录。

`entry.py` 只负责路由和汇总；`handlers/` 负责业务编排；`services/` 负责外部系统与可复用领域能力；`infrastructure/` 提供安全路径、原子写入、脱敏等通用底座。

`schemas/input.schema.json` 负责给影刀输入提供机器可读约束。`tools/doctor.py` 用于初始化、迁移和升级后的模板核心自检。Agent 的任务、阶段和记忆由外部工具管理，不属于模板运行架构，也不影响运行行为。

## 执行流程

```text
影刀准备业务数据
  -> 写 input_{run_id}.json
  -> 调用 run.bat（runner.py 仅用于本地诊断）
  -> runner.py 读取 input_file
  -> core.entry.run_tasks() 按 tasks[].type 路由
  -> core.handlers 编排 core.services
  -> 写业务输出到 data/output/
  -> 写 runner_{run_id}.json
  -> 写 evidence/runs/{run_id}.summary.json
  -> 影刀 RunEvidence 读取 status 并记录
```

当前影刀模板不会把 Python 非成功状态自动转成影刀主流程失败。影刀可以显式处理停止和告警，但默认只对 `locked` 等尚未开始业务执行的场景自动重试；`retryable_error` 的重试范围由 Python 业务设计决定。影刀侧完整编排与已知限制见根目录 `ARCHITECTURE.md`。

## 输入模式

生产调用（三个位置参数均必填）：

```bat
run.bat rpa_001 C:\CodePJ\Demo\data C:\CodePJ\Demo\input_rpa_001.json
```

本地诊断仍使用同一输入契约：

```bat
.venv\Scripts\python.exe runner.py --run_id rpa_001 --repo_path C:\CodePJ\Demo --work_dir C:\CodePJ\Demo\data --input_file C:\CodePJ\Demo\input_rpa_001.json
```

## 设计原则

- 影刀流程保持薄，只做调度和 UI 自动化。
- Python 业务逻辑可测试、可复现、可沉淀。
- `payload` 是业务变化入口。
- `repo_path`、`project` 和 `run_id` 由运行入口注入，输入 `context` 不得覆盖。
- 新业务 handler 应将输出限制在 `data/output/`，默认文件名包含 `run_id`，关键 JSON 使用原子写入；payload 明确指定文件名时以业务契约为准。
- 输出协议稳定，便于影刀分支和 AI 修复。
